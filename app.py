from pathlib import Path

import streamlit as st

from components.benchmark_tab import render_benchmark
from components.compare_tab import render_compare
from components.examples_tab import render_examples
from components.findings_tab import render_findings
from components.prompts_tab import render_prompts
from components.sidebar import render_sidebar
from components.styles import apply_styles, title
from components.tryit import render_tryit
from gen import kbase
from gen.llm import make_llm
from gen.runner import load_benchmark
from gen.system import Cache
from rag.config import LLM_MODEL

ROOT = Path(__file__).parent

st.set_page_config(page_title="Response Lab", layout="wide")
apply_styles()
title("Response Lab", "Make the RAG answers accurate, short and properly cited, and measure each prompt change against a benchmark.")


@st.cache_resource(show_spinner="Reading documents and embedding chunks...")
def get_retriever(files, model_id):
    return kbase.make_retriever(files, model_id)


@st.cache_resource
def get_cache():
    return Cache(ROOT / "results" / "llm_cache.json")


@st.cache_resource
def get_llm():
    return make_llm()


settings = render_sidebar()
if not settings["files"]:
    st.info("Pick some guideline documents in the sidebar to start.")
    st.stop()

try:
    retriever = get_retriever(tuple(settings["files"]), settings["model_id"])
except Exception as error:
    st.error(f"Could not load the documents or the embedding model: {error}")
    st.stop()

if not retriever.chunks:
    st.error("No text could be read from these documents.")
    st.stop()

ctx = {"settings": settings, "retriever": retriever, "items": load_benchmark(), "cache": get_cache(), "llm": get_llm, "model": LLM_MODEL}
st.caption(f"{len(retriever.chunks)} chunks | {len(ctx['items'])} benchmark questions | embeddings: {settings['model_label']} | answers: {LLM_MODEL}")

tabs = st.tabs(["Try it", "Benchmark", "Compare prompts", "Examples", "Prompts", "Findings"])
with tabs[0]:
    render_tryit(ctx)
with tabs[1]:
    render_benchmark(ctx)
with tabs[2]:
    render_compare(ctx)
with tabs[3]:
    render_examples(ctx)
with tabs[4]:
    render_prompts()
with tabs[5]:
    render_findings(ctx)
