import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# MTProto API для работы с большими файлами через Pyrogram
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# Telethon API для YouTube downloads через @hyd_yt_mp3_bot
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "38923554"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "bd666a5f2fc702fed3e7c32bc411a696")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "+79113583410")

# Настройки для локального Bot API Server
USE_LOCAL_API = os.getenv("USE_LOCAL_API", "false").lower() == "true"
LOCAL_API_URL = os.getenv("LOCAL_API_URL", "http://localhost:8081")

# Выбор транскрибера: "groq" (онлайн, быстро) или "local" (оффлайн, медленно)
USE_GROQ = os.getenv("USE_GROQ", "true").lower() == "true"

# Прокси для обхода блокировок Telegram API (опционально)
PROXY_URL = os.getenv("PROXY_URL", "")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY не найден в переменных окружения")
