import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

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
COORDS = {"lat": "37.4941545", "lng": "127.03300871", "adm_code": "1168064000"}

def save_full_data():
    api_params = {
        "adm_code": COORDS["adm_code"], "customer_id": "925381195",
        "lat": COORDS["lat"], "lng": COORDS["lng"],
        "membership_code": "NONE", "vertical_types": "FOOD"
    }

    # 1. 목록 조회
    list_params = api_params.copy()
    list_params.update({"length": "1", "sort": "RANK_DESC", "serving_types": "VD"})
    list_resp = requests.get(f"{BASE_URL}/shops", headers=HEADERS, params=list_params).json()
    shop_summary = list_resp.get("shops", [{}])[0]
    shop_id = shop_summary.get("id")

    # 2. 상세 조회
    detail_resp = requests.get(f"{BASE_URL}/shops/{shop_id}", headers=HEADERS, params=api_params).json()

    # 3. 데이터 통합 및 저장
    full_data = {
        "description": "Yogiyo API Full Data Sample (List + Detail)",
        "retrieved_at": "2026-06-13",
        "list_api_response": shop_summary,
        "detail_api_response": detail_resp
    }

    with open("ygy_full_data_sample.json", "w", encoding="utf-8") as f:
        json.dump(full_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 모든 데이터를 'ygy_full_data_sample.json' 파일에 저장했습니다.")

if __name__ == "__main__":
    save_full_data()
