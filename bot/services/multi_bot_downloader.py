"""
Универсальный загрузчик аудио через несколько Telegram-ботов параллельно
Поддерживает автоматическую обработку кнопок
"""
import asyncio
import uuid
import logging
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeFilename
import os

logger = logging.getLogger(__name__)

# Telegram API credentials
API_ID = int(os.getenv("TELEGRAM_API_ID", "38923554"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "bd666a5f2fc702fed3e7c32bc411a696")
PHONE = os.getenv("TELEGRAM_PHONE", "+79113583410")

# Список ботов для скачивания (будем пробовать параллельно)
DOWNLOAD_BOTS = [
    {
        "username": "SaveTubeMediaBot",
        "button_text": ["Audio", "Аудио", "MP3"],  # Возможные тексты кнопки
        "wait_for_button": True,  # Нужно ли ждать кнопку
    },
    {
        "username": "SaveFromVkBot",
        "button_text": ["Audio", "Аудио", "MP3"],
        "wait_for_button": True,
    },
    {
        "username": "skachaesh_bot",
        "button_text": ["Audio", "Аудио", "MP3"],
        "wait_for_button": True,
    },
    {
        "username": "DiggerDigitalBot",
        "button_text": None,  # Не требует кнопок, сразу отправляет аудио
        "wait_for_button": False,
    }
]

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
        session_string = os.getenv("TELEGRAM_SESSION")

        if session_string:
            _telethon_client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
            logger.info("📱 Multi-bot loader: Using StringSession")
        else:
            session_path = Path(__file__).parent.parent.parent / "session.session"
            _telethon_client = TelegramClient(str(session_path), API_ID, API_HASH)
            logger.info("📁 Multi-bot loader: Using file session")

        await _telethon_client.start(phone=PHONE)
        logger.info("✅ Multi-bot loader: Telethon connected")
        return _telethon_client

    except Exception as e:
        logger.error(f"❌ Failed to start Telethon: {e}")
        raise


async def download_from_single_bot(client, bot_config: dict, url: str, request_id: str):
    """
    Пытается скачать аудио через один бот

    Returns: (success: bool, file_path: str | None, error: str | None)
    """
    bot_username = bot_config["username"]

    try:
        logger.info(f"[{request_id}] Trying @{bot_username}...")

        # Отправляем ссылку боту
        await client.send_message(bot_username, url)
        logger.info(f"[{request_id}] Sent URL to @{bot_username}")

        # Запоминаем ID последнего сообщения
        messages_before = await client.get_messages(bot_username, limit=1)
        last_message_id = messages_before[0].id if messages_before else 0

        # Ждём ответа (макс 60 секунд на первый ответ)
        timeout = 60
        check_interval = 3
        elapsed = 0

        while elapsed < timeout:
            await asyncio.sleep(check_interval)
            elapsed += check_interval

            # Проверяем новые сообщения
            async for message in client.iter_messages(bot_username, limit=5):
                if message.id <= last_message_id:
                    continue

                logger.info(f"[{request_id}] @{bot_username} response: has_audio={bool(message.audio)}, has_document={bool(message.document)}, has_button={bool(message.buttons)}")

                # Если бот прислал аудио сразу
                if message.audio or (message.document and message.document.mime_type and 'audio' in message.document.mime_type):
                    logger.info(f"[{request_id}] @{bot_username} sent audio directly!")

                    filename = f"youtube_{request_id}.mp3"
                    download_path = DOWNLOAD_DIR / filename

                    await message.download_media(str(download_path))
                    size_mb = download_path.stat().st_size / 1024 / 1024
                    logger.info(f"[{request_id}] ✅ Downloaded from @{bot_username}: {size_mb:.2f} MB")

                    return (True, str(download_path), None)

                # Если бот прислал кнопки — нажимаем кнопку "Аудио"
                if message.buttons and bot_config["wait_for_button"]:
                    logger.info(f"[{request_id}] @{bot_username} sent buttons, looking for audio button...")

                    # Ищем кнопку с текстом про аудио
                    for row in message.buttons:
                        for button in row:
                            button_text = button.text.lower()
                            logger.info(f"[{request_id}] Button text: {button.text}")

                            # Проверяем, содержит ли кнопка нужный текст
                            if any(keyword.lower() in button_text for keyword in bot_config["button_text"]):
                                logger.info(f"[{request_id}] Clicking audio button: {button.text}")

                                # Нажимаем кнопку
                                await message.click(data=button.data)

                                # Ждём аудио после нажатия кнопки (макс 120 секунд)
                                audio_timeout = 120
                                audio_elapsed = 0

                                while audio_elapsed < audio_timeout:
                                    await asyncio.sleep(5)
                                    audio_elapsed += 5

                                    # Ищем аудио после нажатия кнопки
                                    async for msg in client.iter_messages(bot_username, limit=10):
                                        if msg.id <= message.id:
                                            continue

                                        if msg.audio or (msg.document and msg.document.mime_type and 'audio' in msg.document.mime_type):
                                            logger.info(f"[{request_id}] @{bot_username} sent audio after button click!")

                                            filename = f"youtube_{request_id}.mp3"
                                            download_path = DOWNLOAD_DIR / filename

                                            await msg.download_media(str(download_path))
                                            size_mb = download_path.stat().st_size / 1024 / 1024
                                            logger.info(f"[{request_id}] ✅ Downloaded from @{bot_username}: {size_mb:.2f} MB")

                                            return (True, str(download_path), None)

                                raise RuntimeError(f"@{bot_username}: No audio after button click")

        raise RuntimeError(f"@{bot_username}: Timeout waiting for response")

    except Exception as e:
        logger.warning(f"[{request_id}] @{bot_username} failed: {e}")
        return (False, None, str(e))


async def download_from_multiple_bots(url: str) -> str:
    """
    Отправляет ссылку нескольким ботам параллельно и возвращает первый полученный аудиофайл

    Args:
        url: ссылка на YouTube/VK/и т.д.

    Returns:
        Путь к скачанному аудиофайлу
    """
    client = await init_telethon()

    if not client or not client.is_connected():
        raise RuntimeError("Telethon client not connected")

    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Starting parallel download from {len(DOWNLOAD_BOTS)} bots")

    # Запускаем скачивание через все боты параллельно
    tasks = [
        download_from_single_bot(client, bot_config, url, request_id)
        for bot_config in DOWNLOAD_BOTS
    ]

    # Ждём первого успешного результата
    for completed_task in asyncio.as_completed(tasks):
        success, file_path, error = await completed_task

        if success and file_path:
            logger.info(f"[{request_id}] ✅ Got audio! Cancelling other bots...")

            # Отменяем остальные задачи
            for task in tasks:
                if not task.done():
                    task.cancel()

            return file_path

    # Если ни один бот не сработал
    raise RuntimeError(f"Не удалось скачать аудио ни через одного бота. Попробуйте другую ссылку.")


async def close_telethon():
    """Закрытие Telethon клиента"""
    global _telethon_client
    if _telethon_client:
        await _telethon_client.disconnect()
        _telethon_client = None
        logger.info("Multi-bot loader: Telethon disconnected")
