import os
import asyncio
from groq import AsyncGroq
from bot.config import GROQ_API_KEY


class GroqTranscriber:
    """Транскрибация через Groq API (Whisper Large v3, бесплатно)"""

    def __init__(self):
        self.client = AsyncGroq(api_key=GROQ_API_KEY, timeout=120.0)  # 2 минуты timeout

    async def transcribe_verbatim(self, audio_path: str) -> str:
        """
        Транскрибирует аудио через Groq API.
        Использует Whisper Large v3 Turbo (быстрая модель).
        """
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
