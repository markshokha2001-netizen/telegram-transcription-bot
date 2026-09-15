"""
Скачивание больших файлов через Telethon Client API (без лимитов Bot API)
Поддерживает файлы любого размера (до 2 ГБ и больше)
"""
import os
import logging
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession

logger = logging.getLogger(__name__)

# Telegram API credentials
API_ID = int(os.getenv("TELEGRAM_API_ID", "38923554"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "bd666a5f2fc702fed3e7c32bc411a696")
PHONE = os.getenv("TELEGRAM_PHONE", "+79113583410")

# Download directory
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Global Telethon client (переиспользуем подключение)
_telethon_client = None


async def init_telethon():
    """Инициализация Telethon клиента"""
    global _telethon_client

    if _telethon_client and _telethon_client.is_connected():
        return _telethon_client

    try:
        session_string = os.getenv("TELEGRAM_SESSION")

        if session_string:
            _telethon_client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
            logger.info("📱 Telethon: Using StringSession from environment")
        else:
            session_path = Path(__file__).parent.parent.parent / "session.session"
            _telethon_client = TelegramClient(str(session_path), API_ID, API_HASH)
            logger.info("📁 Telethon: Using file session (local dev)")

        await _telethon_client.start(phone=PHONE)
        logger.info("✅ Telethon client connected")
        return _telethon_client

    except Exception as e:
        logger.error(f"❌ Failed to start Telethon: {e}")
        raise


async def download_large_file(chat_id: int, message_id: int, file_extension: str = "tmp") -> str:
    """
    Скачивает большой файл через Telethon Client API (обход лимита Bot API в 50 МБ)

    Args:
        chat_id: ID чата (из aiogram message.chat.id)
        message_id: ID сообщения (из aiogram message.message_id)
        file_extension: расширение файла (mp3, mp4, ogg и т.д.)

    Returns:
        Путь к скачанному файлу
    """
    client = await init_telethon()

    if not client or not client.is_connected():
        raise RuntimeError("Telethon client not connected")

    try:
        logger.info(f"🔽 Downloading large file via Telethon: chat_id={chat_id}, msg_id={message_id}")

        # Сначала получаем entity чата (для корректной работы с ID)
        try:
            peer = await client.get_input_entity(chat_id)
            logger.info(f"✅ Got peer entity for chat {chat_id}")
        except Exception as e:
            logger.error(f"❌ Failed to get entity for chat {chat_id}: {e}")
            # Fallback: пробуем напрямую получить сообщение
            peer = chat_id

        # Получаем сообщение по ID
        message = await client.get_messages(peer, ids=message_id)

        if not message:
            raise RuntimeError(f"Message {message_id} not found in chat {chat_id}")

        # Проверяем наличие медиа
        if not message.media:
            raise RuntimeError(f"Message {message_id} has no media")

        # Определяем путь для сохранения
        output_path = DOWNLOAD_DIR / f"large_{message_id}.{file_extension}"

        # Скачиваем через Telethon (без лимитов!)
        logger.info(f"📥 Downloading to {output_path}...")
        await client.download_media(message, str(output_path))

        if not output_path.exists():
            raise RuntimeError("Download failed - file not found")

        file_size_mb = output_path.stat().st_size / 1024 / 1024
        logger.info(f"✅ Large file downloaded: {file_size_mb:.2f} MB")

        return str(output_path)

    except Exception as e:
        logger.error(f"❌ Error downloading large file: {e}")
        raise RuntimeError(f"Не удалось скачать файл через Telethon: {str(e)}")


async def close_telethon():
    """Закрытие Telethon клиента"""
    global _telethon_client
    if _telethon_client:
        await _telethon_client.disconnect()
        _telethon_client = None
        logger.info("Telethon client disconnected")
