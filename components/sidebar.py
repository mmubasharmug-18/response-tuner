from pathlib import Path

import streamlit as st

from rag.config import LLM_MODEL, has_api_key
from rag.embedder import DEFAULT_THRESHOLDS, MODELS

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "guidelines"


def sample_names():
    return sorted(p.name for p in SAMPLES.iterdir() if p.suffix.lower() == ".pdf") if SAMPLES.exists() else []


def render_sidebar():
    with st.sidebar:
        st.header("Settings")
        source = st.radio("Documents", ["Sample guidelines", "Upload files"])
        if source == "Sample guidelines":
            names = sample_names()
            picked = st.multiselect("Files", names, default=names)
            files = [(n, (SAMPLES / n).read_bytes()) for n in picked]
        else:
            uploads = st.file_uploader("Guideline files", type=["pdf", "docx", "txt", "html", "htm"], accept_multiple_files=True)
            files = [(u.name, u.getvalue()) for u in uploads or []]

        st.header("Retrieval")
        model_label = st.selectbox("Embedding model", list(MODELS))
        model_id = MODELS[model_label]
        k = st.slider("Passages sent to the model", 1, 8, 4)
        gate = st.checkbox("Refuse before the model when the match is weak", value=False,
                           help="Off by default so the benchmark tests the prompt, not the retrieval gate.")
        threshold = st.slider("Threshold", 0.0, 0.95, float(DEFAULT_THRESHOLDS.get(model_id, 0.35)), step=0.01, key=f"gate_{model_id}")

        st.header("Language model")
        st.write(LLM_MODEL)
        if has_api_key():
            st.caption("Groq key found in .env")
        else:
            st.caption("No key found. Put GROQ_API_KEY in the .env file and restart the app.")
    return {"files": files, "model_label": model_label, "model_id": model_id, "k": k, "gate": threshold if gate else None}
