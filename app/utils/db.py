from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
# import os # os 모듈은 더 이상 필요 없으므로 제거
from app.config.config import Config # Config 임포트

# TODO: 추후 환경 변수에서 데이터베이스 접속 정보를 가져오도록 수정해야 합니다.
# SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname") # 기존 라인 제거
SQLALCHEMY_DATABASE_URL = Config.DATABASE_URL # Config에서 DATABASE_URL 가져오기

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_recycle=3600, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()