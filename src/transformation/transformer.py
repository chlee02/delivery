import os
import sys
import re
import json
import hashlib
from datetime import datetime
import pandas as pd
from sqlalchemy import or_, and_
from dotenv import load_dotenv

# 프로젝트 루트를 Python path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.connection import db_manager
from src.db.models import Shop, RefinedShop

load_dotenv()

class DataTransformer:
    """수집된 Raw 상점 데이터를 정제하고 샵인샵을 식별하는 엔진 (증분 및 범위 기반 분석 지원)"""

    def __init__(self):
        self.session = db_manager.get_session()

    def _extract_address_components(self, law_detail, custom_detail):
        """법정상세주소와 커스텀상세주소에서 지번, 건물명, 층, 호수를 추출하고 나머지는 메타데이터로 반환합니다."""
        law_detail = law_detail or ""
        custom_detail = custom_detail or ""
        
        combined_raw = f"{law_detail} {custom_detail}".strip()
        metadata_parts = re.findall(r'\((.*?)\)', combined_raw)
        clean_text = re.sub(r'\(.*?\)', '', combined_raw).strip()
        
        jibun_match = re.match(r'^([\d-]+)', clean_text)
        jibun = jibun_match.group(1) if jibun_match else ""
        if jibun:
            clean_text = clean_text.replace(jibun, "", 1).strip()
        
        floor_pattern = r'((?:지하|지상|제지)?\s*[0-9B]+[층Ff])'
        f_match = re.search(floor_pattern, clean_text)
        floor = f_match.group(1).strip() if f_match else ""
        if floor:
            clean_text = clean_text.replace(f_match.group(0), "", 1).strip()
            
        room_pattern = r'([A-Z]?\s*-?\s*\d+호)'
        r_match = re.search(room_pattern, clean_text)
        room = r_match.group(1).strip() if r_match else ""
        if room:
            clean_text = clean_text.replace(r_match.group(0), "", 1).strip()

        building_pattern = r'([가-힣A-Za-z0-9]+(?:빌딩|타운|타워|프라자|아파트|상가|오피스텔|맨션|캐슬|(?<![\d-])\d+동))'
        b_match = re.search(building_pattern, clean_text)
        building = b_match.group(1).strip() if b_match else ""
        if building:
            clean_text = clean_text.replace(b_match.group(0), "", 1).strip()
        
        leftover = re.sub(r'\s+', ' ', clean_text).strip()
        all_metadata = []
        if metadata_parts:
            all_metadata.extend([f"({m})" for m in metadata_parts])
        if leftover:
            all_metadata.append(leftover)
            
        external_metadata = " ".join(all_metadata) if all_metadata else ""
        
        return jibun, building, floor, room, external_metadata

    def run_transformation(self):
        print("🔄 [Transformer] 증분 및 범위 기반 데이터 변환을 시작합니다...")
        
        try:
            # 1. 증분 처리 대상(Target) 선정
            targets = self.session.query(Shop).filter(
                or_(
                    Shop.last_transformed_at == None,
                    Shop.updated_at > Shop.last_transformed_at
                )
            ).all()

            if not targets:
                print("✅ [Transformer] 새로 변환할 데이터가 없습니다.")
                return

            print(f"📊 [Transformer] 총 {len(targets)}개의 신규/수정 데이터를 분석합니다.")

            target_biz_numbers = set()
            target_eupmyeondongs = set()
            target_ids = set()
            
            target_refined_info = []
            for t in targets:
                target_ids.add(t.id)
                jibun, bld, flr, room, leftover = self._extract_address_components(t.law_address_detail, t.custom_detailed_address)
                base_addr = f"{t.law_address_sido or ''} {t.law_address_sigungu or ''} {t.law_address_eupmyeondong or ''}".strip()
                biz_key = re.sub(r'[^0-9]', '', str(t.business_number or ""))
                biz_key = biz_key if len(biz_key) == 10 else ""
                
                if t.business_number:
                    target_biz_numbers.add(t.business_number)
                if t.law_address_eupmyeondong:
                    target_eupmyeondongs.add(t.law_address_eupmyeondong)
                
                target_refined_info.append({
                    "id": t.id,
                    "target_obj": t,
                    "name": t.name,
                    "raw_rating": t.raw_rating,
                    "review_count": t.review_count,
                    "has_review_event": t.has_review_event,
                    "address": base_addr,
                    "detailed_address": jibun,
                    "building_name": bld,
                    "floor": flr,
                    "room_number": room,
                    "lat": t.lat,
                    "lng": t.lng,
                    "category": t.category,
                    "business_number": t.business_number,
                    "biz_key": biz_key,
                    "external_metadata": leftover
                })

            # 2. 연관된 기존 데이터 로드 (Scoped Query)
            filter_conds = []
            if target_biz_numbers:
                filter_conds.append(Shop.business_number.in_(list(target_biz_numbers)))
            if target_eupmyeondongs:
                filter_conds.append(Shop.law_address_eupmyeondong.in_(list(target_eupmyeondongs)))
            
            related_shops = []
            if filter_conds:
                related_shops = self.session.query(Shop).filter(or_(*filter_conds)).all()

            print(f"🔗 [Transformer] 연관된 {len(related_shops)}개의 데이터를 로드하여 관계를 분석합니다.")

            all_data_for_analysis = []
            seen_ids = set()
            for r in target_refined_info:
                all_data_for_analysis.append(r)
                seen_ids.add(r['id'])
            
            for s in related_shops:
                if s.id in seen_ids: continue
                jibun, bld, flr, room, leftover = self._extract_address_components(s.law_address_detail, s.custom_detailed_address)
                base_addr = f"{s.law_address_sido or ''} {s.law_address_sigungu or ''} {s.law_address_eupmyeondong or ''}".strip()
                biz_key = re.sub(r'[^0-9]', '', str(s.business_number or ""))
                biz_key = biz_key if len(biz_key) == 10 else ""
                all_data_for_analysis.append({
                    "id": s.id,
                    "name": s.name,
                    "raw_rating": s.raw_rating,
                    "review_count": s.review_count,
                    "has_review_event": s.has_review_event,
                    "address": base_addr,
                    "detailed_address": jibun,
                    "building_name": bld,
                    "floor": flr,
                    "room_number": room,
                    "lat": s.lat,
                    "lng": s.lng,
                    "category": s.category,
                    "business_number": s.business_number,
                    "biz_key": biz_key,
                    "external_metadata": leftover
                })
            
            df = pd.DataFrame(all_data_for_analysis)

            # 3. 샵인샵 식별 (Union-Find)
            parent = {row['id']: row['id'] for _, row in df.iterrows()}
            def find(i):
                if parent[i] == i: return i
                parent[i] = find(parent[i])
                return parent[i]
            def union(i, j):
                root_i, root_j = find(i), find(j)
                if root_i != root_j: parent[root_i] = root_j

            for _, group in df[df['biz_key'] != ""].groupby('biz_key'):
                ids = group['id'].tolist()
                for k in range(1, len(ids)): union(ids[0], ids[k])
            
            match_cols = ['address', 'detailed_address', 'floor', 'room_number']
            for _, group in df.groupby(match_cols):
                if all(str(val).strip() == "" for val in _): continue
                ids = group['id'].tolist()
                for k in range(1, len(ids)): union(ids[0], ids[k])

            df['group_root'] = df['id'].apply(find)
            group_sizes = df.groupby('group_root')['id'].transform('count')
            df['is_shop_in_shop'] = group_sizes > 1
            df['sis_sibling_count'] = group_sizes - 1
            df['sis_group_id'] = df['group_root'].apply(lambda x: hashlib.md5(str(x).encode()).hexdigest()[:12])
            
            group_names = df.groupby('group_root')['name'].apply(list).to_dict()
            df['sis_sibling_names'] = df.apply(lambda r: ", ".join([n for n in group_names[r['group_root']] if n != r['name']]) if r['is_shop_in_shop'] else "", axis=1)

            # 4. 의심군(is_suspicious) 판별
            df['is_suspicious'] = False
            jibun_counts = df.groupby(['address', 'detailed_address'])['id'].transform('count')
            df.loc[(df['detailed_address'] != "") & (jibun_counts > 5), 'is_suspicious'] = True
            df.loc[(df['room_number'] == "") & (df['external_metadata'].str.contains('일부|외', na=False)), 'is_suspicious'] = True

            # 5. DB 적재 대상 확장: "타겟 상점" + "타겟과 같은 그룹인 기존 상점"
            affected_roots = set(df[df['id'].isin(target_ids)]['group_root'])
            update_ids = set(df[df['group_root'].isin(affected_roots)]['id'])
            
            print(f"💾 [Transformer] {len(update_ids)}개의 연관 데이터를 refined_shops에 업데이트합니다...")
            
            for _, row in df[df['id'].isin(update_ids)].iterrows():
                refined = self.session.query(RefinedShop).filter(RefinedShop.id == row['id']).first()
                if not refined:
                    refined = RefinedShop(id=row['id'])
                    self.session.add(refined)
                
                refined.name = row['name']
                refined.raw_rating = row['raw_rating']
                refined.review_count = row['review_count']
                refined.has_review_event = row['has_review_event']
                refined.address = row['address']
                refined.detailed_address = row['detailed_address']
                refined.building_name = row['building_name']
                refined.floor = row['floor']
                refined.room_number = row['room_number']
                refined.lat = row['lat']
                refined.lng = row['lng']
                refined.category = row['category']
                refined.business_number = row['business_number']
                refined.is_shop_in_shop = bool(row['is_shop_in_shop'])
                refined.is_suspicious = bool(row['is_suspicious'])
                refined.sis_group_id = row['sis_group_id'] if row['is_shop_in_shop'] else None
                refined.sis_sibling_count = int(row['sis_sibling_count'])
                refined.sis_sibling_names = row['sis_sibling_names']
                refined.external_metadata = row['external_metadata']

            # 6. 원본 상점 타임스탬프 업데이트 (Target만)
            for t_info in target_refined_info:
                t_info['target_obj'].last_transformed_at = datetime.utcnow()

            self.session.commit()
            print("✅ [Transformer] 증분 변환 작업이 완료되었습니다.")
            
        except Exception as e:
            self.session.rollback()
            print(f"❌ [Transformer] 오류 발생: {e}")
            raise
        finally:
            self.session.close()

if __name__ == "__main__":
    transformer = DataTransformer()
    transformer.run_transformation()
