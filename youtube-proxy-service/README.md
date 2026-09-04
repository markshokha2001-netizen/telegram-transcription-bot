# YouTube Proxy Service (Telethon)

Промежуточный сервис для автоматического скачивания YouTube аудио через @hyd_yt_mp3_bot

## Как это работает

1. Получает YouTube ссылку от основного бота
2. Через Telethon (как user) отправляет ссылку @hyd_yt_mp3_bot
3. Получает mp3 файл от @hyd_yt_mp3_bot
4. Возвращает mp3 файл основному боту

## Деплой на Render

1. Создайте новый Web Service на Render
2. Подключите этот GitHub репозиторий
3. **Root Directory:** `youtube-proxy-service`
4. **Environment Variables:**
   - `TELEGRAM_API_ID` = `38923554`
   - `TELEGRAM_API_HASH` = `bd666a5f2fc702fed3e7c32bc411a696`
   - `TELEGRAM_PHONE` = ваш номер телефона (с кодом страны, например +79991234567)

5. При первом запуске:
   - Откройте Logs в Render
   - Вам придёт SMS код от Telegram
   - Нужно будет ввести код (но на Render это невозможно)
   - **Решение:** Сначала запустите локально для авторизации

## Локальный запуск (для первой авторизации)

```bash
cd youtube-proxy-service
pip install -r requirements.txt

# Создайте .env файл
cp .env.example .env
# Отредактируйте .env - укажите ваш номер телефона

# Запустите
python main.py

# Telethon попросит код из SMS
# Введите код -> создастся файл session.session
# Этот файл нужно загрузить на Render
```

## API

### POST /download
Скачивает аудио с YouTube через @hyd_yt_mp3_bot

**Request:**
```json
{
  "url": "https://youtube.com/watch?v=...",
  "request_id": "optional-unique-id"
}
```

**Response:** MP3 файл

### GET /health
Health check

**Response:**
```json
{
  "status": "healthy",
  "telethon_connected": true
}
```
