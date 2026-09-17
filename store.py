import json
import os
import uuid
from datetime import datetime, timezone

DATA_DIR = "data"
COUNTER_FILE = os.path.join(DATA_DIR, "_household_counter.json")


def _load_counter() -> dict:
    """Loads the next available number + known chat_id -> household_name map.
    No real names are ever stored here — just chat_id -> household_XX."""
    if not os.path.exists(COUNTER_FILE):
        return {"next_number": 1, "known_ids": {}}
    with open(COUNTER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_counter(counter: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        json.dump(counter, f, ensure_ascii=False, indent=2)


def get_household_name(user_id: str) -> str:
    """
    First time this chat_id appears, it gets the next available household number.
    Same chat_id always maps to the same file on future messages (so the same
    household's data stays together) — but nothing here records who that is.
    """
    counter = _load_counter()

    if user_id in counter["known_ids"]:
        return counter["known_ids"][user_id]

    household_name = f"household_{counter['next_number']:02d}"
    counter["known_ids"][user_id] = household_name
    counter["next_number"] += 1
    _save_counter(counter)

    return household_name


def get_household_file(user_id: str) -> str:
    household_name = get_household_name(user_id)
    return os.path.join(DATA_DIR, f"{household_name}.json")


def load_household_data(user_id: str) -> list:
    """Returns an empty list if this is the first transaction for this household."""
    filepath = get_household_file(user_id)
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_household_data(user_id: str, data: list) -> None:
    """Writes the full list back to disk. Creates the folder and file if needed."""
    filepath = get_household_file(user_id)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_transaction(
        amount: float,
        category: str,
        note: str,
        transcript: str,
        model: str,
        currency: str = "EGP",
        needs_review: bool = False,
) -> dict:
    """Builds one transaction record in the fixed shape."""
    return {
        "id": f"t_{uuid.uuid4().hex[:8]}",
        "ts": datetime.now(timezone.utc).astimezone().isoformat(),
        "amount": amount,
        "currency": currency,
        "category": category,
        "note": note,
        "transcript": transcript,
        "model": model,
        "needs_review": needs_review,
    }


def append_transaction(user_id: str, transaction: dict) -> None:
    """Loads, appends, writes back. This is the whole write path."""
    data = load_household_data(user_id)
    data.append(transaction)
    save_household_data(user_id, data)


def get_all_transactions(user_id: str) -> list:
    """Reads everything back for this household — used by reports.py later."""
    return load_household_data(user_id)