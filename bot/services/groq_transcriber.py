import os
import asyncio
from groq import AsyncGroq
from bot.config import GROQ_API_KEY


class GroqTranscriber:
    """Транскрибация через Groq API (Whisper Large v3, бесплатно)"""

    def __init__(self):
        self.client = AsyncGroq(api_key=GROQ_API_KEY)

    async def transcribe_verbatim(self, audio_path: str) -> str:
        """
        Транскрибирует аудио через Groq API.
        Использует Whisper Large v3 Turbo (быстрая модель).
        """
        try:
            with open(audio_path, "rb") as audio_file:
                transcription = await self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo",
                    language="ru",
                    response_format="verbose_json",
                    temperature=0.0
                )

            return transcription.text.strip()

        except Exception as e:
            raise RuntimeError(f"Ошибка транскрибации через Groq: {str(e)}")

    async def get_transcript_for_summary(self, audio_path: str) -> str:
        """
        Возвращает транскрипт для дальнейшей обработки ИИ.
        """
        return await self.transcribe_verbatim(audio_path)
