"""The reflection sheet (ふりかえりの1枚, SPEC 5-2, 6).

The student writes first: did the first question change (three choices,
never judged by a model) and the question they hold now. Then the moderator
(the reflection role, Opus 5.5) reads the student's whole record once and
returns one question back, pointing at one piece of the record, and at most
three next moves in fixed directions. The student answers in one line or
declines, picks a move or none or writes their own, may rewrite the
question, and picks one seat to go and meet.

Nothing a model writes reaches the screen before code checks it (SPEC 5-2,
14-14), like the guard does for quotes:
  - every 「」 or 『』 in it must hold the record's own words: a part of a
    question, card, split heading or the title of a seat in the materials,
    or a sentence-bounded part of a quote shown (the guard's rule).
    『A／B』 is checked part by part.
  - no name from the gate's list anywhere, and no word from banned_words
    outside 「」『』: those are the moderator's own words. Inside them code
    has already matched the record's words, so an adult's quote with a
    word like 頑張って does not stop the text.
  - a next move points at a material of its own direction, is not a
    question (no ？), and only one move per direction is kept, in the fixed
    order of DIRECTIONS, never the model's order.
A question back that fails becomes the fixed sentence in texts/; a move that
fails is not shown. Reason codes are kept, never the failed words.
"""

import json
import re
from collections import Counter
from dataclasses import dataclass, field

from .banned_words import banned_in
from .gate import Gate, GateError, ModelUnavailable, json_answer, json_request
from .guard import check
from .prompts import REFLECTION
from .texts import ASK_BACK_FALLBACK, load_text

CHANGED_CHOICES = {"changed": "変わった", "a_little": "少し", "same": "変わらない"}
DIRECTIONS = ("left_split", "silent_seat", "question_shift")
DIRECTION_LABELS = {
    "left_split": "置いてきた割れ目",
    "silent_seat": "黙った席",
    "question_shift": "問いの動き",
}
CHOSE_NONE = "none"  # 「どれも選ばない」
CHOSE_OWN = "own"  # 「自分で書く」
MAX_ASK_BACK_CHARS = 160  # Room for one whole sentence of a quote.
MAX_MOVE_CHARS = 80
MAX_LINE_CHARS = 120  # Each line the student writes (SPEC 5-2: one line).

STOP_NAME = "name"
STOP_BANNED = "banned_word"
STOP_QUOTE = "quote_not_in_record"
STOP_UNBALANCED = "unbalanced_quote_marks"
STOP_TOO_LONG = "too_long"
STOP_EMPTY = "empty"
STOP_QUESTION = "move_is_a_question"
STOP_MATERIAL = "wrong_material"
STOP_DIRECTION = "unknown_direction"
STOP_SAME_DIRECTION = "same_direction_twice"

SCHEMA = {
    "type": "object",
    "properties": {
        "ask_back": {
            "type": "object",
            "properties": {"material_id": {"type": "string"}, "text": {"type": "string"}},
            "required": ["material_id", "text"],
            "additionalProperties": False,
        },
        "next_moves": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": list(DIRECTIONS)},
                    "material_id": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["direction", "material_id", "text"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["ask_back", "next_moves"],
    "additionalProperties": False,
}

_QUOTED = re.compile(r"「([^「」]*)」|『([^『』]*)』")
_PART_BREAK = re.compile(r"[／/]")


@dataclass(frozen=True)
class Material:
    material_id: str
    kind: str  # question, now_question, split, quote, silent_seat, card
    text: str = ""
    for_model: dict = field(default_factory=dict, compare=False)
    left: bool = False  # Splits: not pressed by the student.


@dataclass(frozen=True)
class Move:
    direction: str
    material_id: str
    text: str


@dataclass
class Reflection:
    changed: str
    now_question: str
    ask_back: str = ""
    ask_back_material: str = ""
    ask_back_fallback: str = ""  # Why the fixed sentence was used: a code.
    moves: list[Move] = field(default_factory=list)
    moves_stopped: Counter = field(default_factory=Counter)
    unavailable: str = ""  # The model's failure code, if any.
    answer: str = ""
    declined: bool = False
    answered: bool = False
    chosen: str = ""  # A direction, CHOSE_NONE or CHOSE_OWN.
    own_move: str = ""
    rewrite: str = ""
    meet_seat: str = ""
    meet_reason: str = ""
    finished: bool = False
    # The harvest card (SPEC 5-3): codes of the moves shown in ①, and the use
    # picked in ② (a force number as text, or harvest.CHOSE_NO_USE).
    harvest_moves: list[str] = field(default_factory=list)
    harvest_use: str = ""


class Record:
    """The student's record, as the moderator reads it and code checks it."""

    def __init__(self, session):
        self.materials: list[Material] = []
        # Questions, cards, headings and the titles of seats in the materials.
        self.own_words: list[str] = []
        self.quote_texts: list[str] = []  # Quotes shown: sentence-bounded only.
        names = session.gate.names
        seats = {seat.seat_id: seat for seat in session.library.seats}
        entries = {quote.utterance_id: quote for r in session.rounds for quote in r.quotes}
        number = 0
        for index, result in enumerate(session.rounds, start=1):
            if result.question:
                number += 1
                self._add(Material(f"Q{number}", "question", result.question,
                                   {"id": f"Q{number}", "kind": "question", "text": result.question}))
            for split_index, split in enumerate(result.splits):
                left = (index, split_index) not in session.pressed_splits
                material_id = f"P{index}-{split_index + 1}"
                sides = {side: [entries[i].text for i in getattr(split, side) if i in entries]
                         for side in ("side_a", "side_b")}
                self._add(Material(material_id, "split", split.heading, {
                    "id": material_id, "kind": "split", "heading": split.heading, "pressed": not left, **sides,
                }, left=left))
        marked = set(session.marks.values())
        for quote in entries.values():
            material_id = f"U:{quote.utterance_id}"
            self.quote_texts.append(quote.text)
            self.own_words.append(seats[quote.seat_id].title)
            self.materials.append(Material(material_id, "quote", quote.text, {
                "id": material_id, "kind": "quote", "seat": seats[quote.seat_id].for_model(),
                "text": quote.text, "marked": quote.utterance_id in marked,
            }))
        for seat_id in session.silent_seats():
            if seat_id in session.met_seats():
                continue
            self.own_words.append(seats[seat_id].title)
            self.materials.append(Material(f"S:{seat_id}", "silent_seat", "", {
                "id": f"S:{seat_id}", "kind": "silent_seat", "seat": seats[seat_id].for_model(),
            }))
        for number, card in enumerate(session.cards, start=1):
            # A card the student wrote with a name in it stays out, so it
            # cannot stop the whole reflection at the gate.
            if names.hits(card.text):
                continue
            self._add(Material(f"C{number}", "card", card.text,
                               {"id": f"C{number}", "kind": "card", "text": card.text}))

    def _add(self, material: Material) -> None:
        self.materials.append(material)
        self.own_words.append(material.text)

    def by_id(self) -> dict[str, Material]:
        return {material.material_id: material for material in self.materials}

    def holds(self, part: str) -> bool:
        if any(part in words for words in self.own_words):
            return True
        return any(check(part, text).passed for text in self.quote_texts)


def checked(text: str, record: Record, gate: Gate, limit: int) -> str:
    """"" when the text may be shown, else a STOP_* code."""
    if not text.strip():
        return STOP_EMPTY
    if len(text) > limit:
        return STOP_TOO_LONG
    if gate.names.hits(text):  # The whole text, quotes too.
        return STOP_NAME
    outside = _QUOTED.sub("", text)
    if any(mark in outside for mark in "「」『』"):
        return STOP_UNBALANCED
    if banned_in(outside):  # The moderator's own words only.
        return STOP_BANNED
    for match in _QUOTED.finditer(text):
        for part in _PART_BREAK.split(match.group(1) or match.group(2) or ""):
            if part.strip() and not record.holds(part.strip()):
                return STOP_QUOTE
    return ""


def _fits(direction: str, material: Material | None) -> bool:
    if material is None:
        return False
    if direction == "left_split":
        return material.kind == "split" and material.left
    if direction == "silent_seat":
        return material.kind == "silent_seat"
    return material.kind in ("question", "now_question")


def request_for(session, record: Record, changed: str, now_question: str) -> dict:
    first = next((r.question for r in session.rounds if r.question), "")
    data = {
        "first_question": first,
        "changed": CHANGED_CHOICES[changed],
        "now_question": now_question,
        "materials": [material.for_model for material in record.materials],
    }
    return json_request("reflection", REFLECTION, json.dumps(data, ensure_ascii=False), SCHEMA)


def begin(gate: Gate, session, changed: str, now_question: str) -> Reflection:
    reflection = Reflection(changed, now_question)
    record = Record(session)
    record._add(Material("N", "now_question", now_question,
                         {"id": "N", "kind": "now_question", "text": now_question}))
    materials = record.by_id()
    try:
        answer = json_answer(gate.send("reflection", request_for(session, record, changed, now_question)))
        if not isinstance(answer, dict):
            raise ModelUnavailable("bad_output")
    except (GateError, ModelUnavailable) as error:
        reflection.unavailable = str(error)
        answer = {}

    ask = answer.get("ask_back") if isinstance(answer.get("ask_back"), dict) else {}
    text = ask.get("text") if isinstance(ask.get("text"), str) else ""
    reason = checked(text, record, gate, MAX_ASK_BACK_CHARS) if answer else reflection.unavailable
    if not reason and ask.get("material_id") not in materials:
        reason = STOP_MATERIAL
    if reason:
        reflection.ask_back, reflection.ask_back_fallback = load_text(ASK_BACK_FALLBACK), reason
    else:
        reflection.ask_back, reflection.ask_back_material = text.strip(), ask["material_id"]

    kept: dict[str, Move] = {}
    for move in answer.get("next_moves") or []:
        if not isinstance(move, dict):
            continue
        direction, material_id = move.get("direction"), move.get("material_id")
        text = move.get("text") if isinstance(move.get("text"), str) else ""
        reason = ""
        if direction not in DIRECTIONS:
            reason = STOP_DIRECTION
        elif direction in kept:
            reason = STOP_SAME_DIRECTION
        elif not _fits(direction, materials.get(material_id)):
            reason = STOP_MATERIAL
        elif "？" in text or "?" in text:
            reason = STOP_QUESTION
        else:
            reason = checked(text, record, gate, MAX_MOVE_CHARS)
        if reason:
            reflection.moves_stopped[reason] += 1
        else:
            kept[direction] = Move(direction, material_id, text.strip())
    reflection.moves = [kept[d] for d in DIRECTIONS if d in kept]
    return reflection
