FROM python:3.11-slim

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    chromium \
    && apt-get clean

# Копируем chromedriver и код вашего проекта
COPY chromedriver /usr/local/bin/chromedriver
COPY . /app

WORKDIR /app

# Устанавливаем зависимости
RUN pip install -r requirements.txt

# Запускаем приложение
CMD ["python", "kga.py"]
