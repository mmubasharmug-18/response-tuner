import io
import re
import zipfile
from xml.etree import ElementTree

from ..common import BlockList, ReaderError, clean_text, make_metadata, split_keywords
from ..schema import ReaderResult

APP_FIELDS = {"Pages", "Words", "Characters", "Application", "AppVersion", "Company", "TotalTime"}


def local(tag):
    return tag.rsplit("}", 1)[-1]


def app_properties(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            root = ElementTree.fromstring(archive.read("docProps/app.xml"))
    except (KeyError, zipfile.BadZipFile, ElementTree.ParseError):
        return {}
    return {local(e.tag): (e.text or "").strip() for e in root if local(e.tag) in APP_FIELDS and e.text}


def unique(values):
    seen = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def table_rows(table):
    rows = []
    for row in table.rows:
        cells = []
        seen = set()
        for cell in row.cells:
            marker = id(cell._tc)
            if marker in seen:
                continue
            seen.add(marker)
            cells.append(clean_text(cell.text))
        if any(cells):
            rows.append(cells)
    return rows


def paragraph_kind(paragraph):
    style = paragraph.style.name if paragraph.style is not None else ""
    found = re.match(r"^Heading (\d)", style)
    if found:
        return "heading", int(found.group(1)), style
    if style == "Title":
        return "heading", 1, style
    if style == "Subtitle":
        return "heading", 2, style
    properties = paragraph._p.pPr
    numbered = properties is not None and properties.numPr is not None
    if style.startswith("List") or numbered:
        level = 0
        if numbered and properties.numPr.ilvl is not None:
            level = int(properties.numPr.ilvl.val)
        return "list_item", level, style
    return "paragraph", None, style


def walk(parent, document, blocks, counters):
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in parent.iterchildren():
        tag = local(child.tag)
        if tag == "sdt":
            for inner in child.iterchildren():
                if local(inner.tag) == "sdtContent":
                    walk(inner, document, blocks, counters)
        elif tag == "p":
            counters["p"] += 1
            paragraph = Paragraph(child, document)
            text = clean_text(paragraph.text)
            if not text:
                continue
            kind, level, style = paragraph_kind(paragraph)
            blocks.add(kind, text, level=level, method="docx", ref=f"paragraph {counters['p']}", extra={"style": style})
        elif tag == "tbl":
            counters["t"] += 1
            rows = table_rows(Table(child, document))
            if rows:
                blocks.add(
                    "table",
                    "\n".join(" | ".join(r) for r in rows),
                    rows=rows,
                    method="docx",
                    ref=f"table {counters['t']}",
                )


def read(data, options):
    import docx
    from docx import Document

    try:
        document = Document(io.BytesIO(data))
    except Exception as error:
        raise ReaderError(f"Could not open the DOCX file: {error}")

    blocks = BlockList()
    walk(document.element.body, document, blocks, {"p": 0, "t": 0})
    if not blocks.items:
        raise ReaderError("The document has no readable text.")

    headers, footers = [], []
    for section in document.sections:
        headers += [clean_text(p.text) for p in section.header.paragraphs]
        footers += [clean_text(p.text) for p in section.footer.paragraphs]

    warnings = []
    images = len(document.inline_shapes)
    if images:
        warnings.append(f"The document has {images} embedded image(s). Text inside images was not read.")

    props = document.core_properties
    app = app_properties(data)
    pages = int(app["Pages"]) if app.get("Pages", "").isdigit() else None
    metadata = make_metadata(
        title=props.title,
        author=props.author,
        subject=props.subject,
        keywords=split_keywords(props.keywords),
        created=props.created,
        modified=props.modified,
        language=props.language,
        creator_tool=app.get("Application"),
        page_count=pages,
        extra={
            "last_modified_by": props.last_modified_by,
            "revision": props.revision,
            "category": props.category,
            "comments": props.comments,
            "company": app.get("Company"),
            "word_count_reported": app.get("Words"),
            "page_count_note": "reported by the program that last saved the file" if pages else None,
            "headers": unique(headers),
            "footers": unique(footers),
            "embedded_images": images,
        },
    )
    version = getattr(docx, "__version__", "")
    return ReaderResult("python-docx", {"python-docx": version}, metadata, [], blocks.items, warnings)
