# main.py
import os
import json
import subprocess
import sys

# 상태를 저장할 파일명
INDEX_FILE = "current_index.txt"
COORDINATE_FILE = "data/district_coordinate.json"

def get_current_index():
    """현재 가리키고 있는 행정동 인덱스를 읽어옵니다."""
    if not os.path.exists(INDEX_FILE):
        return 0
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        try:
            return int(f.read().strip())
        except ValueError:
            return 0

def update_index(next_index):
    """다음 회차를 위해 인덱스를 파일에 저장합니다."""
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(str(next_index))

def run_step(command_list):
    """서브 프로세스를 실행하고 에러 발생 시 시스템을 종료합니다."""
    print(f"🏃 실행 중: {' '.join(command_list)}")
    # 로컬과 GitHub Actions 환경 모두에서 한글/출력 로그가 깨지지 않도록 인코딩 명시
    result = subprocess.run(command_list, capture_output=False, text=True)
    if result.returncode != 0:
        print(f"❌ 단계 실패 코드: {result.returncode}")
        sys.exit(result.returncode)

def main():
    # 1. 인덱스 및 행정동 데이터 로드
    current_index = get_current_index()
    
    if not os.path.exists(COORDINATE_FILE):
        print(f"❌ {COORDINATE_FILE} 파일이 존재하지 않습니다.")
        sys.exit(1)
        
    with open(COORDINATE_FILE, "r", encoding="utf-8") as f:
        coordinates = json.load(f)
        
    if current_index >= len(coordinates):
        print("🎉 모든 행정동의 수집이 완료되었습니다! 파이프라인을 종료합니다.")
        sys.exit(0)
        
    # 2. 이번 회차에 수집할 행정동 타겟 추출
    target_district = coordinates[current_index]
    adm_code = target_district.get("코드")
    lat = str(target_district.get("위도"))
    lng = str(target_district.get("경도"))
    sido = target_district.get("시도")
    gungu = target_district.get("시군구")
    dong = target_district.get("읍면동")
    
    print(f"\n==================================================")
    print(f"🚀 [회차 {current_index}] {sido} {gungu} {dong} (코드: {adm_code}) 수집 시작")
    print(f"==================================================")

    # 3. Step 1: 요기요 스크래퍼 실행 (인자 규격 반영)
    # 질문자님의 scraper 구조에 맞춰 파일 경로를 지정해 줍니다.
    # 만약 파일 위치가 src/scraper/ygy_scraper.py 라면 아래 경로를 맞춰주세요.
    scraper_path = os.path.join("src", "scraper", "ygy_scraper.py")
    run_step(["python3", scraper_path, "--adm_code", str(adm_code), "--lat", lat, "--lng", lng, "--limit", "100"])

    # 4. Step 2: DQ 검증기 가동
    validator_path = os.path.join("src", "quality", "dq_validator.py") # 혹은 스크립트가 속한 정확한 폴더 경로
    if not os.path.exists(validator_path):
        # 만약 src 내부 등 다른 곳에 있다면 경로를 맞춰줍니다.
        validator_path = "src/quality/dq_validator.py" 
    run_step(["python3", validator_path])

    # 5. Step 3: 데이터 변환 및 Supabase 적재 (Transformer)
    transformer_path = os.path.join("src", "transformation", "transformer.py")
    if not os.path.exists(transformer_path):
        transformer_path = "src/transformation/transformer.py"
    run_step(["python3", transformer_path])

    # 6. 모든 과정이 성공하면 인덱스를 1 증가시켜 업데이트
    next_index = current_index + 1
    update_index(next_index)
    print(f"\n✅ {dong} 처리 성공! 다음 타겟 인덱스는 [{next_index}] 입니다.\n")

if __name__ == "__main__":
    main()