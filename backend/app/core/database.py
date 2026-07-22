import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/interview_platform").strip()

# Sanitize trailing period or whitespace (e.g. if copied from documentation text ending in ".")
if DATABASE_URL.endswith("."):
    DATABASE_URL = DATABASE_URL[:-1].strip()

# SQLAlchemy 2.0 requires 'postgresql://' instead of legacy 'postgres://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Clean up any malformed query parameters like channel_binding=require.
DATABASE_URL = DATABASE_URL.replace("channel_binding=require.", "channel_binding=require")
DATABASE_URL = DATABASE_URL.replace("sslmode=require.", "sslmode=require")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: gives each request its own DB session and closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
