import argparse
import sys
from pathlib import Path

from gen import kbase
from gen.llm import make_llm
from gen.prompts import BASELINE, ORDER
from gen.report import build_report
from gen.runner import load_benchmark, retrieve_all, run_many
from gen.system import Cache
from rag.config import LLM_MODEL
from rag.embedder import DEFAULT_THRESHOLDS

ROOT = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(description="Run the response benchmark for several prompt versions.")
    parser.add_argument("--prompts", nargs="*", default=ORDER + [BASELINE], help="for example v0 v3 v5 extractive")
    parser.add_argument("--embedding", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--limit", type=int, default=0, help="only the first N questions")
    parser.add_argument("--kind", default="", help="only one question type, for example trap")
    parser.add_argument("--gate", action="store_true", help="refuse before the model when retrieval is weak")
    parser.add_argument("--gap", type=float, default=2.5, help="seconds between model calls")
    parser.add_argument("--out", default=str(ROOT / "results" / "report.md"))
    args = parser.parse_args()

    items = load_benchmark()
    if args.kind:
        items = [i for i in items if i["kind"] == args.kind]
    if args.limit:
        items = items[: args.limit]

    retriever = kbase.make_retriever(kbase.read_files(ROOT / "guidelines"), args.embedding)
    retrieved = retrieve_all(retriever, items)
    llm = make_llm(gap=args.gap) if any(p != BASELINE for p in args.prompts) else None
    cache = Cache(ROOT / "results" / "llm_cache.json")
    gate = DEFAULT_THRESHOLDS.get(args.embedding, 0.35) if args.gate else None

    def progress(pid, number, total):
        print(f"\r{pid}: {number}/{total}", end="", flush=True)
        if number == total:
            print()

    runs = run_many(args.prompts, items, retrieved, retriever.embedder, llm, cache, gate, progress)
    report = build_report(runs, getattr(llm, "model", LLM_MODEL), gate)
    print(report)
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print("Saved", out)


if __name__ == "__main__":
    main()
