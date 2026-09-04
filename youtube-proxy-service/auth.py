"""
Скрипт для первой авторизации Telethon
Запустите: python auth.py
"""
from telethon import TelegramClient

API_ID = 38923554
API_HASH = 'bd666a5f2fc702fed3e7c32bc411a696'

async def main():
    client = TelegramClient('session', API_ID, API_HASH)

    print("🔐 Начинаем авторизацию...")
    print("📱 Вам придёт SMS код от Telegram")

    await client.start()

    print("✅ Авторизация успешна!")
    print("✅ Файл session.session создан")
    print("\nТеперь можно закрыть это окно.")

    await client.disconnect()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
