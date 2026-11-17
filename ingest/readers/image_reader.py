import io

from .. import ocr
from ..common import BlockList, ReaderError, make_metadata
from ..schema import PageInfo, ReaderResult

EXIF_KEYS = {"DateTime": "date_time", "Make": "camera_make", "Model": "camera_model",
             "Software": "software", "ImageDescription": "description", "Orientation": "orientation"}


def exif_date(value):
    text = str(value or "").strip()
    if len(text) >= 19 and text[4] == ":" and text[7] == ":":
        return text[:4] + "-" + text[5:7] + "-" + text[8:10] + "T" + text[11:19]
    return None


def exif_details(image):
    from PIL import ExifTags
    try:
        exif = image.getexif()
    except Exception:
        return {}, None
    found = {}
    for tag, value in exif.items():
        name = ExifTags.TAGS.get(tag, str(tag))
        if name in EXIF_KEYS and value not in (None, ""):
            found[EXIF_KEYS[name]] = str(value).strip()
    taken = None
    try:
        taken = exif.get_ifd(0x8769).get(36867)
    except Exception:
        taken = None
    return found, exif_date(taken or exif.get(306))


def read(data, options):
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as error:
        raise ReaderError(f"Could not open the image: {error}")

    frames = getattr(image, "n_frames", 1)
    exif, taken = exif_details(image)
    dpi = image.info.get("dpi")
    metadata = make_metadata(
        created=taken or exif.get("date_time") and exif_date(exif.get("date_time")),
        creator_tool=exif.get("software"),
        subject=exif.get("description"),
        page_count=frames,
        extra={
            "image_format": image.format,
            "color_mode": image.mode,
            "width_px": image.width,
            "height_px": image.height,
            "dpi": [round(float(v)) for v in dpi] if dpi else None,
            "frames": frames,
            "camera_make": exif.get("camera_make"),
            "camera_model": exif.get("camera_model"),
        },
    )
    libraries = {"Pillow": getattr(Image, "__version__", "")}

    if options.ocr == "off":
        return ReaderResult("Pillow", libraries, metadata, [], [], ["OCR is switched off, so nothing was read from this image."])
    try:
        info = ocr.require(options.tesseract_cmd, options.ocr_lang)
    except ocr.OcrUnavailable as error:
        return ReaderResult("Pillow", libraries, metadata, [], [], [str(error)])

    libraries["Tesseract"] = info["version"]
    blocks = BlockList()
    pages = []
    warnings = []
    limit = min(frames, options.max_pages)
    if frames > limit:
        warnings.append(f"Only the first {limit} of {frames} frames were read.")
    for index in range(limit):
        image.seek(index)
        frame = ImageOps.exif_transpose(image.copy())
        before = len(blocks.items)
        confidence = ocr.image_to_blocks(frame, options.ocr_lang, index + 1, blocks)
        new = blocks.items[before:]
        pages.append(PageInfo(
            number=index + 1,
            method="ocr",
            chars=sum(len(b.text) for b in new),
            width=frame.width,
            height=frame.height,
            confidence=confidence,
            blocks=len(new),
        ))
    if not blocks.items:
        warnings.append("OCR found no text in this image.")
    return ReaderResult("Tesseract OCR", libraries, metadata, pages, blocks.items, warnings)
