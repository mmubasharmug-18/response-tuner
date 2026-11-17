import streamlit as st

from gen.findings import summary_lines
from gen.report import build_report

LIMITS = [
    "The benchmark has 35 questions that I wrote against five short example guidelines, so the scores look better than real use.",
    "The checks are rules, not a person reading the answers. A fact written in different words can be missed, and a wrong sentence with no numbers can pass.",
    "Model answers change a little from run to run. The saved answers in results/llm_cache.json keep a comparison fair, but a new run can move a score by a question or two.",
    "The guard cannot tell if a cited sentence is really supported. It only checks the reference, the numbers and the citation marks.",
    "The free Groq plan has rate limits, so a first full run takes about 10 minutes.",
]


def render_findings(ctx):
    runs = st.session_state.get("runs")
    if not runs:
        st.info("Run the benchmark in the Compare prompts tab first.")
        return
    for line in summary_lines(runs):
        st.write("- " + line)
    st.subheader("Limitations")
    for item in LIMITS:
        st.write("- " + item)
    st.subheader("Report")
    st.download_button("Download report (.md)", build_report(runs, ctx["model"], ctx["settings"]["gate"]), file_name="response_report.md")
