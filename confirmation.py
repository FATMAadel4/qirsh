from datetime import datetime, timezone


def _format_date(dt: datetime = None) -> str:
    """Returns 'today', 'yesterday', or the date, based on when the transaction happened."""
    if dt is None:
        dt = datetime.now(timezone.utc).astimezone()

    now = datetime.now(timezone.utc).astimezone()
    delta_days = (now.date() - dt.date()).days

    if delta_days == 0:
        return "today"
    elif delta_days == 1:
        return "yesterday"
    else:
        return dt.strftime("%b %d")


def format_confirmation(transactions: list[dict], currency: str = "EGP") -> str:
    """
    Takes the list of extracted transactions and returns a glanceable,
    human-readable confirmation message. One line per transaction.
    """
    if not transactions:
        return "معلش مفهمتش إن ده مصروف. لو حابة تسجليه ابعتي المبلغ 🙏"

    lines = []
    for t in transactions:
        amount = t.get("amount")
        category = t.get("category", "Other / uncategorized")
        date_str = _format_date()

        if amount is None:
            line = f"⚠️ {category} · amount missing · {date_str}"
        else:
            line = f"✅ {amount:g} {currency} · {category} · {date_str}"

        note = t.get("note")
        if note:
            line += f" ({note})"

        lines.append(line)

    return "\n".join(lines)