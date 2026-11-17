import json
import sys
from pathlib import Path

import pytest

from gen.checks import check_response, is_refusal
from gen.guard import apply_guard, check_refs, ref_is_valid, section_label
from gen.prompts import EMERGENCY_NOTICE, PROMPTS, REFUSAL
from gen.runner import compare, load_benchmark, summarise
from gen.system import Cache, format_context, respond
from rag.embedder import HashEmbedder

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))


def chunk(cid, doc, page, section, text):
    return {
        "chunk_id": cid, "source_file": doc, "title": "Example Guideline", "section_title": section,
        "section_path": ["Example Guideline", section], "category": "General", "chunk_type": "text",
        "page_start": page, "page_end": page, "text": text, "embed_text": text,
    }


CHUNKS = [
    chunk("a", "diabetes.pdf", 2, "Medicines > First choice", "Offer metformin as the first medicine. Do not start metformin if eGFR is below 30."),
    chunk("b", "diabetes.pdf", 4, "Sick day rules", "During an illness with vomiting, pause metformin. Restart after 24 to 48 hours."),
]
HITS = [(CHUNKS[0], 0.8), (CHUNKS[1], 0.5)]
EMB = HashEmbedder()
VEC = EMB.encode(["metformin"])[0]
ITEM = {"id": "X", "question": "When should metformin not be started?", "expect": "answer", "facts": [["30"]], "forbidden": [],
        "cite": [{"doc": "diabetes.pdf", "pages": [2]}], "max_words": 45, "emergency": False}
TRAP = {"id": "T", "question": "What starting dose of metformin should be used?", "expect": "refuse", "facts": [], "forbidden": ["500 mg"],
        "cite": [], "max_words": 35, "emergency": False}


def fake_llm(answer):
    def call(system, user):
        return answer
    call.model = "fake"
    return call


def run(pid, answer, item=ITEM, question=None):
    result = respond(pid, question or item["question"], HITS, VEC, EMB, fake_llm(answer), Cache(None))
    return result, check_response(item, result, HITS)


def test_benchmark_file_is_well_formed():
    items = load_benchmark()
    assert len({i["id"] for i in items}) == len(items) >= 30
    for item in items:
        assert item["expect"] in ("answer", "refuse")
        if item["expect"] == "answer":
            assert item["facts"] and item["cite"]
        else:
            assert not item["facts"]


def test_every_expected_fact_is_in_the_guideline_page():
    import make_guidelines as mg

    texts = {}
    for name, spec in mg.GUIDES.items():
        for n, page in enumerate(spec["pages"], 1):
            parts = []
            for kind, val in page:
                if kind in ("h2", "h3", "p"):
                    parts.append(val)
                elif kind == "bullets":
                    parts += val
                elif kind == "table":
                    parts += [" ".join(r) for r in val]
            texts[(name, n)] = " ".join(parts).lower()
    for item in load_benchmark():
        if item["expect"] != "answer":
            continue
        source = " ".join(texts[(c["doc"], p)] for c in item["cite"] for p in c["pages"])
        for group in item["facts"]:
            assert any(alt.lower() in source for alt in group), (item["id"], group)


def test_context_header_carries_section_and_page():
    text = format_context(HITS)
    assert "[1] Document: Example Guideline | Section: Medicines > First choice | Page: 2" in text


def test_reference_validation():
    assert ref_is_valid("Medicines > First choice, p. 2", CHUNKS[0])
    assert not ref_is_valid("Medicines > First choice, p. 3", CHUNKS[0])
    assert not ref_is_valid("Sick day rules, p. 2", CHUNKS[0])
    assert section_label(CHUNKS[0]) == "Medicines > First choice"
    refs = check_refs("Do not start it. [1: Medicines > First choice, p. 9] Pause it. [2: Sick day rules, p. 4]", HITS)
    assert [r["valid"] for r in refs] == [False, True]


def test_good_answer_passes_every_check():
    result, checks = run("v4", "Do not start metformin if eGFR is below 30. [1: Medicines > First choice, p. 2]")
    assert checks["pass"] and checks["refs"] is True


def test_missing_citation_and_wrong_source_fail():
    _, checks = run("v3", "Do not start metformin if eGFR is below 30.")
    assert checks["cited"] is False and not checks["pass"]
    _, checks = run("v3", "Pause metformin. Restart after 24 to 48 hours. [2]", ITEM)
    assert checks["cite_correct"] is False


def test_made_up_number_and_trap_are_caught():
    _, checks = run("v3", "Do not start metformin if eGFR is below 45. [1]")
    assert checks["no_hallucination"] is False
    _, checks = run("v3", "Start with 500 mg once a day. [1]", TRAP)
    assert checks["no_hallucination"] is False and checks["refusal_ok"] is False


def test_refusal_detection_and_mapping():
    assert is_refusal(REFUSAL) and is_refusal("NOT_FOUND")
    result, checks = run("v1", "NOT_FOUND", TRAP)
    assert result["text"] == REFUSAL and checks["refusal_ok"]


def test_long_answer_is_not_concise():
    _, checks = run("v3", "word " * 60 + "[1]")
    assert checks["concise"] is False


def test_guard_drops_wrong_reference_and_falls_back_without_citation():
    text, used, action = apply_guard("q", "Do not start metformin if eGFR is below 30. [1: Wrong place, p. 9]", HITS, VEC, EMB,
                                     lambda v, h, e: ("Offer metformin as the first medicine. [1]", [CHUNKS[0]]))
    assert action.startswith("fallback") and used == [CHUNKS[0]]


def test_guard_blocks_number_not_in_passages():
    text, used, action = apply_guard("q", "Do not start it if eGFR is below 45. [1: Medicines > First choice, p. 2]", HITS, VEC, EMB,
                                     lambda v, h, e: ("fallback text [1]", [CHUNKS[0]]))
    assert "number not in the passages" in action and text == "fallback text [1]"


def test_guard_moves_citation_to_the_passage_named():
    text, used, action = apply_guard("q", "Pause metformin when ill. [1: Sick day rules, p. 4]", HITS, VEC, EMB, lambda v, h, e: ("", []))
    assert used == [CHUNKS[1]] and text == "Pause metformin when ill. [1]" and "moved" in action


def test_final_prompt_adds_emergency_notice_and_renumbers():
    result, checks = run("v5", "Pause metformin when ill. [2: Sick day rules, p. 4]", ITEM, "My father is unconscious, what now?")
    assert result["text"].startswith(EMERGENCY_NOTICE) and result["text"].endswith("[1]")
    assert result["sources"][0].startswith("[1]")


def test_final_prompt_refusal_is_clean():
    result, _ = run("v5", REFUSAL + " Please ask a doctor.", TRAP)
    assert result["text"] == REFUSAL and result["action"] == "refused"


def test_cache_avoids_second_call(tmp_path):
    cache = Cache(tmp_path / "c.json")
    calls = []

    def llm(system, user):
        calls.append(1)
        return "Do not start metformin if eGFR is below 30. [1]"
    llm.model = "fake"
    for _ in range(2):
        respond("v3", ITEM["question"], HITS, VEC, EMB, llm, cache)
    assert len(calls) == 1
    assert Cache(tmp_path / "c.json").data


def test_model_error_is_recorded_not_raised():
    def broken(system, user):
        raise RuntimeError("rate limit")
    broken.model = "fake"
    result = respond("v3", ITEM["question"], HITS, VEC, EMB, broken, Cache(None))
    assert result["error"] and result["text"] == ""


def test_prompt_versions_build_on_each_other():
    assert PROMPTS["v3"]["system"].startswith(PROMPTS["v2"]["system"])
    assert "[number: section, page]" in PROMPTS["v4"]["system"]
    assert PROMPTS["v5"]["guard"] and not PROMPTS["v4"]["guard"]
