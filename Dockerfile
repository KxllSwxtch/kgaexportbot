# Базовый образ
FROM python:3.11-slim

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    chromium \
    ca-certificates \
    && apt-get clean

# Проверяем наличие и путь к chromium
RUN which chromium
RUN chromium --version || echo "Chromium not found"

# Устанавливаем chromedriver версии 114.0.5735.16
RUN wget https://chromedriver.storage.googleapis.com/114.0.5735.16/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip && \
    mv chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm chromedriver_linux64.zip

# Копируем ваш код
COPY . /app

WORKDIR /app

# Устанавливаем зависимости
RUN pip install -r requirements.txt

# Запускаем приложение
CMD ["python", "kga.py"]
