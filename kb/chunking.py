import re
import textwrap
from dataclasses import dataclass, field

from ingest.schema import table_markdown

TOKEN = re.compile(r"\w+|[^\w\s]")
ABBREVIATIONS = {"dr", "mr", "mrs", "ms", "vs", "e.g", "i.e", "approx", "fig", "no", "st"}
SENTENCE_END = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z0-9(\[])")


@dataclass
class ChunkConfig:
    max_chars: int = 500
    min_chars: int = 120
    overlap_sentences: int = 0


@dataclass
class Unit:
    kind: str
    parts: list
    ids: list
    pages: list
    rows: list | None = None


@dataclass
class Draft:
    kind: str
    text: str
    ids: list = field(default_factory=list)
    pages: list = field(default_factory=list)


def count_tokens(text):
    return len(TOKEN.findall(text))


def split_sentences(text):
    pieces = []
    last = 0
    for found in SENTENCE_END.finditer(text):
        before = text[last:found.start()]
        tail = re.search(r"([A-Za-z]+(?:\.[A-Za-z]+)*)\.$", before)
        if tail and (tail.group(1).lower() in ABBREVIATIONS or (len(tail.group(1)) == 1 and tail.group(1).isupper())):
            continue
        pieces.append(text[last:found.end()].strip())
        last = found.end()
    rest = text[last:].strip()
    if rest:
        pieces.append(rest)
    return pieces


def pack_sentences(text, max_chars, overlap):
    sentences = []
    for sentence in split_sentences(text):
        if len(sentence) > max_chars:
            sentences.extend(textwrap.wrap(sentence, max_chars, break_long_words=True, break_on_hyphens=False))
        else:
            sentences.append(sentence)
    out = []
    current = []
    for sentence in sentences:
        if current and len(" ".join(current + [sentence])) > max_chars:
            out.append(" ".join(current))
            tail = current[-overlap:] if overlap else []
            current = tail if tail and len(" ".join(tail + [sentence])) <= max_chars else []
        current.append(sentence)
    if current:
        out.append(" ".join(current))
    return out


def units_from(blocks):
    units = []
    run = []

    def close_run():
        if run:
            parts = ["  " * (b.level or 0) + "- " + b.text.strip() for b in run]
            units.append(Unit("list", parts, [b.id for b in run], [b.page for b in run]))
            run.clear()

    for block in blocks:
        if block.type == "list_item":
            run.append(block)
            continue
        close_run()
        if block.type == "table":
            rows = [[str(c) for c in r] for r in (block.rows or [])]
            if rows:
                units.append(Unit("table", [], [block.id], [block.page], rows))
        else:
            units.append(Unit("text", [block.text.strip()], [block.id], [block.page]))
    close_run()
    return units


def split_table(rows, max_chars):
    whole = table_markdown(rows)
    if len(whole) <= max_chars or len(rows) < 3:
        return [whole]
    header, body = rows[0], rows[1:]
    pieces = []
    current = []
    for row in body:
        trial = table_markdown([header] + current + [row])
        if current and len(trial) > max_chars:
            pieces.append(table_markdown([header] + current))
            current = []
        current.append(row)
    if current:
        pieces.append(table_markdown([header] + current))
    return pieces


def split_list(parts, max_chars, overlap):
    if len("\n".join(parts)) <= max_chars:
        return ["\n".join(parts)]
    pieces = []
    current = []
    for part in parts:
        if len(part) > max_chars:
            if current:
                pieces.append("\n".join(current))
                current = []
            pieces.extend(pack_sentences(part, max_chars, overlap))
            continue
        if current and len("\n".join(current + [part])) > max_chars:
            pieces.append("\n".join(current))
            current = []
        current.append(part)
    if current:
        pieces.append("\n".join(current))
    return pieces


def chunk_blocks(blocks, config):
    drafts = []
    current = None

    def flush():
        nonlocal current
        if current and current.text.strip():
            drafts.append(current)
        current = None

    for unit in units_from(blocks):
        if unit.kind == "table":
            flush()
            for piece in split_table(unit.rows, config.max_chars):
                drafts.append(Draft("table", piece, list(unit.ids), list(unit.pages)))
            continue
        if unit.kind == "list":
            pieces = split_list(unit.parts, config.max_chars, config.overlap_sentences)
        else:
            text = unit.parts[0]
            pieces = [text] if len(text) <= config.max_chars else pack_sentences(text, config.max_chars, config.overlap_sentences)
        for piece in pieces:
            if current and len(current.text) + 2 + len(piece) <= config.max_chars:
                current.text += "\n\n" + piece
                current.kind = current.kind if current.kind == unit.kind else "mixed"
                current.ids += [i for i in unit.ids if i not in current.ids]
                current.pages += unit.pages
            else:
                flush()
                current = Draft(unit.kind, piece, list(unit.ids), list(unit.pages))
    flush()

    merged = []
    for draft in drafts:
        if merged:
            before = merged[-1]
            small = len(draft.text) < config.min_chars
            fits = len(before.text) + 2 + len(draft.text) <= config.max_chars * 1.2
            if small and fits and draft.kind != "table" and before.kind != "table":
                before.text += "\n\n" + draft.text
                before.kind = before.kind if before.kind == draft.kind else "mixed"
                before.ids += [i for i in draft.ids if i not in before.ids]
                before.pages += draft.pages
                continue
        merged.append(draft)
    return merged
