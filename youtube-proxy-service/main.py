"""
YouTube Proxy Service - использует Telethon для взаимодействия с @hyd_yt_mp3_bot
Получает YouTube ссылки, пересылает в @hyd_yt_mp3_bot, возвращает mp3 файл
"""
import asyncio
import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeFilename
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Telegram API credentials
API_ID = int(os.getenv("TELEGRAM_API_ID", "38923554"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "bd666a5f2fc702fed3e7c32bc411a696")
PHONE = os.getenv("TELEGRAM_PHONE", "")  # Будет запрошен при первом запуске

# Bot username
HYD_BOT = "hyd_yt_mp3_bot"

# Download directory
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Telethon client
client = None

# Очередь запросов
download_queue = {}


class DownloadRequest(BaseModel):
    url: str
    request_id: str = None


@app.on_event("startup")
async def startup():
    """Инициализация Telethon клиента"""
    global client

    try:
        client = TelegramClient('session', API_ID, API_HASH)
        await client.start(phone=PHONE)
        logger.info("✅ Telethon client started successfully")

        # Проверяем доступность @hyd_yt_mp3_bot
        try:
            entity = await client.get_entity(HYD_BOT)
            # Может быть User или Bot
            name = getattr(entity, 'title', None) or getattr(entity, 'first_name', HYD_BOT)
            logger.info(f"✅ Found @{HYD_BOT}: {name}")
        except Exception as e:
            logger.error(f"❌ Cannot find @{HYD_BOT}: {e}")

    except Exception as e:
        logger.error(f"❌ Failed to start Telethon client: {e}")
        raise


@app.on_event("shutdown")
async def shutdown():
    """Закрытие Telethon клиента"""
    if client:
        await client.disconnect()
        logger.info("Telethon client disconnected")


@app.get("/")
async def root():
    return {"status": "ok", "service": "youtube-proxy-telethon"}


@app.get("/health")
async def health():
    is_connected = client and client.is_connected()
    return {
        "status": "healthy" if is_connected else "disconnected",
        "telethon_connected": is_connected
    }


@app.post("/download")
async def download_youtube(request: DownloadRequest):
    """
    Скачивает аудио с YouTube через @hyd_yt_mp3_bot

    Схема работы:
    1. Отправляем YouTube ссылку боту @hyd_yt_mp3_bot
    2. Ждём mp3 файл от бота
    3. Скачиваем файл
    4. Возвращаем файл
    """
    if not client or not client.is_connected():
        raise HTTPException(status_code=503, detail="Telethon client not connected")

    try:
        request_id = request.request_id or str(uuid.uuid4())

        logger.info(f"[{request_id}] Downloading from YouTube: {request.url}")

        # Отправляем ссылку боту
        await client.send_message(HYD_BOT, request.url)
        logger.info(f"[{request_id}] Sent URL to @{HYD_BOT}")

        # Ждём ответ от бота (mp3 файл)
        # Используем событие для получения следующего сообщения от бота
        download_path = None
        timeout = 120  # 2 минуты таймаут

        async def wait_for_audio():
            nonlocal download_path

            async for message in client.iter_messages(HYD_BOT, limit=10):
                # Проверяем, что это аудио или документ
                if message.audio or (message.document and any(
                    isinstance(attr, (DocumentAttributeAudio, DocumentAttributeFilename))
                    for attr in message.document.attributes
                )):
                    # Скачиваем файл
                    filename = f"{request_id}.mp3"
                    download_path = DOWNLOAD_DIR / filename

                    logger.info(f"[{request_id}] Downloading file from @{HYD_BOT}...")
                    await message.download_media(str(download_path))
                    logger.info(f"[{request_id}] File downloaded: {download_path}")
                    return

            raise Exception("No audio file received from bot")

        # Ждём с таймаутом
        try:
            await asyncio.wait_for(wait_for_audio(), timeout=timeout)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=408,
                detail=f"Timeout: @{HYD_BOT} не ответил за {timeout} секунд"
            )

        if not download_path or not download_path.exists():
            raise HTTPException(status_code=500, detail="Failed to download file")

        # Возвращаем файл и удаляем после отправки
        return FileResponse(
            str(download_path),
            media_type="audio/mpeg",
            filename=f"youtube_{request_id}.mp3",
            background=BackgroundTasks().add_task(lambda: download_path.unlink(missing_ok=True))
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
