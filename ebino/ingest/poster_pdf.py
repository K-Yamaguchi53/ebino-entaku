"""Read an inquiry poster (one-page PDF).

Student names sit at the top, so everything above the first section heading is
dropped by position. No name list is needed, and a misread heading fails closed.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from .masks import SeatMasks
from .scrub import forbidden_terms, mask_pairs, normalize_for_match
from .seats import Seat
from .utterance import (
    IngestError, Utterance, VOICE_OWN, assert_clean, make_id, unique_by_id,
)

SECTIONS = ("背景と課題", "目的", "手法", "結果", "結論と展望")
PURPOSE = "目的"
_DECORATION = re.compile(r"^[\d.．、,)）(（【\[■●◆▶▼・]+|[】\]:：]+$")
_X_TOLERANCE = 5
_Y_TOLERANCE = 2
_LINE_TOLERANCE = 3


@dataclass(frozen=True)
class Fragment:
    """A run of text with its position on the page."""

    text: str
    x0: float
    top: float


def heading_of(text: str) -> str | None:
    cleaned = _DECORATION.sub("", normalize_for_match(text))
    return cleaned if cleaned in SECTIONS else None


def split_sections(fragments: list[Fragment]) -> dict[str, str]:
    headings: dict[str, Fragment] = {}
    for fragment in fragments:
        name = heading_of(fragment.text)
        if name:
            headings.setdefault(name, fragment)
    if PURPOSE not in headings:
        raise IngestError("purpose_heading_missing")

    collected: dict[str, list[Fragment]] = {name: [] for name in headings}
    heading_set = set(map(id, headings.values()))
    for fragment in fragments:
        if id(fragment) in heading_set or heading_of(fragment.text):
            continue
        # The owner is the nearest heading above, in this fragment's column.
        above = [
            (head.top, name)
            for name, head in headings.items()
            if head.top <= fragment.top + _Y_TOLERANCE
            and head.x0 <= fragment.x0 + _X_TOLERANCE
        ]
        if above:
            collected[max(above)[1]].append(fragment)

    sections: dict[str, str] = {}
    for name, parts in collected.items():
        parts.sort(key=lambda f: (round(f.top / _LINE_TOLERANCE), f.x0))
        text = "".join(part.text.strip() for part in parts)
        if text:
            sections[name] = text
    return sections


def read_fragments(path: Path) -> list[Fragment]:
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != 1:
            raise IngestError("poster_not_one_page")
        words = pdf.pages[0].extract_words(keep_blank_chars=True)
    return [Fragment(w["text"], w["x0"], w["top"]) for w in words]


def ingest_poster_fragments(
    fragments: list[Fragment], seat: Seat, masks: SeatMasks = SeatMasks()
) -> list[Utterance]:
    masks.check_pages(1)
    if 1 in masks.pages:
        return []
    pairs = masks.pairs(seat.company)
    utterances: list[Utterance] = []
    for section, raw in split_sections(fragments).items():
        text = mask_pairs(raw, pairs).strip()
        if text:
            utterances.append(
                Utterance(
                    id=make_id(seat.kind, seat.source_file, text),
                    seat_id=seat.seat_id,
                    kind=seat.kind,
                    year=seat.year,
                    section=section,
                    voice=VOICE_OWN,
                    text=text,
                    paragraph=text,
                )
            )
    utterances = unique_by_id(utterances)
    assert_clean(utterances, forbidden_terms(term for term, _ in pairs))
    return utterances


def ingest_poster(
    path: Path, seat: Seat, masks: SeatMasks = SeatMasks()
) -> list[Utterance]:
    return ingest_poster_fragments(read_fragments(path), seat, masks)
