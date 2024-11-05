# Используйте официальный образ Python в качестве базового
FROM python:3.11-slim

# Установка необходимых зависимостей
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    && apt-get clean

# Копируем файл chromedriver в контейнер
COPY path/to/chromedriver /usr/local/bin/chromedriver

# Устанавливаем права на выполнение для chromedriver
RUN chmod +x /usr/local/bin/chromedriver

# Установка рабочей директории
WORKDIR /app

# Копируем файлы приложения в контейнер
COPY . .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Указываем порт, который будет использовать приложение
EXPOSE 8000

# Команда для запуска приложения
CMD ["python", "kga.py"]
