import os
import json
import subprocess
import sys
import time  # [추가] 10분 대기를 위한 time 모듈
from datetime import datetime, timedelta  # [추가] 로그 확인용 시간 모듈
from sqlalchemy import text
from src.db.connection import db_manager

# 상태를 저장할 파일명
INDEX_FILE = "current_index.txt"
COORDINATE_FILE = "data/district_coordinate.json"

def update_last_updated_time():
    """데이터베이스의 system_metadata 테이블에 마지막 실행 시간을 저장합니다."""
    session = db_manager.get_session()
    try:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS system_metadata (
                key VARCHAR(50) PRIMARY KEY,
                value VARCHAR(100)
            )
        """))
        
        # 한국 시간 구하기 (KST)
        kst_now = datetime.utcnow() + timedelta(hours=9)
        kst_str = kst_now.strftime('%Y-%m-%d %H:%M:%S')
        
        session.execute(text("""
            INSERT INTO system_metadata (key, value) 
            VALUES ('last_updated', :val)
            ON CONFLICT (key) 
            DO UPDATE SET value = EXCLUDED.value
        """), {"val": kst_str})
        session.commit()
        print(f"💾 DB에 마지막 업데이트 시간 기록 완료: {kst_str}")
    except Exception as e:
        session.rollback()
        print(f"⚠️ DB 업데이트 시간 기록 실패: {e}")
    finally:
        session.close()

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

def run_single_etl():
    """1개의 행정동을 수집하는 단일 ETL 파이프라인 단위입니다."""
    # 1. 루프할 때마다 최신 인덱스 및 행정동 데이터 로드
    current_index = get_current_index()
    
    if not os.path.exists(COORDINATE_FILE):
        print(f"❌ {COORDINATE_FILE} 파일이 존재하지 않습니다.")
        sys.exit(1)
        
    with open(COORDINATE_FILE, "r", encoding="utf-8") as f:
        coordinates = json.load(f)
        
    if current_index >= len(coordinates):
        print("🎉 모든 행정동의 수집이 완료되었습니다! 파이프라인을 완료 상태로 종료합니다.")
        return False  # 수집이 끝났음을 알림
        
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

    # 3. Step 1: 요기요 스크래퍼 실행
    scraper_path = os.path.join("src", "scraper", "ygy_scraper.py")
    run_step(["python3", scraper_path, "--adm_code", str(adm_code), "--lat", lat, "--lng", lng, "--limit", "100"])

    # 4. Step 2: DQ 검증기 가동
    validator_path = os.path.join("src", "quality", "dq_validator.py")
    if not os.path.exists(validator_path):
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
    
    # 7. 데이터베이스에 마지막 업데이트 시각 기록
    update_last_updated_time()
    
    print(f"\n✅ {dong} 처리 성공! 다음 타겟 인덱스는 [{next_index}] 입니다.\n")
    return True  # 다음 루프를 계속 진행할 수 있음

def main():
    TOTAL_ITERATIONS = 6
    INTERVAL_SECONDS = 300

    for i in range(TOTAL_ITERATIONS):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n⏱️ [스케줄 루프 {i+1}/{TOTAL_ITERATIONS}] 현재 시간: {current_time}")
        
        # ETL 파이프라인 1회 가동
        has_next = run_single_etl()
        
        # 더 수집할 데이터가 없다면(종료 조건) 루프 탈출
        if not has_next:
            break
            
        # 마지막 바퀴가 아니라면 5분 동안 대기
        if i < TOTAL_ITERATIONS - 1:
            print(f"⏳ 다음 수집까지 5분간 대기합니다... (대기 시작 시간: {datetime.now().strftime('%H:%M:%S')})")
            time.sleep(INTERVAL_SECONDS)

    print("\n🏁 지정된 1시간 분량(총 6회)의 수집 스케줄 루프가 안전하게 완료되었습니다.")

if __name__ == "__main__":
    main()