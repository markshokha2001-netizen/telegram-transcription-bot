import os
import asyncio
import subprocess
import aiohttp
import uuid
from pathlib import Path
from typing import Optional

class Downloader:
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)

    async def download_audio_from_url_cobalt(self, url: str) -> Optional[str]:
        """
        Скачивает аудио через Cobalt API (поддерживает YouTube, TikTok, Twitter и др.)
        Возвращает путь к файлу или None при ошибке.
        """
        try:
            # Запрос к Cobalt API
            async with aiohttp.ClientSession() as session:
                # Шаг 1: Получить ссылку на аудио от Cobalt
                cobalt_api = "https://co.wuk.sh/api/json"
                payload = {
                    "url": url,
                    "isAudioOnly": True,  # Скачиваем только аудио
                    "aFormat": "mp3",     # Формат аудио
                    "filenamePattern": "basic"
                }

                async with session.post(cobalt_api, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"Cobalt API вернул ошибку {response.status}: {error_text}")

                    result = await response.json()

                    # Проверяем статус ответа
                    if result.get("status") != "stream" and result.get("status") != "redirect":
                        error_msg = result.get("text", "Неизвестная ошибка")
                        raise RuntimeError(f"Cobalt API: {error_msg}")

                    audio_url = result.get("url")
                    if not audio_url:
                        raise RuntimeError("Cobalt API не вернул ссылку на аудио")

                # Шаг 2: Скачать аудиофайл по полученной ссылке
                output_filename = f"{uuid.uuid4().hex}.mp3"
                output_path = self.download_dir / output_filename

                async with session.get(audio_url, timeout=aiohttp.ClientTimeout(total=120)) as audio_response:
                    if audio_response.status != 200:
                        raise RuntimeError(f"Не удалось скачать аудио: HTTP {audio_response.status}")

                    # Скачиваем файл
                    with open(output_path, 'wb') as f:
                        async for chunk in audio_response.content.iter_chunked(8192):
                            f.write(chunk)

                if output_path.exists() and output_path.stat().st_size > 0:
                    return str(output_path)
                else:
                    raise RuntimeError("Скачанный файл пустой или не существует")

        except asyncio.TimeoutError:
            raise RuntimeError("Превышен timeout скачивания (2 минуты). Попробуйте другое видео.")
        except Exception as e:
            raise RuntimeError(f"Ошибка при скачивании через Cobalt: {str(e)}")

    async def download_audio_from_url(self, url: str) -> Optional[str]:
        """
        Скачивает аудиодорожку из видео по ссылке.
        Возвращает путь к файлу или None при ошибке.
        """
        output_template = str(self.download_dir / "%(id)s.%(ext)s")

        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--output", output_template,
            "--no-playlist",
            url
        ]

        async def _download():
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode()
                raise RuntimeError(f"yt-dlp завершился с ошибкой: {error_msg}")

            for file in self.download_dir.glob("*.*"):
                if file.suffix in [".mp3", ".m4a", ".wav", ".ogg"]:
                    return str(file)

            return None

        try:
            # Используем wait_for для надёжного timeout (2 минуты максимум)
            return await asyncio.wait_for(_download(), timeout=120.0)

        except asyncio.TimeoutError:
            raise RuntimeError(f"Превышен timeout скачивания (2 минуты). Попробуйте другое видео или проверьте подключение.")
        except Exception as e:
            raise RuntimeError(f"Ошибка при скачивании: {str(e)}")

    async def extract_audio_from_video(self, video_path: str) -> Optional[str]:
        """
        Извлекает аудиодорожку из видеофайла.
        Возвращает путь к аудиофайлу или None при ошибке.
        """
        video_file = Path(video_path)
        output_file = video_file.with_suffix(".mp3")

        cmd = [
            "ffmpeg",
            "-i", str(video_file),
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "0",
            "-y",
            str(output_file)
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode()
                raise RuntimeError(f"ffmpeg завершился с ошибкой: {error_msg}")

            if output_file.exists():
                return str(output_file)

            return None

        except Exception as e:
            raise RuntimeError(f"Ошибка при извлечении аудио: {str(e)}")

    def cleanup(self, file_path: str):
        """Удаляет файл после обработки"""
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:
            pass
