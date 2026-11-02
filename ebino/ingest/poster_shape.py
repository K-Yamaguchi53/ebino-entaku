"""Show how one poster is read, as shapes only. The teacher runs this by hand.

    python -m ebino.ingest.poster_shape P05

For each piece of text: its position, its length, and what it became (a
heading of which role, body, or dropped above the name line). Then each
section's role and length. No text, heading words or file names are printed,
so the output is safe to paste into chat.
"""

import os
import sys
from pathlib import Path

from .pdf_chars import PdfTextStats
from .poster_pdf import (
    _Y_TOLERANCE, heading_of, pdf_page_count, read_fragments, split_fragment, split_sections,
)
from .seats import load_seats
from .utterance import IngestError


def shape_lines(path: Path) -> list[str]:
    stats = PdfTextStats()
    fragments = read_fragments(path, stats)
    pieces = [
        (f"{number}" if len(parts) == 1 else f"{number}.{sub}", piece)
        for number, fragment in enumerate(fragments, start=1)
        for parts in [split_fragment(fragment)]
        for sub, piece in enumerate(parts, start=1)
    ]
    roles = [heading_of(piece.text) for _, piece in pieces]
    tops = [piece.top for (_, piece), heading in zip(pieces, roles) if heading and heading.role]
    cutoff = min(tops) - _Y_TOLERANCE if tops else None

    lines = [f"fragments: {len(fragments)}, pieces: {len(pieces)}"]
    lines.append(f"control chars removed: {stats.control_chars_removed}")
    lines.append(f"name line (top): {round(cutoff) if cutoff is not None else 'none'}")
    for (label, piece), heading in zip(pieces, roles):
        if cutoff is not None and piece.top < cutoff:
            became = "above the name line (dropped)"
        elif heading:
            became = f"heading {heading.role or '(other)'}"
        else:
            became = "body"
        spaces = sum(ch.isspace() for ch in piece.text)
        lines.append(
            f"piece {label}: top={round(piece.top)} x0={round(piece.x0)} "
            f"chars={len(piece.text)} spaces={spaces} -> {became}"
        )
    try:
        sections = split_sections(fragments)
    except IngestError as error:
        lines.append(f"sections: {error}")
        return lines
    for number, section in enumerate(sections, start=1):
        lines.append(f"section {number}: {section.role or '(other)'} chars={len(section.text)}")
    return lines


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    data_dir = os.environ.get("EBINO_DATA_DIR")
    if not data_dir or len(args) != 1:
        print("usage: set EBINO_DATA_DIR, then python -m ebino.ingest.poster_shape SEAT_ID",
              file=sys.stderr)
        return 2
    seats = {seat.seat_id: seat for seat in load_seats(Path(data_dir) / "seats.tsv")}
    seat = seats.get(args[0])
    if seat is None or seat.kind != "poster":
        print("no poster seat with that id", file=sys.stderr)
        return 2
    path = Path(data_dir) / seat.source_file
    if pdf_page_count(path) != 1:
        print("not a one-page poster", file=sys.stderr)
        return 2
    print("\n".join(shape_lines(path)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
