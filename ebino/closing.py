"""The round's last word: 「最後に、何か伝えたいことはありますか」 (SPEC 14-53 A).

After a round in which seats spoke, the moderator's fixed sentence (texts/,
never written by a model) asks the seats that lit up whether they have
anything to tell. Seats that hold words written (or said) to high-school
students answer with one of those pieces; the others stay quiet. Not one new
word is made (SPEC 3, 1-1).

Which pieces are words to high-school students is decided here by code, from
the section each piece came from, never by a model:
  - 志事図鑑 articles: 高校生に一言, ランキング, 先輩社員からのメッセージ
  - the teacher's article: 高校生に一言
  - posters: the 結論と展望 section, and any section whose heading holds 展望
  - slides: the pages a person listed in EBINO_DATA_DIR/hasshin_pages.tsv
    (columns 席ID・ページ). With no table, no slide page speaks.
The kind of seat is not looked at: the senior talks are posters shaped like
slides, and their pages are slide pages (sections p1, p2, ...).

The moderator picks one such piece per seat, the one nearest the student's
question, by its ID (structured output), and copies the words; the guard
checks the copy against the piece, sentence breaks included. A seat whose
pick fails, or that the guard stops, shows nothing.
"""

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from .gate import Gate, GateError, ModelUnavailable, json_answer, json_request
from .guard import Guard, Quote
from .index import Entry
from .ingest.utterance import Utterance
from .prompts import CLOSING

HASSHIN_PAGES_FILE = "hasshin_pages.tsv"
COLUMNS = ("席ID", "ページ")
MAX_SEATS = 3

ARTICLE_SECTIONS = ("高校生に一言", "ランキング", "先輩社員からのメッセージ")
TEACHER_ARTICLE_SECTIONS = ("高校生に一言",)
KIND_TEACHER = "outsider_teacher"
POSTER_SECTION = "結論と展望"
POSTER_HEADING_WORD = "展望"

SHOWN = "shown"  # At least one seat's words passed the guard.
NONE_HOLD = "none_hold"  # No lit seat holds words to high-school students: no call.
NONE_PASSED = "none_passed"  # Picks came back, none reached the screen.
UNAVAILABLE = "unavailable"  # The model or the gate failed: reason code kept.

SCHEMA = {
    "type": "object",
    "properties": {
        "picks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"utterance_id": {"type": "string"}, "text": {"type": "string"}},
                "required": ["utterance_id", "text"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["picks"],
    "additionalProperties": False,
}


def load_hasshin_pages(path: Path, seat_ids: set[str]) -> dict[str, frozenset[int]]:
    """Slide pages a person marked as words to high-school students.

    No file: no slide page speaks (the quiet side). Errors give line numbers,
    never values."""
    if not path.exists():
        return {}
    pages: dict[str, set[int]] = {}
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError(f"{HASSHIN_PAGES_FILE} columns do not match")
        for row in reader:
            line = reader.line_num
            if None in row or None in row.values():
                raise ValueError(f"{HASSHIN_PAGES_FILE} line {line}: wrong column count")
            seat_id, page = row["席ID"].strip(), row["ページ"].strip()
            if seat_id not in seat_ids:
                raise ValueError(f"{HASSHIN_PAGES_FILE} line {line}: unknown seat")
            if not page.isascii() or not page.isdigit() or int(page) < 1:
                raise ValueError(f"{HASSHIN_PAGES_FILE} line {line}: bad page number")
            pages.setdefault(seat_id, set()).add(int(page))
    return {seat_id: frozenset(numbers) for seat_id, numbers in pages.items()}


def to_students(utterance: Utterance, pages: dict[str, frozenset[int]]) -> bool:
    """Whether a piece holds words to high-school students, by its section."""
    section = utterance.section
    if section in ARTICLE_SECTIONS:
        allowed = TEACHER_ARTICLE_SECTIONS if utterance.kind == KIND_TEACHER else ARTICLE_SECTIONS
        return section in allowed
    if section == POSTER_SECTION or POSTER_HEADING_WORD in utterance.heading:
        return True
    if section.startswith("p") and section[1:].isascii() and section[1:].isdigit():
        return int(section[1:]) in pages.get(utterance.seat_id, frozenset())
    return False


def pieces_by_seat(utterances: list[Utterance], entries: list[Entry],
                   pages: dict[str, frozenset[int]]) -> dict[str, list[Entry]]:
    """Each seat's pieces to high-school students, as index entries."""
    chosen = {u.id for u in utterances if to_students(u, pages)}
    found: dict[str, list[Entry]] = {}
    for entry in entries:
        if entry.utterance_id in chosen:
            found.setdefault(entry.seat_id, []).append(entry)
    return found


@dataclass(frozen=True)
class Word:
    """One seat's words, as the guard gave them back."""

    seat_id: str
    utterance_id: str
    text: str


@dataclass
class Closing:
    status: str
    seats_asked: list[str] = field(default_factory=list)  # Lit seats holding such words.
    words: list[Word] = field(default_factory=list)
    reason: str = ""  # Reason code when unavailable.
    guard_stopped: int = 0
    dropped: int = 0  # Picks naming no piece of an asked seat, or a second for one seat.


def request_for(question: str, pieces: list[Entry]) -> dict:
    data = {"question": question, "pieces": [entry.for_model() for entry in pieces]}
    return json_request("moderator", CLOSING, json.dumps(data, ensure_ascii=False), SCHEMA)


def clean(answer, pieces: list[Entry]) -> tuple[list[Quote], int]:
    """One quote per seat, naming a piece that was sent; the seat comes from
    the piece, never from the model."""
    if not isinstance(answer, dict):
        raise ModelUnavailable("bad_output")
    seat_of = {entry.utterance_id: entry.seat_id for entry in pieces}
    quotes: list[Quote] = []
    seats: set[str] = set()
    dropped = 0
    for item in answer.get("picks") or []:
        utterance_id = item.get("utterance_id") if isinstance(item, dict) else None
        text = item.get("text") if isinstance(item, dict) else None
        if utterance_id not in seat_of or not isinstance(text, str) or seat_of[utterance_id] in seats:
            dropped += 1
            continue
        seats.add(seat_of[utterance_id])
        quotes.append(Quote(utterance_id, text))
    return quotes, dropped


def run(gate: Gate, guard: Guard, question: str, seat_order: list[str],
        held: dict[str, list[Entry]]) -> Closing:
    asked = [seat_id for seat_id in seat_order if held.get(seat_id)][:MAX_SEATS]
    if not asked:
        return Closing(NONE_HOLD)
    pieces = [entry for seat_id in asked for entry in held[seat_id]]
    try:
        answer = json_answer(gate.send("moderator", request_for(question, pieces)))
        quotes, dropped = clean(answer, pieces)
    except (GateError, ModelUnavailable) as error:
        return Closing(UNAVAILABLE, asked, reason=str(error))
    seat_of = {entry.utterance_id: entry.seat_id for entry in pieces}
    result = Closing(NONE_PASSED, asked, dropped=dropped)
    passed = {}
    for verdict in guard.screen(quotes):
        if verdict.passed:
            uid = verdict.quote.utterance_id
            passed[seat_of[uid]] = Word(seat_of[uid], uid, verdict.shown)
        else:
            result.guard_stopped += 1
    # In the order the seats spoke in the round.
    result.words = [passed[seat_id] for seat_id in asked if seat_id in passed]
    if result.words:
        result.status = SHOWN
    return result
