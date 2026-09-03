import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from bot.config import TELEGRAM_BOT_TOKEN, USE_LOCAL_API, LOCAL_API_URL, PROXY_URL
from bot.handlers import media, links, mode_toggle, start

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
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

    dp.include_router(start.router)
    dp.include_router(mode_toggle.router)
    dp.include_router(media.router)
    dp.include_router(links.router)

    logger.info("Бот запущен")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
