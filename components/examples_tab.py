import streamlit as st

from components.tryit import prompt_name, render_response
from gen.checks import CRITICAL, LABELS


def render_examples(ctx):
    runs = st.session_state.get("runs")
    if not runs:
        st.info("Run the benchmark in the Compare prompts tab first.")
        return
    first = next(iter(runs.values()))
    labels = [f"{r['item']['id']}  {r['item']['question']}" for r in first]
    pick = st.selectbox("Question", labels)
    index = labels.index(pick)
    item = first[index]["item"]
    st.write(f"Should: {'answer' if item['expect'] == 'answer' else 'refuse'}. " + (f"Must include: {' + '.join('/'.join(g) for g in item['facts'])}." if item["facts"] else ""))
    for pid, rows in runs.items():
        row = rows[index]
        st.subheader(prompt_name(pid))
        render_response(row["result"], row["hits"], row["checks"])
