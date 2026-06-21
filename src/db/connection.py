import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

Base = declarative_base()

class DBConnectionManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DBConnectionManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        # 기본값으로 로컬 SQLite 파일 데이터베이스 사용
        # 환경변수 DATABASE_URL이 설정되면 클라우드 PostgreSQL(Supabase)에 연결됨
        self.db_url = os.getenv("DATABASE_URL", "sqlite:///local_delivery.db")
        
        # SQLite 연결 시 멀티스레딩 대응 옵션 추가
        connect_args = {}
        if self.db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            
        self.engine = create_engine(self.db_url, connect_args=connect_args, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._initialized = True

    def get_session(self):
        """데이터베이스 세션을 생성하여 반환합니다."""
        return self.SessionLocal()

    def create_tables(self):
        """정의된 모든 테이블 스키마를 데이터베이스에 생성합니다."""
        Base.metadata.create_all(bind=self.engine)

# 전역 싱글톤 커넥터 객체 제공
db_manager = DBConnectionManager()
