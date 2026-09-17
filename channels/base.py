from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class IncomingMessage:
    """The normalised shape every channel must produce. No Telegram types beyond here."""
    user_id: str          # channel-scoped, opaque to core
    kind: str              # "voice" | "text" | "menu_choice"
    text: Optional[str] = None
    audio_ref: Optional[str] = None
    duration_s: Optional[float] = None
    sent_at: datetime = None


class Channel:
    """The contract every channel adapter must satisfy. No logic, just the shape."""

    def receive(self) -> IncomingMessage:
        """Yield the next message, already normalised."""
        raise NotImplementedError

    def fetch_audio(self, msg: IncomingMessage) -> bytes:
        """Download the voice file for a message."""
        raise NotImplementedError

    def send_text(self, user_id: str, text: str) -> None:
        """Send a plain reply."""
        raise NotImplementedError

    def send_menu(self, user_id: str, options: list) -> None:
        """Show the fixed report buttons."""
        raise NotImplementedError