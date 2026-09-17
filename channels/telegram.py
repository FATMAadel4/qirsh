import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from channels.base import Channel, IncomingMessage
import core

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalise(update: Update) -> IncomingMessage:
    """Converts a Telegram Update into the channel-agnostic IncomingMessage shape."""
    chat_id = str(update.effective_chat.id)

    if update.message.voice:
        voice = update.message.voice
        return IncomingMessage(
            user_id=chat_id,
            kind="voice",
            audio_ref=voice.file_id,
            duration_s=voice.duration,
            sent_at=update.message.date,
        )
    elif update.message.text:
        return IncomingMessage(
            user_id=chat_id,
            kind="text",
            text=update.message.text,
            sent_at=update.message.date,
        )
    else:
        return IncomingMessage(user_id=chat_id, kind="unknown", sent_at=update.message.date)


class ReplyAdapter(Channel):
    """A thin per-request Channel that knows how to reply to THIS Telegram update."""

    def __init__(self, telegram_update: Update, context: ContextTypes.DEFAULT_TYPE):
        self._update = telegram_update
        self._context = context

    async def send_text(self, user_id: str, text: str) -> None:
        await self._update.message.reply_text(text)

    async def fetch_audio(self, msg) -> bytes:
        """Downloads the voice file from Telegram using its file_id."""
        file = await self._context.bot.get_file(msg.audio_ref)
        audio_bytes = await file.download_as_bytearray()
        return bytes(audio_bytes)

    def send_menu(self, user_id: str, options: list) -> None:
        raise NotImplementedError("Not needed until reports are built")

    def receive(self) -> IncomingMessage:
        raise NotImplementedError("Not used on this per-request adapter")


async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The only function that touches raw Telegram types. Normalises, then hands off to core."""
    msg = normalise(update)
    channel = ReplyAdapter(update, context)
    await core.handle_incoming(msg, channel)


def build_app(token: str, request=None):
    """Builds and returns the Telegram application, ready to run."""
    builder = ApplicationBuilder().token(token)
    if request:
        builder = builder.request(request)
    app = builder.build()
    app.add_handler(MessageHandler(filters.VOICE | filters.TEXT, handle_update))
    return app