import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from bot.config import TELEGRAM_BOT_TOKEN, USE_LOCAL_API, LOCAL_API_URL, PROXY_URL
from bot.handlers import media, links, mode_toggle, menu, downloads

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def health_check(request):
    """Health check endpoint for Render"""
    return web.Response(text="OK")


async def start_health_server():
    """Start a simple HTTP server for Render health checks"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    # Render provides PORT environment variable
    port = int(os.getenv('PORT', 8080))

    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Health check server started on port {port}")


async def main():
    # Очистка папки downloads при старте (удаляем старые файлы)
    import shutil
    from pathlib import Path
    downloads_dir = Path("downloads")
    if downloads_dir.exists():
        try:
            shutil.rmtree(downloads_dir)
            logger.info("Deleted old downloads directory")
        except Exception as e:
            logger.warning(f"Failed to delete downloads directory: {e}")
    downloads_dir.mkdir(exist_ok=True)
    logger.info("Created fresh downloads directory")

    # Настройка сессии с прокси
    session_kwargs = {}

    if PROXY_URL:
        logger.info(f"Используется прокси: {PROXY_URL}")
        session_kwargs['proxy'] = PROXY_URL

    # Настройка сессии для локального API
    if USE_LOCAL_API:
        from aiogram.client.telegram import TelegramAPIServer
        session = AiohttpSession(
            api=TelegramAPIServer.from_base(LOCAL_API_URL),
            **session_kwargs
        )
        logger.info(f"Используется локальный Bot API: {LOCAL_API_URL}")
        bot = Bot(
            token=TELEGRAM_BOT_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    else:
        if session_kwargs:
            session = AiohttpSession(**session_kwargs)
            bot = Bot(
                token=TELEGRAM_BOT_TOKEN,
                session=session,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
        else:
            bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    dp = Dispatcher()

    dp.include_router(menu.router)  # Главное меню (первым!)
    dp.include_router(downloads.router)  # Скачивание и конвертация (вторым!)
    dp.include_router(mode_toggle.router)
    dp.include_router(media.router)
    dp.include_router(links.router)

    # Start health check server for Render (runs in background)
    asyncio.create_task(start_health_server())

    logger.info("Бот запущен")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
