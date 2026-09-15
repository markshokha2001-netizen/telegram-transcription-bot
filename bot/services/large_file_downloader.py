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

# ID владельца бота (для пересылки больших файлов)
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "6048223351"))  # Ваш Telegram user ID

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


async def download_large_file_direct(bot, message, file_extension: str = "tmp", file_size_mb: float = 0) -> str:
    """
    Скачивает большой файл через Telethon напрямую по file_unique_id (обход лимита Bot API)

    Алгоритм:
    1. Получаем file_unique_id из Bot API (aiogram)
    2. Telethon скачивает файл напрямую по этому ID (без пересылки)

    Args:
        bot: aiogram Bot instance
        message: aiogram Message с файлом
        file_extension: расширение файла (mp3, mp4, ogg и т.д.)
        file_size_mb: размер файла в МБ (для логирования)

    Returns:
        Путь к скачанному файлу
    """
    client = await init_telethon()

    if not client or not client.is_connected():
        raise RuntimeError("Telethon client not connected")

    try:
        logger.info(f"🔽 Downloading large file directly via Telethon: size={file_size_mb:.1f} MB")

        # Получаем file_id из сообщения
        if message.audio:
            file_id = message.audio.file_id
        elif message.video:
            file_id = message.video.file_id
        elif message.document:
            file_id = message.document.file_id
        else:
            raise RuntimeError("No audio/video/document found in message")

        logger.info(f"📄 File ID: {file_id[:30]}...")

        # Bot API не может скачать файл >50 МБ, но мы можем получить file_reference
        # через getFile и передать его в Telethon

        # Получаем полную информацию о файле через Bot API
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path  # путь на серверах Telegram

        logger.info(f"📍 File path on Telegram servers: {file_path}")

        # Telethon может скачать файл по file_path напрямую
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        output_path = DOWNLOAD_DIR / f"large_{unique_id}.{file_extension}"

        logger.info(f"📥 Downloading via Telethon to {output_path}...")

        # Используем Telethon для скачивания через InputFileLocation
        from telethon.tl.types import InputDocumentFileLocation

        # Для больших файлов используем прямое скачивание
        # Получаем message через Telethon чтобы получить правильный Document
        bot_username = (await bot.get_me()).username
        logger.info(f"🤖 Bot username: @{bot_username}")

        # Ищем сообщение в чате с ботом
        async for msg in client.iter_messages(f"@{bot_username}", limit=50):
            if msg.media and msg.id == message.message_id:
                logger.info(f"✅ Found message in Telethon: msg_id={msg.id}")

                # Скачиваем файл
                await client.download_media(msg, str(output_path))

                if not output_path.exists():
                    raise RuntimeError("Download failed - file not found")

                downloaded_size_mb = output_path.stat().st_size / 1024 / 1024
                logger.info(f"✅ Large file downloaded: {downloaded_size_mb:.2f} MB")

                return str(output_path)

        raise RuntimeError(f"Message {message.message_id} not found in bot's chat")

    except Exception as e:
        logger.error(f"❌ Error downloading large file: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Не удалось скачать файл через Telethon: {str(e)}")


async def close_telethon():
    """Закрытие Telethon клиента"""
    global _telethon_client
    if _telethon_client:
        await _telethon_client.disconnect()
        _telethon_client = None
        logger.info("Telethon client disconnected")
