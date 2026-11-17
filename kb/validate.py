REQUIRED = ["chunk_id", "doc_id", "source_file", "source_type", "source_sha256", "title", "section_id",
            "section_title", "category", "chunk_type", "text", "embed_text", "content_hash"]


def check(name, bad, detail_ok, detail_bad, level="fail"):
    return {"check": name, "status": "pass" if not bad else level, "detail": detail_ok if not bad else detail_bad}


def validate(kb):
    chunks = kb["chunks"]
    docs = [d for d in kb["documents"] if d["included"]]
    sections = kb["sections"]
    max_chars = kb["config"]["max_chars"]
    ids = [c["chunk_id"] for c in chunks]
    id_set = set(ids)
    doc_ids = {d["doc_id"] for d in docs}
    section_ids = {s["id"] for s in sections}
    empty = [c["chunk_id"] for c in chunks if not c["text"].strip()]
    missing = [c["chunk_id"] for c in chunks if any(c.get(k) in (None, "") for k in REQUIRED)]
    broken_links = [c["chunk_id"] for c in chunks
                    if c["doc_id"] not in doc_ids or c["section_id"] not in section_ids
                    or (c["prev_chunk_id"] and c["prev_chunk_id"] not in id_set)
                    or (c["next_chunk_id"] and c["next_chunk_id"] not in id_set)]
    oversize = [c["chunk_id"] for c in chunks if c["chunk_type"] != "table" and len(c["text"]) > max_chars * 1.2]
    low_cover = [d["filename"] for d in docs if d["coverage"] < 0.95]
    no_chunks = [d["filename"] for d in docs if d["chunks"] == 0]
    no_title = [d["filename"] for d in docs if not d["author"] and not d["created"]]
    low_ocr = [c["chunk_id"] for c in chunks if c["ocr_confidence"] is not None and c["ocr_confidence"] < 70]
    return [
        check("Chunks exist", not chunks, f"{len(chunks)} chunks from {len(docs)} documents", "No chunks were produced"),
        check("Chunk ids are unique", len(ids) != len(id_set), "All ids are unique", "Some chunk ids repeat"),
        check("No empty chunks", empty, "Every chunk has text", f"{len(empty)} empty chunks"),
        check("Source and section filled on every chunk", missing, "All required fields are filled", f"{len(missing)} chunks miss a field"),
        check("Links point to real records", broken_links, "Documents, sections and neighbours all resolve", f"{len(broken_links)} broken links"),
        check("Chunks stay within the size limit", oversize, f"All text chunks are under {int(max_chars * 1.2)} characters", f"{len(oversize)} chunks are too long"),
        check("All text is covered", low_cover, "At least 95% of the words of every document are in chunks", "Low coverage: " + ", ".join(low_cover)),
        check("Every included document has chunks", no_chunks, "Yes", "No chunks for: " + ", ".join(no_chunks)),
        check("Author or date found in source metadata", no_title, "Every document has an author or a date", "No author or date in: " + ", ".join(no_title), level="warn"),
        check("OCR confidence", low_ocr, "No low-confidence OCR chunks", f"{len(low_ocr)} chunks under 70% confidence, check them by eye", level="warn"),
    ]
