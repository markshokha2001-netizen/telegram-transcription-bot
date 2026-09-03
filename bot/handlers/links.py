import os
import re
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.downloader import Downloader
from bot.services.groq_transcriber import GroqTranscriber
from bot.handlers.media import transcripts, audio_files

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

    await message.answer("Принял, обрабатываю...")

    try:
        audio_path = await downloader.download_audio_from_url(message.text)

        if not audio_path:
            raise RuntimeError("Не удалось скачать аудио")

        audio_files[message.message_id] = audio_path

        transcript = await transcriber.transcribe_verbatim(audio_path)

        transcripts[message.message_id] = transcript

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Сделать конспект", callback_data=f"summary_{message.message_id}")],
            [InlineKeyboardButton(text="🎵 Прислать аудио отдельно", callback_data=f"audio_{message.message_id}")]
        ])

        await message.answer(f"📝 Дословно:\n\n{transcript}", reply_markup=keyboard)

    except Exception as e:
        await message.answer(f"❌ Ошибка при скачивании или обработке: {str(e)}")
        if 'audio_path' in locals() and audio_path:
            downloader.cleanup(audio_path)
