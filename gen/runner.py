import json
from collections import Counter
from pathlib import Path
from statistics import mean

from .checks import CRITICAL, LABELS, check_response
from .prompts import BASELINE, ORDER, PROMPTS
from .system import respond

ROOT = Path(__file__).resolve().parent.parent
CHECK_KEYS = CRITICAL + ["refs"]


def load_benchmark(path=None):
    return json.loads(Path(path or ROOT / "benchmark" / "response_benchmark.json").read_text(encoding="utf-8"))


def retrieve_all(retriever, items, k=4):
    out = {}
    for item in items:
        vector, hits = retriever.search(item["question"], k)
        out[item["id"]] = (vector, hits)
    return out


def run_prompt(pid, items, retrieved, embedder, llm=None, cache=None, gate=None, progress=None):
    rows = []
    for number, item in enumerate(items, 1):
        vector, hits = retrieved[item["id"]]
        result = respond(pid, item["question"], hits, vector, embedder, llm, cache, gate)
        checks = check_response(item, result, hits)
        rows.append({"item": item, "result": result, "checks": checks, "hits": hits})
        if progress:
            progress(pid, number, len(items))
    return rows


def run_many(pids, items, retrieved, embedder, llm=None, cache=None, gate=None, progress=None):
    return {pid: run_prompt(pid, items, retrieved, embedder, llm, cache, gate, progress) for pid in pids}


def rate(values):
    values = [v for v in values if v is not None]
    return sum(1 for v in values if v) / len(values) if values else None


def summarise(rows):
    checks = [r["checks"] for r in rows]
    refuse = [r for r in rows if r["item"]["expect"] == "refuse"]
    answer = [r for r in rows if r["item"]["expect"] == "answer"]
    out = {
        "questions": len(rows),
        "pass_rate": rate([c["pass"] for c in checks]),
        "score": mean(c["score"] for c in checks) if checks else 0.0,
        "hallucination": 1 - rate([c["no_hallucination"] for c in checks]) if checks else 0.0,
        "correct_refusal": rate([r["checks"]["refusal_ok"] for r in refuse]),
        "false_refusal": 1 - rate([r["checks"]["refusal_ok"] for r in answer]) if answer else None,
        "words": mean(c["words"] for c in checks) if checks else 0.0,
        "latency": mean(r["result"]["latency"] for r in rows) if rows else 0.0,
        "errors": sum(1 for r in rows if r["result"]["error"]),
        "actions": dict(Counter(r["result"]["action"].split(":")[0] for r in rows)),
    }
    for key in CHECK_KEYS:
        out[key] = rate([c[key] for c in checks])
    return out


def compare(runs):
    out = []
    for pid, rows in runs.items():
        name = PROMPTS[pid]["name"] if pid in PROMPTS else "Extractive (no model)"
        out.append({"id": pid, "name": name, **summarise(rows)})
    return out


def by_kind(rows):
    kinds = sorted({r["item"]["kind"] for r in rows})
    out = []
    for kind in kinds:
        part = [r for r in rows if r["item"]["kind"] == kind]
        out.append({"kind": kind, "questions": len(part), "pass_rate": rate([r["checks"]["pass"] for r in part]),
                    "score": mean(r["checks"]["score"] for r in part)})
    return out


def failures(rows):
    out = []
    for r in rows:
        failed = [LABELS[k] for k in CRITICAL if r["checks"][k] is False]
        if failed or r["result"]["error"]:
            out.append({"id": r["item"]["id"], "kind": r["item"]["kind"], "question": r["item"]["question"], "failed": failed,
                        "error": r["result"]["error"], "text": r["result"]["text"], "action": r["result"]["action"]})
    return out
