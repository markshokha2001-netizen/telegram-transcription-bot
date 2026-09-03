import os
from pathlib import Path
from pyrogram import Client
from bot.config import API_ID, API_HASH, TELEGRAM_BOT_TOKEN


class FileDownloader:
    """Скачивает большие файлы через Pyrogram (MTProto API)"""

    def __init__(self):
        self.app = None
        self._started = False

    async def init_client(self):
        """Инициализирует Pyrogram клиент (если ещё не инициализирован)"""
        if self.app is None:
            self.app = Client(
                "bot_session",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=TELEGRAM_BOT_TOKEN,
                workdir="downloads"
            )

        if not self._started:
            await self.app.start()
            self._started = True

    async def download_file(self, message) -> str:
        """
        Скачивает файл из сообщения через Pyrogram.
        Работает с файлами до 2 ГБ.

        Args:
            message: Telegram message объект из aiogram

        Returns:
            Путь к скачанному файлу
        """
        await self.init_client()

        # Определяем тип файла и расширение
        if message.audio:
            file_id = message.audio.file_id
            extension = Path(message.audio.file_name or "audio.mp3").suffix
        elif message.voice:
            file_id = message.voice.file_id
            extension = ".ogg"
        elif message.video:
            file_id = message.video.file_id
            extension = ".mp4"
        else:
            raise ValueError("Unsupported message type")

        destination = f"downloads/{file_id}{extension}"
        os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)

        # Скачивание через Pyrogram - используем message_id вместо file_id
        # потому что Pyrogram работает по-другому
        downloaded_path = await self.app.download_media(
            f"bot{TELEGRAM_BOT_TOKEN.split(':')[0]}_{message.message_id}",
            file_name=destination
        )

        return downloaded_path or destination

    async def close(self):
        """Закрывает Pyrogram клиент"""
        if self.app and self._started:
            await self.app.stop()
            self._started = False


# Глобальный инстанс для переиспользования
file_downloader = FileDownloader()
