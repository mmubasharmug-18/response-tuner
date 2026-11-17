import io
import re
from collections import Counter

from .. import ocr
from ..common import BULLET, BlockList, ReaderError, clean_text, make_metadata, split_keywords
from ..schema import PageInfo, ReaderResult


def import_fitz():
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            raise ReaderError("PyMuPDF is not installed. Run: pip install pymupdf")
    return fitz


def is_bold(span):
    return bool(span.get("flags", 0) & 16) or "bold" in str(span.get("font", "")).lower()


def join_lines(lines):
    text = ""
    for line in lines:
        if text.endswith("-") and line[:1].islower():
            text = text[:-1] + line
        else:
            text = (text + " " + line).strip()
    return text


def inside(box, tables):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return any(t[0] <= cx <= t[2] and t[1] <= cy <= t[3] for t in tables)


def page_tables(page):
    finder = getattr(page, "find_tables", None)
    if finder is None:
        return []
    try:
        found = finder()
        tables = []
        for table in getattr(found, "tables", []):
            rows = [[clean_text(c) for c in row] for row in table.extract()]
            rows = [r for r in rows if any(r)]
            if len(rows) >= 2 and max(len(r) for r in rows) >= 2:
                tables.append((list(table.bbox), rows))
        return tables
    except Exception:
        return []


def layout_blocks(layout, table_boxes):
    found = []
    for raw in layout.get("blocks", []):
        if raw.get("type", 0) != 0:
            continue
        lines = []
        weights = Counter()
        bold_chars = 0
        total = 0
        for line in raw.get("lines", []):
            text = clean_text("".join(s.get("text", "") for s in line.get("spans", [])))
            if not text:
                continue
            lines.append(text)
            for span in line.get("spans", []):
                size = len(span.get("text", "").strip())
                if size:
                    weights[round(span.get("size", 0) * 2) / 2] += size
                    total += size
                    bold_chars += size if is_bold(span) else 0
        if not lines or not total:
            continue
        box = [round(v, 1) for v in raw["bbox"]]
        if inside(box, table_boxes):
            continue
        found.append({
            "lines": lines,
            "text": join_lines(lines),
            "size": weights.most_common(1)[0][0],
            "bold": bold_chars / total >= 0.8,
            "bbox": box,
        })
    return found


def split_bullets(block):
    lines = block["lines"]
    if len(lines) < 2 or sum(1 for l in lines if BULLET.match(l)) < 2:
        return None
    items = []
    for line in lines:
        if BULLET.match(line) or not items:
            items.append(line)
        else:
            items[-1] = join_lines([items[-1], line])
    return [BULLET.sub("", i, count=1).strip() for i in items]


def edge_key(text):
    return re.sub(r"\d+", "#", clean_text(text).lower())


def mark_page_furniture(pages):
    if len(pages) < 2:
        return
    counts = Counter()
    for page in pages:
        keys = set()
        for block in page["blocks"]:
            height = page["height"]
            if block["bbox"][3] < height * 0.1 or block["bbox"][1] > height * 0.9:
                keys.add(edge_key(block["text"]))
        counts.update(keys)
    for page in pages:
        height = page["height"]
        for block in page["blocks"]:
            top = block["bbox"][3] < height * 0.1
            bottom = block["bbox"][1] > height * 0.9
            if (top or bottom) and counts[edge_key(block["text"])] >= 2:
                block["furniture"] = "header" if top else "footer"


def read(data, options):
    fitz = import_fitz()
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as error:
        raise ReaderError(f"Could not open the PDF: {error}")
    try:
        return extract(doc, options, fitz)
    finally:
        doc.close()


def extract(doc, options, fitz):
    if doc.needs_pass and not (options.password and doc.authenticate(options.password)):
        raise ReaderError("The PDF is password protected. Type the password in the sidebar.")

    total = doc.page_count
    limit = min(total, options.max_pages)
    warnings = []
    if total > limit:
        warnings.append(f"Only the first {limit} of {total} pages were read.")

    libraries = {"PyMuPDF": str(getattr(fitz, "__version__", "") or getattr(fitz, "VersionBind", ""))}
    ocr_state = {"info": None, "failed": False}
    pages = []
    sizes = Counter()
    images = 0

    for index in range(limit):
        page = doc[index]
        try:
            images += len(page.get_images())
        except Exception:
            pass
        plain = (page.get_text("text") or "").strip()
        if options.ocr == "always":
            use_ocr = True
        elif options.ocr == "auto":
            use_ocr = len(plain) < options.min_text_chars
        else:
            use_ocr = False
        entry = {"number": index + 1, "width": float(page.rect.width), "height": float(page.rect.height),
                 "method": "text-layer", "blocks": [], "tables": [], "page": page}
        if use_ocr:
            entry["method"] = "ocr"
        else:
            tables = page_tables(page)
            entry["tables"] = tables
            entry["blocks"] = layout_blocks(page.get_text("dict"), [t[0] for t in tables])
            for block in entry["blocks"]:
                sizes[block["size"]] += len(block["text"])
        pages.append(entry)

    mark_page_furniture([p for p in pages if p["method"] == "text-layer"])
    body = sizes.most_common(1)[0][0] if sizes else 0
    heading_sizes = sorted({b["size"] for p in pages for b in p["blocks"] if body and b["size"] >= body * 1.2}, reverse=True)

    out = BlockList()
    infos = []
    ocr_pages = []
    for entry in pages:
        number = entry["number"]
        before = len(out.items)
        confidence = None
        method = entry["method"]
        if method == "ocr":
            if not ocr_state["failed"] and ocr_state["info"] is None:
                try:
                    ocr_state["info"] = ocr.require(options.tesseract_cmd, options.ocr_lang)
                    libraries["Tesseract"] = ocr_state["info"]["version"]
                except ocr.OcrUnavailable as error:
                    ocr_state["failed"] = True
                    warnings.append(str(error))
            if ocr_state["failed"]:
                warnings.append(f"Page {number} has no text layer and OCR is not available.")
                method = "none"
            else:
                from PIL import Image
                pixmap = entry["page"].get_pixmap(dpi=options.dpi)
                image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                confidence = ocr.image_to_blocks(image, options.ocr_lang, number, out)
                ocr_pages.append(number)
        else:
            items = []
            for k, block in enumerate(entry["blocks"], 1):
                items.append((block["bbox"][1], "text", k, block))
            for k, (box, rows) in enumerate(entry["tables"], 1):
                items.append((box[1], "table", k, (box, rows)))
            order = []
            text_items = [i for i in items if i[1] == "text"]
            table_items = sorted([i for i in items if i[1] == "table"], key=lambda i: i[0])
            for text_item in text_items:
                while table_items and table_items[0][0] <= text_item[0]:
                    order.append(table_items.pop(0))
                order.append(text_item)
            order.extend(table_items)
            for _, kind, k, payload in order:
                if kind == "table":
                    box, rows = payload
                    out.add("table", "\n".join(" | ".join(r) for r in rows), page=number, rows=rows,
                            bbox=[round(v, 1) for v in box], method="text-layer", ref=f"page {number}, table {k}")
                    continue
                block = payload
                ref = f"page {number}, block {k}"
                if block.get("furniture"):
                    out.add(block["furniture"], block["text"], page=number, bbox=block["bbox"], method="text-layer", ref=ref)
                    continue
                bullets = split_bullets(block)
                if bullets:
                    for item in bullets:
                        out.add("list_item", item, page=number, bbox=block["bbox"], method="text-layer", ref=ref)
                    continue
                text = block["text"]
                big = body and block["size"] >= body * 1.2
                bold_title = block["bold"] and len(block["lines"]) == 1 and len(text) <= 100 and not text.endswith((".", ","))
                if len(block["lines"]) <= 2 and len(text) <= 200 and (big or bold_title):
                    level = heading_sizes.index(block["size"]) + 1 if big and block["size"] in heading_sizes else min(len(heading_sizes) + 1, 4)
                    out.add("heading", text, page=number, level=min(level, 4), bbox=block["bbox"],
                            method="text-layer", ref=ref, extra={"font_size": block["size"]})
                elif BULLET.match(text) and len(block["lines"]) == 1:
                    out.add("list_item", BULLET.sub("", text, count=1).strip(), page=number, bbox=block["bbox"],
                            method="text-layer", ref=ref)
                else:
                    out.add("paragraph", text, page=number, bbox=block["bbox"], method="text-layer", ref=ref)
        new = [b for b in out.items[before:] if b.type not in ("header", "footer")]
        infos.append(PageInfo(
            number=number,
            method=method,
            chars=sum(len(b.text) for b in new),
            width=round(entry["width"], 1),
            height=round(entry["height"], 1),
            confidence=confidence,
            blocks=len(out.items) - before,
        ))
        entry["page"] = None

    raw = doc.metadata or {}
    try:
        toc = len(doc.get_toc())
    except Exception:
        toc = 0
    metadata = make_metadata(
        title=raw.get("title"),
        author=raw.get("author"),
        subject=raw.get("subject"),
        keywords=split_keywords(raw.get("keywords")),
        created=raw.get("creationDate"),
        modified=raw.get("modDate"),
        creator_tool=raw.get("creator") or raw.get("producer"),
        page_count=total,
        extra={
            "producer": raw.get("producer"),
            "pdf_format": raw.get("format"),
            "encrypted": bool(doc.is_encrypted),
            "toc_entries": toc,
            "embedded_images": images,
            "ocr_pages": ocr_pages,
        },
    )
    extractor = "PyMuPDF + Tesseract OCR" if ocr_pages else "PyMuPDF"
    return ReaderResult(extractor, libraries, metadata, infos, out.items, warnings)
