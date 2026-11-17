from .prompts import BASELINE, ORDER, PROMPTS
from .runner import compare, failures


def pct(value):
    return "n/a" if value is None else f"{value:.0%}"


def summary_lines(runs):
    table = {row["id"]: row for row in compare(runs)}
    ids = [p for p in ORDER if p in table]
    lines = []
    if len(ids) >= 2:
        first, last = table[ids[0]], table[ids[-1]]
        lines.append(
            f"Pass rate went from {pct(first['pass_rate'])} with '{first['name']}' to {pct(last['pass_rate'])} with '{last['name']}'. "
            f"The average benchmark score went from {first['score']:.0%} to {last['score']:.0%}."
        )
        steps = []
        for a, b in zip(ids, ids[1:]):
            steps.append((table[b]["pass_rate"] - table[a]["pass_rate"], a, b))
        gain, a, b = max(steps)
        lines.append(f"The biggest single jump was {PROMPTS[a]['name']} to {PROMPTS[b]['name']}: {gain:+.0%} pass rate ({PROMPTS[b]['change']})")
        lines.append(f"Made-up facts (wrong numbers or trap answers) went from {pct(first['hallucination'])} to {pct(last['hallucination'])} of responses.")
        lines.append(f"Correct refusals went from {pct(first['correct_refusal'])} to {pct(last['correct_refusal'])}; good questions wrongly refused: {pct(first['false_refusal'])} to {pct(last['false_refusal'])}.")
        lines.append(f"Average answer length went from {first['words']:.0f} to {last['words']:.0f} words.")
        lines.append(f"Right source cited: {pct(first['cite_correct'])} to {pct(last['cite_correct'])}.")
    for pid in ("v4", "v5"):
        if pid in table and table[pid]["refs"] is not None:
            lines.append(f"{PROMPTS[pid]['name']}: the section and page written by the model were correct in {pct(table[pid]['refs'])} of the answers that had them.")
    if "v5" in table:
        actions = table["v5"]["actions"]
        lines.append("What the guard did on the final prompt: " + ", ".join(f"{n} x {k}" for k, n in sorted(actions.items(), key=lambda x: -x[1])) + ".")
        left = failures(runs["v5"])
        if left:
            lines.append(f"Still failing on the final prompt: {len(left)} questions ({', '.join(f['id'] for f in left)}).")
    if BASELINE in table:
        base = table[BASELINE]
        lines.append(f"For comparison, the old extractive answer (copied sentences, no model) passes {pct(base['pass_rate'])} with {pct(base['facts'])} of key facts included and {pct(base['no_hallucination'])} free of made-up facts.")
    return lines
