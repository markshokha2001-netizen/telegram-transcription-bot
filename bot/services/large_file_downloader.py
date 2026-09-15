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


async def download_large_file_via_forward(bot, message, file_extension: str = "tmp", file_size_mb: float = 0) -> str:
    """
    Скачивает большой файл через Telethon Client API (обход лимита Bot API в 50 МБ)

    Алгоритм:
    1. Bot пересылает файл владельцу (в Saved Messages Telethon-аккаунта)
    2. Telethon скачивает файл из своих Saved Messages (без лимитов)
    3. Telethon удаляет пересланное сообщение (cleanup)

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
        logger.info(f"🔽 Downloading large file via forward to owner: size={file_size_mb:.1f} MB")

        # Шаг 1: Бот пересылает файл владельцу (вашему личному аккаунту)
        logger.info(f"📤 Forwarding message to owner (user_id={OWNER_USER_ID})...")
        forwarded = await bot.forward_message(
            chat_id=OWNER_USER_ID,  # Бот пересылает вам
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

        logger.info(f"✅ Message forwarded to owner, new message_id={forwarded.message_id}")

        # Шаг 2: Telethon (ваш аккаунт) получает доступ к пересланному файлу в своих сообщениях
        import asyncio
        await asyncio.sleep(2)  # Даём время на доставку сообщения

        logger.info(f"🔍 Telethon: getting messages from 'me' (Saved Messages)...")

        # Получаем последние сообщения из Saved Messages (ищем наш файл)
        async for msg in client.iter_messages('me', limit=10):
            if msg.id == forwarded.message_id or (msg.media and (msg.audio or msg.video or msg.document)):
                logger.info(f"✅ Found message with media: msg_id={msg.id}")

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

                # Удаляем пересланное сообщение из Saved Messages
                try:
                    await client.delete_messages('me', msg.id)
                    logger.info("🗑️ Deleted forwarded message from Saved Messages")
                except:
                    pass  # Не критично

                return str(output_path)

        raise RuntimeError("File not found in owner's messages")

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
