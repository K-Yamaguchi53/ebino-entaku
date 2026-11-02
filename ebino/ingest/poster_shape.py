"""Show how one poster is read, as shapes only. The teacher runs this by hand.

    python -m ebino.ingest.poster_shape P05

For each piece of text: its position, its length, and what it became (a
heading of which role and its column, body under which heading, or dropped).
Then each heading's section and its length, empty ones included. It goes
through the same read_layout as the ingestion, so what it shows is what is
kept. No text, heading words or file names are printed, so the output is
safe to paste into chat.
"""

import math
import os
import sys
from pathlib import Path

from .pdf_chars import PdfTextStats
from .poster_pdf import Layout, heading_of, pdf_page_count, read_fragments, read_layout, \
    section_texts, split_fragment
from .seats import load_seats
from .utterance import IngestError


def _labels(source: tuple[int, ...]) -> list[str]:
    """「6」 for a whole fragment, 「6.1」「6.2」 for the pieces of a split one."""
    labels = []
    for index, fragment in enumerate(source):
        count = source.count(fragment)
        sub = source[: index + 1].count(fragment)
        labels.append(f"{fragment + 1}" if count == 1 else f"{fragment + 1}.{sub}")
    return labels


def _edge(x: float) -> str:
    return "end" if math.isinf(x) else str(round(x))


def _layout_lines(layout: Layout) -> list[str]:
    labels = _labels(layout.source)
    heading_label = {k: labels[piece] for k, piece in enumerate(layout.headings)}
    owners: dict[int, list[int | None]] = {}
    for place in layout.placed:
        owners.setdefault(place.piece, []).append(place.owner)

    def under(owner: int | None) -> str:
        return "no heading (dropped)" if owner is None else f"piece {heading_label[owner]}"

    lines = [f"name line (top): {round(layout.cutoff)}"]
    for index, piece in enumerate(layout.pieces):
        heading = layout.found[index]
        if index in layout.headings:
            k = layout.headings.index(index)
            left, right = layout.columns[k]
            became = f"heading {heading.role or '(other)'} [x {_edge(left)}..{_edge(right)}]"
        elif piece.top < layout.cutoff:
            became = "above the name line (dropped)"
        elif len(owners[index]) == 1:
            became = f"body of {under(owners[index][0])}"
        else:
            became = f"body cut in {len(owners[index])}: " + ", ".join(map(under, owners[index]))
        spaces = sum(ch.isspace() for ch in piece.text)
        lines.append(
            f"piece {labels[index]}: top={round(piece.top)} x0={round(piece.x0)} "
            f"chars={len(piece.text)} spaces={spaces} -> {became}"
        )
    number = 0
    for k, text in enumerate(section_texts(layout)):
        role = layout.found[layout.headings[k]].role or "(other)"
        if text:
            number += 1
            lines.append(f"section {number}: {role} chars={len(text)} (piece {heading_label[k]})")
        else:
            lines.append(f"no section: {role} (piece {heading_label[k]}) got no body")
    return lines


def shape_lines(path: Path) -> list[str]:
    stats = PdfTextStats()
    fragments = read_fragments(path, stats)
    lines = [f"fragments: {len(fragments)}"]
    lines.append(f"control chars removed: {stats.control_chars_removed}")
    try:
        layout = read_layout(fragments)
    except IngestError as error:
        lines.append(f"sections: {error}")
        for number, fragment in enumerate(fragments, start=1):
            for piece in split_fragment(fragment):
                heading = heading_of(piece.text)
                became = f"heading {heading.role or '(other)'}" if heading else "body"
                lines.append(
                    f"piece {number}: top={round(piece.top)} x0={round(piece.x0)} "
                    f"chars={len(piece.text)} -> {became}"
                )
        return lines
    lines[0] += f", pieces: {len(layout.pieces)}"
    return lines + _layout_lines(layout)


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
