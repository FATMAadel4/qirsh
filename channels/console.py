import asyncio
from datetime import datetime
from channels.base import Channel, IncomingMessage
import core


class ConsoleChannel(Channel):
    async def send_text(self, user_id: str, text: str) -> None:
        print(f"[BOT -> {user_id}] {text}")

    async def fetch_audio(self, msg: IncomingMessage) -> bytes:
        raise NotImplementedError("Console channel has no audio")

    def send_menu(self, user_id: str, options: list) -> None:
        print(f"[BOT -> {user_id}] Menu: {options}")

    def receive(self) -> IncomingMessage:
        text = input("You: ")
        return IncomingMessage(user_id="console_user", kind="text", text=text, sent_at=datetime.now())


async def run():
    channel = ConsoleChannel()
    print("Console channel started. Type a message (Ctrl+C to quit).")
    while True:
        msg = channel.receive()
        await core.handle_incoming(msg, channel)


if __name__ == "__main__":
    asyncio.run(run())