import copy
import re

from ..common import BlockList, ReaderError, clean_text, make_metadata, split_keywords
from ..schema import ReaderResult

DROP = ["script", "style", "noscript", "template", "svg", "iframe"]
CHROME = ["nav", "footer", "aside", "form"]
HEADINGS = ["h1", "h2", "h3", "h4", "h5", "h6"]
NESTED = ["ul", "ol", "p", "table", "div", "blockquote"] + HEADINGS
BLOCK_TAGS = HEADINGS + ["p", "li", "table", "pre", "blockquote", "dt", "dd", "figcaption", "div"]
BREAK = " "


def normalise(element):
    for br in element.find_all("br"):
        br.replace_with(BREAK)
    text = re.sub(r"\s+", " ", element.get_text())
    lines = [line.strip() for line in text.split(BREAK)]
    return "\n".join(line for line in lines if line)


def own_text(element, nested):
    clone = copy.copy(element)
    for inner in clone.find_all(nested):
        inner.decompose()
    return normalise(clone)


def direct_text(element):
    from bs4 import NavigableString
    parts = [str(c).strip() for c in element.children if isinstance(c, NavigableString) and str(c).strip()]
    return clean_text(" ".join(parts))


def table_rows(table):
    rows = []
    header = False
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        values = [normalise(c).replace("\n", " ") for c in cells]
        if any(values):
            rows.append(values)
            if not rows[1:] and all(c.name == "th" for c in cells):
                header = True
    return rows, header


def meta_map(soup):
    found = {}
    for tag in soup.find_all("meta"):
        name = (tag.get("name") or tag.get("property") or tag.get("http-equiv") or "").strip().lower()
        content = (tag.get("content") or "").strip()
        if name and content:
            found.setdefault(name, content)
    return found


def pick(meta, *names):
    for name in names:
        if meta.get(name):
            return meta[name]
    return None


def read(data, options):
    from bs4 import BeautifulSoup
    try:
        import lxml
        parser = "lxml"
    except ImportError:
        parser = "html.parser"
    soup = BeautifulSoup(data, parser)
    if soup.find() is None:
        raise ReaderError("No HTML tags were found in this file.")

    meta = meta_map(soup)
    html_tag = soup.find("html")
    canonical = soup.find("link", rel="canonical")
    title_tag = soup.title.get_text().strip() if soup.title else None

    for tag in soup.find_all(DROP):
        tag.decompose()
    if options.strip_html_chrome:
        for tag in soup.find_all(CHROME):
            tag.decompose()

    root = soup.find("main") or soup.find("article") or soup.body or soup
    blocks = BlockList()
    counter = {}
    for element in root.find_all(BLOCK_TAGS):
        name = element.name
        if name != "table" and element.find_parent("table") is not None:
            continue
        counter[name] = counter.get(name, 0) + 1
        ref = f"<{name}> #{counter[name]}"
        if name in HEADINGS:
            text = normalise(element)
            if text:
                blocks.add("heading", text, level=int(name[1]), method="html", ref=ref)
        elif name == "p" or name == "pre":
            text = normalise(element) if name == "p" else element.get_text().strip("\n")
            if text.strip():
                blocks.add("paragraph", text, method="html", ref=ref)
        elif name == "li":
            text = own_text(element, NESTED)
            if text:
                depth = len(element.find_parents(["ul", "ol"])) - 1
                blocks.add("list_item", text, level=max(depth, 0), method="html", ref=ref)
        elif name == "table":
            rows, header = table_rows(element)
            if rows:
                caption = element.find("caption")
                blocks.add(
                    "table",
                    "\n".join(" | ".join(r) for r in rows),
                    rows=rows,
                    method="html",
                    ref=ref,
                    extra={"header_row": header, "caption": normalise(caption) if caption else None},
                )
        elif name == "div":
            text = direct_text(element)
            if text:
                blocks.add("paragraph", text, method="html", ref=ref)
        else:
            text = own_text(element, NESTED)
            if text:
                blocks.add("paragraph", text, method="html", ref=ref)

    if not blocks.items:
        raise ReaderError("The page has no readable text after removing scripts and styles.")

    metadata = make_metadata(
        title=pick(meta, "og:title", "twitter:title") or title_tag,
        author=pick(meta, "author", "article:author", "dc.creator"),
        subject=pick(meta, "description", "og:description", "dc.description"),
        keywords=split_keywords(pick(meta, "keywords")),
        created=pick(meta, "date", "article:published_time", "dc.date", "created"),
        modified=pick(meta, "last-modified", "article:modified_time", "dcterms.modified"),
        language=html_tag.get("lang") if html_tag else None,
        creator_tool=pick(meta, "generator"),
        extra={
            "encoding": soup.original_encoding,
            "canonical_url": canonical.get("href") if canonical else None,
            "meta_tags": meta,
            "html_title": title_tag,
        },
    )
    return ReaderResult("BeautifulSoup", {"parser": parser}, metadata, [], blocks.items, [])
