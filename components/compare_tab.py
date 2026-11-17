import pandas as pd
import streamlit as st

from components.tryit import prompt_name
from gen.checks import CRITICAL, LABELS
from gen.prompts import BASELINE, ORDER
from gen.runner import by_kind, compare, failures, retrieve_all, run_many
from rag.config import has_api_key

PERCENT_COLUMNS = ["pass_rate", "score", "facts", "no_hallucination", "cited", "cite_correct", "concise", "refusal_ok", "refs"]


def percent(frame, columns):
    shown = frame.copy()
    for column in columns:
        if column in shown:
            shown[column] = shown[column].astype(float) * 100
    return shown


def render_compare(ctx):
    options = ORDER + [BASELINE]
    chosen = st.multiselect("Prompt versions", options, default=options, format_func=prompt_name)
    total = len(ctx["items"])
    count = st.slider("Questions to run", 5, total, total)
    needs_key = any(p != BASELINE for p in chosen)
    st.caption("Model answers are saved in results/llm_cache.json, so a second run with the same prompts is instant. "
               "A first full run takes about 10 minutes because calls are spaced out to stay under the rate limit.")
    if needs_key and not has_api_key():
        st.error("No Groq key found. Put GROQ_API_KEY in the .env file and restart the app. The extractive row can still run.")
    if st.button("Run benchmark", type="primary", disabled=not chosen):
        items = ctx["items"][:count]
        retrieved = retrieve_all(ctx["retriever"], items, ctx["settings"]["k"])
        bar = st.progress(0.0)
        steps = max(1, len(chosen) * len(items))
        done = {"n": 0}

        def progress(pid, number, size):
            done["n"] += 1
            bar.progress(min(1.0, done["n"] / steps), text=f"{prompt_name(pid)}: {number}/{size}")

        llm = ctx["llm"]() if needs_key and has_api_key() else None
        st.session_state["runs"] = run_many(chosen, items, retrieved, ctx["retriever"].embedder, llm, ctx["cache"], ctx["settings"]["gate"], progress)
        bar.empty()

    runs = st.session_state.get("runs")
    if not runs:
        st.info("Press Run benchmark to compare the prompt versions.")
        return

    rows = compare(runs)
    frame = pd.DataFrame(rows)
    frame["Prompt"] = [prompt_name(r["id"]) for r in rows]
    columns = ["Prompt", "pass_rate", "score", "facts", "no_hallucination", "cited", "cite_correct", "concise", "refusal_ok", "words", "errors"]
    shown = percent(frame[columns], PERCENT_COLUMNS)
    config = {c: st.column_config.NumberColumn(LABELS.get(c, c.replace("_", " ").title()), format="%.0f%%") for c in PERCENT_COLUMNS if c in columns}
    config["pass_rate"] = st.column_config.NumberColumn("Pass rate", format="%.0f%%")
    config["score"] = st.column_config.NumberColumn("Score", format="%.0f%%")
    config["words"] = st.column_config.NumberColumn("Avg words", format="%.0f")
    st.subheader("Comparison")
    st.dataframe(shown, hide_index=True, column_config=config)
    errors = sum(r["errors"] for r in rows)
    if errors:
        st.warning(f"{errors} model calls failed (rate limit or network). Press Run benchmark again to retry only those.")

    chart = percent(frame.set_index("Prompt")[["pass_rate", "no_hallucination", "cite_correct"]], ["pass_rate", "no_hallucination", "cite_correct"])
    chart.columns = ["Pass rate", "No made-up facts", "Right source cited"]
    st.bar_chart(chart, stack=False)

    ids = [r["id"] for r in rows]
    st.subheader("Look at one prompt")
    pid = st.selectbox("Prompt", ids, index=len(ids) - 1, format_func=prompt_name, key="compare_pick")
    kinds = pd.DataFrame(by_kind(runs[pid]))
    kinds = percent(kinds, ["pass_rate", "score"])
    st.dataframe(kinds, hide_index=True, column_config={
        "kind": "Type", "questions": "Questions",
        "pass_rate": st.column_config.NumberColumn("Pass rate", format="%.0f%%"), "score": st.column_config.NumberColumn("Score", format="%.0f%%")})
    left = failures(runs[pid])
    if left:
        st.write(f"{len(left)} questions fail at least one check.")
        st.dataframe(pd.DataFrame([{"ID": f["id"], "Type": f["kind"], "Question": f["question"], "Failed": ", ".join(f["failed"]) or f["error"], "Guard": f["action"]} for f in left]), hide_index=True)
    else:
        st.success("No failures.")
