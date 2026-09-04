"""
YouTube Downloader Microservice для Railway
Простой FastAPI сервер для скачивания аудио с YouTube
"""
import asyncio
import os
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess

app = FastAPI()

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


class DownloadRequest(BaseModel):
    url: str


@app.get("/")
async def root():
    return {"status": "ok", "service": "youtube-downloader"}


@app.post("/download")
async def download_audio(request: DownloadRequest):
    """
    Скачивает аудио с YouTube и возвращает файл
    """
    try:
        # Генерируем уникальное имя файла
        file_id = uuid.uuid4().hex
        output_template = str(DOWNLOAD_DIR / f"{file_id}.%(ext)s")

        cmd = [
            "yt-dlp",
            "--format", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--output", output_template,
            "--no-playlist",
            "--no-warnings",
            "--geo-bypass",
            "--extractor-args", "youtube:player_client=android,web",
            request.url
        ]

        # Запускаем yt-dlp
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Ждём завершения с timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=180.0
            )
        except asyncio.TimeoutError:
            process.kill()
            raise HTTPException(
                status_code=408,
                detail="Timeout: скачивание заняло больше 3 минут"
            )

        if process.returncode != 0:
            error_msg = stderr.decode()
            raise HTTPException(
                status_code=500,
                detail=f"yt-dlp error: {error_msg[:500]}"
            )

        # Находим скачанный файл
        for file in DOWNLOAD_DIR.glob(f"{file_id}.*"):
            if file.suffix in [".mp3", ".m4a", ".wav", ".ogg"]:
                # Возвращаем файл и удаляем после отправки
                return FileResponse(
                    str(file),
                    media_type="audio/mpeg",
                    filename=f"{file_id}.mp3",
                    background=lambda: file.unlink(missing_ok=True)
                )

        raise HTTPException(status_code=500, detail="Файл не найден после скачивания")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy"}
