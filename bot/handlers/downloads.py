import os
import re
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from bot.services.downloader import Downloader
from bot.handlers.menu import get_main_menu

router = Router()
downloader = Downloader()

# Регулярка для YouTube
URL_REGEX = re.compile(
    r'(https?://)?(www\.)?(youtube\.com|youtu\.be|m\.youtube\.com)/'
    r'(watch\?v=|embed/|v/|shorts/)?([a-zA-Z0-9_-]{11})'
)

# Состояния для отслеживания режимов работы
user_modes = {}  # {user_id: "download_youtube" | "video_to_audio" | None}


# Обработчик YouTube ссылок для скачивания (режим "📥 Скачать с YouTube")
@router.message(F.text)
async def handle_youtube_download_link(message: Message):
    """Скачивание видео с YouTube (без транскрибации)"""

    # Проверяем, находится ли пользователь в режиме скачивания
    user_id = message.from_user.id
    if user_modes.get(user_id) != "download_youtube":
        return  # Не наш режим

    if not message.text:
        return

    match = URL_REGEX.search(message.text)
    if not match:
        await message.answer("❌ Это не похоже на ссылку YouTube. Попробуйте ещё раз.")
        return

    status_msg = await message.answer("📥 Скачиваю видео с YouTube...")

    try:
        print(f"[Download] Начинаем скачивание видео: {message.text}")

        # Используем Telethon + @DiggerDigitalBot для скачивания
        video_path = await downloader.download_video_from_url_youtube(message.text)

        if not video_path:
            raise RuntimeError("Не удалось скачать видео")

        print(f"[Download] Видео скачано: {video_path}")

        # Проверяем размер
        file_size = os.path.getsize(video_path) / (1024 * 1024)  # МБ

        if file_size > 200:
            await status_msg.edit_text(
                f"❌ Видео слишком большое ({file_size:.1f} МБ)\n\n"
                f"Максимальный размер: 200 МБ"
            )
            downloader.cleanup(video_path)
            # Сбрасываем режим
            user_modes[user_id] = None
            return

        # Отправляем видео
        await status_msg.edit_text(f"📤 Отправляю видео ({file_size:.1f} МБ)...")

        file = FSInputFile(video_path)
        await message.answer_document(
            file,
            caption=f"📥 Видео с YouTube ({file_size:.1f} МБ)",
            reply_markup=get_main_menu()
        )

        await status_msg.delete()

        # Удаляем файл после отправки
        import asyncio
        await asyncio.sleep(2)
        downloader.cleanup(video_path)

        # Сбрасываем режим
        user_modes[user_id] = None

        await message.answer(
            "✅ Готово! Выберите новое действие из меню:",
            reply_markup=get_main_menu()
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка при скачивании: {str(e)}")
        print(f"[Download] Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        # Сбрасываем режим
        user_modes[user_id] = None


# Обработчик видео для конвертации в аудио (режим "🔄 Видео → Аудио")
@router.message(F.video)
async def handle_video_to_audio(message: Message):
    """Конвертация видео в аудио"""

    # Проверяем, находится ли пользователь в режиме конвертации
    user_id = message.from_user.id
    if user_modes.get(user_id) != "video_to_audio":
        return  # Не наш режим

    status_msg = await message.answer("🔄 Конвертирую видео в аудио...")

    try:
        # Скачиваем видео
        file = await message.bot.download(message.video)

        # Сохраняем временный файл
        video_path = f"downloads/video_{message.message_id}.mp4"
        os.makedirs("downloads", exist_ok=True)

        with open(video_path, 'wb') as f:
            f.write(file.read())

        print(f"[VideoToAudio] Видео сохранено: {video_path}")

        # Извлекаем аудио через ffmpeg
        audio_path = f"downloads/audio_{message.message_id}.mp3"

        import asyncio
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i", video_path,
            "-vn",  # Без видео
            "-acodec", "libmp3lame",  # MP3 кодек
            "-q:a", "2",  # Качество
            "-y",  # Перезаписать если существует
            audio_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await process.communicate()

        if not os.path.exists(audio_path):
            raise RuntimeError("Не удалось извлечь аудио")

        print(f"[VideoToAudio] Аудио извлечено: {audio_path}")

        # Проверяем размер
        file_size = os.path.getsize(audio_path) / (1024 * 1024)  # МБ

        # Отправляем аудио
        await status_msg.edit_text(f"📤 Отправляю аудио ({file_size:.1f} МБ)...")

        file = FSInputFile(audio_path)
        await message.answer_document(
            file,
            caption=f"🔄 Аудио из видео ({file_size:.1f} МБ)",
            reply_markup=get_main_menu()
        )

        await status_msg.delete()

        # Удаляем файлы после отправки
        await asyncio.sleep(2)
        downloader.cleanup(video_path)
        downloader.cleanup(audio_path)

        # Сбрасываем режим
        user_modes[user_id] = None

        await message.answer(
            "✅ Готово! Выберите новое действие из меню:",
            reply_markup=get_main_menu()
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка при конвертации: {str(e)}")
        print(f"[VideoToAudio] Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        # Сбрасываем режим
        user_modes[user_id] = None
