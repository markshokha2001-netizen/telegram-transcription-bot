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


async def download_large_file_direct(bot_username: str, message, file_extension: str = "tmp", file_size_mb: float = 0) -> str:
    """
    Скачивает большой файл через Telethon из чата с ботом

    Telethon (личный аккаунт) может читать ВСЕ свои чаты, включая чат с ботом.
    Ищем сообщение в диалоге "ваш аккаунт <-> бот".

    Args:
        bot_username: username бота (например "doslovnovslovo_bot")
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
        logger.info(f"🔽 Downloading large file via Telethon from bot chat: size={file_size_mb:.1f} MB")

        # Ищем сообщение в чате с ботом
        # Telethon видит все сообщения в диалоге "вы <-> бот", включая ВАШИ сообщения боту
        message_id = message.message_id

        logger.info(f"📍 Looking for message_id={message_id} in bot chat @{bot_username}")

        # Ищем в чате с ботом
        msg = None

        # Пробуем получить прямо по ID
        try:
            messages = await client.get_messages(f"@{bot_username}", ids=message_id)
            if messages and messages.media:
                msg = messages
                logger.info(f"✅ Found message by ID: {message_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not get message by ID: {e}")

        # Если не нашли по ID — ищем по размеру среди последних
        if not msg:
            logger.info(f"🔍 Searching recent messages in @{bot_username} chat...")

            async for m in client.iter_messages(f"@{bot_username}", limit=50):
                # Ищем ИСХОДЯЩИЕ сообщения (от вас боту) с медиа
                if m.out and m.media and (m.audio or m.document or m.video):
                    file_size = 0
                    if m.audio and hasattr(m.audio, 'size'):
                        file_size = m.audio.size
                    elif m.document and hasattr(m.document, 'size'):
                        file_size = m.document.size
                    elif m.video and hasattr(m.video, 'size'):
                        file_size = m.video.size

                    size_mb = file_size / 1024 / 1024
                    logger.info(f"  Checking outgoing msg_id={m.id}, size={size_mb:.1f} MB")

                    # Ищем файл примерно такого же размера
                    if abs(size_mb - file_size_mb) / max(file_size_mb, 1) < 0.2:  # 20% допуск
                        logger.info(f"✅ Found matching file: size={size_mb:.1f} MB ≈ {file_size_mb:.1f} MB")
                        msg = m
                        break

        if not msg:
            raise RuntimeError(f"Message with audio not found in bot chat @{bot_username}")

        if not msg.media:
            raise RuntimeError(f"Message has no media")

        logger.info(f"✅ Found message with media in Telethon")

        # Определяем путь для сохранения
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        output_path = DOWNLOAD_DIR / f"large_{unique_id}.{file_extension}"

        # Скачиваем через Telethon (без лимитов!)
        logger.info(f"📥 Downloading to {output_path}...")
        await client.download_media(msg, str(output_path))

        if not output_path.exists():
            raise RuntimeError("Download failed - file not found")

        downloaded_size_mb = output_path.stat().st_size / 1024 / 1024
        logger.info(f"✅ Large file downloaded: {downloaded_size_mb:.2f} MB")

        return str(output_path)

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
