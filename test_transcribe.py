# test_transcribe.py

from transcribe import transcribe

with open("voice_samples/voice1.ogg", "rb") as f:
    audio_bytes = f.read()

text_deepgram, model1 = transcribe(audio_bytes, model="deepgram")
print(f"[{model1}] {text_deepgram}")

text_gpt4o, model2 = transcribe(audio_bytes, model="gpt-4o")
print(f"[{model2}] {text_gpt4o}")