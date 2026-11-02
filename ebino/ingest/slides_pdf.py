"""Read presentation slides (PDF): collapse decorative repeats, then scrub.

Slides name people in free positions, so what to hide comes from masks.tsv.
The batch run refuses a slide seat that has no rows there.
"""

from pathlib import Path

import pdfplumber

from .masks import SeatMasks
from .pdf_chars import fold_radicals
from .pdf_quiet import quiet_pdf_warnings
from .scrub import forbidden_terms, normalize_for_match, scrub_slide_text
from .seats import Seat
from .utterance import Utterance, VOICE_OWN, assert_clean, make_id, unique_by_id


def collapse_lines(pages: list[list[str]]) -> list[list[str]]:
    """Decorative text prints one line many times; keep its first appearance."""
    seen: set[str] = set()
    collapsed: list[list[str]] = []
    for lines in pages:
        kept: list[str] = []
        for line in lines:
            key = normalize_for_match(line)
            if key and key not in seen:
                seen.add(key)
                kept.append(line.strip())
        collapsed.append(kept)
    return collapsed


def read_pages(path: Path) -> list[list[str]]:
    quiet_pdf_warnings()
    with pdfplumber.open(path) as pdf:
        # dedupe_chars handles glyphs overprinted to fake bold or outlines.
        return [
            fold_radicals(page.dedupe_chars().extract_text() or "").splitlines()
            for page in pdf.pages
        ]


def ingest_slide_pages(
    pages: list[list[str]], seat: Seat, masks: SeatMasks = SeatMasks()
) -> list[Utterance]:
    masks.check_pages(len(pages))
    pairs = masks.pairs(seat)
    utterances: list[Utterance] = []
    for number, lines in enumerate(collapse_lines(pages), start=1):
        if number in masks.pages:
            continue
        text = "\n".join(scrub_slide_text(line, pairs) for line in lines).strip()
        if text:
            utterances.append(
                Utterance(
                    id=make_id(seat.kind, seat.source_file, text),
                    seat_id=seat.seat_id,
                    kind=seat.kind,
                    section=f"p{number}",
                    voice=VOICE_OWN,
                    text=text,
                    paragraph=text,
                )
            )
    utterances = unique_by_id(utterances)
    assert_clean(utterances, forbidden_terms(term for term, _ in pairs))
    return utterances


def ingest_slides(path: Path, seat: Seat, masks: SeatMasks) -> list[Utterance]:
    return ingest_slide_pages(read_pages(path), seat, masks)
