import re

MAX_QUERY_CHARS = 500
MIN_QUERY_CHARS = 3

EMERGENCY = re.compile(
    r"\b(emergency|overdos\w*|suicid\w*|unconscious|cannot breathe|can't breathe|not breathing|severe bleeding|"
    r"chest pain|having a stroke|heart attack|anaphyla\w*)\b",
    re.IGNORECASE,
)


def validate_query(text):
    if text is None:
        return False, "Please type a question."
    cleaned = " ".join(str(text).split())
    if not cleaned:
        return False, "Please type a question."
    if len(cleaned) < MIN_QUERY_CHARS:
        return False, "The question is too short. Please write a full question."
    if len(cleaned) > MAX_QUERY_CHARS:
        return False, f"The question is too long. Please keep it under {MAX_QUERY_CHARS} characters."
    letters = sum(ch.isalpha() for ch in cleaned)
    if letters == 0:
        return False, "The question has no words. Please write a medical question."
    if letters < 0.4 * len(cleaned.replace(" ", "")):
        return False, "The question has too many symbols or numbers. Please write it in words."
    if len(re.findall(r"[A-Za-z]{2,}", cleaned)) < 2:
        return False, "Please write a question with at least two words."
    return True, cleaned


def needs_emergency_notice(text):
    return bool(EMERGENCY.search(text or ""))
