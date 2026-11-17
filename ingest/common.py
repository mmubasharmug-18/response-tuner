import re
from datetime import datetime

from .schema import Block

BULLET = re.compile(r"^\s*([•●▪‣\-*]|\d{1,2}[.)])\s+")
PDF_DATE = re.compile(r"^D?:?(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Zz+\-])?(\d{2})?'?(\d{2})?'?$")


class ReaderError(Exception):
    pass


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def clean_lines(value):
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in (value or "").splitlines()]
    return "\n".join(line for line in lines if line)


def iso_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    found = PDF_DATE.match(text)
    if found and text.startswith("D:"):
        year, month, day, hour, minute, second, sign, tz_hour, tz_min = found.groups()
        stamp = f"{year}-{month or '01'}-{day or '01'}T{hour or '00'}:{minute or '00'}:{second or '00'}"
        if sign in ("+", "-") and tz_hour:
            stamp += f"{sign}{tz_hour}:{tz_min or '00'}"
        elif sign in ("Z", "z"):
            stamp += "+00:00"
        return stamp
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return text


def split_keywords(value):
    if not value:
        return []
    return [k.strip() for k in re.split(r"[;,]", str(value)) if k.strip()]


def make_metadata(title=None, author=None, subject=None, keywords=None, created=None,
                  modified=None, language=None, creator_tool=None, page_count=None, extra=None):
    return {
        "title": title or None,
        "author": author or None,
        "subject": subject or None,
        "keywords": keywords or [],
        "created": iso_date(created),
        "modified": iso_date(modified),
        "language": language or None,
        "creator_tool": creator_tool or None,
        "page_count": page_count,
        "extra": {k: v for k, v in (extra or {}).items() if v not in (None, "", [], {})},
    }


class BlockList:
    def __init__(self):
        self.items = []

    def add(self, type, text, page=None, **kwargs):
        block = Block(id=f"b{len(self.items) + 1:04d}", type=type, text=text, order=len(self.items) + 1, page=page, **kwargs)
        self.items.append(block)
        return block
