import logging
from store import build_transaction, append_transaction
from transcribe import transcribe
from router import choose_model
from extract import extract
from confirmation import format_confirmation

logger = logging.getLogger(__name__)


async def handle_incoming(msg, channel):
    if msg.kind == "voice":
        logger.info(
            f"[CORE] voice message from user_id={msg.user_id} "
            f"duration={msg.duration_s}s audio_ref={msg.audio_ref}"
        )

        model_choice = choose_model(msg.duration_s)
        audio_bytes = await channel.fetch_audio(msg)
        text, model_used = transcribe(audio_bytes, model=model_choice)
        logger.info(f"[CORE] transcript ({model_used}): \"{text}\"")

        transactions = extract(text)
        logger.info(f"[CORE] extracted {len(transactions)} transaction(s)")

        for t in transactions:
            transaction = build_transaction(
                amount=t.get("amount"),
                category=t.get("category"),
                note=t.get("note", ""),
                transcript=text,
                model=model_used,
                needs_review=(t.get("amount") is None),
            )
            append_transaction(msg.user_id, transaction)

        reply = format_confirmation(transactions)
        await channel.send_text(msg.user_id, reply)

    elif msg.kind == "text":
        logger.info(f"[CORE] text message from user_id={msg.user_id} content=\"{msg.text}\"")

        transactions = extract(msg.text)
        logger.info(f"[CORE] extracted {len(transactions)} transaction(s)")

        for t in transactions:
            transaction = build_transaction(
                amount=t.get("amount"),
                category=t.get("category"),
                note=t.get("note", ""),
                transcript=msg.text,
                model="text-input",
                needs_review=(t.get("amount") is None),
            )
            append_transaction(msg.user_id, transaction)

        reply = format_confirmation(transactions)
        await channel.send_text(msg.user_id, reply)

    else:
        logger.info(f"[CORE] unsupported message kind={msg.kind} from user_id={msg.user_id}")