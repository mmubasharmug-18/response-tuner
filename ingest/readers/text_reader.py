import re

from ..common import BULLET, BlockList, ReaderError, make_metadata
from ..schema import ReaderResult

MD_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
NUM_HEADING = re.compile(r"^\d+(\.\d+)*[.)]?\s+[A-Z][^.!?;:,]{0,60}$")


def decode(data):
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8"), "utf-8-sig"
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16"), "utf-16"
    for name in ("utf-8", "cp1252"):
        try:
            return data.decode(name), name
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1"), "latin-1"


def heading_level(line, first):
    text = line.strip()
    found = MD_HEADING.match(text)
    if found:
        return len(found.group(1)), found.group(2)
    letters = [c for c in text if c.isalpha()]
    if len(letters) >= 3 and text.upper() == text and len(text) <= 60 and (
        text.endswith(":") or not any(c.isdigit() for c in text)
    ):
        return (1 if first else 2), text.rstrip(":").strip()
    if NUM_HEADING.match(text) and not BULLET.match(text):
        return 2, text
    return None, text


def read(data, options):
    text, encoding = decode(data)
    if not text.strip():
        raise ReaderError("The text file has no readable text.")
    newline = "CRLF" if "\r\n" in text else "LF"
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    blocks = BlockList()
    paragraph = []
    start_line = 0

    def flush():
        if paragraph:
            blocks.add(
                "paragraph",
                "\n".join(paragraph),
                method="plain-text",
                ref=f"lines {start_line}-{start_line + len(paragraph) - 1}",
            )
            paragraph.clear()

    for number, raw in enumerate(lines, 1):
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        level, heading_text = heading_level(line, first=not blocks.items and not paragraph)
        if level:
            flush()
            blocks.add("heading", heading_text, level=level, method="plain-text", ref=f"line {number}")
        elif BULLET.match(line):
            flush()
            blocks.add("list_item", BULLET.sub("", line, count=1).strip(), method="plain-text", ref=f"line {number}")
        elif line.startswith((" ", "\t")) and blocks.items and blocks.items[-1].type == "list_item" and not paragraph:
            blocks.items[-1].text += " " + line.strip()
        else:
            if not paragraph:
                start_line = number
            paragraph.append(line.strip())
    flush()

    metadata = make_metadata(
        extra={
            "encoding": encoding,
            "line_endings": newline,
            "lines": len(lines),
            "characters": len(text),
        }
    )
    return ReaderResult("plain text", {"python": "built-in"}, metadata, [], blocks.items, [])
