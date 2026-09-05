from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

router = Router()

# Создаём главное меню
def get_main_menu():
    """Возвращает главное меню с кнопками"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Транскрибация YouTube")],
            [KeyboardButton(text="🎙️ Транскрибация аудио/видео")],
            [KeyboardButton(text="📥 Скачать с YouTube")],
            [KeyboardButton(text="🔄 Видео → Аудио")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )
    return keyboard


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "👋 Привет! Я бот для транскрибации и работы с медиа.\n\n"
        "Что я умею:\n"
        "🎬 Транскрибировать видео с YouTube\n"
        "🎙️ Транскрибировать аудио и видео файлы\n"
        "📥 Скачивать видео с YouTube\n"
        "🔄 Конвертировать видео в аудио\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_main_menu()
    )


# Обработчик кнопки "Завершить сессию"
@router.callback_query(F.data == "end_session")
async def handle_end_session(callback: CallbackQuery):
    """Обработчик завершения сессии"""
    await callback.answer()

    # Импортируем здесь, чтобы избежать циклического импорта
    from bot.handlers import downloads

    # Сбрасываем режим пользователя
    user_id = callback.from_user.id
    downloads.user_modes[user_id] = None

    await callback.message.answer(
        "✅ Сессия завершена!\n\n"
        "Выберите новое действие из меню:",
        reply_markup=get_main_menu()
    )


# Обработчики меню

@router.message(F.text == "🎬 Транскрибация YouTube")
async def menu_youtube_transcribe(message: Message):
    """Запрос на транскрибацию YouTube"""
    # Импортируем здесь, чтобы избежать циклического импорта
    from bot.handlers import downloads

    user_id = message.from_user.id
    downloads.user_modes[user_id] = None  # Обычный режим транскрибации

    await message.answer(
        "🎬 Пришлите ссылку на YouTube видео\n\n"
        "Я скачаю аудио и переведу его в текст дословно."
    )


@router.message(F.text == "🎙️ Транскрибация аудио/видео")
async def menu_media_transcribe(message: Message):
    """Запрос на транскрибацию файла"""
    # Импортируем здесь, чтобы избежать циклического импорта
    from bot.handlers import downloads

    user_id = message.from_user.id
    downloads.user_modes[user_id] = None  # Обычный режим транскрибации

    await message.answer(
        "🎙️ Отправьте мне:\n"
        "• Голосовое сообщение\n"
        "• Аудио файл (MP3, WAV, OGG, M4A)\n"
        "• Видео файл\n\n"
        "Я переведу его в текст дословно."
    )


@router.message(F.text == "📥 Скачать с YouTube")
async def menu_youtube_download(message: Message):
    """Запрос на скачивание видео"""
    # Импортируем здесь, чтобы избежать циклического импорта
    from bot.handlers import downloads

    user_id = message.from_user.id
    downloads.user_modes[user_id] = "download_youtube"  # Режим скачивания

    await message.answer(
        "📥 Пришлите ссылку на YouTube видео\n\n"
        "Я скачаю видео и отправлю вам файлом.\n\n"
        "⚠️ Максимальный размер: 200 МБ"
    )


@router.message(F.text == "🔄 Видео → Аудио")
async def menu_video_to_audio(message: Message):
    """Запрос на конвертацию видео в аудио"""
    # Импортируем здесь, чтобы избежать циклического импорта
    from bot.handlers import downloads

    user_id = message.from_user.id
    downloads.user_modes[user_id] = "video_to_audio"  # Режим конвертации

    await message.answer(
        "🔄 Отправьте видео файл\n\n"
        "Я извлеку из него аудио и отправлю файлом."
    )
