import streamlit as st

STYLE = """
<style>
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2fb6d8 0%, #4a9fd8 100%);
}
[data-testid="stSidebar"] label *,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
    color: #10222e;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #07151d;
    font-weight: 700;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea {
    background: #ffffff;
    border-radius: 8px;
}
[data-testid="stSidebar"] [data-testid="stSliderTickBarMin"],
[data-testid="stSidebar"] [data-testid="stSliderTickBarMax"] {
    color: #10222e;
}
[data-testid="stSidebar"] button[kind="secondary"] {
    background: #ffffff;
    border: none;
}
[data-testid="stSidebar"] button[kind="primary"] * {
    color: #ffffff;
}
.app-title {
    text-align: center;
    font-size: 2.4rem;
    font-weight: 700;
    margin-top: 0.5rem;
}
.app-subtitle {
    text-align: center;
    color: #555a66;
    margin-bottom: 1.5rem;
}
.stButton > button {
    border-radius: 8px;
}
.stTextArea textarea {
    background: #f1f2f8;
    font-family: monospace;
    font-size: 13px;
}
.answer-box {
    white-space: pre-wrap;
    background: #f1f2f8;
    border-left: 4px solid #5a5fc8;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
}
.source-line {
    font-size: 0.9rem;
    color: #3b3f4d;
    margin: 0.15rem 0;
}
.passage {
    background: #f1f2f8;
    border-radius: 8px;
    padding: 0.7rem 1rem;
    margin-bottom: 0.6rem;
    border-left: 4px solid #9aa0d8;
}
.passage.good { border-left-color: #2e9e5b; }
.passage.bad { border-left-color: #cf4a4a; }
.passage.low { opacity: 0.6; }
.passage-head { font-weight: 600; font-size: 0.92rem; margin-bottom: 0.3rem; }
.passage-text { white-space: pre-wrap; font-size: 0.9rem; color: #2a2d3a; }
.decision {
    border-radius: 8px;
    padding: 0.6rem 1rem;
    margin: 0.5rem 0 1rem 0;
    font-weight: 600;
}
.decision.yes { background: #e3f4ea; color: #1b5e38; }
.decision.no { background: #fbe7e7; color: #8a2d2d; }
</style>
"""


def apply_styles():
    st.markdown(STYLE, unsafe_allow_html=True)


def title(text, subtitle):
    st.markdown(f'<div class="app-title">{text}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="app-subtitle">{subtitle}</div>', unsafe_allow_html=True)
