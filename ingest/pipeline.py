import hashlib
import time
from datetime import datetime, timezone

from . import detect, ocr
from .common import ReaderError
from .readers import docx_reader, html_reader, image_reader, pdf_reader, text_reader
from .schema import ExtractedDocument, Options, SourceInfo

READERS = {
    "pdf": pdf_reader,
    "docx": docx_reader,
    "html": html_reader,
    "txt": text_reader,
    "image": image_reader,
}

UNSUPPORTED = {
    "doc": "Old Word .doc files are not supported. Open the file in Word and save it as .docx.",
    "rtf": "RTF files are not supported. Save the file as .docx or .txt.",
    "xlsx": "Excel files are not supported by this pipeline.",
    "pptx": "PowerPoint files are not supported by this pipeline.",
    "zip": "This is a ZIP archive. Unzip it and upload the files inside.",
    "empty": "The file is empty.",
    "unknown": "The file type could not be recognised.",
}


def version_of(name):
    from importlib import metadata
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return ""


def tool_status(tesseract_cmd=""):
    try:
        import pymupdf as fitz
        fitz_version = str(getattr(fitz, "__version__", "")) or "installed"
    except ImportError:
        try:
            import fitz
            fitz_version = str(getattr(fitz, "__version__", "")) or "installed"
        except ImportError:
            fitz_version = ""
    tesseract = ocr.status(tesseract_cmd)
    return {
        "PyMuPDF": fitz_version,
        "python-docx": version_of("python-docx"),
        "BeautifulSoup": version_of("beautifulsoup4"),
        "Pillow": version_of("pillow"),
        "pytesseract": version_of("pytesseract"),
        "Tesseract OCR": tesseract["version"] if tesseract["ok"] else "",
        "Tesseract languages": ", ".join(tesseract["languages"]) if tesseract["ok"] else "",
    }


def set_status(pages, blocks, text):
    if not text.strip():
        return "partial"
    if any(p.chars == 0 for p in pages):
        return "partial"
    return "ok"


def ingest(data, filename, options=None):
    options = options or Options()
    started = time.perf_counter()
    found = detect.detect(data, filename)
    source = SourceInfo(
        filename=filename,
        extension=found["extension"],
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        detected_type=found["type"],
        mime=found["mime"],
        detection=found["method"],
        extension_matches=found["extension_matches"],
        read_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    warnings = []
    if found["extension_matches"] is False:
        warnings.append(f"The file name ends in {found['extension']} but the content looks like {found['type']}. The content was used.")

    reader = READERS.get(found["type"])
    if reader is None:
        warnings.append(UNSUPPORTED.get(found["type"], UNSUPPORTED["unknown"]))
        return ExtractedDocument(source, "unsupported", {}, [], [], warnings, time.perf_counter() - started)

    try:
        result = reader.read(data, options)
    except ReaderError as error:
        warnings.append(str(error))
        return ExtractedDocument(source, "failed", {}, [], [], warnings, time.perf_counter() - started)
    except Exception as error:
        warnings.append(f"Unexpected error while reading: {type(error).__name__}: {error}")
        return ExtractedDocument(source, "failed", {}, [], [], warnings, time.perf_counter() - started)

    source.extractor = result.extractor
    source.libraries = result.libraries
    doc = ExtractedDocument(
        source=source,
        status="ok",
        metadata=result.metadata,
        pages=result.pages,
        blocks=result.blocks,
        warnings=warnings + result.warnings,
        elapsed=time.perf_counter() - started,
    )
    doc.status = set_status(doc.pages, doc.blocks, doc.text())
    return doc


def ingest_many(files, options=None):
    return [ingest(data, name, options) for name, data in files]
