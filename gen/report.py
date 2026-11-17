from .checks import LABELS
from .findings import pct, summary_lines
from .prompts import PROMPTS
from .runner import by_kind, compare, failures


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def build_report(runs, model="", gate=None):
    rows = compare(runs)
    parts = [f"# Response generation results\n\nModel: {model} | {rows[0]['questions']} benchmark questions | retrieval gate: {'on at ' + format(gate, '.2f') if gate is not None else 'off'}"]
    head = ["Prompt", "Pass rate", "Score", "Key facts", "No made-up facts", "Cited", "Right source", "Short", "Refuses right", "Words"]
    body = [[f"{r['id']} {r['name']}", pct(r["pass_rate"]), f"{r['score']:.0%}", pct(r["facts"]), pct(r["no_hallucination"]), pct(r["cited"]),
             pct(r["cite_correct"]), pct(r["concise"]), pct(r["refusal_ok"]), f"{r['words']:.0f}"] for r in rows]
    parts.append("## Prompt comparison\n\n" + md_table(head, body))
    refs = [[f"{r['id']} {r['name']}", pct(r["refs"])] for r in rows if r["refs"] is not None]
    if refs:
        parts.append("## Section and page written by the model\n\n" + md_table(["Prompt", "Correct"], refs))
    last = list(runs)[-1] if "v5" not in runs else "v5"
    kinds = [[k["kind"], k["questions"], pct(k["pass_rate"]), f"{k['score']:.0%}"] for k in by_kind(runs[last])]
    parts.append(f"## By question type ({last})\n\n" + md_table(["Type", "Questions", "Pass rate", "Score"], kinds))
    left = failures(runs[last])
    if left:
        lines = [[f["id"], f["kind"], ", ".join(f["failed"]) or f["error"], f["action"]] for f in left]
        parts.append(f"## Still failing ({last})\n\n" + md_table(["ID", "Type", "Failed", "Guard"], lines))
    parts.append("## Findings\n\n" + "\n".join("- " + line for line in summary_lines(runs)))
    parts.append("## Prompts\n\n" + "\n".join(f"- {pid} {spec['name']}: {spec['change']}" for pid, spec in PROMPTS.items()))
    return "\n\n".join(parts) + "\n"
