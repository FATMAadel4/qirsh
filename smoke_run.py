"""
S1-08: End-to-end smoke run

Wires the whole pipeline together and pushes real voice samples through it:
voice in -> transcribe -> route -> extract -> store -> reply.

Run this from the root of the qirsh project (same folder as router.py,
transcribe.py, extract.py, store.py, confirmation.py, categories.py),
with voice_samples/ present and your .env loaded (OPENAI_API_KEY,
DEEPGRAM_API_KEY).

    python smoke_run.py

Needs `mutagen` to read .ogg duration (pip install mutagen). Falls back to
ffprobe if mutagen can't parse the file.

Acceptance criterion (S1-08): at least 10 of the original samples complete
the full loop and appear correctly in the data store.
"""
import os
import sys
import glob
import logging

from router import choose_model
from transcribe import transcribe
from extract import extract
from store import build_transaction, append_transaction, get_all_transactions
from confirmation import format_confirmation
from categories import FIXED_CATEGORIES

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("smoke_run")

VOICE_DIR = "voice_samples"
TEST_USER_ID = "smoke_test_user"   # fixed id so runs don't create a fresh household_XX every time
MIN_REQUIRED_PASS = 10


def get_duration_seconds(filepath: str) -> float:
    """Best-effort duration in seconds for an .ogg voice file."""
    try:
        from mutagen.oggopus import OggOpus
        return float(OggOpus(filepath).info.length)
    except Exception:
        pass
    try:
        from mutagen.oggvorbis import OggVorbis
        return float(OggVorbis(filepath).info.length)
    except Exception:
        pass
    import subprocess, json as _json
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", filepath
        ])
        return float(_json.loads(out)["format"]["duration"])
    except Exception as e:
        raise RuntimeError(f"could not determine duration for {filepath}: {e}")


def run_one(filepath: str) -> dict:
    """Runs one voice sample through the full pipeline. Returns a result record."""
    sample_id = os.path.splitext(os.path.basename(filepath))[0]
    result = {"sample_id": sample_id, "path": filepath, "ok": False, "error": None}

    try:
        duration_s = get_duration_seconds(filepath)
        result["duration_s"] = duration_s

        model_choice = choose_model(duration_s)
        result["model_choice"] = model_choice

        with open(filepath, "rb") as f:
            audio_bytes = f.read()

        text, model_used = transcribe(audio_bytes, model=model_choice)
        result["transcript"] = text
        result["model_used"] = model_used
        logger.info(f"[{sample_id}] duration={duration_s:.1f}s model={model_used} transcript=\"{text}\"")

        transactions = extract(text)
        result["transactions"] = transactions
        logger.info(f"[{sample_id}] extracted {len(transactions)} transaction(s)")

        invalid = [t for t in transactions if t.get("category") not in FIXED_CATEGORIES]
        if invalid:
            raise ValueError(f"invalid categories returned: {invalid}")

        stored_ids = []
        for t in transactions:
            transaction = build_transaction(
                amount=t.get("amount"),
                category=t.get("category"),
                note=t.get("note", ""),
                transcript=text,
                model=model_used,
                needs_review=(t.get("amount") is None),
            )
            append_transaction(TEST_USER_ID, transaction)
            stored_ids.append(transaction["id"])
        result["stored_ids"] = stored_ids

        reply = format_confirmation(transactions)
        result["reply"] = reply
        logger.info(f"[{sample_id}] reply:\n{reply}\n")

        result["ok"] = True

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[{sample_id}] FAILED: {e}\n")

    return result


def verify_store(expected_ids: set) -> dict:
    """Reads everything back for the test household and checks every stored id shows up."""
    all_txns = get_all_transactions(TEST_USER_ID)
    found_ids = {t["id"] for t in all_txns}
    missing = expected_ids - found_ids
    return {
        "total_in_store": len(all_txns),
        "expected": len(expected_ids),
        "missing": missing,
        "verified": len(missing) == 0,
    }


def main():
    files = sorted(
        glob.glob(os.path.join(VOICE_DIR, "*.ogg")),
        key=lambda p: int("".join(filter(str.isdigit, os.path.basename(p))) or 0),
    )
    if not files:
        print(f"No .ogg files found in {VOICE_DIR}/")
        sys.exit(1)

    print(f"Found {len(files)} voice samples. Running full pipeline on each...\n")

    results = [run_one(f) for f in files]

    passed = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]

    all_expected_ids = set()
    for r in passed:
        all_expected_ids.update(r.get("stored_ids", []))

    store_check = verify_store(all_expected_ids)

    print("=" * 70)
    print("SMOKE RUN SUMMARY — S1-08")
    print("=" * 70)
    for r in results:
        status = "✅ PASS" if r["ok"] else f"❌ FAIL ({r['error']})"
        print(f"{r['sample_id']:12s} {status}")

    print("-" * 70)
    print(f"Passed: {len(passed)}/{len(results)}")
    print(f"Failed: {len(failed)}/{len(results)}")
    print(
        f"Store verification: {'✅ OK' if store_check['verified'] else '❌ MISMATCH'} "
        f"({store_check['expected']} expected, {store_check['total_in_store']} total in store, "
        f"missing={store_check['missing']})"
    )

    acceptance_met = len(passed) >= MIN_REQUIRED_PASS and store_check["verified"]
    print("-" * 70)
    print(
        "Acceptance criterion (>=10 samples complete loop + appear in store): "
        f"{'✅ MET' if acceptance_met else '❌ NOT MET'}"
    )
    print("=" * 70)

    sys.exit(0 if acceptance_met else 1)


if __name__ == "__main__":
    main()