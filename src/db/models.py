from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from datetime import datetime
from src.db.connection import Base

class Shop(Base):
    __tablename__ = "shops"

    # 요기요 및 지도 플랫폼 상점 고유 식별 ID
    id = Column(String, primary_key=True, index=True)
    
    # 상점 기본 정보
    name = Column(String, nullable=False)
    raw_rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True, default=0)
    
    # 리뷰 이벤트 메뉴/옵션 포함 여부
    has_review_event = Column(Boolean, nullable=True, default=False)
    
    # 주소 및 비즈니스 식별 정보 (원본 데이터 보존을 위해 세분화)
    law_address_sido = Column(String, nullable=True)
    law_address_sigungu = Column(String, nullable=True)
    law_address_eupmyeondong = Column(String, nullable=True)
    law_address_detail = Column(String, nullable=True)
    custom_detailed_address = Column(String, nullable=True)
    
    company_name = Column(String, nullable=True)
    business_number = Column(String, nullable=True)
    
    # 위치 및 이미지 메타데이터
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    logo_url = Column(String, nullable=True)
    category = Column(String, nullable=True)

    # 상태 추적 및 증분 처리를 위한 타임스탬프 (인덱스 포함)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_validated_at = Column(DateTime, nullable=True, index=True)
    last_transformed_at = Column(DateTime, nullable=True, index=True)

    def __repr__(self):
        return f"<Shop {self.name} (ID: {self.id}, Rating: {self.raw_rating}, Event: {self.has_review_event})>"


class RefinedShop(Base):
    __tablename__ = "refined_shops"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    raw_rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True, default=0)
    has_review_event = Column(Boolean, nullable=True, default=False)
    
    # 주소 정보 (세분화)
    address = Column(String, nullable=True)           # 시/도 + 시/군/구 + 읍/면/동
    detailed_address = Column(String, nullable=True)  # 지번 (Lot Number)
    building_name = Column(String, nullable=True)     # 건물명
    floor = Column(String, nullable=True)             # 층
    room_number = Column(String, nullable=True)       # 호수
    
    category = Column(String, nullable=True)
    business_number = Column(String, nullable=True)
    
    # 위치 정보
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    # 샵인샵(위장 가맹점) 식별 정보
    is_shop_in_shop = Column(Boolean, default=False)
    is_suspicious = Column(Boolean, default=False)     # 주소 밀도 기반 의심군 여부
    sis_group_id = Column(String, nullable=True)       # 동일 그룹 해시 ID
    sis_sibling_count = Column(Integer, default=0)     # 그룹 내 다른 상점 수
    sis_sibling_names = Column(String, nullable=True)  # 그룹 내 다른 상점 상호명 리스트
    external_metadata = Column(String, nullable=True)  # 추출 후 남은 자투리 정보 (JSON 등)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    refined_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<RefinedShop {self.name} (ID: {self.id}, Rating: {self.raw_rating}, SIS: {self.is_shop_in_shop})>"
