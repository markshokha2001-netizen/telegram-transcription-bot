"""
Экспорт Telethon сессии в StringSession для использования на сервере
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
    print("Trying to export session...")
    print("WARNING: Make sure to STOP the bot on Render first to release the session!\n")

    # Загружаем существующую сессию
    client = TelegramClient('session.session', API_ID, API_HASH)

    try:
        await client.connect()

        if not await client.is_user_authorized():
            print("ERROR: Session is not authorized!")
            print("HINT: You need to authorize first")
            await client.disconnect()
            return

        # Экспортируем в StringSession
        session_string = StringSession.save(client.session)

        print("\n" + "="*70)
        print("SUCCESS! SESSION STRING (add this to Render environment variables):")
        print("="*70)
        print(f"\nVariable name: TELEGRAM_SESSION")
        print(f"Value:\n{session_string}\n")
        print("="*70)
        print("\nSteps to add to Render:")
        print("1. Go to your service on Render Dashboard")
        print("2. Click 'Environment' tab")
        print("3. Add new environment variable:")
        print("   Name: TELEGRAM_SESSION")
        print(f"   Value: {session_string}")
        print("4. Save and redeploy")
        print("="*70)

    except Exception as e:
        if "AuthKeyDuplicated" in str(type(e).__name__):
            print("\nERROR: Session is still being used on Render!")
            print("Steps to fix:")
            print("   1. Go to Render Dashboard")
            print("   2. Stop/suspend your bot service")
            print("   3. Wait 10 seconds")
            print("   4. Run this script again")
        else:
            print(f"ERROR: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
