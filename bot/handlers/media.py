import os
import asyncio
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.downloader import Downloader
from bot.services.groq_transcriber import GroqTranscriber
from bot.services.export import Exporter
from bot.services.large_file_downloader import download_large_file_via_forward
import logging

router = Router()
downloader = Downloader()
exporter = Exporter()
logger = logging.getLogger(__name__)

# Используем только Groq для деплоя (быстро, онлайн)
transcriber = GroqTranscriber()

# Хранилище для связи между транскриптами и исходными файлами
transcripts = {}
audio_files = {}
file_names = {}  # Хранилище для имён исходных файлов

# Стандартный лимит Telegram Bot API
MAX_FILE_SIZE_BOT_API = 50 * 1024 * 1024  # 50 МБ - лимит Bot API
MAX_MESSAGE_LENGTH = 4000  # Лимит Telegram 4096, оставляем запас для заголовка


def get_export_keyboard(message_id: int) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру с кнопками экспорта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 TXT", callback_data=f"export_txt_{message_id}"),
            InlineKeyboardButton(text="📘 DOCX", callback_data=f"export_docx_{message_id}"),
            InlineKeyboardButton(text="📕 PDF", callback_data=f"export_pdf_{message_id}")
        ],
        [
            InlineKeyboardButton(text="✨ AI-исправление", callback_data=f"ai_fix_{message_id}"),
            InlineKeyboardButton(text="🤖 Конспект", callback_data=f"summary_{message_id}")
        ],
        [
            InlineKeyboardButton(text="✅ Завершить сессию", callback_data="end_session")
        ]
    ])


async def send_long_transcript(message: Message, transcript: str, keyboard: InlineKeyboardMarkup):
    """Отправляет транскрипт, разбивая на части если он длинный"""
    if len(transcript) <= MAX_MESSAGE_LENGTH:
        # Короткий текст — отправляем одним сообщением с кнопками
        await message.answer(f"📝 Дословно:\n\n{transcript}", reply_markup=keyboard)
    else:
        # Длинный текст — разбиваем на части
        parts = []
        remaining = transcript

        while remaining:
            chunk = remaining[:MAX_MESSAGE_LENGTH]
            remaining = remaining[MAX_MESSAGE_LENGTH:]
            parts.append(chunk)

        # Отправляем все части текста
        for i, part in enumerate(parts, 1):
            await message.answer(f"📝 Дословно (часть {i}/{len(parts)}):\n\n{part}")

        # Последнее сообщение с кнопками
        await message.answer(
            f"✅ Транскрибация завершена ({len(parts)} частей, {len(transcript)} символов)\n\n"
            f"Используйте кнопки ниже для экспорта или создания конспекта:",
            reply_markup=keyboard
        )


@router.message(F.voice)
async def handle_voice(message: Message):
    """Обработка голосовых сообщений"""
    duration = message.voice.duration or 0
    status_msg = await message.answer(
        f"Принял, обрабатываю...\n"
        f"Длительность: {duration//60}:{duration%60:02d}\n"
        f"⏳ Транскрибирую..."
    )

    try:
        file = await message.bot.get_file(message.voice.file_id)
        file_path = f"downloads/{message.voice.file_id}.ogg"
        os.makedirs("downloads", exist_ok=True)

        # Скачивание через стандартный aiogram
        await message.bot.download_file(file.file_path, file_path)

        transcript = await transcriber.transcribe_verbatim(file_path)

        transcripts[message.message_id] = transcript
        file_names[message.message_id] = "voice_message"  # Голосовые сообщения не имеют имени

        keyboard = get_export_keyboard(message.message_id)

        await send_long_transcript(message, transcript, keyboard)

        downloader.cleanup(file_path)

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Ошибка обработки голосового: {error_detail}")
        await message.answer(f"❌ Ошибка при обработке: {str(e)}")


@router.message(F.audio)
async def handle_audio(message: Message):
    """Обработка аудиофайлов"""
    file_size_mb = message.audio.file_size / 1024 / 1024 if message.audio.file_size else 0
    duration = message.audio.duration or 0

    # Определяем метод скачивания
    use_telethon = message.audio.file_size and message.audio.file_size > MAX_FILE_SIZE_BOT_API

    status_msg = await message.answer(
        f"Принял, обрабатываю...\n"
        f"Размер: {file_size_mb:.1f} МБ, длительность: {duration//60}:{duration%60:02d}\n"
        f"{'🔄 Большой файл — использую Telethon Client API (без лимитов)' if use_telethon else '⏳ Скачиваю через Bot API...'}"
    )

    try:
        file_extension = Path(message.audio.file_name or "audio.mp3").suffix
        os.makedirs("downloads", exist_ok=True)

        if use_telethon:
            # Большой файл — скачиваем через Telethon (без лимитов!)
            logger.info(f"Audio file is {file_size_mb:.1f} MB (>{MAX_FILE_SIZE_BOT_API/1024/1024:.0f} MB) — using Telethon")
            await status_msg.edit_text(
                f"Файл большой ({file_size_mb:.1f} МБ)\n"
                f"📥 Скачиваю через Telethon Client API (без лимитов)..."
            )
            file_path = await download_large_file_via_forward(
                bot=message.bot,
                message=message,
                file_extension=file_extension.lstrip('.'),
                file_size_mb=file_size_mb
            )
        else:
            # Обычный файл — скачиваем через Bot API
            file = await message.bot.get_file(message.audio.file_id)
            file_path = f"downloads/{message.audio.file_id}{file_extension}"
            await message.bot.download_file(file.file_path, file_path)

        await status_msg.edit_text(
            f"Файл скачан ({file_size_mb:.1f} МБ)\n"
            f"🎤 Транскрибирую... это займёт время для больших файлов"
        )

        transcript = await transcriber.transcribe_verbatim(file_path)

        transcripts[message.message_id] = transcript
        # Сохраняем имя файла без расширения
        original_name = Path(message.audio.file_name or "audio").stem
        file_names[message.message_id] = original_name

        keyboard = get_export_keyboard(message.message_id)

        await send_long_transcript(message, transcript, keyboard)

        downloader.cleanup(file_path)

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Ошибка обработки аудио: {error_detail}")
        await message.answer(f"❌ Ошибка при обработке: {str(e)}\n\nЕсли файл большой, попробуйте включить USE_GROQ=true для быстрой транскрибации.")


@router.message(F.video)
async def handle_video(message: Message):
    """Обработка видеофайлов"""
    file_size_mb = message.video.file_size / 1024 / 1024 if message.video.file_size else 0
    duration = message.video.duration or 0

    # Определяем метод скачивания
    use_telethon = message.video.file_size and message.video.file_size > MAX_FILE_SIZE_BOT_API

    status_msg = await message.answer(
        f"Принял, обрабатываю...\n"
        f"Размер: {file_size_mb:.1f} МБ, длительность: {duration//60}:{duration%60:02d}\n"
        f"{'🔄 Большой файл — использую Telethon Client API (без лимитов)' if use_telethon else '⏳ Скачиваю через Bot API...'}"
    )

    try:
        os.makedirs("downloads", exist_ok=True)

        if use_telethon:
            # Большой файл — скачиваем через Telethon (без лимитов!)
            logger.info(f"Video file is {file_size_mb:.1f} MB (>{MAX_FILE_SIZE_BOT_API/1024/1024:.0f} MB) — using Telethon")
            await status_msg.edit_text(
                f"Файл большой ({file_size_mb:.1f} МБ)\n"
                f"📥 Скачиваю через Telethon Client API (без лимитов)..."
            )
            video_path = await download_large_file_via_forward(
                bot=message.bot,
                message=message,
                file_extension='mp4',
                file_size_mb=file_size_mb
            )
        else:
            # Обычный файл — скачиваем через Bot API
            file = await message.bot.get_file(message.video.file_id)
            video_path = f"downloads/{message.video.file_id}.mp4"
            await message.bot.download_file(file.file_path, video_path)

        await status_msg.edit_text(
            f"Видео скачано ({file_size_mb:.1f} МБ)\n"
            f"🎵 Извлекаю аудио..."
        )

        audio_path = await downloader.extract_audio_from_video(video_path)

        if not audio_path:
            raise RuntimeError("Не удалось извлечь аудио из видео")

        audio_files[message.message_id] = audio_path

        await status_msg.edit_text(
            f"Аудио извлечено\n"
            f"🎤 Транскрибирую... это займёт время для больших файлов"
        )

        transcript = await transcriber.transcribe_verbatim(audio_path)

        transcripts[message.message_id] = transcript
        # Сохраняем имя видеофайла без расширения
        original_name = Path(message.video.file_name or "video").stem if message.video.file_name else "video"
        file_names[message.message_id] = original_name

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 TXT", callback_data=f"export_txt_{message.message_id}"),
                InlineKeyboardButton(text="📘 DOCX", callback_data=f"export_docx_{message.message_id}"),
                InlineKeyboardButton(text="📕 PDF", callback_data=f"export_pdf_{message.message_id}")
            ],
            [
                InlineKeyboardButton(text="🤖 Сделать конспект", callback_data=f"summary_{message.message_id}")
            ],
            [
                InlineKeyboardButton(text="🎵 Прислать аудио отдельно", callback_data=f"audio_{message.message_id}")
            ]
        ])

        await send_long_transcript(message, transcript, keyboard)

        downloader.cleanup(video_path)

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Ошибка обработки видео: {error_detail}")
        await message.answer(f"❌ Ошибка при обработке: {str(e)}\n\nЕсли файл большой, попробуйте включить USE_GROQ=true для быстрой транскрибации.")
