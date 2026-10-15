from collections.abc import Generator

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

#1. Configure the database engine
database_url = URL.create(
    drivername="postgresql+psycopg",
    username=settings.DB_USER,
    password=settings.DB_PASSWORD,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_NAME,
)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
)

#2. Create a factory for database sessions
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

#3. Provide a session to FastAPI endpoints
def get_db() -> Generator[Session,None,None]:
    db = SessionLocal()
    
    try:
        yield db
        
    finally:
        db.close()