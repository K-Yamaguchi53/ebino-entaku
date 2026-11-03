"""Read an inquiry poster copied by hand to text (.txt).

Some posters are only an image. The teacher's side copies them to UTF-8 text,
section by section: a line starting with 「## 」 is a heading, and the lines up
to the next heading are its body. Lines before the first heading (a title, the
students' names) are dropped. The mark alone decides a heading; its name and
role are found as for a PDF heading (poster_pdf.copied_heading).

From the sections on, a copied poster takes the same path as a PDF one
(poster_pdf.poster_utterances): words hidden, the purpose sample required, the
leak check run.
"""

from pathlib import Path

from .masks import SeatMasks
from .poster_pdf import Section, copied_heading, poster_utterances, whole_page_masked
from .seats import Seat
from .utterance import IngestError, Utterance

SUFFIX = ".txt"
# 「## 」 with an ASCII space; a full-width space is taken too, as typed with a
# Japanese input method.
HEADING_MARKS = ("## ", "##　")


def heading_text(line: str) -> str | None:
    """The words after the mark, or None when the line is not a heading."""
    for mark in HEADING_MARKS:
        if line.startswith(mark):
            return line[len(mark) :]
    return None


def text_sections(text: str) -> list[Section]:
    """Body lines are joined as they are, each stripped, with nothing added:
    the same as a PDF poster's lines. A heading with no body is no section."""
    found: list[tuple[str, str | None, list[str]]] = []
    for line in text.splitlines():
        words = heading_text(line)
        if words is not None:
            heading = copied_heading(words)
            if heading is None:
                raise IngestError("poster_heading_empty")
            found.append((heading.label, heading.role, []))
        elif found:
            found[-1][2].append(line.strip())
    if not found:
        raise IngestError("poster_heading_missing")
    return [
        Section(label, role, "".join(body))
        for label, role, body in found
        if "".join(body)
    ]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")  # A BOM, if any, is taken off.


def ingest_text_poster(path: Path, seat: Seat, masks: SeatMasks = SeatMasks()) -> list[Utterance]:
    if whole_page_masked(masks):
        return []
    return poster_utterances(text_sections(read_text(path)), seat, masks)
