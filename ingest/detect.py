import io
import os
import zipfile

EXTENSIONS = {
    ".pdf": "pdf", ".docx": "docx", ".doc": "doc", ".rtf": "rtf",
    ".txt": "txt", ".text": "txt", ".md": "txt", ".log": "txt",
    ".html": "html", ".htm": "html", ".xhtml": "html",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".tif": "image",
    ".tiff": "image", ".bmp": "image", ".gif": "image", ".webp": "image",
    ".xlsx": "xlsx", ".pptx": "pptx",
}

MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "rtf": "application/rtf",
    "html": "text/html",
    "txt": "text/plain",
    "image": "image/*",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "zip": "application/zip",
    "empty": "application/octet-stream",
    "unknown": "application/octet-stream",
}

IMAGE_MIME = {
    "png": "image/png", "jpeg": "image/jpeg", "tiff": "image/tiff",
    "bmp": "image/bmp", "gif": "image/gif", "webp": "image/webp",
}

HTML_MARKERS = ("<!doctype html", "<html", "<head", "<body", "<div", "<table", "<h1", "<h2", "<p>", "<p ")


def image_kind(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith((b"II*\x00", b"MM\x00*")):
        return "tiff"
    if data.startswith(b"BM"):
        return "bmp"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def looks_like_text(data):
    sample = data[:4096]
    if sample.startswith((b"\xff\xfe", b"\xfe\xff", b"\xef\xbb\xbf")):
        return True
    if not sample:
        return False
    odd = sum(1 for b in sample if b < 9 or 14 <= b < 32)
    return odd / len(sample) < 0.02


def sniff(data):
    if not data:
        return "empty"
    if b"%PDF-" in data[:1024]:
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        try:
            names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        except zipfile.BadZipFile:
            return "unknown"
        if "word/document.xml" in names:
            return "docx"
        if "xl/workbook.xml" in names:
            return "xlsx"
        if "ppt/presentation.xml" in names:
            return "pptx"
        return "zip"
    if data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "doc"
    if image_kind(data):
        return "image"
    if data.lstrip().startswith(b"{\\rtf"):
        return "rtf"
    if not looks_like_text(data):
        return None
    head = data[:4096]
    if head.startswith((b"\xff\xfe", b"\xfe\xff")):
        lowered = head.decode("utf-16", errors="ignore").lower()
    else:
        lowered = head.decode("utf-8", errors="ignore").lower()
    if any(marker in lowered for marker in HTML_MARKERS):
        return "html"
    return "txt"


def detect(data, filename):
    extension = os.path.splitext(filename or "")[1].lower()
    from_name = EXTENSIONS.get(extension)
    found = sniff(data)
    if found is None:
        found = from_name or "unknown"
        method = "extension" if from_name else "none"
    else:
        method = "content"
    matches = None if from_name is None or found == "empty" else from_name == found
    mime = IMAGE_MIME.get(image_kind(data), MIME["image"]) if found == "image" else MIME.get(found, MIME["unknown"])
    return {"type": found, "mime": mime, "method": method, "extension": extension, "extension_matches": matches}
