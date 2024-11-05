# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Устанавливаем необходимые системные зависимости
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    && apt-get clean

# Копируем файл chromedriver в контейнер
COPY chromedriver /usr/local/bin/chromedriver

# Устанавливаем права на выполнение для chromedriver
RUN chmod +x /usr/local/bin/chromedriver

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем все файлы проекта в рабочую директорию
COPY . .

# Устанавливаем зависимости из requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Указываем команду для запуска вашего приложения
CMD ["python", "kga.py"]
