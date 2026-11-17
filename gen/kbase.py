from pathlib import Path

from ingest import pipeline
from ingest.schema import Options
from kb import builder

from rag.embedder import load_embedder
from rag.index import VectorIndex


def read_files(folder):
    return [(p.name, p.read_bytes()) for p in sorted(Path(folder).glob("*.pdf"))]


def build_kb(files, max_chars=500, min_chars=120, ocr="auto", tesseract=""):
    docs = pipeline.ingest_many(list(files), Options(ocr=ocr, tesseract_cmd=tesseract))
    return builder.build(docs, builder.KBConfig(max_chars, min_chars, 0, True, True, True))


class Retriever:
    def __init__(self, chunks, embedder):
        self.chunks = chunks
        self.embedder = embedder
        self.index = VectorIndex(chunks, embedder)

    def search(self, question, k=4):
        vector = self.embedder.encode([question])[0]
        return vector, self.index.search(vector, k)


def make_retriever(files, model_id, max_chars=500, min_chars=120, ocr="auto", tesseract=""):
    kb = build_kb(files, max_chars, min_chars, ocr, tesseract)
    return Retriever(kb["chunks"], load_embedder(model_id))
