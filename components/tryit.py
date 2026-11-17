import html

import streamlit as st

from gen.checks import LABELS
from gen.guard import section_label
from gen.prompts import BASELINE, ORDER, PROMPTS
from gen.system import page_text, respond
from rag.config import has_api_key
from rag.query import validate_query


def prompt_name(pid):
    return "Extractive (no model)" if pid == BASELINE else f"{pid} {PROMPTS[pid]['name']}"


def show_checks(checks):
    from gen.checks import CRITICAL

    lines = []
    for key in CRITICAL + ["refs"]:
        value = checks.get(key)
        if value is None:
            continue
        lines.append(f"{'PASS' if value else 'FAIL'}  {LABELS[key]}")
    st.text("\n".join(lines))
    st.caption(f"Score {checks['score']:.0%} | {checks['words']} words | {'passes the benchmark' if checks['pass'] else 'fails the benchmark'}")


def render_response(result, hits, checks=None):
    if result["error"]:
        st.error(result["error"])
        return
    st.markdown(f'<div class="answer-box">{html.escape(result["text"])}</div>', unsafe_allow_html=True)
    for line in result["sources"]:
        st.markdown(f'<div class="source-line">{html.escape(line)}</div>', unsafe_allow_html=True)
    st.caption(f"{result['action']} | {result['latency']:.0f} ms" + (" | from cache" if result["cached"] else ""))
    if checks:
        show_checks(checks)
    with st.expander("Raw model output"):
        st.text(result["raw"])
    with st.expander("Passages sent to the model"):
        for number, (chunk, score) in enumerate(hits, 1):
            st.markdown(f"**[{number}] {chunk['title']} | {section_label(chunk)} | p. {page_text(chunk)}** (score {score:.2f})")
            st.text(chunk["text"])


def render_tryit(ctx):
    from gen.checks import check_response

    items = ctx["items"]
    pick = st.selectbox("Benchmark question", ["(write my own)"] + [i["question"] for i in items])
    typed = st.text_input("Question", value="" if pick == "(write my own)" else pick)
    options = ORDER + [BASELINE]
    pid = st.selectbox("Prompt version", options, index=options.index("v5"), format_func=prompt_name)
    if pid != BASELINE:
        st.caption(PROMPTS[pid]["change"])
    if not st.button("Get answer", type="primary"):
        return
    ok, cleaned = validate_query(typed) if typed else (False, "Please type a question.")
    if not ok:
        st.warning(cleaned)
        return
    if pid != BASELINE and not has_api_key():
        st.error("No Groq key found. Put GROQ_API_KEY in the .env file and restart the app.")
        return
    retriever = ctx["retriever"]
    vector, hits = retriever.search(cleaned, ctx["settings"]["k"])
    with st.spinner("Writing the answer..."):
        result = respond(pid, cleaned, hits, vector, retriever.embedder, ctx["llm"]() if pid != BASELINE else None, ctx["cache"], ctx["settings"]["gate"])
    item = next((i for i in items if i["question"] == cleaned), None)
    checks = check_response(item, result, hits) if item else None
    render_response(result, hits, checks)
