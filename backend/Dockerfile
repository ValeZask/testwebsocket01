FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости для PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

# Railway автоматически предоставляет переменную PORT
EXPOSE $PORT

# Используем переменную PORT от Railway
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT