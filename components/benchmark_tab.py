from pathlib import Path

import pandas as pd
import streamlit as st

STANDARD = Path(__file__).resolve().parent.parent / "benchmark" / "RESPONSE_STANDARD.md"


def render_benchmark(ctx):
    st.write("The benchmark says what a good response must look like for 35 questions. The standard comes first, then the questions.")
    st.markdown(STANDARD.read_text(encoding="utf-8"))
    items = ctx["items"]
    kinds = sorted({i["kind"] for i in items})
    pick = st.multiselect("Question type", kinds, default=kinds)
    rows = []
    for item in items:
        if item["kind"] not in pick:
            continue
        rows.append({
            "ID": item["id"], "Type": item["kind"], "Question": item["question"],
            "Should": "answer" if item["expect"] == "answer" else "refuse",
            "Must include": " + ".join("/".join(g) for g in item["facts"]),
            "Must not include": ", ".join(item["forbidden"]),
            "Source": ", ".join(f"{c['doc'].replace('_guideline.pdf', '')} p.{'-'.join(map(str, c['pages']))}" for c in item["cite"]),
            "Max words": item["max_words"],
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    counts = pd.Series([i["kind"] for i in items]).value_counts()
    st.bar_chart(counts)
