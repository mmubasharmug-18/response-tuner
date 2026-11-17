import re
from functools import lru_cache
from statistics import median

from .common import BULLET, clean_text


class OcrUnavailable(Exception):
    pass


def configure(cmd):
    import pytesseract
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd


@lru_cache(maxsize=8)
def status(cmd=""):
    try:
        import pytesseract
    except ImportError:
        return {"ok": False, "version": "", "languages": [], "error": "pytesseract is not installed"}
    configure(cmd)
    try:
        version = str(pytesseract.get_tesseract_version())
        languages = sorted(pytesseract.get_languages(config=""))
        return {"ok": True, "version": version, "languages": languages, "error": ""}
    except Exception as error:
        return {"ok": False, "version": "", "languages": [], "error": str(error).splitlines()[0] if str(error) else "Tesseract not found"}


def require(cmd, lang):
    info = status(cmd)
    if not info["ok"]:
        raise OcrUnavailable(
            "Tesseract OCR was not found. Install it and add it to PATH, or type its path in the sidebar."
        )
    wanted = [part for part in re.split(r"[+,]", lang) if part]
    missing = [part for part in wanted if part not in info["languages"]]
    if missing:
        raise OcrUnavailable(f"Tesseract language data missing for: {', '.join(missing)}")
    configure(cmd)
    return info


def prepare(image):
    from PIL import ImageOps
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")
    return ImageOps.autocontrast(image.convert("L"))


def line_width(line):
    text = " ".join(line["words"])
    return (line["box"][2] - line["box"][0]) / max(len(text), 1)


def union(box, other):
    if box is None:
        return list(other)
    return [min(box[0], other[0]), min(box[1], other[1]), max(box[2], other[2]), max(box[3], other[3])]


def image_to_blocks(image, lang, page, blocks):
    import pytesseract
    from pytesseract import Output

    data = pytesseract.image_to_data(prepare(image), lang=lang, output_type=Output.DICT)
    paragraphs = {}
    for i, raw in enumerate(data["text"]):
        word = (raw or "").strip()
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if not word or conf < 0:
            continue
        lines = paragraphs.setdefault((data["block_num"][i], data["par_num"][i]), {})
        line = lines.setdefault(data["line_num"][i], {"words": [], "confs": [], "heights": [], "box": None})
        left, top = data["left"][i], data["top"][i]
        line["words"].append(word)
        line["confs"].append(conf)
        line["heights"].append(data["height"][i])
        line["box"] = union(line["box"], [left, top, left + data["width"][i], top + data["height"][i]])

    if not paragraphs:
        return None
    all_lines = [line for lines in paragraphs.values() for line in lines.values()]
    body_width = median([line_width(line) for line in all_lines])
    all_confs = [c for line in all_lines for c in line["confs"]]
    ref = f"page {page}" if page else "image"

    def emit(kind, group, level=None):
        confs = [c for line in group for c in line["confs"]]
        box = None
        for line in group:
            box = union(box, line["box"])
        blocks.add(
            kind,
            "\n".join(clean_text(" ".join(line["words"])) for line in group),
            page=page,
            level=level,
            method="ocr",
            confidence=round(sum(confs) / len(confs), 1),
            bbox=box,
            ref=ref,
        )

    for lines in paragraphs.values():
        current = []
        for line in lines.values():
            text = clean_text(" ".join(line["words"]))
            size = line_width(line) / body_width
            if size >= 1.25 and len(text) <= 120:
                if current:
                    emit("paragraph", current)
                    current = []
                emit("heading", [line], 1 if size >= 1.7 else 2)
            elif BULLET.match(text):
                if current:
                    emit("paragraph", current)
                    current = []
                emit("list_item", [line])
            else:
                current.append(line)
        if current:
            emit("paragraph", current)
    return round(sum(all_confs) / len(all_confs), 1)
