"""Parser for the Ontario Residential Tenancies Act, 2006, as exported from e-Laws to PDF.

pymupdf4llm turns the PDF into Markdown, where the layout of the Act shows up as:

    # **Application of Act**
    **3** (1)  This Act, except Part V.1, applies ...  2013, c. 3, s. 22 (1).

    ## **Section Amendments with date in force (d/m/y)**
    2013, c. 3, s. 22 - 01/06/2014

A section starts wherever a bold heading is followed by a section number.
"""

import re
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

import pymupdf4llm

SECTION_START = re.compile(
    r"\*\*(?P<heading>[^*\n]+?)\*\*\s+"
    r"(?:\*\*)?(?P<number>\d{1,3}(?:\.\d{1,2})?)(?:\*\*)?\s+"
    r"(?=\(\d+\)|[A-Z])"
)
PART_HEADING = re.compile(r"\*\*(PART [IVXLC]+(?:\.\d+)?\b[^*\n]*)\*\*")
AMENDMENT_HISTORY = re.compile(r"\*\*Section Amendments[^*]*\*\*.*?(?=\*\*|\Z)", re.S)
# Legislative history at the end of a subsection, e.g. ". 2006, c. 17, s. 116 (1)."
SOURCE_NOTE = re.compile(r"(?<=[.;)])\s+\d{4}, c\. \d+.*?[.;](?=\s+[-(A-Z*#_<]|\s*$)")
SEE_NOTE = re.compile(r"\(See: [^)]*\)")
HTML_TAG = re.compile(r"</?\w+>")
ITALICS = re.compile(r"(?<!\w)_([^_\n]+?)_(?!\w)")
MARKDOWN = re.compile(r"^\s*(?:#+|-)\s+|\*\*", re.M)


@dataclass
class Section:
    number: str
    heading: str
    part: str
    page_start: int
    page_end: int
    text: str

    @property
    def is_repealed(self) -> bool:
        return bool(re.match(r"\S+ Repealed", self.text))


def section_sort_key(number: str) -> tuple[int, int]:
    """48.10 sorts after 48.9."""
    main, _, sub = number.partition(".")
    return int(main), int(sub or 0)


def parse(pdf_path: Path) -> list[Section]:
    pages = pymupdf4llm.to_markdown(
        str(pdf_path),
        page_chunks=True,
        header=False,
        footer=False,
        use_ocr=False,
        show_progress=False,
    )

    markdown = ""
    page_offsets = []
    for page in pages:
        page_offsets.append(len(markdown))
        markdown += page["text"] + "\n"

    def page_at(offset: int) -> int:
        return bisect_right(page_offsets, offset)

    starts = _section_starts(markdown)
    parts = [(m.start(), m.group(1).strip()) for m in PART_HEADING.finditer(markdown)]

    sections = []
    for start, next_start in zip(starts, starts[1:] + [None]):
        end = next_start.start() if next_start else len(markdown)
        sections.append(
            Section(
                number=start["number"],
                heading=start["heading"].strip(),
                part=next((name for pos, name in reversed(parts) if pos < start.start()), ""),
                page_start=page_at(start.start()),
                page_end=page_at(end - 1),
                text=_clean(markdown[start.start("number"):end]),
            )
        )
    return sections


def _section_starts(markdown: str) -> list[re.Match]:
    starts: list[re.Match] = []
    for match in SECTION_START.finditer(markdown):
        # Part titles and the table of contents are in capitals
        if match["heading"].isupper():
            continue
        # Section numbers only go up; anything else is a cross-reference
        if starts and section_sort_key(match["number"]) <= section_sort_key(starts[-1]["number"]):
            continue
        starts.append(match)
    return starts


def _clean(text: str) -> str:
    text = AMENDMENT_HISTORY.sub("", text)
    text = PART_HEADING.sub("", text)
    text = HTML_TAG.sub("", text)
    text = SEE_NOTE.sub("", text)
    text = SOURCE_NOTE.sub("", text)
    text = MARKDOWN.sub("", text)
    text = ITALICS.sub(r"\1", text)
    return re.sub(r"\s+", " ", text).strip()
