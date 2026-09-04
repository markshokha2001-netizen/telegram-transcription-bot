"""
YouTube Downloader через Telethon + @hyd_yt_mp3_bot
Встроенный модуль для основного бота
"""
import asyncio
import os
import logging
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeFilename
import uuid

logger = logging.getLogger(__name__)

# Telegram API credentials
API_ID = int(os.getenv("TELEGRAM_API_ID", "38923554"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "bd666a5f2fc702fed3e7c32bc411a696")
PHONE = os.getenv("TELEGRAM_PHONE", "+79113583410")

# Bot username
HYD_BOT = "DiggerDigitalBot"

# Download directory
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Global Telethon client
_telethon_client = None


async def init_telethon():
    """Инициализация Telethon клиента"""
    global _telethon_client

    if _telethon_client and _telethon_client.is_connected():
        return _telethon_client

    try:
        session_path = Path(__file__).parent.parent.parent / "session.session"
        _telethon_client = TelegramClient(str(session_path), API_ID, API_HASH)
        await _telethon_client.start(phone=PHONE)
        logger.info("✅ Telethon client started successfully")

        # Проверяем доступность @hyd_yt_mp3_bot
        try:
            entity = await _telethon_client.get_entity(HYD_BOT)
            name = getattr(entity, 'title', None) or getattr(entity, 'first_name', HYD_BOT)
            logger.info(f"✅ Found @{HYD_BOT}: {name}")
        except Exception as e:
            logger.warning(f"⚠️ Cannot verify @{HYD_BOT}: {e}")

        return _telethon_client
    except Exception as e:
        logger.error(f"❌ Failed to start Telethon client: {e}")
        raise


async def close_telethon():
    """Закрытие Telethon клиента"""
    global _telethon_client
    if _telethon_client:
        await _telethon_client.disconnect()
        _telethon_client = None
        logger.info("Telethon client disconnected")


async def download_from_youtube(url: str) -> str:
    """
    Скачивает аудио с YouTube через @hyd_yt_mp3_bot

    Возвращает путь к скачанному файлу
    """
    client = await init_telethon()

    if not client or not client.is_connected():
        raise RuntimeError("Telethon client not connected")

    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Downloading from YouTube: {url}")

    try:
        # Отправляем ссылку боту
        await client.send_message(HYD_BOT, url)
        logger.info(f"[{request_id}] Sent URL to @{HYD_BOT}")

        # Ждём ответ от бота (mp3 файл)
        download_path = None
        timeout = 120  # 2 минуты таймаут

        async def wait_for_audio():
            nonlocal download_path

            # Ждём новое сообщение от бота
            await asyncio.sleep(2)  # Даём боту время на обработку

            async for message in client.iter_messages(HYD_BOT, limit=5):
                # Проверяем, что это аудио или документ
                if message.audio or (message.document and any(
                    isinstance(attr, (DocumentAttributeAudio, DocumentAttributeFilename))
                    for attr in message.document.attributes
                )):
                    # Скачиваем файл
                    filename = f"youtube_{request_id}.mp3"
                    download_path = DOWNLOAD_DIR / filename

                    logger.info(f"[{request_id}] Downloading file from @{HYD_BOT}...")
                    await message.download_media(str(download_path))
                    logger.info(f"[{request_id}] File downloaded: {download_path}")
                    return

            raise RuntimeError(f"No audio file received from @{HYD_BOT}")

        # Ждём с таймаутом
        try:
            await asyncio.wait_for(wait_for_audio(), timeout=timeout)
        except asyncio.TimeoutError:
            raise RuntimeError(f"Timeout: @{HYD_BOT} не ответил за {timeout} секунд")

        if not download_path or not download_path.exists():
            raise RuntimeError("Failed to download file from @{HYD_BOT}")

        return str(download_path)

    except Exception as e:
        logger.error(f"[{request_id}] Error: {e}")
        raise RuntimeError(f"Ошибка при скачивании через @{HYD_BOT}: {str(e)}")
