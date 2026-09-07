"""
Создание новой Telethon сессии в формате StringSession
"""
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

API_ID = int(os.getenv("TELEGRAM_API_ID", "38923554"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "bd666a5f2fc702fed3e7c32bc411a696")
PHONE = os.getenv("TELEGRAM_PHONE", "+79113583410")

async def main():
    print("Creating NEW Telethon session for Render...\n")

    # Создаём новый клиент с пустой StringSession
    client = TelegramClient(StringSession(), API_ID, API_HASH)

    await client.start(phone=PHONE)

    print("\nSession created successfully!")

    # Экспортируем StringSession
    session_string = StringSession.save(client.session)

    print("\n" + "="*70)
    print("SUCCESS! NEW SESSION STRING:")
    print("="*70)
    print(f"\nVariable name: TELEGRAM_SESSION")
    print(f"Value:\n{session_string}\n")
    print("="*70)
    print("\nSteps to add to Render:")
    print("1. Go to https://dashboard.render.com/")
    print("2. Find your telegram-transcription-bot service")
    print("3. Click 'Environment' tab")
    print("4. Add new environment variable:")
    print("   Name: TELEGRAM_SESSION")
    print(f"   Value: {session_string}")
    print("5. Click 'Save Changes'")
    print("6. Resume/restart the service")
    print("="*70)

    await client.disconnect()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
