import re

from rag.answer import numbers_in

MARKER = re.compile(r"\[(\d+)(?:\s*:\s*([^\]]*))?\]")
REF = re.compile(r"^(.*?)[,;]?\s*pp?\.\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*$", re.IGNORECASE)


def section_label(chunk):
    path = chunk["section_path"] or [chunk["section_title"]]
    if len(path) > 1:
        path = path[1:]
    return " > ".join(p for p in path if p)


def parse_markers(text):
    return [(m.start(), m.end(), int(m.group(1)), (m.group(2) or "").strip()) for m in MARKER.finditer(text)]


def ref_is_valid(ref, chunk):
    found = REF.match(ref.strip())
    if not found:
        return False
    section, first, last = found.group(1).strip().lower(), int(found.group(2)), int(found.group(3) or found.group(2))
    label = section_label(chunk).lower()
    if not section or not (section in label or label in section):
        return False
    return chunk["page_start"] <= first <= chunk["page_end"] and chunk["page_start"] <= last <= chunk["page_end"]


def check_refs(text, hits):
    results = []
    for _, _, number, ref in parse_markers(text):
        if not 1 <= number <= len(hits):
            results.append({"number": number, "valid": False, "has_ref": bool(ref)})
        else:
            results.append({"number": number, "valid": ref_is_valid(ref, hits[number - 1][0]) if ref else True, "has_ref": bool(ref)})
    return results


def strip_markers(text):
    return re.sub(r"\s+", " ", MARKER.sub("", text)).strip()


def split_segments(text):
    text = MARKER.sub(lambda m: f"[{m.group(1)}]", text)
    parts = re.split(r"\n+|(?<=[.!?\]])\s+(?=[A-Z0-9])", text)
    return [p.strip() for p in parts if p.strip()]


def uncited_segments(text, hits):
    out = []
    for segment in split_segments(text):
        numbers = [n for _, _, n, _ in parse_markers(segment) if 1 <= n <= len(hits)]
        if not numbers:
            out.append(segment)
    return out


def apply_guard(question, raw, hits, vector, embedder, extractive):
    from rag.answer import renumber

    from .prompts import REFUSAL

    text = raw.strip()
    if "could not find this in the guideline" in text.lower() or text.strip(" .*").upper() == "NOT_FOUND":
        return REFUSAL, [], "refused"

    notes = []
    fixed = {"moved": 0, "dropped": 0}

    def resolve(match):
        number, ref = int(match.group(1)), (match.group(2) or "").strip()
        if 1 <= number <= len(hits) and (not ref or ref_is_valid(ref, hits[number - 1][0])):
            return f"[{number}]"
        for index, (chunk, _) in enumerate(hits, 1):
            if ref and ref_is_valid(ref, chunk):
                fixed["moved"] += 1
                return f"[{index}]"
        fixed["dropped"] += 1
        return ""

    text = MARKER.sub(resolve, text)
    if fixed["moved"]:
        notes.append(f"{fixed['moved']} citation(s) moved to the passage named in the reference")
    if fixed["dropped"]:
        notes.append(f"{fixed['dropped']} wrong reference(s) dropped")

    markers = [n for _, _, n, _ in parse_markers(text)]
    if not markers:
        fallback_text, used = extractive(vector, hits, embedder)
        return fallback_text, used, "fallback: no valid citation"

    cited = []
    for n in markers:
        if n not in cited:
            cited.append(n)
    cited_text = " ".join(hits[n - 1][0]["text"] for n in cited)
    body = strip_markers(text)
    unsupported = numbers_in(body) - numbers_in(question) - numbers_in(cited_text)
    if unsupported:
        fallback_text, used = extractive(vector, hits, embedder)
        return fallback_text, used, "fallback: number not in the passages (" + ", ".join(sorted(unsupported)) + ")"

    segments = split_segments(text)
    loose = uncited_segments(text, hits)
    if loose and len(loose) < len(segments):
        for segment in loose:
            text = text.replace(segment, "").strip()
        text = re.sub(r"\n{2,}", "\n", text)
        notes.append(f"{len(loose)} sentence(s) without a citation removed")

    text = MARKER.sub(lambda m: f"[{m.group(1)}]", text)
    text = renumber(text, cited)
    text = re.sub(r"[ \t]+", " ", text).strip()
    action = "kept" if not notes else "cleaned: " + "; ".join(notes)
    return text, [hits[n - 1][0] for n in cited], action
