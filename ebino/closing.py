"""The round's last word: 「最後に、何か伝えたいことはありますか」 (SPEC 14-53 A,
widened by the teacher on 11/3).

After a round in which seats spoke, the moderator's fixed sentence (texts/,
never written by a model) asks the seats that lit up whether they have
anything to tell. Each answers with one piece of its own; not one new word
is made (SPEC 3, 1-1).

Which pieces may answer is decided by the kind of talk each piece was tagged
with at ingest (talk_kinds.py; the teacher's table texts/talk_kinds.tsv):
every kind but 「なし」 (none). A ranking's title alone (a line ending in
ベスト or ランキング and a number) never answers. Section names are not looked
at.

For each seat, code picks one kind: among the kinds the seat still has a
piece for that this student has not been shown, the kind shown to this
student the fewest times, ties in the table's order; a kind picked for a seat
counts at once, so seats in one round lean apart. The moderator then picks
one piece of that kind, the one nearest the student's question, by its ID
(structured output), and copies the words; the guard checks the copy against
the piece, sentence breaks included. A seat whose pick fails, or that the
guard stops, shows nothing. A piece is never shown twice to one student.
"""

import json
import re
from collections import Counter
from dataclasses import dataclass, field

from .gate import Gate, GateError, ModelUnavailable, json_answer, json_request
from .guard import Guard, Quote
from .index import Entry
from .prompts import CLOSING
from .talk_kinds import NONE

MAX_SEATS = 3
# 「やってよかったことベスト3」「好きな場所ランキング５」: a ranking's title alone.
_RANKING_TITLE = re.compile(r"(?:ベスト|ランキング)\s*[0-9０-９一二三四五六七八九十]+\s*[!！]?\s*$")

SHOWN = "shown"  # At least one seat's words passed the guard.
NONE_HOLD = "none_hold"  # No lit seat holds a piece that may answer: no call.
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


def is_ranking_title(text: str) -> bool:
    return "\n" not in text.strip() and _RANKING_TITLE.search(text.strip()) is not None


def pieces_by_seat(entries: list[Entry], kind_of: dict[str, str]) -> dict[str, dict[str, list[Entry]]]:
    """Each seat's pieces that may answer, by kind, in reading order."""
    found: dict[str, dict[str, list[Entry]]] = {}
    for entry in entries:
        kind = kind_of.get(entry.utterance_id, NONE)
        if kind == NONE or is_ranking_title(entry.text):
            continue
        found.setdefault(entry.seat_id, {}).setdefault(kind, []).append(entry)
    return found


def choose_kind(by_kind: dict[str, list[Entry]], shown_ids: set[str], counts: Counter,
                order: list[str]) -> str | None:
    """The kind shown the fewest times among those with a piece not shown yet."""
    open_kinds = [kind for kind, pieces in by_kind.items()
                  if any(entry.utterance_id not in shown_ids for entry in pieces)]
    if not open_kinds:
        return None
    rank = {kind: index for index, kind in enumerate(order)}
    return min(open_kinds, key=lambda kind: (counts[kind], rank.get(kind, len(rank))))


@dataclass(frozen=True)
class Word:
    """One seat's words, as the guard gave them back."""

    seat_id: str
    utterance_id: str
    text: str
    kind: str


@dataclass
class Closing:
    status: str
    seats_asked: list[str] = field(default_factory=list)  # Lit seats holding a piece that may answer.
    kinds_asked: list[str] = field(default_factory=list)  # The kind picked for each asked seat.
    words: list[Word] = field(default_factory=list)
    reason: str = ""  # Reason code when unavailable.
    guard_stopped: int = 0
    dropped: int = 0  # Picks naming no piece sent, or a second for one seat.


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
        held: dict[str, dict[str, list[Entry]]], shown_ids: set[str], counts: Counter,
        order: list[str]) -> Closing:
    """shown_ids: every piece this student has been shown; counts: how many
    times each kind was shown to this student in earlier rounds."""
    counts = Counter(counts)
    asked: list[str] = []
    kinds: list[str] = []
    pieces: list[Entry] = []
    for seat_id in seat_order:
        if len(asked) == MAX_SEATS:
            break
        kind = choose_kind(held.get(seat_id, {}), shown_ids, counts, order)
        if kind is None:
            continue
        asked.append(seat_id)
        kinds.append(kind)
        counts[kind] += 1
        pieces += [entry for entry in held[seat_id][kind] if entry.utterance_id not in shown_ids]
    if not asked:
        return Closing(NONE_HOLD)
    try:
        answer = json_answer(gate.send("moderator", request_for(question, pieces)))
        quotes, dropped = clean(answer, pieces)
    except (GateError, ModelUnavailable) as error:
        return Closing(UNAVAILABLE, asked, kinds, reason=str(error))
    seat_of = {entry.utterance_id: entry.seat_id for entry in pieces}
    kind_of_seat = dict(zip(asked, kinds))
    result = Closing(NONE_PASSED, asked, kinds, dropped=dropped)
    passed = {}
    for verdict in guard.screen(quotes):
        if verdict.passed:
            uid = verdict.quote.utterance_id
            seat_id = seat_of[uid]
            passed[seat_id] = Word(seat_id, uid, verdict.shown, kind_of_seat[seat_id])
        else:
            result.guard_stopped += 1
    # In the order the seats spoke in the round.
    result.words = [passed[seat_id] for seat_id in asked if seat_id in passed]
    if result.words:
        result.status = SHOWN
    return result
