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
        print(f"[YouTube] Начинаем скачивание через yt-dlp (Android client): {message.text}")
        await status_msg.edit_text("⬇️ Скачиваю аудио с YouTube...")

        # Используем yt-dlp с параметрами для обхода блокировок YouTube
        audio_path = await downloader.download_audio_from_url_youtube(message.text)

        if not audio_path:
            raise RuntimeError("Не удалось скачать аудио")

        print(f"[YouTube] Аудио скачано: {audio_path}")
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

        await message.answer(f"📝 Дословно:\n\n{transcript}", reply_markup=keyboard)

    except Exception as e:
        print(f"[YouTube] Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        await message.answer(f"❌ Ошибка при скачивании или обработке: {str(e)}")
        if 'audio_path' in locals() and audio_path:
            downloader.cleanup(audio_path)
