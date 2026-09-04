import os
import re
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.downloader import Downloader
from bot.services.groq_transcriber import GroqTranscriber
from bot.handlers.media import transcripts, audio_files, file_names

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

    status_msg = await message.answer("Принял, обрабатываю...")

    try:
        print(f"[YouTube] Начинаем скачивание через @DiggerDigitalBot: {message.text}")
        await status_msg.edit_text("⬇️ Скачиваю аудио с YouTube через @DiggerDigitalBot...")

        # Используем Telethon + @DiggerDigitalBot для скачивания
        audio_path = await downloader.download_audio_from_url_youtube(message.text)

        if not audio_path:
            raise RuntimeError("Не удалось скачать аудио")

        print(f"[YouTube] Аудио скачано: {audio_path}")

        # Проверяем размер и сжимаем если нужно (для Groq API лимит 25 МБ)
        await status_msg.edit_text("🔄 Проверяю размер файла...")
        print(f"[YouTube] ПЕРЕД сжатием: {audio_path}")

        from bot.services.audio_converter import compress_audio_if_needed

        try:
            audio_path = await compress_audio_if_needed(audio_path)
            print(f"[YouTube] ✅ ПОСЛЕ сжатия: {audio_path}")
        except Exception as compress_error:
            print(f"[YouTube] ❌ ОШИБКА сжатия: {compress_error}")
            import traceback
            traceback.print_exc()
            # Продолжаем с оригинальным файлом (хотя Groq откажет, но увидим ошибку)

        print(f"[YouTube] Финальный файл для транскрибации: {audio_path}")

        audio_files[message.message_id] = audio_path

        await status_msg.edit_text("🎤 Транскрибирую...")
        print(f"[YouTube] Начинаем транскрибацию: {audio_path}")

        transcript = await transcriber.transcribe_verbatim(audio_path)

        print(f"[YouTube] Транскрибация завершена, длина текста: {len(transcript)}")
        transcripts[message.message_id] = transcript

        # Сохраняем имя файла для экспорта (используем ID видео из URL)
        video_id = match.group(5)  # ID видео из regex
        file_names[message.message_id] = f"youtube_{video_id}"

        # Импортируем функцию создания клавиатуры
        from bot.handlers.media import get_export_keyboard
        keyboard = get_export_keyboard(message.message_id)

        # Telegram лимит: 4096 символов на сообщение
        # Если текст длиннее, разбиваем на части
        MAX_MESSAGE_LENGTH = 4000  # Оставляем запас для заголовка

        if len(transcript) <= MAX_MESSAGE_LENGTH:
            # Короткий текст — отправляем одним сообщением
            await message.answer(f"📝 Дословно:\n\n{transcript}", reply_markup=keyboard)
        else:
            # Длинный текст — разбиваем на части
            # Первое сообщение с кнопками
            first_part = transcript[:MAX_MESSAGE_LENGTH]
            await message.answer(f"📝 Дословно (часть 1):\n\n{first_part}", reply_markup=keyboard)

            # Остальные части без кнопок
            remaining = transcript[MAX_MESSAGE_LENGTH:]
            part_num = 2

            while remaining:
                chunk = remaining[:MAX_MESSAGE_LENGTH]
                remaining = remaining[MAX_MESSAGE_LENGTH:]
                await message.answer(f"📝 Дословно (часть {part_num}):\n\n{chunk}")
                part_num += 1

            print(f"[YouTube] Текст разбит на {part_num - 1} частей")

    except Exception as e:
        print(f"[YouTube] Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        await message.answer(f"❌ Ошибка при скачивании или обработке: {str(e)}")
        if 'audio_path' in locals() and audio_path:
            downloader.cleanup(audio_path)
