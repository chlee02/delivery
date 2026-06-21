import os
import sys
from datetime import datetime
from sqlalchemy import or_
from dotenv import load_dotenv

# 프로젝트 루트를 Python path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.db.connection import db_manager
from src.db.models import Shop

load_dotenv()

class DataQualityValidator:
    """수집된 데이터의 품질 및 정합성을 검증하는 DQ 엔진 (증분 처리 지원)"""
    
    def __init__(self):
        self.session = db_manager.get_session()
        self.results = {
            "total_records": 0,
            "passed_records": 0,
            "failed_records": 0,
            "details": []
        }

    def run_validation(self):
        """데이터베이스 내의 상점 데이터를 기반으로 증분 품질 검증 실행"""
        print("🔍 [Data Quality] 증분 상점 데이터 품질 검증을 시작합니다...")
        
        try:
            # 증분 대상 선정: 미검증 데이터이거나 수집기에 의해 업데이트된 데이터
            # last_validated_at IS NULL OR updated_at > last_validated_at
            shops = self.session.query(Shop).filter(
                or_(
                    Shop.last_validated_at == None,
                    Shop.updated_at > Shop.last_validated_at
                )
            ).all()
            
            self.results["total_records"] = len(shops)
            
            if not shops:
                print("✅ [Data Quality] 새로 검증할 데이터가 없습니다.")
                return self.results

            print(f"📊 [Data Quality] 총 {len(shops)}개의 대상 데이터를 검증합니다.")

            for shop in shops:
                fail_reasons = []
                
                # Rule 1: ID 및 이름 Null 검증 (Critical)
                if not shop.id:
                    fail_reasons.append("ID가 누락되었습니다 (Critical)")
                if not shop.name or shop.name.strip() == "":
                    fail_reasons.append("상점명이 누락되었습니다 (Critical)")

                # Rule 2: 평점 유효 범위 검증 (0.0 ~ 5.0)
                if shop.raw_rating is not None:
                    if not (0.0 <= shop.raw_rating <= 5.0):
                        fail_reasons.append(f"평점 범위 초과: {shop.raw_rating}")
                else:
                    fail_reasons.append("평점이 누락되었습니다")

                # Rule 3: 리뷰 수 음수 유효성 검증
                if shop.review_count is not None:
                    if shop.review_count < 0:
                        fail_reasons.append(f"리뷰 개수가 음수입니다: {shop.review_count}")
                else:
                    fail_reasons.append("리뷰 개수가 누락되었습니다")

                # Rule 4: 필수 주소 유효성 검증 (세분화된 필드 기준)
                if not all([shop.law_address_sido, shop.law_address_sigungu, shop.law_address_eupmyeondong, shop.law_address_detail]):
                    missing = []
                    if not shop.law_address_sido: missing.append("시/도")
                    if not shop.law_address_sigungu: missing.append("시/군/구")
                    if not shop.law_address_eupmyeondong: missing.append("읍/면/동")
                    if not shop.law_address_detail: missing.append("상세주소(법정)")
                    fail_reasons.append(f"필수 주소 정보 누락: {', '.join(missing)}")

                # Rule 5: 사업자 정보 유효성 검증
                has_biz_num = shop.business_number and "등록번호 미등록" not in shop.business_number
                has_company_name = shop.company_name and shop.company_name.strip() != ""
                
                if not has_biz_num and not has_company_name:
                    fail_reasons.append("사업자 정보(상호명 및 등록번호)가 모두 누락되었습니다")
                elif not has_biz_num:
                    fail_reasons.append("사업자등록번호가 누락되었습니다")

                # 검증 결과 집계
                is_passed = len(fail_reasons) == 0
                record_status = {
                    "shop_id": shop.id,
                    "shop_name": shop.name,
                    "status": "PASSED" if is_passed else "FAILED",
                    "errors": fail_reasons
                }
                self.results["details"].append(record_status)
                
                if is_passed:
                    self.results["passed_records"] += 1
                else:
                    self.results["failed_records"] += 1
                    if any("Critical" in reason for reason in fail_reasons):
                        self._trigger_slack_alert(shop.id, shop.name, fail_reasons)
                
                # 검증 상태 업데이트 (통과 여부와 상관없이 시도 완료 처리)
                shop.last_validated_at = datetime.utcnow()
            
            self.session.commit()
            self._print_report()
            return self.results
            
        except Exception as e:
            self.session.rollback()
            print(f"❌ [Data Quality] 검증 도중 오류 발생: {e}")
            raise
        finally:
            self.session.close()

    def _trigger_slack_alert(self, shop_id, shop_name, reasons):
        """임계 결함 감지 시 슬랙 웹훅으로 실시간 알림을 발송하는 시뮬레이터"""
        print(f"\n🚨 [CRITICAL ALERT] 데이터 품질 장애 감지!")
        print(f"   ├─ 상점: {shop_name} (ID: {shop_id})")
        print(f"   ├─ 결함 내용: {', '.join(reasons)}")
        print(f"   └─ 조치 필요: 수집기 로그 확인 및 데이터 적재 차단 검토 요망\n")

    def _print_report(self):
        """검증 요약 보고서를 콘솔 및 로컬 파일에 출력"""
        passed = self.results["passed_records"]
        failed = self.results["failed_records"]
        total = self.results["total_records"]
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        report_md = f"""
==================================================
📊 증분 데이터 품질 검증 요약 보고서
==================================================
- 실행 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 이번 회차 검증 레코드 수: {total} 개
- 통과(PASSED): {passed} 개
- 결함(FAILED): {failed} 개
- 종합 통과율(Pass Rate): {pass_rate:.1f}%
==================================================
"""
        print(report_md)
        
        if total > 0:
            print("📋 상세 검증 내역:")
            for detail in self.results["details"]:
                status_symbol = "✅" if detail["status"] == "PASSED" else "❌"
                error_msg = f" -> 오류: {', '.join(detail['errors'])}" if detail["errors"] else ""
                print(f"  {status_symbol} [{detail['status']}] {detail['shop_name']} ({detail['shop_id']}){error_msg}")
            print("==================================================\n")

if __name__ == "__main__":
    validator = DataQualityValidator()
    validator.run_validation()
