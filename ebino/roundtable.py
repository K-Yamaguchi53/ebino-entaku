"""One round of the round table: a student's question in, the seats' own
words out (SPEC 5-1).

    librarian (finds pieces) -> moderator (picks and orders quotes, splits)
    -> guard (each quote against its piece) -> what the screen may show

Three ways a round ends, kept apart (SPEC 5-1, 14-51):
  - answered: at least one quote passed the guard.
  - silent: no seat answered. The screen shows only the count, 0, and the
    question becomes a question card. No model adds words on the screen;
    the editor writes only on the back of the card (SPEC 14-13).
  - unavailable: a model refused or failed, or the gate stopped a request.
    The screen shows the fixed sentence in texts/ and the reason code is
    recorded. This is not silence, so it never shows 「答えた席：0」.

Before any of that, the question alone is checked against the gate's name
list. A hit calls no model and makes no card: the round ends as ask_again
with its own fixed sentence, because waiting would not help. Which word hit
is never kept, and neither is the question, so neither the screen nor the
records can show the name list.
"""

from dataclasses import dataclass, field

from . import editor, librarian, moderator
from .editor import QuestionCard
from .gate import Gate, GateError, ModelUnavailable
from .guard import Guard, Quote, plant_fake
from .index import Entry
from .ingest.seats import Seat
from .texts import MODEL_UNAVAILABLE, NAME_IN_QUESTION, PLANTED_FAKE_QUOTE, load_text

ANSWERED = "answered"
SILENT = "silent"
UNAVAILABLE = "unavailable"
ASK_AGAIN = "ask_again"  # The question held a name; no model was called.
REASON_NAME_IN_QUESTION = "name_in_question"


@dataclass(frozen=True)
class ShownQuote:
    utterance_id: str
    seat_id: str
    voice: str
    text: str  # The piece's own words, as the guard gives them back.


@dataclass(frozen=True)
class Split:
    heading: str
    side_a: tuple[str, ...]  # Utterance IDs of shown quotes.
    side_b: tuple[str, ...]


@dataclass
class Round:
    question: str
    status: str
    reason: str = ""  # Why a round was unavailable: a reason code only.
    message: str = ""  # The fixed sentence for an unavailable round.
    quotes: list[ShownQuote] = field(default_factory=list)
    splits: list[Split] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)  # What the librarian found.
    librarian_ended: str = ""
    guard_passed: int = 0
    guard_stopped: int = 0
    # The planted fake (SPEC 7-3): its own text, shown as stopped.
    planted_stopped: list[str] = field(default_factory=list)
    planted_passed: int = 0
    splits_dropped: int = 0
    # Related seats with no words: 「まだ誰も聞いていない」 (SPEC 14-12).
    silent_seats: list[str] = field(default_factory=list)
    card: QuestionCard | None = None  # Made only when no seat answered.

    @property
    def seat_order(self) -> list[str]:
        return list(dict.fromkeys(quote.seat_id for quote in self.quotes))

    @property
    def answered_seats(self) -> int:
        return len(self.seat_order)


def _splits(plans, shown: dict[str, ShownQuote], gate: Gate) -> tuple[list[Split], int]:
    kept, dropped = [], 0
    for split in plans:
        side_a = tuple(i for i in split.side_a if i in shown and i not in split.side_b)
        side_b = tuple(i for i in split.side_b if i in shown and i not in split.side_a)
        # A heading needs words on both sides that reached the screen, and
        # names no one (SPEC 14-39).
        if split.heading and side_a and side_b and not gate.names.hits(split.heading):
            kept.append(Split(split.heading, side_a, side_b))
        else:
            dropped += 1
    return kept, dropped


def run(
    gate: Gate, entries: list[Entry], seats: list[Seat], guard: Guard, question: str, plant: bool = False
) -> Round:
    if gate.names.hits(question):
        return Round("", ASK_AGAIN, reason=REASON_NAME_IN_QUESTION, message=load_text(NAME_IN_QUESTION))
    by_id = {entry.utterance_id: entry for entry in entries}
    try:
        found = librarian.find(gate, entries, question)
        result = Round(question, SILENT, candidates=found.utterance_ids, librarian_ended=found.ended)
        if not found.utterance_ids:
            result.card = editor.card_for_no_answer(gate, question, seats)
            return result
        plan = moderator.plan(gate, question, [by_id[i] for i in found.utterance_ids], seats)
    except (GateError, ModelUnavailable) as error:
        return Round(question, UNAVAILABLE, reason=str(error), message=load_text(MODEL_UNAVAILABLE))

    quotes: list[Quote] = list(plan.quotes)
    if plant:
        quotes = plant_fake(quotes, load_text(PLANTED_FAKE_QUOTE))
    shown: dict[str, ShownQuote] = {}
    for verdict in guard.screen(quotes):
        quote = verdict.quote
        if quote.planted:
            if verdict.passed:
                result.planted_passed += 1
            else:
                result.planted_stopped.append(quote.text)
            continue
        if verdict.passed:
            entry = by_id[quote.utterance_id]
            shown[quote.utterance_id] = ShownQuote(quote.utterance_id, entry.seat_id, entry.voice, verdict.shown)
            result.guard_passed += 1
        else:
            result.guard_stopped += 1
    result.quotes = list(shown.values())
    result.splits, result.splits_dropped = _splits(plan.splits, shown, gate)
    answered = set(result.seat_order)
    result.silent_seats = [s for s in plan.silent_seat_ids if s not in answered]
    result.status = ANSWERED if result.quotes else SILENT
    if result.status == SILENT:
        result.card = editor.card_for_no_answer(gate, question, seats)
    return result
