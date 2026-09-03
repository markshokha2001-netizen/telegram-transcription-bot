import asyncio
from pathlib import Path
from typing import Optional
from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self, model_size: str = "medium"):
        """
        Инициализирует модель Faster Whisper.
        model_size: размер модели ("tiny", "base", "small", "medium", "large-v2", "large-v3")
        """
        self.model = None
        self.model_size = model_size

    async def load_model(self):
        """Загружает модель в память (если ещё не загружена)"""
        if self.model is None:
            loop = asyncio.get_event_loop()
            # Используем CPU вместо CUDA для совместимости
            self.model = await loop.run_in_executor(
                None,
                lambda: WhisperModel(self.model_size, device="cpu", compute_type="int8")
            )

    async def transcribe_verbatim(self, audio_path: str) -> str:
        """
        Транскрибирует аудио в дословном режиме.
        Сохраняет всё как есть.
        """
        await self.load_model()

        loop = asyncio.get_event_loop()
        segments, info = await loop.run_in_executor(
            None,
            lambda: self.model.transcribe(
                audio_path,
                language="ru",
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False
            )
        )

        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        return " ".join(text_parts)

    async def get_transcript_for_summary(self, audio_path: str) -> str:
        """
        Возвращает транскрипт для дальнейшей обработки ИИ.
        """
        return await self.transcribe_verbatim(audio_path)
