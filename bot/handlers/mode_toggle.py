from pathlib import Path
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.summarizer import Summarizer
from bot.services.downloader import Downloader
from bot.services.export import Exporter
from bot.handlers.media import transcripts, audio_files, file_names

router = Router()
summarizer = Summarizer()
downloader = Downloader()
exporter = Exporter()

# Хранилище для конспектов и исправленных текстов
summaries = {}
fixed_texts = {}


@router.callback_query(F.data.startswith("summary_"))
async def handle_summary_request(callback: CallbackQuery):
    """Обработка нажатия кнопки 'Сделать конспект'"""
    await callback.answer()

    message_id = int(callback.data.split("_")[1])

    if message_id not in transcripts:
        await callback.message.answer("❌ Транскрипт не найден. Возможно, бот был перезапущен.")
        return

    status_msg = await callback.message.answer("🤖 Создаю конспект...")

    try:
        transcript = transcripts[message_id]
        summary = await summarizer.create_summary(transcript)

        # Сохраняем конспект для возможности экспорта
        summaries[message_id] = summary

        # Кнопки для экспорта конспекта
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 TXT", callback_data=f"export_summary_txt_{message_id}"),
                InlineKeyboardButton(text="📘 DOCX", callback_data=f"export_summary_docx_{message_id}"),
                InlineKeyboardButton(text="📕 PDF", callback_data=f"export_summary_pdf_{message_id}")
            ]
        ])

        await callback.message.answer(f"🤖 Конспект:\n\n{summary}", reply_markup=keyboard)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при создании конспекта: {str(e)}")


@router.callback_query(F.data.startswith("ai_fix_"))
async def handle_ai_fix_request(callback: CallbackQuery):
    """Обработка нажатия кнопки 'AI-исправление'"""
    await callback.answer()

    message_id = int(callback.data.split("_")[2])

    if message_id not in transcripts:
        await callback.message.answer("❌ Транскрипт не найден. Возможно, бот был перезапущен.")
        return

    status_msg = await callback.message.answer("✨ Исправляю текст...")

    try:
        transcript = transcripts[message_id]
        fixed_text = await summarizer.fix_transcript(transcript)

        # Сохраняем исправленный текст для возможности экспорта
        fixed_texts[message_id] = fixed_text

        # Кнопки для экспорта исправленного текста
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 TXT", callback_data=f"export_fixed_txt_{message_id}"),
                InlineKeyboardButton(text="📘 DOCX", callback_data=f"export_fixed_docx_{message_id}"),
                InlineKeyboardButton(text="📕 PDF", callback_data=f"export_fixed_pdf_{message_id}")
            ]
        ])

        await callback.message.answer(f"✨ Исправленный текст:\n\n{fixed_text}", reply_markup=keyboard)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при исправлении текста: {str(e)}")


@router.callback_query(F.data.startswith("audio_"))
async def handle_audio_request(callback: CallbackQuery):
    """Обработка нажатия кнопки 'Прислать аудио отдельно'"""
    await callback.answer()

    message_id = int(callback.data.split("_")[1])

    if message_id not in audio_files:
        await callback.message.answer("❌ Аудиофайл не найден. Возможно, он был удалён.")
        return

    try:
        audio_path = audio_files[message_id]

        if not Path(audio_path).exists():
            await callback.message.answer("❌ Аудиофайл больше не существует.")
            del audio_files[message_id]
            return

        audio_file = FSInputFile(audio_path)
        await callback.message.answer_audio(audio_file)

        downloader.cleanup(audio_path)
        del audio_files[message_id]

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при отправке аудио: {str(e)}")

@router.callback_query(F.data.startswith("export_txt_"))
async def handle_export_txt(callback: CallbackQuery):
    """Обработка экспорта в TXT"""
    await callback.answer()

    message_id = int(callback.data.split("_")[2])

    if message_id not in transcripts:
        await callback.message.answer("❌ Транскрипт не найден. Возможно, бот был перезапущен.")
        return

    try:
        transcript = transcripts[message_id]
        # Получаем имя исходного файла
        original_name = file_names.get(message_id, "transcript")
        filename = f"{original_name}.txt"
        filepath = exporter.export_to_txt(transcript, filename)

        file = FSInputFile(filepath)
        await callback.message.answer_document(file, caption="📄 Транскрипт в формате TXT")

        # Очищаем файл после отправки
        downloader.cleanup(filepath)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")


@router.callback_query(F.data.startswith("export_docx_"))
async def handle_export_docx(callback: CallbackQuery):
    """Обработка экспорта в DOCX"""
    await callback.answer()

    message_id = int(callback.data.split("_")[2])

    if message_id not in transcripts:
        await callback.message.answer("❌ Транскрипт не найден. Возможно, бот был перезапущен.")
        return

    try:
        transcript = transcripts[message_id]
        # Получаем имя исходного файла
        original_name = file_names.get(message_id, "transcript")
        filename = f"{original_name}.docx"
        filepath = exporter.export_to_docx(transcript, filename)

        file = FSInputFile(filepath)
        await callback.message.answer_document(file, caption="📘 Транскрипт в формате DOCX")

        # Очищаем файл после отправки
        downloader.cleanup(filepath)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")


@router.callback_query(F.data.startswith("export_pdf_"))
async def handle_export_pdf(callback: CallbackQuery):
    """Обработка экспорта в PDF"""
    await callback.answer()

    message_id = int(callback.data.split("_")[2])

    if message_id not in transcripts:
        await callback.message.answer("❌ Транскрипт не найден. Возможно, бот был перезапущен.")
        return

    try:
        transcript = transcripts[message_id]
        # Получаем имя исходного файла
        original_name = file_names.get(message_id, "transcript")
        filename = f"{original_name}.pdf"
        filepath = exporter.export_to_pdf(transcript, filename)

        file = FSInputFile(filepath)
        await callback.message.answer_document(file, caption="📕 Транскрипт в формате PDF")

        # Очищаем файл после отправки
        downloader.cleanup(filepath)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")


# Экспорт конспектов

@router.callback_query(F.data.startswith("export_summary_txt_"))
async def handle_export_summary_txt(callback: CallbackQuery):
    """Обработка экспорта конспекта в TXT"""
    await callback.answer()

    message_id = int(callback.data.split("_")[3])

    if message_id not in summaries:
        await callback.message.answer("❌ Конспект не найден. Возможно, бот был перезапущен.")
        return

    try:
        summary = summaries[message_id]
        # Получаем имя исходного файла и добавляем суффикс
        original_name = file_names.get(message_id, "transcript")
        filename = f"{original_name}_summary.txt"
        filepath = exporter.export_to_txt(summary, filename)

        file = FSInputFile(filepath)
        await callback.message.answer_document(file, caption="📄 Конспект в формате TXT")

        downloader.cleanup(filepath)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")


@router.callback_query(F.data.startswith("export_summary_docx_"))
async def handle_export_summary_docx(callback: CallbackQuery):
    """Обработка экспорта конспекта в DOCX"""
    await callback.answer()

    message_id = int(callback.data.split("_")[3])

    if message_id not in summaries:
        await callback.message.answer("❌ Конспект не найден. Возможно, бот был перезапущен.")
        return

    try:
        summary = summaries[message_id]
        # Получаем имя исходного файла и добавляем суффикс
        original_name = file_names.get(message_id, "transcript")
        filename = f"{original_name}_summary.docx"
        filepath = exporter.export_to_docx(summary, filename)

        file = FSInputFile(filepath)
        await callback.message.answer_document(file, caption="📘 Конспект в формате DOCX")

        downloader.cleanup(filepath)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")


@router.callback_query(F.data.startswith("export_summary_pdf_"))
async def handle_export_summary_pdf(callback: CallbackQuery):
    """Обработка экспорта конспекта в PDF"""
    await callback.answer()

    message_id = int(callback.data.split("_")[3])

    if message_id not in summaries:
        await callback.message.answer("❌ Конспект не найден. Возможно, бот был перезапущен.")
        return

    try:
        summary = summaries[message_id]
        # Получаем имя исходного файла и добавляем суффикс
        original_name = file_names.get(message_id, "transcript")
        filename = f"{original_name}_summary.pdf"
        filepath = exporter.export_to_pdf(summary, filename)

        file = FSInputFile(filepath)
        await callback.message.answer_document(file, caption="📕 Конспект в формате PDF")

        downloader.cleanup(filepath)

    except Exception as e:
async def handle_export_summary_pdf(callback: CallbackQuery):
    """Обработка экспорта конспекта в PDF"""
    await callback.answer()

    message_id = int(callback.data.split("_")[3])

    if message_id not in summaries:
        await callback.message.answer("❌ Конспект не найден. Возможно, бот был перезапущен.")
        return

    try:
        summary = summaries[message_id]
        filepath = exporter.export_to_pdf(summary)

        file = FSInputFile(filepath)
        await callback.message.answer_document(file, caption="📕 Конспект в формате PDF")

        downloader.cleanup(filepath)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")


# Экспорт исправленных текстов

@router.callback_query(F.data.startswith("export_fixed_txt_"))
async def handle_export_fixed_txt(callback: CallbackQuery):
    """Обработка экспорта исправленного текста в TXT"""
    await callback.answer()

    message_id = int(callback.data.split("_")[3])

    if message_id not in fixed_texts:
        await callback.message.answer("❌ Исправленный текст не найден. Возможно, бот был перезапущен.")
        return

    try:
        fixed_text = fixed_texts[message_id]
        # Получаем имя исходного файла и добавляем суффикс
        original_name = file_names.get(message_id, "transcript")
        filename = f"{original_name}_fixed.txt"
        filepath = exporter.export_to_txt(fixed_text, filename)

        file = FSInputFile(filepath)
        await callback.message.answer_document(file, caption="📄 Исправленный текст в формате TXT")

        downloader.cleanup(filepath)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")


@router.callback_query(F.data.startswith("export_fixed_docx_"))
async def handle_export_fixed_docx(callback: CallbackQuery):
    """Обработка экспорта исправленного текста в DOCX"""
    await callback.answer()

    message_id = int(callback.data.split("_")[3])

    if message_id not in fixed_texts:
        await callback.message.answer("❌ Исправленный текст не найден. Возможно, бот был перезапущен.")
        return

    try:
        fixed_text = fixed_texts[message_id]
        # Получаем имя исходного файла и добавляем суффикс
        original_name = file_names.get(message_id, "transcript")
        filename = f"{original_name}_fixed.docx"
        filepath = exporter.export_to_docx(fixed_text, filename)

        file = FSInputFile(filepath)
        await callback.message.answer_document(file, caption="📘 Исправленный текст в формате DOCX")

        downloader.cleanup(filepath)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")


@router.callback_query(F.data.startswith("export_fixed_pdf_"))
async def handle_export_fixed_pdf(callback: CallbackQuery):
    """Обработка экспорта исправленного текста в PDF"""
    await callback.answer()

    message_id = int(callback.data.split("_")[3])

    if message_id not in fixed_texts:
        await callback.message.answer("❌ Исправленный текст не найден. Возможно, бот был перезапущен.")
        return

    try:
        fixed_text = fixed_texts[message_id]
        # Получаем имя исходного файла и добавляем суффикс
        original_name = file_names.get(message_id, "transcript")
        filename = f"{original_name}_fixed.pdf"
        filepath = exporter.export_to_pdf(fixed_text, filename)

        file = FSInputFile(filepath)
        await callback.message.answer_document(file, caption="📕 Исправленный текст в формате PDF")

        downloader.cleanup(filepath)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")
