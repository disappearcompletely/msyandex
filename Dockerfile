# Используйте официальный образ Python как родительский образ
FROM python:3.8-slim

# Установите рабочий каталог в контейнере
WORKDIR /app

# Копируйте файлы зависимостей
COPY requirements.txt requirements.txt

# Установите зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируйте остальные файлы проекта
COPY . .

# Задайте переменную среды для Flask
ENV FLASK_APP=app.py

# Откройте порт, который используется вашим приложением
EXPOSE 5002

# Запустите приложение
CMD ["flask", "run", "--host=0.0.0.0", "--port=5002"]
