DURATION_THRESHOLD_SECONDS = 3.0


def choose_model(duration_s: float) -> str:
    if duration_s is None:
        raise ValueError("choose_model() requires a duration; text messages don't need routing.")

    if duration_s < DURATION_THRESHOLD_SECONDS:
        return "gpt-4o"
    else:
        return "deepgram"