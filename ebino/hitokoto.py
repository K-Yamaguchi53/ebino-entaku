"""帰る前に、ひとこと (直し38): the reflection, as the teacher's sample shows it.

In place of the reflection sheet (reflection.py, still there when
EBINO_REFLECT=old), the student, at the end of the sitting:

  1. 今日の地図: sees the first question over a small map of up to three
     people of the day (the words marked, then one to one, then the bubbles
     opened; the latest first in each), a dashed line between two of them
     when a split's two sides each hold one, and under it each person's
     words. The listener (a fast model) picks a short part of each card,
     which lights up where code finds it, word for word. The student presses
     one, or the card itself, or 「おまかせ」 (picked by code).
  2. 帰る前に、ひとこと: the listener asks two questions, one per direction
     and in this order: reaction (what came first on reading the words),
     self (does that person's talk fit them too). Only how it is said is the
     model's. Two 「わからない」 in a row turn to the ladder of questions to
     pick from, made from the record and texts/ only: the split's two
     people's words, the people on the map, and a line with a blank.
  3. the teacher's scale question (0 to 15, the first question's doubt as 10)
     and the next question, by the answer (the third direction, 前).
  4. what to keep: a way to keep in mind, a lesson near the talk (③ when
     there was one), and a seat to hear more from (②).
  5. 今日、光ったところ: the light model picks one of the student's own
     sentences and ties it to one of the school's six forces, in two short
     sentences; code decides when it cannot be used.
  6. one sheet to print, with no name on it.

Nothing a model writes reaches the screen before code checks it, as
reflection.checked does (「」 holds the record's or the student's own words,
no name, no banned word outside 「」), and more: no lure (coach.LURE_FORMS),
no sentence starting 「あなたは」, one question ending in ？ with at most one
question word, no word of texts/listener_avoid.txt. A question that fails is
the fixed question of its direction (texts/hitokoto.tsv); reason codes are
kept, never the failed words. What the student writes here goes through the
name check first: with a name in it, it is neither kept nor sent.
"""

import json
import re
import time
from dataclasses import dataclass, field

from . import harvest, subjects
from .banned_words import BANNED_WORDS
from .coach import LURE_FORMS
from .gate import Gate, GateError, ModelUnavailable, json_answer, json_request
from .ingest.scrub import normalize_for_match
from .prompts import LISTENER as LISTENER_PROMPT
from .reflection import _QUOTED, Record, checked
from .seat_label import KIND_LABELS
from .texts import load_lines, load_table

LISTENER = "listener"  # The gate's roles (MODELS, EFFORT).
LISTENER_SECONDS = 8.0  # The wait, with no retry; past it, the fixed question.

MAX_PEOPLE = 3
MAX_PART = 16  # A lit part of a card.
MAX_QUESTION = 60
MAX_LINE = 120  # Each line the student writes.
MAX_LISTENER = 2  # Questions the listener puts: one per direction.
MAX_LADDER = 3  # Questions of the ladder.
MAX_QUESTIONS = 6  # The listener's, the ladder's and the scale's, at most.
SCALE_FIRST, SCALE_TOP = 10, 15

REACTION, SELF = "reaction", "self"
DIRECTIONS = (REACTION, SELF)  # In this order, each once. 前 is the scale's.
QUESTION_WORDS = ("なぜ", "どう", "何")


# Where the sample puts the points (its viewBox is 600 x 330): the split's
# two, then the third. The grey points are other seats met, as decoration.
SLOTS = ((200, 160), (400, 210), (300, 120))
GREY_SLOTS = ((150, 120), (420, 110), (470, 160), (260, 250), (360, 260), (120, 230), (330, 90))

WHY_MARK = "mark"  # How a person came onto the map.
WHY_ONE = "one"
WHY_BUBBLE = "bubble"

# Stops (reason codes, never the words).
STOP_LURE = "lure_form"
STOP_YOU_ARE = "you_are"
STOP_NOT_ONE_QUESTION = "not_one_question"
STOP_QUESTION_WORDS = "question_words"
STOP_AVOID = "avoid_word"
STOP_PRAISE = "praise"
STOP_MISSING = "missing"
STOP_FORCE = "unknown_force"
STOP_FORCE_NOT_NAMED = "force_not_named"
STOP_QUOTE_NOT_WRITTEN = "quote_not_written"
STUDENT_AVOID = "student_avoid"  # The student wrote of home, money or health: not dug into.
NO_PEOPLE = "no_people"
NOTHING_WRITTEN = "nothing_written"

# The stages, in order.
MAP, TALK, LADDER_TWO, LADDER_THREE, FILL, SCALE, FORWARD, WAY, SUBJECT, SUBJECT_NOTE, MEET, USE, END, \
    LIT, SHEET = ("map", "talk", "ladder_two", "ladder_three", "fill", "scale", "forward", "way", "subject",
                  "subject_note", "meet", "use", "end", "lit", "sheet")
TALKING = (MAP, TALK, LADDER_TWO, LADDER_THREE, FILL, SCALE, FORWARD, WAY, SUBJECT, SUBJECT_NOTE, MEET, USE, END)
SUBJECT_ANSWERS = ("yes", "no", "unsure")  # あった・なかった・わからない

TEXTS = "hitokoto"
FORCE_TEXTS = "hitokoto_forces"
BLANK_TEXTS = "hitokoto_blank"
AVOID_TEXTS = "listener_avoid"
TEXT_IDS = (
    "name", "step_map", "step_talk", "step_light", "step_sheet", "first_label", "map_lead", "map_split",
    "map_counts", "omakase", "omakase_said", "go", "stop", "dont_know", "thinking", "summing", "who_ai",
    "who_teacher", "who_me", "send", "placeholder", "again", "ask_reaction", "ask_self", "ladder_two",
    "ladder_two_me", "ladder_three", "ladder_fill", "ladder_fill_line", "fill_ok", "fill_skip", "scale_q",
    "scale_low", "scale_first", "scale_ok", "scale_me", "scale_down", "scale_same", "scale_up", "skip", "way_q",
    "way_ok", "way_none", "way_example", "subject_q", "subject_yes", "subject_no", "subject_unsure",
    "subject_which", "subject_example", "meet_pick", "meet_met", "meet_others", "meet_ok", "meet_none", "light_title", "light_scale",
    "light_lead", "light_lead_chosen", "light_chosen_who", "light_deep_tail", "light_step", "now_label",
    "to_sheet", "sheet_title", "sheet_now", "sheet_same", "sheet_story", "sheet_step", "story_people",
    "story_word", "story_chosen", "story_wrote", "story_scale", "story_more", "story_way", "story_subject",
    "story_subject_note", "print", "print_note", "print_side", "deep_word", "deep_more", "deep_way",
    "deep_need", "deep_chosen", "now_after",
)
FILL_BLANK = "［　　］"  # In ladder_fill_line: where the student writes.

_SENTENCE_END = re.compile(r"[。．！!\n]")
_TRAIL = re.compile(r"[。．、，,.！!？?…\s　]+$")
_PLACE = re.compile(r"\{(\*?)(\w+)\}")


def words() -> dict[str, str]:
    """{ID: 文字} from texts/hitokoto.tsv, every row there."""
    rows = {row["ID"]: row["文字"] for row in load_table(TEXTS, ("ID", "文字"))}
    if set(rows) != set(TEXT_IDS):
        raise ValueError(f"{TEXTS}.tsv must have the rows {', '.join(TEXT_IDS)}")
    return rows


def screen_words() -> dict:
    """What the screen is sent once, with the forces' names."""
    return {"words": words(), "kinds": KIND_LABELS}


def is_blank(text: str) -> bool:
    """「わからない」「ない」 and the like (texts/hitokoto_blank.txt), alone."""
    body = _TRAIL.sub("", (text or "").strip())
    return not body or body in load_lines(BLANK_TEXTS)


def has_avoid(text: str) -> bool:
    body = normalize_for_match(text or "")
    return any(normalize_for_match(word) in body for word in load_lines(AVOID_TEXTS))


def fill(template: str, **values) -> str:
    return _PLACE.sub(lambda m: str(values[m.group(2)]), template)


@dataclass
class Person:
    seat_id: str
    title: str
    kind: str
    utterance_id: str
    text: str  # The words as recorded (the guard's), never the spoken words.
    said: bool  # The person's own words (「」) or an article's (its note).
    note: str
    why: str  # WHY_MARK, WHY_ONE or WHY_BUBBLE.
    x: int = 0
    y: int = 0

    def view(self) -> dict:
        return {"seat_id": self.seat_id, "title": self.title, "kind": self.kind,
                "kind_label": KIND_LABELS.get(self.kind, ""), "text": self.text, "said": self.said,
                "note": self.note, "x": self.x, "y": self.y}


@dataclass
class Asked:
    """One question put to the student, as shown."""

    step: str  # A direction, ladder_two, ladder_three, fill, scale, forward.
    text: str
    by: str  # "listener" (passed the checks), "fixed" (texts/), "teacher".
    fallback: str = ""  # Why the listener's question was not used: a code.
    seconds: float = 0.0


@dataclass
class Hitokoto:
    first_question: str
    people: list[Person] = field(default_factory=list)
    split: dict | None = None  # {"heading", "a", "b"}: two people's indexes.
    grey: list[tuple[int, int]] = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    stage: str = MAP
    parts: dict[int, str] = field(default_factory=dict)  # Person index -> lit part.
    parts_asked: bool = False
    parts_reason: str = ""
    parts_seconds: float = 0.0
    chosen: int | None = None
    chosen_part: str = ""
    omakase: bool = False
    asked: list[Asked] = field(default_factory=list)
    answers: list[dict] = field(default_factory=list)  # {"step", "text"} or {"step", "dont_know": True}.
    written: list[dict] = field(default_factory=list)  # The student's own words: {"step", "text"}.
    listener_asked: int = 0
    blank_run: int = 0
    ladder_shown: int = 0
    ladder_two: int | None = None  # The split's side picked (person index).
    ladder_three: int | None = None
    fill_text: str = ""
    scale: int | None = None
    forward: str = ""
    way: str = ""
    subject: str = ""  # A SUBJECT_ANSWERS key.
    subject_note: str = ""
    subject_pick: object = None  # subjects.Pick
    meet_seat: str = ""
    meet_use: str = ""
    now_question: str = ""

    # --- what the screen gets ---

    def map_view(self) -> dict:
        return {"first_question": self.first_question, "people": [p.view() for p in self.people],
                "split": self.split, "grey": [list(xy) for xy in self.grey], "counts": self.counts,
                "stage": self.stage}

    def question_count(self) -> int:
        return sum(1 for a in self.asked if a.step != "forward")


# --- who is on the map ---

def pick_people(session, opened: list[str]) -> list[Person]:
    """Up to MAX_PEOPLE: the words marked, then one to one, then the bubbles
    opened; within each, the one read last first. Each with one card of
    words: the mark, else a bubble opened, else (one to one only) the first
    piece of the item asked last there."""
    shown = {q.utterance_id: q for r in session.rounds for q in r.quotes}
    opened = [uid for uid in dict.fromkeys(opened) if uid in shown]
    marks = [(seat_id, uid) for seat_id, uid in session.marks.items() if uid in shown]
    order: list[tuple[str, str]] = []
    order += [(seat_id, WHY_MARK) for seat_id, _ in reversed(marks)]
    order += [(seat_id, WHY_ONE) for seat_id in reversed(list(session._one_seats()))]
    order += [(shown[uid].seat_id, WHY_BUBBLE) for uid in reversed(opened)]
    marked = dict(marks)
    last_opened = {}
    for uid in opened:
        last_opened[shown[uid].seat_id] = uid
    seats = {seat.seat_id: seat for seat in session.library.seats}
    people: list[Person] = []
    for seat_id, why in order:
        if len(people) >= MAX_PEOPLE or seat_id not in seats or any(p.seat_id == seat_id for p in people):
            continue
        uid = marked.get(seat_id) or last_opened.get(seat_id)
        if uid:
            utterance = session._utterances[uid]
            text = shown[uid].text
        else:
            utterance = _one_piece(session, seat_id)
            if utterance is None:
                continue
            uid, text = utterance.id, utterance.text
        seat = seats[seat_id]
        people.append(Person(seat_id, seat.title, seat.kind, uid, text, not utterance.note, utterance.note, why))
    return people


def _one_piece(session, seat_id: str):
    """The first piece of the item asked last at one to one, or None."""
    asked = session.one_asked.get(seat_id) or []
    if not asked:
        return None
    found = {item: pieces for item, _, pieces in session.one_items(seat_id)}
    pieces = found.get(asked[-1]) or []
    return pieces[0] if pieces else None


def find_split(session, people: list[Person], sheet_heading) -> dict | None:
    """The first split whose two sides each hold a person on the map: one
    from each side (the one picked first), and its heading."""
    shown = {q.utterance_id: q.seat_id for r in session.rounds for q in r.quotes}
    for result in session.rounds:
        for split in result.splits:
            sides = []
            for side in (split.side_a, split.side_b):
                seats = {shown[uid] for uid in side if uid in shown}
                sides.append(next((i for i, p in enumerate(people) if p.seat_id in seats), None))
            if None not in sides and sides[0] != sides[1]:
                return {"heading": sheet_heading(split.heading), "a": sides[0], "b": sides[1]}
    return None


def place(people: list[Person], split: dict | None) -> list[Person]:
    """The sample's places: the split's two at the first two, the dashed line between."""
    order = list(range(len(people)))
    if split:
        order = [split["a"], split["b"]] + [i for i in order if i not in (split["a"], split["b"])]
    for slot, index in zip(SLOTS, order):
        people[index].x, people[index].y = slot
    return people


def begin(session, opened: list[str], sheet_heading) -> Hitokoto:
    first = next((r.question for r in session.rounds if r.question), "")
    talk = Hitokoto(first)
    talk.people = pick_people(session, opened)
    talk.split = find_split(session, talk.people, sheet_heading)
    place(talk.people, talk.split)
    on_map = {p.seat_id for p in talk.people}
    met = [s for s in dict.fromkeys([*session.met_seats(), *session._one_seats()]) if s not in on_map]
    talk.grey = list(GREY_SLOTS[:len(met)])
    talk.counts = {"people": len(on_map) + len(met), "marks": len(session.marks), "cards": len(session.cards)}
    if not talk.people:  # No one to read: the first question, then the scale.
        talk.stage = SCALE
        talk.asked.append(Asked("scale", words()["scale_q"], "teacher"))
    return talk


# --- the listener ---

def _send(gate: Gate, role: str, system: str, data: dict, schema: dict, seconds: float, max_tokens: int):
    """(answer, reason, seconds waited): the answer is None when the model
    could not be used or did not answer in time."""
    started = time.monotonic()
    try:
        answer = json_answer(gate.send(role, json_request(role, system, json.dumps(data, ensure_ascii=False),
                                                          schema, max_tokens=max_tokens), timeout=seconds))
        reason = "" if isinstance(answer, dict) else "bad_output"
    except (GateError, ModelUnavailable) as error:
        answer, reason = None, str(error)
    return (answer if not reason else None), reason, round(time.monotonic() - started, 1)


def listener_system() -> str:
    return LISTENER_PROMPT.format(part_limit=MAX_PART, question_limit=MAX_QUESTION, banned="・".join(BANNED_WORDS))


PARTS_SCHEMA = {
    "type": "object",
    "properties": {"parts": {"type": "array", "items": {
        "type": "object", "properties": {"id": {"type": "string"}, "part": {"type": "string"}},
        "required": ["id", "part"], "additionalProperties": False}}},
    "required": ["parts"], "additionalProperties": False,
}


def ask_parts(gate: Gate, talk: Hitokoto) -> None:
    """Once: a short part of each card, lit where it is in the card word for word."""
    if talk.parts_asked or not talk.people:
        return
    talk.parts_asked = True
    data = {"task": "keywords", "first_question": talk.first_question,
            "cards": [{"id": str(i + 1), "text": p.text} for i, p in enumerate(talk.people)]}
    answer, reason, talk.parts_seconds = _send(gate, LISTENER, listener_system(), data, PARTS_SCHEMA,
                                               LISTENER_SECONDS, 1000)
    talk.parts_reason = reason
    for item in (answer or {}).get("parts") or []:
        if not isinstance(item, dict) or not isinstance(item.get("part"), str):
            continue
        part = item["part"].strip()
        index = int(item["id"]) - 1 if str(item.get("id", "")).isdigit() else -1
        if not 0 <= index < len(talk.people) or index in talk.parts:
            continue
        if part and len(part) <= MAX_PART and part in talk.people[index].text and not gate.names.hits(part):
            talk.parts[index] = part
    if answer is not None and not talk.parts:
        talk.parts_reason = "no_part_found"
