import json
from dataclasses import asdict, dataclass, field
from statistics import mean

SCHEMA_VERSION = "1.0"
SKIP_TYPES = ("header", "footer")


@dataclass
class Options:
    ocr: str = "auto"
    ocr_lang: str = "eng"
    dpi: int = 200
    min_text_chars: int = 25
    tesseract_cmd: str = ""
    password: str = ""
    strip_html_chrome: bool = True
    max_pages: int = 100


@dataclass
class Block:
    id: str
    type: str
    text: str
    order: int
    page: int | None = None
    level: int | None = None
    method: str = ""
    confidence: float | None = None
    bbox: list | None = None
    rows: list | None = None
    ref: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class PageInfo:
    number: int
    method: str
    chars: int = 0
    width: float | None = None
    height: float | None = None
    confidence: float | None = None
    blocks: int = 0


@dataclass
class SourceInfo:
    filename: str
    extension: str
    size_bytes: int
    sha256: str
    detected_type: str
    mime: str
    detection: str
    extension_matches: bool | None
    read_at: str
    extractor: str = ""
    libraries: dict = field(default_factory=dict)


@dataclass
class ReaderResult:
    extractor: str
    libraries: dict
    metadata: dict
    pages: list
    blocks: list
    warnings: list


@dataclass
class ExtractedDocument:
    source: SourceInfo
    status: str
    metadata: dict
    pages: list
    blocks: list
    warnings: list
    elapsed: float

    def text(self):
        return "\n\n".join(b.text for b in self.blocks if b.text and b.type not in SKIP_TYPES)

    def stats(self):
        text = self.text()
        counts = {}
        for block in self.blocks:
            counts[block.type] = counts.get(block.type, 0) + 1
        confidences = [b.confidence for b in self.blocks if b.confidence is not None]
        return {
            "pages": len(self.pages),
            "blocks": len(self.blocks),
            "blocks_by_type": counts,
            "characters": len(text),
            "words": len(text.split()),
            "ocr_pages": sum(1 for p in self.pages if p.method == "ocr"),
            "pages_without_text": sum(1 for p in self.pages if p.chars == 0),
            "mean_ocr_confidence": round(mean(confidences), 1) if confidences else None,
        }

    def to_dict(self):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": self.status,
            "source": asdict(self.source),
            "metadata": self.metadata,
            "pages": [asdict(p) for p in self.pages],
            "blocks": [asdict(b) for b in self.blocks],
            "text": self.text(),
            "stats": self.stats(),
            "warnings": self.warnings,
            "elapsed_seconds": round(self.elapsed, 3),
        }

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self):
        return blocks_to_markdown(self.blocks)


def table_markdown(rows):
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    padded = [list(r) + [""] * (width - len(r)) for r in rows]
    clean = [[str(c).replace("|", "/").replace("\n", " ") for c in r] for r in padded]
    lines = ["| " + " | ".join(clean[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in clean[1:]]
    return "\n".join(lines)


def blocks_to_markdown(blocks):
    parts = []
    for block in blocks:
        if block.type in SKIP_TYPES:
            continue
        if block.type == "heading":
            parts.append("#" * min(max(block.level or 2, 1), 6) + " " + block.text)
        elif block.type == "list_item":
            parts.append("  " * (block.level or 0) + "- " + block.text)
        elif block.type == "table":
            parts.append(table_markdown(block.rows or []))
        else:
            parts.append(block.text)
    return "\n\n".join(p for p in parts if p)
