import re
from statistics import mean

from rag.answer import numbers_in

from .guard import parse_markers, split_segments, strip_markers
from .prompts import EMERGENCY_NOTICE

BANNED = ("the passage", "the passages", "the context", "provided text", "as an ai", "language model", "the guideline passages")
CRITICAL = ["facts", "refusal_ok", "no_hallucination", "cited", "cite_correct", "concise", "emergency", "style"]
LABELS = {
    "facts": "Key facts included", "refusal_ok": "Refuses only when it should", "no_hallucination": "No made-up facts",
    "cited": "Every sentence cited", "cite_correct": "Right source cited", "concise": "Short enough", "emergency": "Emergency step first",
    "style": "Plain style", "refs": "Section and page correct",
}


def is_refusal(text):
    low = text.lower()
    return "could not find this in the guideline" in low or "not_found" in low


def overlaps(chunk, pages):
    return any(chunk["page_start"] <= p <= chunk["page_end"] for p in pages)


def matches_source(chunk, cite):
    return any(chunk["source_file"] == c["doc"] and overlaps(chunk, c["pages"]) for c in cite)


def word_count(text):
    body = strip_markers(text).replace(EMERGENCY_NOTICE, "")
    return len(body.split())


def check_response(item, result, hits):
    text = result["text"]
    chunks = result["marker_chunks"]
    answer_expected = item["expect"] == "answer"
    refused = is_refusal(text)
    body = strip_markers(text)
    low = body.lower()
    out = {}

    out["refusal_ok"] = (not refused) if answer_expected else refused
    out["facts"] = all(any(alt.lower() in low for alt in group) for group in item["facts"]) if answer_expected else None

    allowed = numbers_in(item["question"])
    for chunk, _ in hits:
        allowed |= numbers_in(chunk["text"])
    made_up = bool(numbers_in(body) - allowed) if not refused else False
    trapped = any(f.lower() in low for f in item["forbidden"])
    out["no_hallucination"] = not (made_up or trapped)

    out["concise"] = word_count(text) <= item["max_words"]
    out["style"] = not any(b in low for b in BANNED)

    if answer_expected:
        notice = EMERGENCY_NOTICE.lower()
        segments = [s for s in split_segments(text) if s.lower() != notice]
        valid = [n for _, _, n, _ in parse_markers(text) if 1 <= n <= len(chunks)]
        covered = [s for s in segments if any(1 <= n <= len(chunks) for _, _, n, _ in parse_markers(s))]
        out["cited"] = bool(valid) and bool(segments) and len(covered) / len(segments) >= 0.8 and not refused
        out["cite_correct"] = any(matches_source(chunks[n - 1], item["cite"]) for n in valid) if valid else False
    else:
        out["cited"] = None
        out["cite_correct"] = None

    out["emergency"] = ("emergency" in text[:220].lower()) if item["emergency"] else None

    refs = result.get("refs") or {"total": 0, "valid": 0}
    out["refs"] = (refs["valid"] == refs["total"]) if refs["total"] and answer_expected else None

    applicable = [v for v in out.values() if v is not None]
    out["score"] = mean(applicable) if applicable else 0.0
    out["pass"] = all(out[k] for k in CRITICAL if out[k] is not None)
    out["words"] = word_count(text)
    return out
