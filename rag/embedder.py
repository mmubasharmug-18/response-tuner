import hashlib
import re

import numpy as np

MODELS = {
    "all-MiniLM-L6-v2 (general)": "sentence-transformers/all-MiniLM-L6-v2",
    "PubMedBERT (biomedical)": "NeuML/pubmedbert-base-embeddings",
    "Offline hash (no download)": "hash",
}

DEFAULT_THRESHOLDS = {
    "sentence-transformers/all-MiniLM-L6-v2": 0.35,
    "NeuML/pubmedbert-base-embeddings": 0.55,
    "hash": 0.22,
}

STOP = set(
    "a an the of to in on at for and or is are was were be been being it its this that these those with as by from "
    "do does did can could should would will may might what which who whom how when where why i my me we you your "
    "if then than so not no there their they them he she his her also about into over under after before more most "
    "some any each per up down out".split()
)

TOKEN = re.compile(r"[a-z0-9]+(?:[./-][a-z0-9]+)*")
SUFFIXES = ("ations", "ation", "ings", "ing", "edly", "ed", "ies", "es", "s", "ly")


def stem(word):
    if len(word) <= 4 or any(ch.isdigit() for ch in word):
        return word
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def words(text):
    return [stem(w) for w in TOKEN.findall(text.lower()) if w not in STOP]


class HashEmbedder:
    name = "hash"

    def __init__(self, dim=1024):
        self.dim = dim

    def slot(self, token):
        digest = hashlib.md5(token.encode("utf-8")).digest()
        value = int.from_bytes(digest[:8], "little")
        return value % self.dim, 1.0 if (value >> 40) & 1 else -1.0

    def encode(self, texts):
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            tokens = words(text)
            counts = {}
            for token in tokens:
                counts[token] = counts.get(token, 0) + 1
            for a, b in zip(tokens, tokens[1:]):
                counts[a + "_" + b] = counts.get(a + "_" + b, 0) + 0.5
            for token, count in counts.items():
                index, sign = self.slot(token)
                out[row, index] += sign * (1 + np.log(count)) if count >= 1 else sign * count
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return out / norms


class SentenceEmbedder:
    def __init__(self, name):
        from sentence_transformers import SentenceTransformer

        self.name = name
        self.model = SentenceTransformer(name)

    def encode(self, texts):
        vectors = self.model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False, batch_size=32)
        return np.asarray(vectors, dtype=np.float32)


def load_embedder(model_id):
    if model_id == "hash":
        return HashEmbedder()
    return SentenceEmbedder(model_id)
