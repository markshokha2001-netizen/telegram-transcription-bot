# Telegram Transcription Bot

Бот для транскрибации аудио и видео в текст с возможностью создания конспектов.

## Возможности

- 🎤 Транскрибация голосовых сообщений, аудио и видео
- 🔗 Скачивание и обработка видео по ссылкам (YouTube и др.)
- 🤖 Генерация структурированных конспектов через AI
- 📄 Экспорт транскриптов и конспектов в TXT, DOCX, PDF

## Деплой

### Railway.app (рекомендуется)

1. Создайте аккаунт на [Railway.app](https://railway.app)
2. Нажмите "New Project" → "Deploy from GitHub repo"
3. Выберите этот репозиторий
4. Добавьте переменные окружения:
   - `TELEGRAM_BOT_TOKEN` - токен вашего бота от @BotFather
   - `GROQ_API_KEY` - API ключ от [Groq](https://console.groq.com)
   - `API_ID` и `API_HASH` - от [my.telegram.org](https://my.telegram.org)
   - `USE_GROQ=true` - использовать онлайн транскрибацию
5. Deploy!

### Render.com

1. Создайте аккаунт на [Render.com](https://render.com)
2. New → Web Service → Connect repository
3. Build Command: `docker build -t bot .`
4. Start Command: `python -m bot.main`
5. Добавьте те же переменные окружения
6. Create Web Service

### Локальный запуск

```bash
# Установите зависимости
pip install -r requirements.txt

# Создайте .env файл
cp .env.example .env
# Заполните переменные окружения

# Запустите бота
python -m bot.main
```

## Переменные окружения

```env
TELEGRAM_BOT_TOKEN=your_bot_token
GROQ_API_KEY=your_groq_key
API_ID=your_api_id
API_HASH=your_api_hash
USE_GROQ=true
```

## Технологии

- Python 3.11+
- aiogram (Telegram Bot API)
- Groq API (транскрибация Whisper Large v3)
- Groq API (конспекты GPT-OSS-120B)
- yt-dlp (скачивание видео)
- ffmpeg (обработка аудио/видео)
