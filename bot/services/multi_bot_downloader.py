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
        "button_sequence": [
            {"text": ["Скачать аудио", "Audio"], "wait_after": 5}  # Одна кнопка
        ],
    },
    {
        "username": "SaveFromVkBot",
        "button_sequence": [
            {"text": ["Audio", "Аудио"], "wait_after": 5}  # Одна кнопка
        ],
    },
    {
        "username": "skachaesh_bot",
        "button_sequence": [
            {"text": ["m4a"], "wait_after": 3},  # Сначала формат
            {"text": ["Original", "Русский"], "wait_after": 5}  # Потом язык
        ],
    },
    {
        "username": "DiggerDigitalBot",
        "button_sequence": None,  # Не требует кнопок, сразу отправляет аудио
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

        # Если бот не требует кнопок (DiggerDigitalBot)
        if bot_config["button_sequence"] is None:
            logger.info(f"[{request_id}] @{bot_username}: waiting for direct audio...")

            timeout = 120
            check_interval = 5
            elapsed = 0

            while elapsed < timeout:
                await asyncio.sleep(check_interval)
                elapsed += check_interval

                async for message in client.iter_messages(bot_username, limit=5):
                    if message.id <= last_message_id:
                        continue

                    if message.audio or (message.document and message.document.mime_type and 'audio' in message.document.mime_type):
                        logger.info(f"[{request_id}] @{bot_username} sent audio!")

                        filename = f"youtube_{request_id}.mp3"
                        download_path = DOWNLOAD_DIR / filename

                        await message.download_media(str(download_path))
                        size_mb = download_path.stat().st_size / 1024 / 1024
                        logger.info(f"[{request_id}] ✅ Downloaded from @{bot_username}: {size_mb:.2f} MB")

                        return (True, str(download_path), None)

            raise RuntimeError(f"@{bot_username}: No audio received")

        # Бот требует последовательность кнопок
        current_message_id = last_message_id

        for step_num, button_step in enumerate(bot_config["button_sequence"], 1):
            logger.info(f"[{request_id}] @{bot_username} step {step_num}: looking for button {button_step['text']}")

            # Ждём сообщение с кнопками
            timeout = 60
            check_interval = 3
            elapsed = 0
            found_button = False

            while elapsed < timeout and not found_button:
                await asyncio.sleep(check_interval)
                elapsed += check_interval

                async for message in client.iter_messages(bot_username, limit=5):
                    if message.id <= current_message_id:
                        continue

                    # Проверяем, может это уже аудио (некоторые боты сразу отправляют)
                    if message.audio or (message.document and message.document.mime_type and 'audio' in message.document.mime_type):
                        logger.info(f"[{request_id}] @{bot_username} sent audio directly!")

                        filename = f"youtube_{request_id}.mp3"
                        download_path = DOWNLOAD_DIR / filename

                        await message.download_media(str(download_path))
                        size_mb = download_path.stat().st_size / 1024 / 1024
                        logger.info(f"[{request_id}] ✅ Downloaded from @{bot_username}: {size_mb:.2f} MB")

                        return (True, str(download_path), None)

                    # Ищем кнопку
                    if message.buttons:
                        for row in message.buttons:
                            for button in row:
                                button_text = button.text.lower()

                                # Проверяем, содержит ли кнопка нужный текст
                                if any(keyword.lower() in button_text for keyword in button_step["text"]):
                                    logger.info(f"[{request_id}] @{bot_username} clicking button: {button.text}")

                                    # Нажимаем кнопку
                                    await message.click(data=button.data)
                                    current_message_id = message.id
                                    found_button = True

                                    # Ждём после нажатия
                                    await asyncio.sleep(button_step["wait_after"])
                                    break
                            if found_button:
                                break
                        if found_button:
                            break

            if not found_button:
                raise RuntimeError(f"@{bot_username}: Button not found at step {step_num}")

        # После всех кнопок ждём аудио
        logger.info(f"[{request_id}] @{bot_username}: all buttons clicked, waiting for audio...")

        timeout = 120
        check_interval = 5
        elapsed = 0

        while elapsed < timeout:
            await asyncio.sleep(check_interval)
            elapsed += check_interval

            async for message in client.iter_messages(bot_username, limit=10):
                if message.id <= current_message_id:
                    continue

                if message.audio or (message.document and message.document.mime_type and 'audio' in message.document.mime_type):
                    logger.info(f"[{request_id}] @{bot_username} sent audio after buttons!")

                    filename = f"youtube_{request_id}.mp3"
                    download_path = DOWNLOAD_DIR / filename

                    await message.download_media(str(download_path))
                    size_mb = download_path.stat().st_size / 1024 / 1024
                    logger.info(f"[{request_id}] ✅ Downloaded from @{bot_username}: {size_mb:.2f} MB")

                    return (True, str(download_path), None)

        raise RuntimeError(f"@{bot_username}: No audio after buttons")

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

    # Создаём Task объекты (не корутины!)
    tasks = [
        asyncio.create_task(download_from_single_bot(client, bot_config, url, request_id))
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
