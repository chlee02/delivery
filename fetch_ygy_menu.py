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
# '기대만족-본점' ID
SHOP_ID = "413273"
COORDS = {"lat": "37.4941545", "lng": "127.03300871", "adm_code": "1168064000"}

def fetch_menu_data():
    api_params = {
        "adm_code": COORDS["adm_code"], "customer_id": "925381195",
        "lat": COORDS["lat"], "lng": COORDS["lng"],
        "membership_code": "NONE", "vertical_types": "FOOD"
    }

    print(f"📡 [Menu Fetcher] {SHOP_ID} 매장의 전체 메뉴 데이터를 요청합니다...")
    
    # 메뉴 정보 조회 엔드포인트
    menu_url = f"{BASE_URL}/shops/{SHOP_ID}/menu"
    response = requests.get(menu_url, headers=HEADERS, params=api_params)
    
    if response.status_code == 200:
        menu_data = response.json()
        with open("ygy_menu_sample.json", "w", encoding="utf-8") as f:
            json.dump(menu_data, f, indent=2, ensure_ascii=False)
        print(f"✅ 모든 메뉴 데이터를 'ygy_menu_sample.json'에 저장했습니다.")
    else:
        print(f"❌ 메뉴 정보 호출 실패: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    fetch_menu_data()
