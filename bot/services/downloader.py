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

    async def download_audio_from_url_youtube(self, url: str) -> Optional[str]:
        """
        Скачивает аудио с YouTube через отдельный микросервис на Render.
        Возвращает путь к файлу или None при ошибке.
        """
        youtube_service_url = "https://youtube-downloader-service-fhp5.onrender.com/download"

        try:
            async with aiohttp.ClientSession() as session:
                # Отправляем запрос на микросервис
                async with session.post(
                    youtube_service_url,
                    json={"url": url},
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"YouTube микросервис вернул ошибку {response.status}: {error_text[:500]}")

                    # Скачиваем аудиофайл
                    output_filename = f"{uuid.uuid4().hex}.mp3"
                    output_path = self.download_dir / output_filename

                    with open(output_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)

                    if output_path.exists() and output_path.stat().st_size > 0:
                        return str(output_path)
                    else:
                        raise RuntimeError("Скачанный файл пустой или не существует")

        except asyncio.TimeoutError:
            raise RuntimeError("Превышен timeout скачивания (3 минуты). Попробуйте другое видео.")
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Ошибка подключения к YouTube микросервису: {str(e)}")
        except Exception as e:
            import re
            error_text = str(e)
            error_text = re.sub(r'<[^>]+>', '', error_text)
            raise RuntimeError(f"Ошибка при скачивании с YouTube: {error_text[:500]}")

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
