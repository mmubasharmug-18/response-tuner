import re
from dataclasses import dataclass, field

from ingest.schema import SKIP_TYPES

CATEGORY_RULES = [
    ("Allergies", ("allerg", "adverse reaction")),
    ("Medications", ("medic", "drug", "prescri", "dose", "dosing")),
    ("Examination", ("exam", "vital", "finding", "observation")),
    ("Results", ("result", "laborator", "investigation", "test", "scan", "imaging", "chemistry", "haemat", "hematol", "urinalysis")),
    ("History", ("history", "presenting", "complaint", "symptom")),
    ("Assessment", ("assessment", "diagnos", "impression", "summary", "conclusion")),
    ("Follow-up", ("follow", "review", "next step")),
    ("Plan", ("plan", "advice", "recommend", "management", "treatment", "lifestyle", "instruction")),
    ("Purpose", ("purpose", "reason", "referral", "introduction", "scope", "background", "aim")),
    ("Patient information", ("patient information", "faq", "question", "seek", "warning sign", "when to", "get help", "emergency")),
]

CATEGORIES = [name for name, _ in CATEGORY_RULES] + ["General"]


@dataclass
class Section:
    id: str
    doc_id: str
    order: int
    title: str
    level: int
    path: list
    category: str
    page_start: int | None
    page_end: int | None
    blocks: list = field(default_factory=list)

    def to_row(self):
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "order": self.order,
            "title": self.title,
            "level": self.level,
            "path": self.path,
            "category": self.category,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "block_ids": [b.id for b in self.blocks],
            "words": sum(len(b.text.split()) for b in self.blocks),
        }


def classify(titles):
    for title in reversed(titles):
        low = title.lower()
        for category, words in CATEGORY_RULES:
            for word in words:
                if re.search(r"\b" + re.escape(word), low):
                    return category
    return "General"


def clean_title(text):
    text = re.sub(r"^\s*(?:\d+(?:\.\d+)*[.)]?|[A-Z][.)])\s+", "", text).strip()
    text = text.strip(" :")
    if text.isupper() and len(text) > 3:
        text = text.capitalize()
    return text or "Untitled"


def find_root(blocks, doc_title):
    headings = [b for b in blocks if b.type == "heading"]
    if not blocks or blocks[0].type != "heading" or not headings:
        return None
    first = blocks[0]
    top = min((b.level or 2) for b in headings)
    same_level = [b for b in headings if (b.level or 2) == top]
    if (first.level or 2) != top:
        return None
    if len(same_level) == 1 or first.text.strip().lower() == (doc_title or "").strip().lower():
        return first
    return None


def build_sections(blocks, doc_id, doc_title):
    blocks = [b for b in blocks if b.type not in SKIP_TYPES and b.text and b.text.strip()]
    root = find_root(blocks, doc_title)
    sections = []
    stack = []
    state = {"current": None}

    def open_section(title, level, path):
        number = len(sections) + 1
        section = Section(
            id=f"{doc_id}-s{number:02d}", doc_id=doc_id, order=number, title=title, level=level,
            path=path, category=classify(path + [title]), page_start=None, page_end=None,
        )
        sections.append(section)
        state["current"] = section
        return section

    for block in blocks:
        if block.type == "heading":
            if block is root:
                state["current"] = None
                stack = []
                continue
            level = block.level or 2
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, clean_title(block.text)))
            state["current"] = None
            continue
        if state["current"] is None:
            if stack:
                titles = [t for _, t in stack]
                open_section(titles[-1], stack[-1][0], titles)
            elif block is not None and root is not None:
                open_section("Overview", 0, [])
            else:
                open_section("Introduction", 0, [])
        current = state["current"]
        current.blocks.append(block)
        if block.page is not None:
            current.page_start = block.page if current.page_start is None else min(current.page_start, block.page)
            current.page_end = block.page if current.page_end is None else max(current.page_end, block.page)
    if len(sections) == 1 and sections[0].title == "Introduction":
        sections[0].title = "Full document"
    return sections
