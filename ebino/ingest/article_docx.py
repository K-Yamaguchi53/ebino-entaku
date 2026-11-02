"""Read an interview article (docx): one numbered table, content in column 3.

Only an allowlist of rows passes. An unknown or mistyped row is dropped, so a
new row can never carry a name through by accident.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from .masks import SeatMasks
from .scrub import ArticleScrubber, interviewer_terms, name_parts
from .seats import Seat
from .utterance import (
    IngestError,
    Utterance,
    VOICE_ARTICLE,
    assert_clean,
    dedupe_sentences,
    make_id,
    split_voice,
    unique_by_id,
)

ROW_NAME = "1"
ROW_INTERVIEWER = "10"
ROW_BODY = "8"
USED_ROWS = {
    "3": "キャッチコピー",
    "4-2": "プロフィール",
    "5": "仕事の内容",
    "7": "本文タイトル",
    "8": "本文",
    "9": "ランキング",
}
_DASHES = re.compile(r"[‐‑‒–—―−ーｰ]")
_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
_CONTENT_COLUMN = 2


@dataclass
class ArticleRows:
    rows: dict[str, list[str]]
    dropped_rows: int = 0


@dataclass
class ArticleStats:
    unsplit_name: bool = False
    single_char_name: bool = False
    dropped_rows: int = 0
    notes: list[str] = field(default_factory=list)


def row_number(raw: str) -> str:
    """Normalize '９' and '４－１' so both layouts resolve to the same key."""
    text = unicodedata.normalize("NFKC", raw)
    return _DASHES.sub("-", re.sub(r"\s+", "", text))


def cell_paragraphs(cell) -> list[str]:
    """Cell text, including text boxes, without Word's fallback duplicate."""
    paragraphs: list[str] = []
    seen: set[str] = set()
    for element in cell._tc.iter(qn("w:p")):
        if any(parent.tag == _FALLBACK for parent in element.iterancestors()):
            continue
        text = Paragraph(element, cell).text.strip()
        if text and text not in seen:
            seen.add(text)
            paragraphs.append(text)
    return paragraphs


def pick_table(tables: list[Table], table_no: int | None) -> Table:
    if not tables:
        raise IngestError("no_table")
    if len(tables) == 1:
        return tables[0]
    if table_no is None or not 1 <= table_no <= len(tables):
        raise IngestError("table_choice_required")
    return tables[table_no - 1]


def read_rows(table: Table) -> ArticleRows:
    rows: dict[str, list[str]] = {}
    dropped = 0
    keep = {ROW_NAME, ROW_INTERVIEWER, *USED_ROWS}
    for row in table.rows:
        cells = row.cells
        key = row_number(cells[0].text) if cells else ""
        if key not in keep or len(cells) <= _CONTENT_COLUMN:
            dropped += 1
            continue
        rows.setdefault(key, []).extend(cell_paragraphs(cells[_CONTENT_COLUMN]))
    return ArticleRows(rows, dropped)


def ingest_article_rows(
    parsed: ArticleRows, seat: Seat, masks: SeatMasks = SeatMasks()
) -> tuple[list[Utterance], ArticleStats]:
    if masks.pages:
        # A docx has no fixed pages, so the request cannot be honored safely.
        raise IngestError("page_mask_on_article")
    raw_name = " ".join(parsed.rows.get(ROW_NAME, []))
    person = name_parts(raw_name)
    if not person.terms:
        # Without the name nothing can be masked, so the article must not pass.
        raise IngestError("name_row_missing")
    if not parsed.rows.get(ROW_BODY):
        raise IngestError("body_row_missing")

    scrub = ArticleScrubber(
        person_terms=person.terms,
        interviewer_terms=tuple(
            interviewer_terms("\n".join(parsed.rows.get(ROW_INTERVIEWER, [])))
        ),
        seat_pairs=tuple(masks.pairs(seat.company)),
    )
    utterances: list[Utterance] = []
    for key, section in USED_ROWS.items():
        for raw in parsed.rows.get(key, []):
            paragraph = dedupe_sentences(scrub(raw)).strip()
            if not paragraph:
                continue
            pieces = (
                split_voice(paragraph) if key == ROW_BODY else [(VOICE_ARTICLE, paragraph)]
            )
            for voice, text in pieces:
                utterances.append(
                    Utterance(
                        id=make_id(seat.kind, seat.source_file, text),
                        seat_id=seat.seat_id,
                        kind=seat.kind,
                        year=seat.year,
                        section=section,
                        voice=voice,
                        text=text,
                        paragraph=paragraph,
                    )
                )
    utterances = unique_by_id(utterances)
    assert_clean(utterances, scrub.forbidden())
    stats = ArticleStats(
        unsplit_name=person.unsplit,
        single_char_name=person.single_char,
        dropped_rows=parsed.dropped_rows,
    )
    return utterances, stats


def ingest_article(
    path: Path, seat: Seat, masks: SeatMasks = SeatMasks()
) -> tuple[list[Utterance], ArticleStats]:
    table = pick_table(Document(str(path)).tables, seat.table_no)
    return ingest_article_rows(read_rows(table), seat, masks)
