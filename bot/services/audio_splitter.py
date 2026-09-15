"""
Разделение больших аудиофайлов на части для обхода лимитов API
"""
import os
import asyncio
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Groq API лимит: ~25 МБ на файл
MAX_CHUNK_SIZE_MB = 24  # Берём с запасом


async def split_audio_by_size(audio_path: str, max_size_mb: int = MAX_CHUNK_SIZE_MB) -> List[str]:
    """
    Разрезает аудиофайл на части по размеру (не по времени).

    Использует ffmpeg для разделения аудио на чанки примерно одинакового размера.

    Args:
        audio_path: путь к исходному аудиофайлу
        max_size_mb: максимальный размер чанка в МБ

    Returns:
        Список путей к созданным чанкам
    """
    # Проверяем, не видео ли это (нужно извлечь аудио сначала)
    audio_path = await _ensure_audio_only(audio_path)

    file_size_mb = os.path.getsize(audio_path) / 1024 / 1024

    if file_size_mb <= max_size_mb:
        logger.info(f"File size {file_size_mb:.1f} MB is within limit, no split needed")
        return [audio_path]

    logger.info(f"Splitting audio: {file_size_mb:.1f} MB → chunks of ~{max_size_mb} MB")

    # Определяем количество частей
    num_chunks = int(file_size_mb / max_size_mb) + 1
    logger.info(f"Will create {num_chunks} chunks")

    # Получаем длительность аудио
    duration = await _get_audio_duration(audio_path)
    if not duration:
        raise RuntimeError("Could not determine audio duration")

    logger.info(f"Audio duration: {duration:.1f} seconds")

    # Вычисляем длительность каждого чанка
    chunk_duration = duration / num_chunks
    logger.info(f"Each chunk will be ~{chunk_duration:.1f} seconds")

    # Создаём чанки
    output_dir = Path(audio_path).parent
    base_name = Path(audio_path).stem
    extension = Path(audio_path).suffix

    chunk_paths = []

    for i in range(num_chunks):
        start_time = i * chunk_duration
        chunk_path = output_dir / f"{base_name}_chunk{i+1}{extension}"

        logger.info(f"Creating chunk {i+1}/{num_chunks}: {chunk_path.name}")

        # ffmpeg: вырезаем кусок аудио начиная с start_time длительностью chunk_duration
        cmd = [
            "ffmpeg",
            "-i", audio_path,
            "-ss", str(start_time),  # начало
            "-t", str(chunk_duration),  # длительность
            "-vn",  # без видео (на случай если это видеофайл)
            "-acodec", "copy",  # копируем аудио без реенкодинга (быстро)
            "-y",  # перезаписать если существует
            str(chunk_path)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"ffmpeg error: {stderr.decode()}")
            raise RuntimeError(f"Failed to create chunk {i+1}")

        if not chunk_path.exists():
            raise RuntimeError(f"Chunk {i+1} was not created")

        chunk_size_mb = chunk_path.stat().st_size / 1024 / 1024
        logger.info(f"✅ Chunk {i+1} created: {chunk_size_mb:.1f} MB")

        chunk_paths.append(str(chunk_path))

    logger.info(f"✅ Split complete: {len(chunk_paths)} chunks created")
    return chunk_paths


async def _ensure_audio_only(file_path: str) -> str:
    """
    Проверяет, не содержит ли файл видео. Если да — извлекает только аудио.
    Возвращает путь к чистому аудиофайлу.
    """
    # Проверяем наличие видеострима
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    # Если есть видеострим — извлекаем аудио
    if stdout.decode().strip() == "video":
        logger.info(f"File contains video, extracting audio only...")

        output_dir = Path(file_path).parent
        base_name = Path(file_path).stem
        audio_only_path = output_dir / f"{base_name}_audio.mp3"

        # Извлекаем аудио
        extract_cmd = [
            "ffmpeg",
            "-i", file_path,
            "-vn",  # без видео
            "-acodec", "libmp3lame",  # конвертируем в MP3
            "-q:a", "2",  # качество
            "-y",
            str(audio_only_path)
        ]

        process = await asyncio.create_subprocess_exec(
            *extract_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"ffmpeg extract error: {stderr.decode()}")
            raise RuntimeError("Failed to extract audio from video")

        if not audio_only_path.exists():
            raise RuntimeError("Audio extraction failed")

        size_mb = audio_only_path.stat().st_size / 1024 / 1024
        logger.info(f"✅ Audio extracted: {size_mb:.1f} MB")

        return str(audio_only_path)

    # Это уже чистое аудио
    return file_path


async def _get_audio_duration(audio_path: str) -> float:
    """Получает длительность аудио в секундах через ffprobe"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        logger.error(f"ffprobe error: {stderr.decode()}")
        return 0

    try:
        duration = float(stdout.decode().strip())
        return duration
    except ValueError:
        return 0


def cleanup_chunks(chunk_paths: List[str], keep_original: bool = True):
    """Удаляет временные чанки после обработки"""
    for chunk_path in chunk_paths:
        try:
            # Удаляем только чанки (файлы с _chunk в имени)
            if "_chunk" in chunk_path or not keep_original:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
                    logger.info(f"🗑️ Deleted chunk: {Path(chunk_path).name}")
        except Exception as e:
            logger.warning(f"Failed to delete chunk {chunk_path}: {e}")
