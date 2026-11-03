"""One student's sitting at the round table, and what the screen is sent
(SPEC 5-1, 14-12, 14-51: a seat list until the map is drawn).

The screen gets plain data built here, never a model's words except the
quotes the guard passed (which are the pieces' own text) and split headings.
Seat labels come from the seat table through seat_label, so company and
display name reach the screen only when EBINO_SHOW_COMPANY=1 and never reach
a model. The year is never sent (SPEC 14-34).

One sitting at a time: there is no login and no second student at once
(SPEC 3). Starting again makes a new sitting with a new random ID.
"""

import re
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import editor, harvest, reflection, roundtable
from .editor import QuestionCard
from .reflection import CHANGED_CHOICES, CHOSE_NONE, CHOSE_OWN, DIRECTION_LABELS, MAX_LINE_CHARS, Reflection
from .texts import NAME_IN_QUESTION, load_text
from .gate import Gate
from .guard import Guard
from .index import Entry, build_index, load_topics, load_utterances
from .ingest.seats import Seat, load_seats
from .ingest.utterance import Utterance
from .purpose import PurposeSample, PurposeShelf, samples
from .records import Records, session_record, today
from .seat_label import KIND_LABELS, seat_label

MAX_QUESTION_CHARS = 200
MAX_CARD_CHARS = 200
# The one question asked first (SPEC 2-1, 14-20). The keys are what is kept.
LAB_CHOICES = {
    "quest": "Quest",
    "action": "Action",
    "creation": "Creation（生活文化科）",
    "not_said": "言わない",
}


class Refused(Exception):
    """A screen request that cannot be done. Reason code only."""


# The moderator's headings begin 「ここで割れた：」 (prompts.MODERATOR). The
# round table keeps it; the sheet already says 割れたところ and 置いてきた：.
_SPLIT_LEAD = re.compile(r"^\s*ここで割れた\s*[：:]\s*")


def _sheet_heading(heading: str) -> str:
    return _SPLIT_LEAD.sub("", heading) or heading


def _line(text, limit: int, empty_code: str, required: bool = True) -> str:
    """One line the student wrote, trimmed and capped."""
    text = " ".join((text if isinstance(text, str) else "").split())
    if required and not text:
        raise Refused(empty_code)
    if len(text) > limit:
        raise Refused("too_long")
    return text


@dataclass
class Library:
    """What every sitting reads: loaded once when the app starts."""

    seats: list[Seat]
    utterances: list[Utterance]
    entries: list[Entry]
    purposes: list[PurposeSample]
    show_private: bool = False

    @classmethod
    def build(cls, seats, utterances, topics, show_private=False) -> "Library":
        return cls(seats, utterances, build_index(utterances, seats, topics),
                   samples(utterances, seats), show_private)

    @classmethod
    def load(cls, data_dir: Path, show_private: bool = False) -> "Library":
        return cls.build(load_seats(data_dir / "seats.tsv"), load_utterances(data_dir),
                         load_topics(data_dir), show_private)

    def seat_view(self, seat: Seat) -> dict:
        label = seat_label(seat, self.show_private)
        return {"seat_id": seat.seat_id, "kind": seat.kind, "title": label.title, "detail": label.detail}

    def seat_list(self) -> list[dict]:
        order = list(KIND_LABELS)
        seats = sorted(self.seats, key=lambda s: order.index(s.kind) if s.kind in order else len(order))
        return [self.seat_view(seat) for seat in seats]


@dataclass
class Session:
    library: Library
    gate: Gate
    plant: bool = False  # Mix in the planted fake (SPEC 7-3), for the demo.
    rng: object = None
    session_id: str = field(default_factory=lambda: secrets.token_hex(4))
    lab: str = ""
    rounds: list[roundtable.Round] = field(default_factory=list)
    cards: list[QuestionCard] = field(default_factory=list)
    marks: dict[str, str] = field(default_factory=dict)  # seat_id -> utterance_id
    pressed_splits: set[tuple[int, int]] = field(default_factory=set)  # (round, split)
    started: float = field(default_factory=time.monotonic)  # Seconds used, never clock time.
    date: str = field(default_factory=today)
    records: Records | None = None  # None: nothing is kept (tests only).
    reflection: Reflection | None = None

    def __post_init__(self):
        self.guard = Guard(self.library.utterances)
        self.shelf = PurposeShelf(self.library.purposes, self.rng)
        self._seats = {seat.seat_id: seat for seat in self.library.seats}
        self._utterances = {u.id: u for u in self.library.utterances}

    def save(self) -> None:
        """Kept after every step (SPEC 2-1: every action is recorded by itself)."""
        if self.records is not None:
            self.records.save_session(session_record(self))

    # --- what the student does ---

    def set_lab(self, choice: str) -> None:
        if choice not in LAB_CHOICES:
            raise Refused("unknown_lab_choice")
        self.lab = choice
        self.save()

    def ask(self, question: str) -> dict:
        question = (question or "").strip()
        if not question:
            raise Refused("empty_question")
        if len(question) > MAX_QUESTION_CHARS:
            raise Refused("question_too_long")
        result = roundtable.run(self.gate, self.library.entries, self.library.seats, self.guard,
                                question, plant=self.plant)
        self.rounds.append(result)
        if result.card:
            self.cards.append(result.card)
        self.save()
        return self.round_view(len(self.rounds))

    def write_card(self, seat_id: str, text: str) -> dict:
        """A card the student writes at a seat shown as 「まだ誰も聞いていない」."""
        if seat_id not in self.silent_seats():
            raise Refused("not_a_silent_seat")
        if len((text or "").strip()) > MAX_CARD_CHARS:
            raise Refused("card_too_long")
        card = editor.card_from_student(self.gate, seat_id, text or "", self.library.seats)
        if card is None:
            raise Refused("empty_card")
        self.cards.append(card)
        self.save()
        return card.front()

    def mark(self, round_no: int, utterance_id: str) -> dict:
        """One marked quote per seat (SPEC 5-2). Marking it again takes it off."""
        quote = next((q for q in self._round(round_no).quotes if q.utterance_id == utterance_id), None)
        if quote is None:
            raise Refused("unknown_quote")
        if self.marks.get(quote.seat_id) == utterance_id:
            del self.marks[quote.seat_id]
        else:
            self.marks[quote.seat_id] = utterance_id
        self.save()
        return dict(self.marks)

    def press_split(self, round_no: int, index: int) -> str:
        """The heading goes into the input box as it is (SPEC 5-1 hint 1)."""
        splits = self._round(round_no).splits
        if not isinstance(index, int) or not 0 <= index < len(splits):
            raise Refused("unknown_split")
        self.pressed_splits.add((round_no, index))
        self.save()
        return splits[index].heading

    def next_purposes(self) -> list[dict]:
        return [self.purpose_view(sample) for sample in self.shelf.next()]

    def paragraph(self, utterance_id: str) -> dict:
        """The paragraph a shown quote came from (SPEC 5-1: back to the source)."""
        if utterance_id not in self.shown_ids():
            raise Refused("not_shown")
        utterance = self._utterances[utterance_id]
        return {"utterance_id": utterance_id, "paragraph": utterance.paragraph or utterance.text}

    # --- the reflection sheet (SPEC 5-2) ---

    def reflect_begin(self, changed: str, now_question: str) -> dict:
        """The student writes first; then the moderator reads the record once."""
        if not any(r.status in (roundtable.ANSWERED, roundtable.SILENT) for r in self.rounds):
            raise Refused("no_round_yet")
        if self.reflection is not None:
            raise Refused("reflection_started")
        if changed not in CHANGED_CHOICES:
            raise Refused("unknown_changed_choice")
        now_question = _line(now_question, MAX_QUESTION_CHARS, "empty_now_question")
        if self.gate.names.hits(now_question):
            return {"status": roundtable.ASK_AGAIN, "message": load_text(NAME_IN_QUESTION)}
        self.reflection = reflection.begin(self.gate, self, changed, now_question)
        self.save()
        return {"status": "ok", "ask_back": self.reflection.ask_back}

    def reflect_answer(self, answer: str, declined: bool = False) -> dict:
        """One line, or 「答えない」. The next moves are shown after this."""
        current = self._reflection()
        if current.answered:
            raise Refused("already_answered")
        if declined:
            current.declined = True
        else:
            current.answer = _line(answer, MAX_LINE_CHARS, "empty_answer")
        current.answered = True
        self.save()
        return {"moves": [{"direction": m.direction, "label": DIRECTION_LABELS[m.direction], "text": m.text}
                          for m in current.moves]}

    def reflect_finish(self, chosen: str, own_move: str, rewrite: str, meet_seat: str, meet_reason: str) -> dict:
        current = self._reflection()
        if not current.answered or current.finished:
            raise Refused("not_ready_to_finish")
        if chosen not in [m.direction for m in current.moves] + [CHOSE_NONE, CHOSE_OWN]:
            raise Refused("unknown_move")
        if meet_seat not in self._seats:
            raise Refused("unknown_seat")
        current.chosen = chosen
        if chosen == CHOSE_OWN:
            current.own_move = _line(own_move, MAX_LINE_CHARS, "empty_own_move")
        current.rewrite = _line(rewrite, MAX_QUESTION_CHARS, "", required=False)
        current.meet_seat = meet_seat
        current.meet_reason = _line(meet_reason, MAX_LINE_CHARS, "", required=False)
        current.finished = True
        self.save()
        # ② comes right after the seat to meet is picked (SPEC 5-3).
        return self.sheet_view() | {"uses": [harvest.use_view(force) for force in harvest.uses_offered(self)]}

    def harvest(self, use: str) -> dict:
        """② picked (or 「選ばない」); the card's ① and ② lines (SPEC 5-3)."""
        current = self._reflection()
        if not current.finished or current.harvest_use:
            raise Refused("not_ready_for_harvest")
        offered = [str(force) for force in harvest.uses_offered(self)]
        if use not in offered + [harvest.CHOSE_NO_USE]:
            raise Refused("unknown_use")
        picked = harvest.pick(harvest.found_moves(self, _sheet_heading))
        current.harvest_moves = [move.code for move in picked]
        current.harvest_use = use
        self.save()
        title = seat_label(self._seats[current.meet_seat], self.library.show_private).title
        return {
            "moves": harvest.moves_line(picked),
            "meet": harvest.meet_line(title, None if use == harvest.CHOSE_NO_USE else int(use)),
        }

    def _reflection(self) -> Reflection:
        if self.reflection is None:
            raise Refused("reflection_not_started")
        return self.reflection

    def sheet_view(self) -> dict:
        """The sheet as the student keeps it (SPEC 5-2 table)."""
        current = self._reflection()
        shown = {q.utterance_id: q for r in self.rounds for q in r.quotes}
        met_lives = []
        for seat_id in self.met_seats():
            utterance_id = self.marks.get(seat_id)
            if utterance_id in shown:
                utterance = self._utterances[utterance_id]
                met_lives.append({"text": shown[utterance_id].text, "said": not utterance.note,
                                  "source": self.source(seat_id, utterance)})
        move = next((m for m in current.moves if m.direction == current.chosen), None)
        meet = self.library.seat_view(self._seats[current.meet_seat]) if current.meet_seat else None
        return {
            "first_question": next((r.question for r in self.rounds if r.question), ""),
            "met_lives": met_lives,
            "splits": [{"heading": _sheet_heading(s.heading), "pressed": (n, i) in self.pressed_splits}
                       for n, r in enumerate(self.rounds, start=1) for i, s in enumerate(r.splits)],
            "cards": [card.text for card in self.cards],
            "changed": CHANGED_CHOICES[current.changed],
            "now_question": current.now_question,
            "ask_back": current.ask_back,
            "answer": current.answer,
            "declined": current.declined,
            "chosen": current.chosen,
            "move": {"label": DIRECTION_LABELS[move.direction], "text": move.text} if move else None,
            "own_move": current.own_move,
            "rewrite": current.rewrite,
            "meet": meet | {"reason": current.meet_reason} if meet else None,
        }

    # --- what the sitting has gathered ---

    def met_seats(self) -> list[str]:
        """Seats whose words reached the screen, in the order first met."""
        return list(dict.fromkeys(s for r in self.rounds for s in r.seat_order))

    def silent_seats(self) -> list[str]:
        return list(dict.fromkeys(s for r in self.rounds for s in r.silent_seats))

    def shown_ids(self) -> set[str]:
        return {q.utterance_id for r in self.rounds for q in r.quotes}

    def seconds_used(self) -> int:
        return int(time.monotonic() - self.started)

    # --- views ---

    def _round(self, round_no: int) -> roundtable.Round:
        if not isinstance(round_no, int) or not 1 <= round_no <= len(self.rounds):
            raise Refused("unknown_round")
        return self.rounds[round_no - 1]

    def source(self, seat_id: str, utterance: Utterance) -> dict:
        seat = self._seats[seat_id]
        label = seat_label(seat, self.library.show_private)
        return {"title": label.title, "detail": label.detail, "note": utterance.note}

    def round_view(self, round_no: int) -> dict:
        result = self._round(round_no)
        quotes = []
        for quote in result.quotes:
            utterance = self._utterances[quote.utterance_id]
            quotes.append({
                "utterance_id": quote.utterance_id,
                "seat_id": quote.seat_id,
                "text": quote.text,
                # A person's own words get 「」; article text gets its note instead.
                "said": not utterance.note,
                "source": self.source(quote.seat_id, utterance),
            })
        return {
            "round": round_no,
            "question": result.question,  # "" when it held a name (ask_again).
            "status": result.status,
            "reason": result.reason,
            "message": result.message,
            "answered_seats": result.answered_seats,
            "seat_order": result.seat_order,
            "steps": {"found": len(result.candidates), "passed": result.guard_passed,
                      "stopped": result.guard_stopped},
            "quotes": quotes,
            "planted_stopped": list(result.planted_stopped),
            "splits": [{"index": i, "heading": s.heading, "side_a": list(s.side_a), "side_b": list(s.side_b)}
                       for i, s in enumerate(result.splits)],
            "silent_seats": list(result.silent_seats),
            "card": result.card.front() if result.card else None,
            "met_seats": self.met_seats(),
        }

    def purpose_view(self, sample: PurposeSample) -> dict:
        seat = self._seats[sample.seat_id]
        label = seat_label(seat, self.library.show_private)
        return {"seat_id": sample.seat_id, "texts": list(sample.texts),
                "source": {"title": label.title, "detail": label.detail, "note": ""}}
