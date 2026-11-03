"""Read an interview article (docx): one numbered table, content in column 3.

Only an allowlist of rows passes. An unknown or mistyped row is dropped, so a
new row can never carry a name through by accident.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from .masks import SeatMasks
from .scrub import ArticleScrubber, interviewer_terms, people_parts
from .seats import Seat
from .utterance import (
    IngestError,
    Utterance,
    TEACHER_ARTICLE_NOTE,
    VOICE_ARTICLE,
    VOICE_COMPANY,
    VOICE_OWN,
    VOICE_SENIOR,
    VOICE_SPOKEN,
    assert_clean,
    dedupe_sentences,
    make_id,
    split_voice,
    unique_by_id,
)

ROW_NAME = "1"  # One paragraph per person; company pages hold the head's name.
ROW_INTERVIEWER = "10"
ROW_BODY = "8"
# Last year's company pages have no body, only these (SPEC 14-43).
ROWS_STANDING_IN_FOR_BODY = ("13", "14")
USED_ROWS = {
    "3": "キャッチコピー",
    "4-2": "プロフィール",
    "5": "仕事の内容",
    "7": "本文タイトル",
    "8": "本文",
    "9": "ランキング",
    # Last year's booklet only (SPEC 14-36).
    "11": "高校生に一言",
    "12": "求める人材",
    "13": "会社PR",
    "14": "先輩社員からのメッセージ",
}
# Its docx files are the teacher's own article; its PDFs are a visitor's slides.
KIND_TEACHER_ARTICLE = "outsider_teacher"
ROW_VOICES = {
    "11": VOICE_SPOKEN,
    "12": VOICE_COMPANY,
    "13": VOICE_COMPANY,
    "14": VOICE_SENIOR,
}
_DASHES = re.compile(r"[‐‑‒–—―−ーｰ]")
_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
_CONTENT_COLUMN = 2
# A paragraph ending in one of these closes a sentence, so it is never a wrap.
_SENTENCE_ENDS = "。．.！？!?」』）)…"
# Shorter paragraphs are headings or list items; they never set the line width.
_MIN_LINE_WIDTH = 10
_WIDTH_SLACK = 1
# A line shorter than this never joins the next: short lines of one length
# can be notes taken while listening, not a printed paragraph cut in two.
_MIN_JOIN_LENGTH = 15
# A line starting with a list or heading mark never joins, on either side.
# A number is a mark with 「.」「、」「）」 or 「位」 after it, and a number of one
# or two digits is one with anything after it but a digit or a unit
# (「１　山の上」「２川の駅」「20〜24歳」 are; 「3月に」「7割が」 are not). A decimal
# (「1.5倍」) never is. Q only when no letter follows (「QRコード」).
_NUMBER_UNITS = "年月日%％万千百円人回歳時分割"
_LIST_MARK = re.compile(
    r"(?:[①-⑳【・●○■□◆◇※★☆▼▶]"
    r"|[QＱ](?![A-Za-zＡ-Ｚａ-ｚ])"
    r"|[AＡ][:：]"
    r"|[(（][0-9０-９]+[)）]"
    r"|[0-9０-９]+(?:[.．](?![0-9０-９])|[、）)]|位)"
    rf"|[0-9０-９]{{1,2}}(?![0-9０-９{_NUMBER_UNITS}]|[.．][0-9０-９]))"
)


@dataclass
class ArticleRows:
    rows: dict[str, list[str]]
    dropped_rows: int = 0


@dataclass
class ArticleStats:
    unsplit_name: bool = False
    single_char_name: bool = False
    dropped_rows: int = 0
    wrapped_lines_joined: int = 0
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


def _ends_a_sentence(paragraph: str) -> bool:
    return paragraph.endswith(tuple(_SENTENCE_ENDS))


def line_width(paragraphs: list[str]) -> int | None:
    """The width of a printed line, when one file's paragraphs show it.

    An article taken from a PDF can hold each printed line as a paragraph,
    so a word is cut where the line ended (「…職員一人ひと」「りの…」). Such
    lines all have about the same length and do not end a sentence. The
    width is the commonest length among those paragraphs; it needs two of
    them, so a lone heading never sets it. None when nothing shows a width.
    """
    lengths = Counter(
        len(p) for p in paragraphs if not _ends_a_sentence(p) and len(p) >= _MIN_LINE_WIDTH
    )
    if not lengths:
        return None
    width, count = max(lengths.items(), key=lambda item: (item[1], item[0]))
    return width if count >= 2 else None


def _starts_with_mark(paragraph: str) -> bool:
    return _LIST_MARK.match(paragraph) is not None


def join_wrapped(rows: dict[str, list[str]]) -> tuple[dict[str, list[str]], int]:
    """Join each printed line back onto the paragraph it was cut from.

    A paragraph of the file's line width (±1) that does not end a sentence
    is a wrapped line, and the next paragraph of the same row continues it.
    Headings (shorter) and paragraphs that end a sentence stay as they are.
    Never joined: a line shorter than _MIN_JOIN_LENGTH on the left, and a
    line starting with a list or heading mark on either side.
    Only the rows that are shown take part: the name row keeps one paragraph
    per person. Returns the rows and how many lines were joined.
    """
    width = line_width([p for key in USED_ROWS for p in rows.get(key, [])])
    if width is None:
        return rows, 0
    joined_rows = dict(rows)
    joined = 0
    for key in USED_ROWS:
        kept: list[str] = []
        carry = False
        for paragraph in rows.get(key, []):
            if carry and not _starts_with_mark(paragraph):
                kept[-1] += paragraph
                joined += 1
            else:
                kept.append(paragraph)
            carry = (not _ends_a_sentence(paragraph)
                     and abs(len(paragraph) - width) <= _WIDTH_SLACK
                     and len(paragraph) >= _MIN_JOIN_LENGTH
                     and not _starts_with_mark(paragraph))
        if key in rows:
            joined_rows[key] = kept
    return joined_rows, joined


def ingest_article_rows(
    parsed: ArticleRows, seat: Seat, masks: SeatMasks = SeatMasks()
) -> tuple[list[Utterance], ArticleStats]:
    if masks.pages:
        # A docx has no fixed pages, so the request cannot be honored safely.
        raise IngestError("page_mask_on_article")
    person = people_parts(parsed.rows.get(ROW_NAME, []))
    if not person.terms:
        # Without the name nothing can be masked, so the article must not pass.
        raise IngestError("name_row_missing")
    if not any(
        parsed.rows.get(key) for key in (ROW_BODY, *ROWS_STANDING_IN_FOR_BODY)
    ):
        raise IngestError("body_row_missing")

    scrub = ArticleScrubber(
        person_terms=person.terms,
        interviewer_terms=tuple(
            interviewer_terms("\n".join(parsed.rows.get(ROW_INTERVIEWER, [])))
        ),
        seat_pairs=tuple(masks.pairs(seat)),
    )
    # The teacher wrote the article themself: every row is their own words, not
    # split at 「」, and shown as the teacher's article (SPEC 14-50).
    own = seat.kind == KIND_TEACHER_ARTICLE
    rows, wrapped = join_wrapped(parsed.rows)
    utterances: list[Utterance] = []
    for key, section in USED_ROWS.items():
        for raw in rows.get(key, []):
            paragraph = dedupe_sentences(scrub(raw)).strip()
            if not paragraph:
                continue
            if own:
                pieces = [(VOICE_OWN, paragraph)]
            elif key == ROW_BODY:
                pieces = split_voice(paragraph)
            else:
                pieces = [(ROW_VOICES.get(key, VOICE_ARTICLE), paragraph)]
            for voice, text in pieces:
                utterances.append(
                    Utterance(
                        id=make_id(seat.kind, seat.source_file, text),
                        seat_id=seat.seat_id,
                        kind=seat.kind,
                        section=section,
                        voice=voice,
                        text=text,
                        paragraph=paragraph,
                        source_note=TEACHER_ARTICLE_NOTE if own else "",
                    )
                )
    utterances = unique_by_id(utterances)
    assert_clean(utterances, scrub.forbidden())
    stats = ArticleStats(
        unsplit_name=person.unsplit,
        single_char_name=person.single_char,
        dropped_rows=parsed.dropped_rows,
        wrapped_lines_joined=wrapped,
    )
    return utterances, stats


def ingest_article(
    path: Path, seat: Seat, masks: SeatMasks = SeatMasks()
) -> tuple[list[Utterance], ArticleStats]:
    table = pick_table(Document(str(path)).tables, seat.table_no)
    return ingest_article_rows(read_rows(table), seat, masks)
