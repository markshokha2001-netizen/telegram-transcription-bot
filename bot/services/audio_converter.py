"""
Конвертация больших аудиофайлов для Groq API (лимит 25 МБ)
"""
import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

GROQ_MAX_SIZE_MB = 25


async def compress_audio_if_needed(audio_path: str) -> str:
    """
    Проверяет размер аудио и сжимает, если больше 25 МБ.
    Возвращает путь к файлу (оригинал или сжатый).
    """
    audio_file = Path(audio_path)
    file_size_mb = audio_file.stat().st_size / 1024 / 1024

    logger.info(f"Audio file size: {file_size_mb:.2f} MB")

    if file_size_mb <= GROQ_MAX_SIZE_MB:
        logger.info("File size OK for Groq API")
        return audio_path

    logger.info(f"File too large ({file_size_mb:.2f} MB > {GROQ_MAX_SIZE_MB} MB), compressing...")

    # Создаём путь для сжатого файла
    compressed_path = audio_file.parent / f"{audio_file.stem}_compressed.mp3"

    try:
        # Сжимаем через ffmpeg (битрейт 64k = ~8 MB на час аудио)
        # Это в ~20 раз меньше оригинала, но качество речи сохраняется
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", str(audio_path),
                "-ar", "16000",  # Sample rate 16kHz (оптимально для речи)
                "-ac", "1",  # Mono (стерео не нужно для речи)
                "-b:a", "64k",  # Битрейт 64 kbps
                "-y",  # Перезаписать если существует
                str(compressed_path)
            ],
            capture_output=True,
            text=True,
            timeout=300  # 5 минут таймаут
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr}")
            raise RuntimeError(f"Ошибка конвертации: {result.stderr[:200]}")

        compressed_size_mb = compressed_path.stat().st_size / 1024 / 1024
        logger.info(f"Compressed: {file_size_mb:.2f} MB → {compressed_size_mb:.2f} MB")

        # Удаляем оригинал (экономим место)
        os.remove(audio_path)

        return str(compressed_path)

    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout конвертации (5 минут). Файл слишком большой.")
    except FileNotFoundError:
        raise RuntimeError("ffmpeg не найден. Установите ffmpeg для обработки больших файлов.")
    except Exception as e:
        logger.error(f"Compression error: {e}")
        raise RuntimeError(f"Ошибка сжатия аудио: {str(e)}")
