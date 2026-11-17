import hashlib
import re
from dataclasses import dataclass

from .chunking import ChunkConfig, chunk_blocks, count_tokens
from .sections import build_sections


@dataclass
class KBConfig:
    max_chars: int = 500
    min_chars: int = 120
    overlap_sentences: int = 0
    add_context: bool = True
    skip_duplicate_files: bool = True
    drop_duplicate_chunks: bool = True


def normalise(text):
    return re.sub(r"\W+", " ", text.lower()).strip()


def doc_title(doc):
    title = (doc.metadata.get("title") or "").strip()
    if title:
        return title
    for block in doc.blocks:
        if block.type == "heading" and block.text.strip():
            return block.text.strip().title() if block.text.isupper() else block.text.strip()
    return doc.source.filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()


def context_line(title, section):
    parts = [title] + [p for p in section.path if p != title]
    if section.title not in parts:
        parts.append(section.title)
    return " > ".join(parts)


def page_range(pages):
    found = [p for p in pages if p is not None]
    return (min(found), max(found)) if found else (None, None)


def document_row(doc, did, title, included, reason, sections, chunks, coverage):
    meta = doc.metadata
    stats = doc.stats()
    return {
        "doc_id": did,
        "filename": doc.source.filename,
        "file_type": doc.source.detected_type,
        "extractor": doc.source.extractor,
        "status": doc.status,
        "included": included,
        "skipped_reason": reason,
        "title": title,
        "author": meta.get("author"),
        "subject": meta.get("subject"),
        "keywords": meta.get("keywords") or [],
        "created": meta.get("created"),
        "modified": meta.get("modified"),
        "language": meta.get("language"),
        "page_count": meta.get("page_count"),
        "size_bytes": doc.source.size_bytes,
        "sha256": doc.source.sha256,
        "read_at": doc.source.read_at,
        "sections": sections,
        "chunks": chunks,
        "words": stats["words"],
        "ocr_pages": stats["ocr_pages"],
        "mean_ocr_confidence": stats["mean_ocr_confidence"],
        "coverage": coverage,
        "warnings": doc.warnings,
    }


def build(docs, config=None):
    config = config or KBConfig()
    chunk_config = ChunkConfig(config.max_chars, config.min_chars, config.overlap_sentences)
    documents, all_sections, chunks = [], [], []
    seen_files = {}
    for doc in docs:
        did = doc.source.sha256[:12]
        title = doc_title(doc)
        if doc.status in ("failed", "unsupported") or not doc.blocks:
            reason = doc.warnings[0] if doc.warnings else "Nothing could be read from this file."
            documents.append(document_row(doc, did, title, False, reason, 0, 0, 0.0))
            continue
        if config.skip_duplicate_files and doc.source.sha256 in seen_files:
            reason = f"Same content as {seen_files[doc.source.sha256]}"
            documents.append(document_row(doc, did, title, False, reason, 0, 0, 0.0))
            continue
        seen_files[doc.source.sha256] = doc.source.filename
        sections = build_sections(doc.blocks, did, title)
        meta = doc.metadata
        pieces = 0
        covered_words = 0
        for section in sections:
            for number, draft in enumerate(chunk_blocks(section.blocks, chunk_config), 1):
                start, end = page_range(draft.pages)
                header = context_line(title, section)
                body = draft.text
                confidences = [b.confidence for b in section.blocks if b.id in draft.ids and b.confidence is not None]
                methods = sorted({b.method for b in section.blocks if b.id in draft.ids and b.method})
                record = {
                    "chunk_id": f"{section.id}-c{number:02d}",
                    "doc_id": did,
                    "source_file": doc.source.filename,
                    "source_type": doc.source.detected_type,
                    "source_sha256": doc.source.sha256,
                    "title": title,
                    "author": meta.get("author"),
                    "subject": meta.get("subject"),
                    "keywords": meta.get("keywords") or [],
                    "created": meta.get("created"),
                    "modified": meta.get("modified"),
                    "language": meta.get("language"),
                    "section_id": section.id,
                    "section_order": section.order,
                    "section_title": section.title,
                    "section_path": section.path,
                    "category": section.category,
                    "chunk_type": draft.kind,
                    "page_start": start,
                    "page_end": end,
                    "extraction_method": ", ".join(methods) or doc.source.extractor,
                    "ocr_confidence": round(sum(confidences) / len(confidences), 1) if confidences else None,
                    "block_ids": draft.ids,
                    "text": body,
                    "embed_text": f"{header}\n{body}" if config.add_context else body,
                    "char_count": len(body),
                    "word_count": len(body.split()),
                    "token_estimate": count_tokens(body),
                    "content_hash": hashlib.sha256(normalise(body).encode("utf-8")).hexdigest()[:16],
                    "prev_chunk_id": None,
                    "next_chunk_id": None,
                }
                chunks.append(record)
                pieces += 1
                covered_words += record["word_count"]
        source_words = sum(len(b.text.split()) for s in sections for b in s.blocks)
        coverage = round(min(covered_words / source_words, 1.0), 3) if source_words else 1.0
        all_sections += [s.to_row() for s in sections]
        documents.append(document_row(doc, did, title, True, "", len(sections), pieces, coverage))

    dropped = []
    if config.drop_duplicate_chunks:
        first = {}
        kept = []
        for record in chunks:
            same = first.get(record["content_hash"])
            if same and record["char_count"] >= 40:
                dropped.append({"chunk_id": record["chunk_id"], "source_file": record["source_file"], "duplicate_of": same})
                continue
            first[record["content_hash"]] = record["chunk_id"]
            kept.append(record)
        chunks = kept

    by_doc = {}
    for index, record in enumerate(chunks):
        by_doc.setdefault(record["doc_id"], []).append(record)
    for records in by_doc.values():
        for index, record in enumerate(records):
            record["chunk_index"] = index + 1
            record["prev_chunk_id"] = records[index - 1]["chunk_id"] if index else None
            record["next_chunk_id"] = records[index + 1]["chunk_id"] if index + 1 < len(records) else None
    for row in documents:
        if row["included"]:
            row["chunks"] = len(by_doc.get(row["doc_id"], []))
    kept_sections = {r["section_id"] for r in chunks}
    for section in all_sections:
        section["chunks"] = sum(1 for r in chunks if r["section_id"] == section["id"])
    all_sections = [s for s in all_sections if s["id"] in kept_sections or s["chunks"] == 0]

    return {
        "config": {
            "max_chars": config.max_chars, "min_chars": config.min_chars,
            "overlap_sentences": config.overlap_sentences, "add_context": config.add_context,
        },
        "documents": documents,
        "sections": all_sections,
        "chunks": chunks,
        "dropped_duplicates": dropped,
    }
