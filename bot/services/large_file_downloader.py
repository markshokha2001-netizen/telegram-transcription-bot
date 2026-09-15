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


async def download_large_file_direct(message, file_extension: str = "tmp", file_size_mb: float = 0) -> str:
    """
    Скачивает большой файл через Telethon напрямую из чата пользователя

    Telethon (личный аккаунт) может читать сообщения в любом чате, где есть доступ.
    Пользователь отправляет файл боту → Telethon читает его из того же чата → скачивает.

    Args:
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
        logger.info(f"🔽 Downloading large file via Telethon from user chat: size={file_size_mb:.1f} MB")

        # Получаем user_id отправителя (владелец бота)
        user_id = message.from_user.id
        message_id = message.message_id

        logger.info(f"📍 Looking for message_id={message_id} in user chat={user_id}")

        # Ищем сообщение в чате пользователя
        # Telethon (ваш аккаунт) может читать ваши собственные сообщения
        msg = await client.get_messages(user_id, ids=message_id)

        if not msg:
            logger.warning(f"⚠️ Message {message_id} not found by ID, searching recent messages...")

            # Fallback: ищем по размеру среди последних сообщений
            async for m in client.iter_messages(user_id, limit=30):
                if m.media and (m.audio or m.document or m.video):
                    file_size = 0
                    if m.audio and hasattr(m.audio, 'size'):
                        file_size = m.audio.size
                    elif m.document and hasattr(m.document, 'size'):
                        file_size = m.document.size
                    elif m.video and hasattr(m.video, 'size'):
                        file_size = m.video.size

                    size_mb = file_size / 1024 / 1024

                    # Ищем файл примерно такого же размера
                    if abs(size_mb - file_size_mb) / max(file_size_mb, 1) < 0.2:  # 20% допуск
                        logger.info(f"✅ Found matching file: size={size_mb:.1f} MB ≈ {file_size_mb:.1f} MB")
                        msg = m
                        break

        if not msg:
            raise RuntimeError(f"Message with audio not found in user chat {user_id}")

        if not msg.media:
            raise RuntimeError(f"Message {message_id} has no media")

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
