"""The moderator: picks which seats speak, in what order, with which quotes,
and puts a heading only where views split (SPEC 5-1, 6).

The moderator names pieces by ID and copies the words it wants to show; the
guard then checks each copy against its piece, and the screen shows the
piece's own text (SPEC 6, 14-51), or since 直し31-7 the same as spoken words
that code checked (speaker.py), the piece's own text always readable beside
it. What comes back here is only the model's
choice, cleaned by code: unknown pieces and extra quotes are dropped. Which
seat a quote belongs to is taken from the piece, never from the model.
"""

import json
from dataclasses import dataclass

from .gate import Gate, ModelUnavailable, json_answer, json_request
from .guard import Quote
from .index import Entry
from .ingest.seats import Seat
from .prompts import MODERATOR

MAX_SEATS = 8
MAX_QUOTES_PER_SEAT = 2
MAX_SPLITS = 3
MAX_SILENT = 8
# The seats sent with the pieces (直し31-6): those the pieces are of, and at
# most this many more whose pieces share a topic with them (the seats
# 「まだ誰も聞いていない」 may come from), not the whole table.
MAX_OTHER_SEATS = 12
# The wait for the model, with no retry (直し31-1): past it the round is
# unavailable, as when the model cannot be used, and the question stays in
# the box to be sent again.
TIMEOUT_SECONDS = 60.0

SCHEMA = {
    "type": "object",
    "properties": {
        "quotes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"utterance_id": {"type": "string"}, "text": {"type": "string"}},
                "required": ["utterance_id", "text"],
                "additionalProperties": False,
            },
        },
        "splits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "side_a": {"type": "array", "items": {"type": "string"}},
                    "side_b": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["heading", "side_a", "side_b"],
                "additionalProperties": False,
            },
        },
        "silent_seat_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["quotes", "splits", "silent_seat_ids"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class SplitPlan:
    heading: str
    side_a: tuple[str, ...]
    side_b: tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    quotes: tuple[Quote, ...]  # In speaking order.
    splits: tuple[SplitPlan, ...]
    # Seats the moderator found related to the question but with no words
    # among the pieces: they show 「まだ誰も聞いていない」 (SPEC 14-12).
    silent_seat_ids: tuple[str, ...] = ()


def request_for(question: str, candidates: list[Entry], seats: list[Seat], ai_question: str = "") -> dict:
    """The instruction part is the system text; the data part (the question,
    the pieces and the seat list) is the message, so the two can be kept
    apart (SPEC 6). Seats go in through Seat.for_model only. With
    ai_question, the question is the student's answer to it (coach.py)."""
    data = {"question": question}
    if ai_question:
        data["ai_question"] = ai_question
    data |= {
        "pieces": [entry.for_model() for entry in candidates],
        "seats": [seat.for_model() for seat in seats],
    }
    return json_request("moderator", MODERATOR, json.dumps(data, ensure_ascii=False), SCHEMA)


def related_seats(candidates: list[Entry], entries: list[Entry], seats: list[Seat]) -> list[Seat]:
    """The seats of the pieces, then the others whose pieces share the most
    topics with the pieces' (ties in table order), at most MAX_OTHER_SEATS."""
    own = {entry.seat_id for entry in candidates}
    topics = {topic for entry in candidates for topic in entry.topics}
    shared: dict[str, int] = {}
    for entry in entries:
        if entry.seat_id not in own:
            shared[entry.seat_id] = shared.get(entry.seat_id, 0) + len(topics & set(entry.topics))
    others = sorted((seat for seat in seats if shared.get(seat.seat_id)), key=lambda s: -shared[s.seat_id])
    keep = own | {seat.seat_id for seat in others[:MAX_OTHER_SEATS]}
    return [seat for seat in seats if seat.seat_id in keep]


def _ids(value) -> tuple[str, ...]:
    return tuple(dict.fromkeys(v for v in value if isinstance(v, str))) if isinstance(value, list) else ()


def clean(answer, candidates: list[Entry], seats: list[Seat] = ()) -> Plan:
    if not isinstance(answer, dict):
        raise ModelUnavailable("bad_output")
    seat_of = {entry.utterance_id: entry.seat_id for entry in candidates}
    quotes: list[Quote] = []
    per_seat: dict[str, int] = {}
    seen: set[str] = set()
    for item in answer.get("quotes") or []:
        if not isinstance(item, dict):
            continue
        utterance_id, text = item.get("utterance_id"), item.get("text")
        if utterance_id not in seat_of or not isinstance(text, str) or utterance_id in seen:
            continue
        seat = seat_of[utterance_id]
        if seat not in per_seat and len(per_seat) == MAX_SEATS:
            continue
        if per_seat.get(seat, 0) == MAX_QUOTES_PER_SEAT:
            continue
        per_seat[seat] = per_seat.get(seat, 0) + 1
        seen.add(utterance_id)
        quotes.append(Quote(utterance_id, text))
    splits = []
    for item in answer.get("splits") or []:
        if isinstance(item, dict) and isinstance(item.get("heading"), str):
            splits.append(SplitPlan(item["heading"].strip(), _ids(item.get("side_a")), _ids(item.get("side_b"))))
    known = {seat.seat_id for seat in seats}
    silent = [s for s in _ids(answer.get("silent_seat_ids")) if s in known and s not in per_seat]
    return Plan(tuple(quotes), tuple(splits[:MAX_SPLITS]), tuple(silent[:MAX_SILENT]))


def plan(gate: Gate, question: str, candidates: list[Entry], seats: list[Seat], ai_question: str = "",
         sent: list[Seat] | None = None) -> Plan:
    """Raises GateError or ModelUnavailable (reason codes only). sent: the
    seats put in the request (related_seats; 直し31-6), all when None; the
    answer is checked against every seat."""
    answer = json_answer(gate.send("moderator", request_for(question, candidates, seats if sent is None else sent,
                                                            ai_question), timeout=TIMEOUT_SECONDS))
    return clean(answer, candidates, seats)
