from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/chat_db")

# Добавляем параметры для правильной работы с кодировкой
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Логирование SQL запросов для отладки
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