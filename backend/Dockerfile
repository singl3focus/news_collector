FROM python:3.11-slim as builder

# Установка зависимостей системы
RUN apt-get update && \
    apt-get install -y gcc && \
    rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY src/ ./src
COPY config.yaml .

# Команда запуска
CMD ["python", "-m", "src.main"]