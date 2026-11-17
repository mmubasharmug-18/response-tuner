import hashlib
import json
import time
from pathlib import Path

from rag.answer import extractive_answer, source_line
from rag.query import needs_emergency_notice

from .guard import apply_guard, check_refs, parse_markers
from .prompts import BASELINE, EMERGENCY_NOTICE, PROMPTS, REFUSAL, USER_TEMPLATE
from .guard import section_label


def format_context(hits):
    blocks = []
    for number, (chunk, _) in enumerate(hits, 1):
        blocks.append(f"[{number}] Document: {chunk['title']} | Section: {section_label(chunk)} | Page: {page_text(chunk)}\n{chunk['text']}")
    return "\n\n".join(blocks)


def page_text(chunk):
    a, b = chunk["page_start"], chunk["page_end"]
    return str(a) if a == b else f"{a}-{b}"


class Cache:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.data = {}
        if self.path and self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {}

    @staticmethod
    def key(model, system, user):
        return hashlib.sha1(f"{model}\n{system}\n{user}".encode("utf-8")).hexdigest()

    def get(self, key):
        return self.data.get(key)

    def put(self, key, value):
        self.data[key] = value
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=1), encoding="utf-8")


def cited_sources(text, chunks):
    seen = []
    for _, _, n, _ in parse_markers(text):
        if 1 <= n <= len(chunks) and n not in seen:
            seen.append(n)
    return [source_line(n, chunks[n - 1]) for n in seen]


def empty_result(pid):
    return {"prompt": pid, "raw": "", "text": "", "marker_chunks": [], "sources": [], "action": "", "error": None,
            "latency": 0.0, "refs": None, "cached": False}


def respond(pid, question, hits, vector, embedder, llm=None, cache=None, gate=None):
    result = empty_result(pid)
    chunks = [c for c, _ in hits]
    flagged = needs_emergency_notice(question)
    started = time.perf_counter()

    if gate is not None and (not hits or hits[0][1] < gate):
        result.update(raw=REFUSAL, text=REFUSAL, action="gate")
        return result

    if pid == BASELINE:
        text, used = extractive_answer(vector, hits, embedder, gate or 0.35)
        if not text:
            text, used = REFUSAL, []
        result.update(raw=text, text=text, marker_chunks=used, sources=[source_line(n, c) for n, c in enumerate(used, 1)],
                      action="extractive", latency=(time.perf_counter() - started) * 1000)
        return result

    spec = PROMPTS[pid]
    user = USER_TEMPLATE.format(context=format_context(hits), question=question)
    model = getattr(llm, "model", "none")
    key = Cache.key(model, spec["system"], user)
    stored = cache.get(key) if cache else None
    try:
        if stored:
            raw, latency = stored["raw"], stored["latency"]
            result["cached"] = True
        else:
            if llm is None:
                raise RuntimeError("no language model is set up")
            call_start = time.perf_counter()
            raw = llm(spec["system"], user)
            latency = (time.perf_counter() - call_start) * 1000
            if cache:
                cache.put(key, {"raw": raw, "latency": latency})
    except Exception as error:
        result.update(error=str(error)[:200], action="error", latency=(time.perf_counter() - started) * 1000)
        return result

    result["raw"] = raw
    result["latency"] = latency
    refs = check_refs(raw, hits)
    with_ref = [r for r in refs if r["has_ref"]]
    if with_ref:
        result["refs"] = {"total": len(with_ref), "valid": sum(1 for r in with_ref if r["valid"])}

    if spec["guard"]:
        text, used, action = apply_guard(question, raw, hits, vector, embedder,
                                          lambda v, h, e: extractive_answer(v, h, e, 0.35))
        if flagged:
            text = EMERGENCY_NOTICE + "\n" + text
        result.update(text=text, marker_chunks=used, sources=[source_line(n, c) for n, c in enumerate(used, 1)], action=action)
        return result

    text = REFUSAL if raw.strip(" .*").upper() == "NOT_FOUND" else raw.strip()
    result.update(text=text, marker_chunks=chunks, sources=cited_sources(text, chunks), action="raw")
    return result
