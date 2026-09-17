import logging
from store import build_transaction, append_transaction
from transcribe import transcribe
from router import choose_model

logger = logging.getLogger(__name__)


async def handle_incoming(msg, channel):
    """
    Orchestrates the flow for one normalised message.
    Has no idea which app the user is on — only talks to `channel` through the base.Channel contract.
    """
    if msg.kind == "voice":
        logger.info(
            f"[CORE] voice message from user_id={msg.user_id} "
            f"duration={msg.duration_s}s audio_ref={msg.audio_ref}"
        )

        model_choice = choose_model(msg.duration_s)
        logger.info(f"[CORE] routing to model={model_choice} (duration={msg.duration_s}s)")

        audio_bytes = await channel.fetch_audio(msg)
        text, model_used = transcribe(audio_bytes, model=model_choice)
        logger.info(f"[CORE] transcript ({model_used}): \"{text}\"")

        transaction = build_transaction(
            amount=None,
            category="Other / uncategorized",
            note=None,
            transcript=text,
            model=model_used,
            needs_review=True,
        )
        append_transaction(msg.user_id, transaction)

        await channel.send_text(msg.user_id, f"✅ Voice note transcribed ({model_used}) and saved.")

    elif msg.kind == "text":
        logger.info(f"[CORE] text message from user_id={msg.user_id} content=\"{msg.text}\"")

        transaction = build_transaction(
            amount=None,
            category="Other / uncategorized",
            note=None,
            transcript=msg.text,
            model="manual-test",
            needs_review=True,
        )
        append_transaction(msg.user_id, transaction)

        await channel.send_text(msg.user_id, "✅ Text message received and saved as a transaction.")

    else:
        logger.info(f"[CORE] unsupported message kind={msg.kind} from user_id={msg.user_id}")