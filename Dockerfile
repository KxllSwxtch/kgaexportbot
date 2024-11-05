FROM python:3.11-slim

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    chromium \
    && apt-get clean

# Скачиваем chromedriver
RUN CHROMEDRIVER_VERSION=$(wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    wget -N https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
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
