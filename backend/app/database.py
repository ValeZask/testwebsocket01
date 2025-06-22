from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Railway предоставляет DATABASE_URL автоматически для PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback для локальной разработки
    DATABASE_URL = "postgresql://postgres:password@localhost:5432/chat_db"

# Railway использует postgres:// но SQLAlchemy 1.4+ требует postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Добавляем параметры для правильной работы с кодировкой
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Отключаем в продакшене для производительности
    pool_pre_ping=True,  # Проверка соединения перед использованием
    connect_args={
        "client_encoding": "utf8",
        "options": "-c timezone=utc"
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()