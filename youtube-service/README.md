# YouTube Downloader Microservice

Простой микросервис для скачивания аудио с YouTube через yt-dlp.

## Деплой на Railway

1. Зарегистрируйтесь на https://railway.app (через GitHub)
2. Создайте новый проект
3. Deploy from GitHub repo → выберите этот репозиторий
4. Railway автоматически определит Python и установит зависимости
5. Сервис будет доступен по URL типа `https://your-service.railway.app`

## API

### POST /download
Скачивает аудио с YouTube

**Request:**
```json
{
  "url": "https://youtube.com/watch?v=..."
}
```

**Response:** MP3 файл

### GET /health
Health check endpoint

**Response:**
```json
{
  "status": "healthy"
}
```

## Локальный запуск

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
