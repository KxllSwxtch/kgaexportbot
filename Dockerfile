# Используем базовый образ Python
FROM python:3.11-slim

# Устанавливаем необходимые пакеты
RUN apt-get update && \
    apt-get install -y \
    wget \
    unzip \
    && apt-get clean

# Копируем Chromedriver
COPY chromedriver /usr/local/bin/chromedriver

# Устанавливаем права на выполнение для Chromedriver
RUN chmod +x /usr/local/bin/chromedriver

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы приложения
COPY . .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Команда для запуска бота
CMD ["python", "your_bot_file.py"]
