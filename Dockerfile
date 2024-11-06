# Начальная стадия с базой Python
FROM python:3.11-slim

# Установка необходимых пакетов и версии Chromium
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    chromium \
    && apt-get clean

# Установка последней доступной версии ChromeDriver для Chrome 130
RUN wget -N https://chromedriver.storage.googleapis.com/130.0.6735.0/chromedriver_linux64.zip || \
    wget -N https://chromedriver.storage.googleapis.com/130.0.6723.91/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip && \
    mv chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm chromedriver_linux64.zip

# Копирование кода и установка зависимостей
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt

# Запуск приложения
CMD ["python", "kga.py"]
