import os
import sys
import json
import requests
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 요기요 API 엔드포인트 및 인증 헤더
BASE_URL = "https://api.yogiyo.co.kr/shopyo/v1"
HEADERS = {
    "x-api-key": "qua9EeW1ohth4ain",
    "X-YGY-APP-VERSION": "9.0.0",
    "X-YGY-OS-TYPE": "IOS",
    "x-ygy-route": "v2",
    "Origin": "https://www.yogiyo.co.kr",
    "Referer": "https://www.yogiyo.co.kr/",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
}

# 강남역 좌표
COORDS = {
    "lat": "37.4941545",
    "lng": "127.03300871",
    "adm_code": "1168064000"
}

def inspect_single_shop():
    print("🔍 [Inspector] 요기요 API에서 단일 매장의 모든 데이터를 추출합니다...")
    
    api_params = {
        "adm_code": COORDS["adm_code"],
        "customer_id": "925381195",
        "lat": COORDS["lat"],
        "lng": COORDS["lng"],
        "membership_code": "NONE",
        "vertical_types": "FOOD"
    }

    # 1. 목록에서 첫 번째 상점 가져오기
    list_url = f"{BASE_URL}/shops"
    list_params = api_params.copy()
    list_params.update({
        "length": "1",
        "start": "0",
        "sort": "RANK_DESC",
        "serving_types": "VD",
        "use_bargainyo": "false"
    })

    try:
        list_resp = requests.get(list_url, headers=HEADERS, params=list_params, timeout=10)
        if list_resp.status_code != 200:
            print(f"❌ 목록 API 호출 실패: {list_resp.status_code}")
            return

        shops = list_resp.json().get("shops", [])
        if not shops:
            print("⚠️ 검색된 상점이 없습니다.")
            return

        shop_summary = shops[0]
        shop_id = shop_summary.get("id")
        
        print(f"\n--- [1/2] 목록 API 응답 (Shop ID: {shop_id}) ---")
        print(json.dumps(shop_summary, indent=2, ensure_ascii=False))

        # 2. 상세 정보 가져오기
        detail_url = f"{BASE_URL}/shops/{shop_id}"
        detail_resp = requests.get(detail_url, headers=HEADERS, params=api_params, timeout=10)
        
        if detail_resp.status_code == 200:
            shop_detail = detail_resp.json()
            print(f"\n--- [2/2] 상세 API 응답 ---")
            print(json.dumps(shop_detail, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 상세 API 호출 실패: {detail_resp.status_code}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    inspect_single_shop()
