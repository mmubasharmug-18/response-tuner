import streamlit as st

from gen.prompts import ORDER, PROMPTS, USER_TEMPLATE


def render_prompts():
    st.write("Only the system prompt changes between versions. The passages and the question are sent the same way every time.")
    st.caption("What every version receives as the user message:")
    st.code(USER_TEMPLATE, language="text")
    for pid in ORDER:
        spec = PROMPTS[pid]
        with st.expander(f"{pid} {spec['name']}: {spec['change']}", expanded=pid == "v5"):
            st.code(spec["system"], language="text")
            if spec["guard"]:
                st.write("Code after the model: wrong section or page references are fixed or dropped, a number that is not in the cited passages "
                         "sends the answer back to the extractive text, sentences without a citation are removed, and an emergency notice is added when the question needs one.")
