import csv
import io
import json
import zipfile

from .validate import validate

CSV_COLUMNS = [
    "chunk_id", "doc_id", "source_file", "source_type", "title", "author", "created", "modified", "language",
    "section_id", "section_title", "section_path", "category", "chunk_type", "chunk_index", "page_start", "page_end",
    "extraction_method", "ocr_confidence", "char_count", "word_count", "token_estimate", "prev_chunk_id",
    "next_chunk_id", "content_hash", "text", "embed_text",
]


def to_jsonl(chunks):
    return "\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + ("\n" if chunks else "")


def to_csv(chunks):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for chunk in chunks:
        row = dict(chunk)
        row["section_path"] = " > ".join(chunk["section_path"])
        writer.writerow(row)
    return buffer.getvalue()


def to_json(value):
    return json.dumps(value, indent=2, ensure_ascii=False)


def summary(kb):
    chunks = kb["chunks"]
    docs = kb["documents"]
    by_category = {}
    by_type = {}
    for c in chunks:
        by_category[c["category"]] = by_category.get(c["category"], 0) + 1
        by_type[c["source_type"]] = by_type.get(c["source_type"], 0) + 1
    return {
        "documents_received": len(docs),
        "documents_included": sum(1 for d in docs if d["included"]),
        "documents_skipped": [{"file": d["filename"], "reason": d["skipped_reason"]} for d in docs if not d["included"]],
        "sections": len(kb["sections"]),
        "chunks": len(chunks),
        "duplicate_chunks_dropped": len(kb["dropped_duplicates"]),
        "chunks_by_category": by_category,
        "chunks_by_source_type": by_type,
        "average_chunk_chars": round(sum(c["char_count"] for c in chunks) / len(chunks)) if chunks else 0,
        "settings": kb["config"],
        "checks": validate(kb),
    }


def bundle(kb):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("chunks.jsonl", to_jsonl(kb["chunks"]))
        archive.writestr("chunks.csv", to_csv(kb["chunks"]))
        archive.writestr("sections.json", to_json(kb["sections"]))
        archive.writestr("documents.json", to_json(kb["documents"]))
        archive.writestr("report.json", to_json(summary(kb)))
    return buffer.getvalue()
