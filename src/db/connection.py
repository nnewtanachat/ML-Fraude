import os
import logging

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Please set it in .env or as an environment variable."
    )

engine = create_engine(
    DATABASE_URL,
    pool_size=5,           # connection pool ขั้นต่ำ
    max_overflow=10,       # เพิ่มได้อีก 10 ตอน load สูง
    pool_recycle=3600,     # recycle connection ทุก 1 ชม. (ป้องกัน stale connection)
    pool_pre_ping=True,    # เช็ค connection ก่อนใช้ (ป้องกัน disconnect)
    echo=False,            # ไม่ log SQL (production)
)

SessionLocal = sessionmaker(bind=engine)


def get_db():
    """Dependency สำหรับ FastAPI — auto close session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
