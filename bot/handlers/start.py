from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка команды /start"""
    await message.answer(
        "👋 Привет! Я бот для транскрибации аудио и видео.\n\n"
        "Отправь мне:\n"
        "🎤 Голосовое сообщение\n"
        "🎵 Аудиофайл (mp3, wav, ogg, m4a, flac)\n"
        "🎬 Видеофайл\n"
        "🔗 Ссылку на YouTube\n\n"
        "Я переведу аудио в текст и смогу сделать краткий конспект с помощью ИИ."
    )
