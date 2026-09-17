from dotenv import load_dotenv
load_dotenv()
import os
from openai import OpenAI
from deepgram import DeepgramClient

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
deepgram_client = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))


def transcribe(audio_bytes: bytes, model: str) -> tuple[str, str]:
    """
    Takes raw audio bytes, returns (text, model_used).
    The caller picks which model by name — this function does not decide that;
    routing logic lives in router.py (S1-05).

    model must be "deepgram" or "gpt-4o".
    """
    if model == "deepgram":
        text = _transcribe_with_deepgram(audio_bytes)
    elif model == "gpt-4o":
        text = _transcribe_with_gpt4o(audio_bytes)
    else:
        raise ValueError(f"Unknown transcription model: {model}")

    return text, model


def _transcribe_with_deepgram(audio_bytes: bytes) -> str:
    response = deepgram_client.listen.v1.media.transcribe_file(
        request=audio_bytes,
        model="nova-3",
        language="ar",
    )
    return response.results.channels[0].alternatives[0].transcript


def _transcribe_with_gpt4o(audio_bytes: bytes) -> str:
    import io
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.ogg"  # OpenAI SDK محتاج اسم ملف عشان يعرف الصيغة

    result = openai_client.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=audio_file,
        language="ar",
    )
    return result.text