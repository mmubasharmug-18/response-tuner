import math
import re
from collections import Counter

STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "are", "was", "be", "by", "at", "as", "it", "this", "that", "should", "what", "how"}
WORD = re.compile(r"[a-z0-9]+")


def tokens(text):
    return [w for w in WORD.findall(text.lower()) if w not in STOP]


class Index:
    def __init__(self, chunks):
        self.chunks = chunks
        self.docs = [Counter(tokens(c["embed_text"])) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.average = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0
        self.freq = Counter()
        for d in self.docs:
            self.freq.update(d.keys())

    def search(self, query, limit=5, category=None, doc_id=None, chunk_type=None):
        words = tokens(query)
        results = []
        total = len(self.chunks)
        for i, chunk in enumerate(self.chunks):
            if category and chunk["category"] != category:
                continue
            if doc_id and chunk["doc_id"] != doc_id:
                continue
            if chunk_type and chunk["chunk_type"] != chunk_type:
                continue
            score = 0.0
            hit = []
            for w in words:
                f = self.docs[i].get(w, 0)
                if not f:
                    continue
                idf = math.log(1 + (total - self.freq[w] + 0.5) / (self.freq[w] + 0.5))
                score += idf * (f * 2.2) / (f + 1.2 * (0.25 + 0.75 * self.lengths[i] / self.average))
                hit.append(w)
            if score > 0:
                results.append({"score": round(score, 3), "matched": sorted(set(hit)), "chunk": chunk})
        results.sort(key=lambda r: -r["score"])
        return results[:limit]
