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
        Скачивает аудио с YouTube через yt-dlp с параметрами из VideoDownloadBot.
        Возвращает путь к файлу или None при ошибке.
        """
        output_template = str(self.download_dir / "%(id)s.%(ext)s")

        # Параметры адаптированы из VideoDownloadBot для максимальной совместимости
        cmd = [
            "yt-dlp",
            "--format", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--output", output_template,
            "--no-playlist",
            "--no-warnings",
            "--no-check-certificate",
            # Обход geo-ограничений и блокировок
            "--geo-bypass",
            # Множественные User-Agent и методы извлечения
            "--extractor-args", "youtube:player_client=android,web",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            # Обход rate limiting
            "--limit-rate", "5M",
            "--retries", "3",
            "--fragment-retries", "3",
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
                # Очищаем HTML-теги из ошибки для Telegram
                import re
                error_msg = re.sub(r'<[^>]+>', '', error_msg)
                raise RuntimeError(f"yt-dlp завершился с ошибкой: {error_msg[:500]}")

            for file in self.download_dir.glob("*.*"):
                if file.suffix in [".mp3", ".m4a", ".wav", ".ogg"]:
                    return str(file)

            return None

        try:
            # Используем wait_for для надёжного timeout (3 минуты максимум для YouTube)
            return await asyncio.wait_for(_download(), timeout=180.0)

        except asyncio.TimeoutError:
            raise RuntimeError("Превышен timeout скачивания (3 минуты). YouTube может блокировать запросы с этого сервера.")
        except Exception as e:
            # Очищаем HTML-теги из любых ошибок
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
