import os
import sys
import time
import argparse
import random
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

# 프로젝트 루트를 Python path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.connection import db_manager
from src.db.models import Shop

# .env 파일 로드
load_dotenv()

# 리뷰 이벤트 감지 키워드 리스트
EVENT_KEYWORDS = ["리뷰", "이벤트", "리뷰약속", "뇌물", "서비스", "리뷰참여"]

# 요기요 API 엔드포인트 및 인증 헤더 (v3에서 검증된 스펙 사용)
BASE_URL = "https://api.yogiyo.co.kr/shopyo/v1"
HEADERS = {
    "x-api-key": os.getenv("YOGIYO_API_KEY", ""),
    "X-YGY-APP-VERSION": "9.0.0",
    "X-YGY-OS-TYPE": "IOS",
    "x-ygy-route": "v2",
    "Origin": "https://www.yogiyo.co.kr",
    "Referer": "https://www.yogiyo.co.kr/",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
}

# 기본 위경도 및 행정동 코드 (기본값: 서울 강남역 인근)
DEFAULT_COORDS = {
    "lat": "37.4941545",
    "lng": "127.03300871",
    "adm_code": "1168064000"
}

def generate_mock_data():
    """테스트 및 안전한 오프라인 개발을 위해 10개의 리얼한 모의 상점 데이터를 생성합니다."""
    print("🤖 [Mock Mode] 모의 상점 데이터를 생성하여 로컬 데이터베이스에 적재합니다...")
    
    # 신규 필드에 맞춰 모의 데이터 구조 업데이트 필요 시 여기서 수정
    mock_shops = [
        {
            "id": "mock_ygy_1001",
            "name": "할머니의 인생 제육 역삼점",
            "raw_rating": 4.9,
            "review_count": 842,
            "has_review_event": True,
            "law_address_sido": "서울",
            "law_address_sigungu": "강남구",
            "law_address_eupmyeondong": "역삼동",
            "law_address_detail": "역삼로 123",
            "custom_detailed_address": "지하 1층 102호 (공유주방 A)",
            "company_name": "제육천국",
            "category": "한식",
            "business_number": "120-11-22233"
        }
    ]
    
    session = db_manager.get_session()
    try:
        db_manager.create_tables()
        for shop_data in mock_shops:
            shop = session.query(Shop).filter(Shop.id == shop_data["id"]).first()
            if not shop:
                shop = Shop(id=shop_data["id"])
                session.add(shop)
            
            shop.name = shop_data["name"]
            shop.raw_rating = shop_data["raw_rating"]
            shop.review_count = shop_data["review_count"]
            shop.has_review_event = shop_data["has_review_event"]
            shop.law_address_sido = shop_data.get("law_address_sido")
            shop.law_address_sigungu = shop_data.get("law_address_sigungu")
            shop.law_address_eupmyeondong = shop_data.get("law_address_eupmyeondong")
            shop.law_address_detail = shop_data.get("law_address_detail")
            shop.custom_detailed_address = shop_data.get("custom_detailed_address")
            shop.company_name = shop_data.get("company_name")
            shop.category = shop_data["category"]
            shop.business_number = shop_data["business_number"]
            shop.updated_at = datetime.utcnow()
            
        session.commit()
        print(f"✅ [Mock Mode] 총 {len(mock_shops)}개의 모의 상점 적재 완료!")
    except Exception as e:
        session.rollback()
        print(f"❌ [Mock Mode] 적재 오류 발생: {e}")
        sys.exit(1)
    finally:
        session.close()

def run_real_scraper(limit, offset=0, lat=None, lng=None, adm_code=None):
    """API 직접 통신을 이용하여 실데이터를 수집하고 DB에 적재합니다."""
    
    # 행정동 코드 필수 검증
    if not adm_code:
        print("❌ [Error] 행정동 코드(adm_code)는 필수 항목입니다. 실행을 중단합니다.")
        sys.exit(1)
        
    # API 키 누락 검증
    if not os.getenv("YOGIYO_API_KEY"):
        print("⚠️ [Warning] YOGIYO_API_KEY 환경변수가 설정되지 않았습니다. 실시간 수집이 실패할 수 있습니다.")

    
    # 위치 정보 결정 (직접 입력 > 기본값)
    if lat and lng:
        coords = {"lat": lat, "lng": lng, "adm_code": adm_code}
        print(f"📍 직접 입력된 좌표 사용: {coords}")
    else:
        coords = DEFAULT_COORDS
        coords["adm_code"] = adm_code # 입력된 행정동 코드로 덮어쓰기
        print(f"📍 좌표 인자 미비로 기본값(강남역) 좌표와 입력된 행정동 코드를 사용합니다: {coords}")
    
    print(f"🚀 [API Scraper] 행정동 코드 '{adm_code}' 기준 수집을 가동합니다... ({offset}번째부터 최대 {limit}개)")
    
    # API 요청을 위한 공통 파라미터 세팅
    api_params = {
        "adm_code": coords["adm_code"],
        "customer_id": "925381195",
        "lat": coords["lat"],
        "lng": coords["lng"],
        "membership_code": "NONE",
        "vertical_types": "FOOD"
    }

    db_manager.create_tables()
    session = db_manager.get_session()

    # 1. 주변 상점 리스트 수집 API 호출
    list_url = f"{BASE_URL}/shops"
    list_params = api_params.copy()
    list_params.update({
        "length": str(limit),
        "start": str(offset),
        "sort": "RANK_DESC",
        "serving_types": "VD",
        "use_bargainyo": "false"
    })

    try:
        time.sleep(random.uniform(1.0, 2.0))
        response = requests.get(list_url, headers=HEADERS, params=list_params, timeout=10)
        if response.status_code != 200:
            print(f"❌ 상점 리스트 API 호출 실패 (상태코드: {response.status_code})")
            return
        
        shops_list = response.json().get("shops", [])
        print(f"📊 검색된 요기요 상점: {len(shops_list)}개")

        # 2. 개별 상점 분석 및 적재
        for s in shops_list:
            shop_id = str(s.get("id"))
            name = s.get("name")
            raw_rating = float(s.get("review", {}).get("average_rating", 0.0))
            review_count = int(s.get("review", {}).get("count", 0))

            # DB 존재 여부 확인 (중복 스킵 로직)
            shop = session.query(Shop).filter(Shop.id == shop_id).first()
            
            if shop:
                # 이미 존재하면 상세 호출 없이 평점/리뷰수만 업데이트
                print(f"♻️  기존 상점 업데이트: [{name}] (상세 호출 스킵)")
                shop.raw_rating = raw_rating
                shop.review_count = review_count
                shop.updated_at = datetime.utcnow() # 증분 처리를 위해 업데이트 시각 명시적 갱신
                session.commit()
                continue

            # 신규 상점이면 상세 API 호출
            print(f"🍽️  신규 상점 상세 분석: [{name}] (ID: {shop_id})")
            detail_url = f"{BASE_URL}/shops/{shop_id}"
            has_review_event = False
            
            law_address_sido = ""
            law_address_sigungu = ""
            law_address_eupmyeondong = ""
            law_address_detail = ""
            custom_detailed_address = ""
            company_name = ""
            business_number = ""
            s_lat = None
            s_lng = None
            logo_url = ""

            try:
                time.sleep(random.uniform(1.0, 2.0))
                detail_resp = requests.get(detail_url, headers=HEADERS, params=api_params, timeout=10)
                if detail_resp.status_code == 200:
                    detail = detail_resp.json()
                    
                    company = detail.get("company", {})
                    business_number = company.get("company_number", "")
                    company_name = company.get("company_name", "")
                    
                    profile = detail.get("profile", {})
                    law_address_sido = profile.get("law_address_sido", "")
                    law_address_sigungu = profile.get("law_address_sigungu", "")
                    law_address_eupmyeondong = profile.get("law_address_eupmyeondong", "")
                    law_address_detail = profile.get("law_address_detail", "").strip()
                    custom_detailed_address = profile.get("custom_detailed_address", "")

                    location = detail.get("location", {})
                    s_lat = float(location.get("lat")) if location.get("lat") else None
                    s_lng = float(location.get("lng")) if location.get("lng") else None
                    
                    image = detail.get("image", {})
                    logo_url = image.get("logo_url", "")

                    full_text = str(detail)
                    if any(kw in full_text for kw in EVENT_KEYWORDS):
                        has_review_event = True
                else:
                    print(f"   ⚠️ 상세 정보 호출 실패 (상태코드: {detail_resp.status_code})")
            except Exception as ex_detail:
                print(f"   ⚠️ 상세 정보 분석 도중 예외 발생: {ex_detail}")

            # 신규 데이터 추가
            shop = Shop(id=shop_id)
            session.add(shop)

            shop.name = name
            shop.raw_rating = raw_rating
            shop.review_count = review_count
            shop.has_review_event = has_review_event
            shop.law_address_sido = law_address_sido
            shop.law_address_sigungu = law_address_sigungu
            shop.law_address_eupmyeondong = law_address_eupmyeondong
            shop.law_address_detail = law_address_detail
            shop.custom_detailed_address = custom_detailed_address
            shop.company_name = company_name
            shop.business_number = business_number or "등록번호 미등록"
            shop.lat = s_lat
            shop.lng = s_lng
            shop.logo_url = logo_url
            shop.category = s.get("vendor_categories", ["기타"])[0]
            shop.updated_at = datetime.utcnow() # 생성 시에도 업데이트 시각 설정

            session.commit()
            print(f"   └ 신규 적재 완료: [이벤트: {has_review_event} / 사업자명: {company_name}]")

        print("🎉 [API Scraper] 모든 상점 데이터 수집 및 DB 적재 완료!")

    except Exception as e:
        session.rollback()
        print(f"❌ 데이터 수집 파이프라인 구동 중 오류 발생: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean Delivery Pipeline - 요기요 데이터 수집기")
    parser.add_argument("--mock", action="store_true", help="크롤러를 가동하지 않고 10개의 리얼한 로컬 테스트용 모의 데이터 적재")
    parser.add_argument("--limit", type=int, default=5, help="수집할 상점의 최대 개수 (실제 크롤링 시)")
    parser.add_argument("--offset", type=int, default=0, help="수집을 시작할 인덱스 (0부터 시작)")
    parser.add_argument("--lat", type=str, help="위도 (직접 입력 시)")
    parser.add_argument("--lng", type=str, help="경도 (직접 입력 시)")
    parser.add_argument("--adm_code", type=str, required=True, help="행정동 코드 (필수)")
    
    args = parser.parse_args()
    
    if args.mock:
        generate_mock_data()
    else:
        run_real_scraper(args.limit, args.offset, args.lat, args.lng, args.adm_code)
