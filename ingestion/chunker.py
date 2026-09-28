"""Split sections into chunks that fit the embedding model.

Sections that fit stay whole. Longer ones are split into subsections, and
neighbouring subsections are joined back together until either the size limit
is reached or the meaning shifts (low embedding similarity between neighbours).
A chunk never crosses a section boundary.
"""

import re
from dataclasses import dataclass

import numpy as np

from app.core.config import settings
from app.embeddings.embedder import count_tokens, embed_passages
from ingestion.parsers.ontario_rta import Section

# Don't split on meaning alone below this size
MIN_TOKENS = 120
# Split at the weakest quarter of links between neighbouring subsections
SPLIT_PERCENTILE = 25

SUBSECTION = re.compile(r"\((\d+(?:\.\d+)?)\)\s")
CROSS_REFERENCE_WORDS = {
    "subsection", "subsections", "clause", "clauses", "section", "sections",
    "paragraph", "and", "or", "to",
}
# ".", ";" or ":" followed by a space, but not after abbreviations like "subs." or "s."
SENTENCE_END = re.compile(r"(?<!\bs)(?<!\bsubs)(?<!\bc)(?<!\bcl)(?<!\bpara)(?<!\bReg)[.;:]\s")


@dataclass
class Chunk:
    id: str
    section: str
    heading: str
    part: str
    page_start: int
    page_end: int
    text: str
    tokens: int


def build_chunks(sections: list[Section], source_id: str, source_title: str) -> list[Chunk]:
    chunks = []
    for section in sections:
        if not section.is_repealed:
            chunks.extend(chunk_section(section, source_id, source_title))
    return chunks


def chunk_section(section: Section, source_id: str, source_title: str) -> list[Chunk]:
    # The prefix keeps each chunk understandable on its own and tells the model what to cite
    prefix = f"{source_title}, s. {section.number}: {section.heading}\n"
    budget = settings.max_chunk_tokens - count_tokens(prefix)

    if count_tokens(section.text) <= budget:
        pieces = [section.text]
    else:
        units = [piece for sub in split_subsections(section.text) for piece in fit_to_budget(sub, budget)]
        pieces = group_by_meaning(units, budget)

    chunk_id = f"{source_id}-s{section.number}"
    return [
        Chunk(
            id=chunk_id if len(pieces) == 1 else f"{chunk_id}-{i}",
            section=section.number,
            heading=section.heading,
            part=section.part,
            page_start=section.page_start,
            page_end=section.page_end,
            text=prefix + piece,
            tokens=count_tokens(prefix + piece),
        )
        for i, piece in enumerate(pieces, start=1)
    ]


def split_subsections(text: str) -> list[str]:
    """'126 (1) ... Same (2) ... (3) ...' becomes one string per subsection."""
    cuts = []
    last_number = 0.0
    for match in SUBSECTION.finditer(text):
        words_before = text[:match.start()].split()
        if words_before and words_before[-1].lower().strip(",") in CROSS_REFERENCE_WORDS:
            continue
        number = float(match.group(1))
        if number <= last_number:
            continue
        last_number = number
        if match.start() < 15:  # the (1) right after the section number
            continue

        # A short subsection heading like "Same" or "Contents of notice" belongs with the subsection
        cut = match.start()
        sentence_ends = list(SENTENCE_END.finditer(text, 0, cut))
        if sentence_ends and len(text[sentence_ends[-1].end():cut].split()) <= 12:
            cut = sentence_ends[-1].end()
        cuts.append(cut)

    bounds = [0, *cuts, len(text)]
    return [text[a:b].strip() for a, b in zip(bounds, bounds[1:]) if text[a:b].strip()]


def fit_to_budget(text: str, budget: int) -> list[str]:
    """Split a single oversized subsection (s. 2's definitions, for example) at sentence ends."""
    if count_tokens(text) <= budget:
        return [text]

    pieces, current = [], ""
    for sentence in _sentences(text):
        candidate = f"{current} {sentence}".strip()
        if current and count_tokens(candidate) > budget:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        pieces.append(current)

    # Last resort for a single sentence that is still too long
    result = []
    for piece in pieces:
        if count_tokens(piece) <= budget:
            result.append(piece)
        else:
            words, step = piece.split(), max(budget * 2 // 3, 1)
            result.extend(" ".join(words[i:i + step]) for i in range(0, len(words), step))
    return result


def group_by_meaning(units: list[str], budget: int) -> list[str]:
    if len(units) == 1:
        return units

    similarities = neighbour_similarities(units)
    threshold = np.percentile(similarities, SPLIT_PERCENTILE)

    groups, current = [], units[0]
    for unit, similarity in zip(units[1:], similarities):
        joined = f"{current} {unit}"
        too_big = count_tokens(joined) > budget
        topic_shift = similarity <= threshold and count_tokens(current) >= MIN_TOKENS
        if too_big or topic_shift:
            groups.append(current)
            current = unit
        else:
            current = joined
    groups.append(current)
    return groups


def neighbour_similarities(units: list[str]) -> list[float]:
    vectors = embed_passages(units)  # normalized, so the dot product is the cosine similarity
    return [float(np.dot(a, b)) for a, b in zip(vectors, vectors[1:])]


def _sentences(text: str) -> list[str]:
    sentences, start = [], 0
    for match in SENTENCE_END.finditer(text):
        sentences.append(text[start:match.end()].strip())
        start = match.end()
    sentences.append(text[start:].strip())
    return [s for s in sentences if s]
