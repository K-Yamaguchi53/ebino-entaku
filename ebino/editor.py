"""Question cards and the editor (SPEC 5-1, 6, 14-12, 14-13).

A card is made in these ways (SPEC 14-12, 14-53):
  - no_answer: no seat answered the question (「この問いに答えた席：0」); the
    question itself becomes the card.
  - student: the student pressed a silent seat and wrote what they want to
    ask that person; what they wrote becomes the card as it is.
  - not_heard_yet: under 「もっと聞く」 the seat's section ran out and the
    student pressed 「ここから先は、まだ聞いていない」; the round's question
    goes to that seat.
  - ask_seat: 「司会が○○に聞いてみる」 found nothing and the student pressed
    「まだ答えていない」; the card's question goes to that seat. It holds the
    record's words in a fixed sentence, not the student's own words.
No model writes a card's text: it is the student's own words, or for
ask_seat the checked question built from the record. The editor (Sonnet 5.5)
adds, on the back of the card only, seats that could be asked and, for a
question that asks only for a fact, a rephrasing that asks why. The back is
for the teacher and next year's interviewers; it is never on the student's
screen, and nothing on it is offered to the student (SPEC 14-13).

If the editor cannot answer, or does not within TIMEOUT_SECONDS (no retry;
直し31-1), the card is still made without a back, and the reason code is kept.
"""

import json
import secrets
from dataclasses import dataclass, field

from .gate import Gate, GateError, ModelUnavailable, json_answer, json_request
from .ingest.seats import Seat
from .prompts import EDITOR

ORIGIN_NO_ANSWER = "no_answer"
ORIGIN_STUDENT = "student"
# The student pressed 「ここから先は、まだ聞いていない」 under 「もっと聞く」: the
# round's question goes to that seat (SPEC 2-2).
ORIGIN_NOT_HEARD = "not_heard_yet"
MAX_ASK = 3
MAX_REPHRASE_CHARS = 80
TIMEOUT_SECONDS = 20.0  # The wait for the model, with no retry (直し31-1).

SCHEMA = {
    "type": "object",
    "properties": {
        "ask_seat_ids": {"type": "array", "items": {"type": "string"}},
        "rephrase": {"type": "string"},
    },
    "required": ["ask_seat_ids", "rephrase"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Back:
    """The back of a card: for the teacher and interviewers only."""

    ask_seat_ids: tuple[str, ...] = ()
    rephrase: str = ""
    reason: str = ""  # Why the editor gave no back: a reason code only.


@dataclass(frozen=True)
class QuestionCard:
    card_id: str
    origin: str
    text: str  # The student's words, unchanged.
    seat_id: str = ""  # The seat the card is to (student cards and 「まだ聞いていない」).
    back: Back = field(default_factory=Back)

    def front(self) -> dict:
        """What the student's screen may show."""
        return {"card_id": self.card_id, "origin": self.origin, "text": self.text, "seat_id": self.seat_id}


def new_card_id() -> str:
    # Random, so card IDs say nothing about order or who wrote them (SPEC 2-1).
    return "q-" + secrets.token_hex(4)


def write_back(gate: Gate, text: str, seats: list[Seat]) -> Back:
    data = {"question": text, "seats": [seat.for_model() for seat in seats]}
    request = json_request("editor", EDITOR, json.dumps(data, ensure_ascii=False), SCHEMA)
    try:
        answer = json_answer(gate.send("editor", request, timeout=TIMEOUT_SECONDS))
    except (GateError, ModelUnavailable) as error:
        return Back(reason=str(error))
    if not isinstance(answer, dict):
        return Back(reason="bad_output")
    known = {seat.seat_id for seat in seats}
    ask = [s for s in dict.fromkeys(answer.get("ask_seat_ids") or []) if isinstance(s, str) and s in known]
    rephrase = answer.get("rephrase")
    rephrase = rephrase.strip() if isinstance(rephrase, str) else ""
    # The back is model words: keep it short and free of names.
    if len(rephrase) > MAX_REPHRASE_CHARS or gate.names.hits(rephrase):
        rephrase = ""
    return Back(tuple(ask[:MAX_ASK]), rephrase)


def card_for_no_answer(gate: Gate, question: str, seats: list[Seat]) -> QuestionCard:
    return QuestionCard(new_card_id(), ORIGIN_NO_ANSWER, question, back=write_back(gate, question, seats))


def card_for_seat(gate: Gate, origin: str, seat_id: str, text: str, seats: list[Seat]) -> QuestionCard:
    """A card to one seat the student pressed for (「まだ聞いていない」 under
    「もっと聞く」, holding the question the student wrote; SPEC 2-2)."""
    return QuestionCard(new_card_id(), origin, text, seat_id, write_back(gate, text, seats))


def card_from_student(gate: Gate, seat_id: str, text: str, seats: list[Seat]) -> QuestionCard | None:
    """None when the box was left empty or the seat is unknown."""
    text = text.strip()
    if not text or seat_id not in {seat.seat_id for seat in seats}:
        return None
    return QuestionCard(new_card_id(), ORIGIN_STUDENT, text, seat_id, write_back(gate, text, seats))
