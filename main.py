import os
from dotenv import load_dotenv
from telegram.request import HTTPXRequest
from channels.telegram import build_app

load_dotenv()


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set in .env")
        return

    # زودنا الـ timeout عشان الشبكة بطيئة/متذبذبة
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )

    app = build_app(token, request=request)
    print("Bot started — listening for messages...")
    app.run_polling()


if __name__ == "__main__":
    main()