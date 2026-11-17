import re

import numpy as np

from kb.chunking import split_sentences

NUMBER = re.compile(r"\d+(?:\.\d+)?")
BULLET = re.compile(r"^\s*[-*•]\s+")

NOT_FOUND = "NOT_FOUND"

PROMPT = """You answer medical questions using only the numbered passages below.
Rules:
- Use only facts in the passages. Do not add outside knowledge.
- Put the passage number in square brackets after each fact, like [1].
- Keep the answer short and in plain English.
- If the passages do not answer the question, reply with exactly NOT_FOUND.

Passages:
{context}

Question: {question}

Answer:"""


def table_units(text):
    rows = [line for line in text.split("\n") if line.startswith("|")]
    if len(rows) < 3:
        return []
    cells = [[c.strip() for c in row.strip("|").split("|")] for row in rows]
    header = cells[0]
    units = []
    for row in cells[2:]:
        parts = [f"{h}: {v}" for h, v in zip(header, row) if v]
        if parts:
            units.append("; ".join(parts) + ".")
    return units


def unit_groups(chunk):
    text = chunk["text"]
    if chunk["chunk_type"] == "table":
        return [(u, None) for u in table_units(text)]
    out = []
    group = 0
    lead = None
    for block in re.split(r"\n\s*\n", text):
        lines = [line for line in block.split("\n") if line.strip()]
        if lines and all(BULLET.match(line) for line in lines):
            if lead is None:
                group += 1
                lead = group
            out.extend((BULLET.sub("", line).strip(), lead) for line in lines)
            lead = None
            continue
        lead_in = bool(lines) and lines[-1].rstrip().endswith(":") and not BULLET.match(lines[-1])
        if lead_in:
            group += 1
            lead = group
        else:
            lead = None
        for line in lines:
            if BULLET.match(line):
                group += 1
                out.append((BULLET.sub("", line).strip(), group))
            else:
                out.extend((u, lead) for u in split_sentences(line))
    return [(u.strip(), g) for u, g in out if len(u.strip()) > 2 and not u.strip().endswith(":")]


def chunk_units(chunk):
    return [u for u, _ in unit_groups(chunk)]


def pages_label(chunk):
    a, b = chunk["page_start"], chunk["page_end"]
    return f"p. {a}" if a == b else f"pp. {a}-{b}"


def source_line(number, chunk):
    path = " > ".join(chunk["section_path"]) if chunk["section_path"] else chunk["section_title"] or "Untitled section"
    return f"[{number}] {chunk['title']} | {path} | {pages_label(chunk)}"


def build_sources(chunks):
    sources = []
    for number, chunk in enumerate(chunks, 1):
        sources.append({
            "number": number,
            "chunk_id": chunk["chunk_id"],
            "file": chunk["source_file"],
            "title": chunk["title"],
            "section": " > ".join(chunk["section_path"]) if chunk["section_path"] else chunk["section_title"],
            "page_start": chunk["page_start"],
            "page_end": chunk["page_end"],
            "pages": pages_label(chunk),
            "text": chunk["text"],
            "line": source_line(number, chunk),
        })
    return sources


def extractive_answer(question_vec, hits, embedder, threshold, max_units=3, margin=0.10):
    candidates = []
    for rank, (chunk, chunk_score) in enumerate(hits):
        for position, (unit, group) in enumerate(unit_groups(chunk)):
            candidates.append((rank, position, unit, chunk, group))
    if not candidates:
        return "", []
    header = lambda c: " ".join(c["section_path"]) if c["section_path"] else c["section_title"]
    vectors = embedder.encode([f"{header(c)}. {u}" for _, _, u, c, _ in candidates])
    scores = vectors @ question_vec
    best = float(scores.max())
    floor = max(best - margin, 0.75 * best, 0.7 * threshold)
    order = [i for i in np.argsort(-scores) if scores[i] >= floor][:max_units]
    chosen = set(order)
    for i in order:
        rank, _, _, chunk, group = candidates[i]
        if group is not None:
            chosen.update(j for j, c in enumerate(candidates) if c[0] == rank and c[4] == group)
    picked = sorted(chosen, key=lambda i: (candidates[i][0], candidates[i][1]))
    used = []
    lines = []
    for i in picked:
        rank, _, unit, chunk, _ = candidates[i]
        if chunk["chunk_id"] not in used:
            used.append(chunk["chunk_id"])
        number = used.index(chunk["chunk_id"]) + 1
        text = unit if unit.endswith((".", "!", "?")) else unit + "."
        lines.append(f"{text} [{number}]")
    chunk_by_id = {c["chunk_id"]: c for c, _ in hits}
    return " ".join(lines), [chunk_by_id[cid] for cid in used]


def llm_answer(question, hits, model):
    from groq import Groq

    from .config import get_api_key

    chunks = [c for c, _ in hits]
    context = "\n\n".join(f"[{n}] ({c['title']}, {' > '.join(c['section_path'])}, {pages_label(c)})\n{c['text']}" for n, c in enumerate(chunks, 1))
    client = Groq(api_key=get_api_key(), timeout=20, max_retries=0)
    options = {"reasoning_effort": "low"} if "gpt-oss" in model else {}
    reply = client.chat.completions.create(
        model=model, temperature=0.1, max_tokens=2000,
        messages=[{"role": "user", "content": PROMPT.format(context=context, question=question)}],
        **options,
    )
    text = (reply.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("the model sent back an empty answer")
    text = re.sub(r"[【\[]\s*(\d+(?:\s*,\s*\d+)*)\s*[】\]]", lambda m: " ".join(f"[{n.strip()}]" for n in m.group(1).split(",")), text)
    text = text.replace("\u2011", "-")
    if text.strip(" .\n*`").upper() == NOT_FOUND or text.upper().startswith(NOT_FOUND):
        return None, chunks
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text) if 0 < int(n) <= len(chunks)})
    if not cited:
        cited = list(range(1, len(chunks) + 1))
        text = text + " " + " ".join(f"[{n}]" for n in cited)
    return text, [chunks[n - 1] for n in cited], cited


def renumber(text, cited):
    mapping = {old: new for new, old in enumerate(cited, 1)}
    return re.sub(r"\[(\d+)\]", lambda m: f"[{mapping.get(int(m.group(1)), m.group(1))}]", text)


def numbers_in(text):
    return set(NUMBER.findall(re.sub(r"\[\d+\]", "", text)))
