import numpy as np


class VectorIndex:
    def __init__(self, chunks, embedder):
        self.chunks = chunks
        self.embedder = embedder
        texts = [c["embed_text"] for c in chunks]
        self.matrix = embedder.encode(texts) if texts else np.zeros((0, 1), dtype=np.float32)

    def __len__(self):
        return len(self.chunks)

    def search(self, query_vector, k=4):
        if not len(self.chunks):
            return []
        scores = self.matrix @ query_vector
        k = min(k, len(scores))
        top = np.argpartition(-scores, k - 1)[:k]
        top = top[np.argsort(-scores[top])]
        return [(self.chunks[i], float(scores[i])) for i in top]
