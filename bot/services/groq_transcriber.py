import os
import asyncio
import logging
from groq import AsyncGroq
from bot.config import GROQ_API_KEY
from bot.services.audio_splitter import split_audio_by_size, cleanup_chunks

logger = logging.getLogger(__name__)


class GroqTranscriber:
    """Транскрибация через Groq API (Whisper Large v3, бесплатно)"""

    def __init__(self):
        self.client = AsyncGroq(api_key=GROQ_API_KEY, timeout=120.0)  # 2 минуты timeout

    async def transcribe_verbatim(self, audio_path: str) -> str:
        """
        Транскрибирует аудио через Groq API.
        Автоматически разрезает большие файлы (>24 МБ) на части.
        Использует Whisper Large v3 Turbo (быстрая модель).
        """
        # Проверяем размер файла
        file_size_mb = os.path.getsize(audio_path) / 1024 / 1024
        logger.info(f"Transcribing audio: {file_size_mb:.1f} MB")

        # Если файл большой — разрезаем на части
        if file_size_mb > 24:
            logger.info(f"File is large ({file_size_mb:.1f} MB), splitting into chunks...")
            chunks = await split_audio_by_size(audio_path)
            logger.info(f"Split into {len(chunks)} chunks, transcribing each...")

            transcripts = []
            for i, chunk_path in enumerate(chunks, 1):
                logger.info(f"Transcribing chunk {i}/{len(chunks)}...")
                transcript = await self._transcribe_single_file(chunk_path)
                transcripts.append(transcript)
                logger.info(f"✅ Chunk {i}/{len(chunks)} done")

            # Удаляем временные чанки
            cleanup_chunks(chunks, keep_original=True)

            # Склеиваем результаты
            full_transcript = "\n\n".join(transcripts)
            logger.info(f"✅ All chunks transcribed, total length: {len(full_transcript)} chars")
            return full_transcript

        else:
            # Файл небольшой — транскрибируем напрямую
            return await self._transcribe_single_file(audio_path)

    async def _transcribe_single_file(self, audio_path: str) -> str:
        """Транскрибирует один файл (внутренний метод)"""
        async def _transcribe():
            with open(audio_path, "rb") as audio_file:
                transcription = await self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo",
                    language="ru",
                    response_format="verbose_json",
                    temperature=0.0
                )
            return transcription.text.strip()

        try:
            # Используем wait_for для надёжного timeout (3 минуты максимум)
            return await asyncio.wait_for(_transcribe(), timeout=180.0)

        except asyncio.TimeoutError:
            raise RuntimeError(f"Превышен timeout транскрибации (3 минуты). Попробуйте файл поменьше или проверьте подключение к интернету.")
        except Exception as e:
            raise RuntimeError(f"Ошибка транскрибации через Groq: {str(e)}")

    async def get_transcript_for_summary(self, audio_path: str) -> str:
        """
        Возвращает транскрипт для дальнейшей обработки ИИ.
        """
        return await self.transcribe_verbatim(audio_path)
