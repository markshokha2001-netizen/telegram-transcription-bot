import os
import re
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.downloader import Downloader
from bot.services.groq_transcriber import GroqTranscriber
from bot.services.progress_bar import ProgressBar
from bot.handlers.media import transcripts, audio_files, file_names
import asyncio

router = Router()
downloader = Downloader()
# Используем только Groq для деплоя (быстро, онлайн)
transcriber = GroqTranscriber()

URL_REGEX = re.compile(
    r'(https?://)?(www\.)?(youtube\.com|youtu\.be|m\.youtube\.com)/'
    r'(watch\?v=|embed/|v/|shorts/)?([a-zA-Z0-9_-]{11})'
)


@router.message(F.text)
async def handle_link(message: Message):
    """Обработка текстовых сообщений со ссылками на YouTube"""

    if not message.text:
        return

    match = URL_REGEX.search(message.text)

    if not match:
        return

    # Проверяем режим пользователя — игнорируем, если в режиме скачивания
    from bot.handlers.downloads import user_modes
    user_id = message.from_user.id
    current_mode = user_modes.get(user_id)

    if current_mode == "download_youtube":
        return  # Пусть обработает downloads.py

    # Создаём прогресс-бар
    progress = ProgressBar(message)
    task_completed = False

    async def process():
        nonlocal task_completed
        try:
            print(f"[YouTube] Начинаем скачивание через @DiggerDigitalBot: {message.text}")

            # Используем Telethon + @DiggerDigitalBot для скачивания
            audio_path = await downloader.download_audio_from_url_youtube(message.text)

            if not audio_path:
                raise RuntimeError("Не удалось скачать аудио")

            print(f"[YouTube] Аудио скачано: {audio_path}")

            # Проверяем размер и сжимаем если нужно
            print(f"[YouTube] ПЕРЕД сжатием: {audio_path}")

            from bot.services.audio_converter import compress_audio_if_needed

            try:
                audio_path = await compress_audio_if_needed(audio_path)
                print(f"[YouTube] ✅ ПОСЛЕ сжатия: {audio_path}")
            except Exception as compress_error:
                print(f"[YouTube] ❌ ОШИБКА сжатия: {compress_error}")
                import traceback
                traceback.print_exc()

            print(f"[YouTube] Финальный файл для транскрибации: {audio_path}")

            audio_files[message.message_id] = audio_path

            print(f"[YouTube] Начинаем транскрибацию: {audio_path}")

            transcript = await transcriber.transcribe_verbatim(audio_path)

            print(f"[YouTube] Транскрибация завершена, длина текста: {len(transcript)}")
            transcripts[message.message_id] = transcript

            # Сохраняем имя файла для экспорта
            video_id = match.group(5)
            file_names[message.message_id] = f"youtube_{video_id}"

            # Импортируем функцию создания клавиатуры
            from bot.handlers.media import get_export_keyboard
            keyboard = get_export_keyboard(message.message_id)

            task_completed = True
            return (transcript, keyboard, audio_path)
        except Exception as e:
            task_completed = True
            raise e

    try:
        # Запускаем прогресс-бар
        progress_task = asyncio.create_task(progress.start(completion_check=lambda: task_completed))

        # Выполняем задачу
        transcript, keyboard, audio_path = await process()

        # Завершаем прогресс-бар
        await progress.complete()

        # Отправляем результат
        MAX_MESSAGE_LENGTH = 4000

        if len(transcript) <= MAX_MESSAGE_LENGTH:
            await message.answer(f"📝 Дословно:\n\n{transcript}", reply_markup=keyboard)
        else:
            # Длинный текст — разбиваем на части
            parts = []
            remaining = transcript

            while remaining:
                chunk = remaining[:MAX_MESSAGE_LENGTH]
                remaining = remaining[MAX_MESSAGE_LENGTH:]
                parts.append(chunk)

            for i, part in enumerate(parts, 1):
                await message.answer(f"📝 Дословно (часть {i}/{len(parts)}):\n\n{part}")

            await message.answer(
                f"✅ Транскрибация завершена ({len(parts)} частей, {len(transcript)} символов)\n\n"
                f"Используйте кнопки ниже для экспорта или создания конспекта:",
                reply_markup=keyboard
            )

            print(f"[YouTube] Текст разбит на {len(parts)} частей")

    except Exception as e:
        await progress.complete()
        print(f"[YouTube] Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        await message.answer(f"❌ Ошибка при скачивании или обработке: {str(e)}")
        if 'audio_path' in locals() and audio_path:
            downloader.cleanup(audio_path)
    finally:
        if 'progress_task' in locals() and not progress_task.done():
            progress_task.cancel()
