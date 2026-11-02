"""The moderator: picks which seats speak, in what order, with which quotes,
and puts a heading only where views split (SPEC 5-1, 6).

The moderator names pieces by ID and copies the words it wants to show; the
guard then checks each copy against its piece, and the screen shows the
piece's own text (SPEC 6, 14-51). What comes back here is only the model's
choice, cleaned by code: unknown pieces and extra quotes are dropped. Which
seat a quote belongs to is taken from the piece, never from the model.
"""

import json
from dataclasses import dataclass

from .gate import Gate, ModelUnavailable, json_answer, json_request
from .guard import Quote
from .index import Entry
from .prompts import MODERATOR

MAX_SEATS = 8
MAX_QUOTES_PER_SEAT = 2
MAX_SPLITS = 3

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
    },
    "required": ["quotes", "splits"],
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


def request_for(question: str, candidates: list[Entry]) -> dict:
    """The instruction part is the system text; the data part (the question
    and the pieces) is the message, so the two can be kept apart (SPEC 6)."""
    data = {"question": question, "pieces": [entry.for_model() for entry in candidates]}
    return json_request("moderator", MODERATOR, json.dumps(data, ensure_ascii=False), SCHEMA)


def _ids(value) -> tuple[str, ...]:
    return tuple(dict.fromkeys(v for v in value if isinstance(v, str))) if isinstance(value, list) else ()


def clean(answer, candidates: list[Entry]) -> Plan:
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
    return Plan(tuple(quotes), tuple(splits[:MAX_SPLITS]))


def plan(gate: Gate, question: str, candidates: list[Entry]) -> Plan:
    """Raises GateError or ModelUnavailable (reason codes only)."""
    return clean(json_answer(gate.send("moderator", request_for(question, candidates))), candidates)
