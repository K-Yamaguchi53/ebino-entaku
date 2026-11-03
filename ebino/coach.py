"""コーチとオブザーバー: two AI questions at the end of a round (SPEC 5-1, 6,
14-60).

After a round in which the student asked (answered or silent), one request
asks the model for two questions to the student in one structured output:
  - coach: from the way the school's teachers think. Its source is the
    pieces of the seats listed in EBINO_DATA_DIR/coach.tsv (columns 席ID・
    地図に出す), already masked at ingest. A seat whose 地図に出す is 0 is
    never on the map and never picked by the moderator: it is only the
    coach's source. With no coach.tsv, or one with no rows or no pieces, the
    coach's card is not asked for.
  - observer: from the view of people who run a company, hire people or do
    research at a university, as texts/observer_view.txt says. It has no
    source text and is no person.
The model reads the student's record up to this round (the questions typed
and answered, split headings, quotes shown and seats not asked yet), the AI
questions shown before this round (asked_before, so their form is not
repeated; SPEC 14-61) and the coach's pieces; never the Lab, the subjects or
a name.

Nothing the model writes reaches the screen before code checks it, the same
way as the reflection's question back (reflection.checked), and more:
  - 「」『』 must hold the record's own words; no name; no banned word
    outside them (banned_words); no lure that hides an answer inside the
    question, or a choice (LURE_FORMS, here in code); no digit outside them;
    one sentence ending in ？; at most MAX_CHARS characters.
A card that fails is not shown and nothing is put in its place; when both
fail the band is not shown. Stops are counted by reason; failed words are
never kept. When the model cannot be used the band is not shown.

The student may answer one card of a band in one line (the box opens
empty). The answer goes with that question to the next round as its input
(roundtable.run), where the seats answer as always; that round never makes a
question card by itself (SPEC 14-57), and it is not a move on the harvest
card (harvest.py).

EBINO_COACH=0 turns the band off (config.coach_on).
"""

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .gate import Gate, GateError, ModelUnavailable, json_answer, json_request
from .guard import check
from .ingest.scrub import normalize_for_match
from .prompts import COACH as COACH_PROMPT
from .reflection import _QUOTED, checked
from .texts import AI_QUESTION_BADGE, COACH_LABEL, OBSERVER_LABEL, OBSERVER_VIEW, load_text, read_table

ROLE = "coach"  # The gate's role (MODELS, EFFORT) for both cards.
COACH = "coach"
OBSERVER = "observer"
CARDS = (COACH, OBSERVER)  # The fixed order on screen, never a ranking.
LABELS = {COACH: COACH_LABEL, OBSERVER: OBSERVER_LABEL}
MAX_CHARS = 60

COACH_FILE = "coach.tsv"
COACH_COLUMNS = ("席ID", "地図に出す")

# Lures that hide an answer in the question, and choices laid out for the
# student. Checked outside 「」『』 after NFKC with spaces removed, like
# banned_words; the banned words are checked too.
LURE_FORMS = (
    "と思わない", "と思いません", "じゃない？", "じゃないか", "じゃありません",
    "ではない？", "ではないか", "ではありません", "よね", "のでは",
    "ほうがいい", "方がいい", "しよう", "ませんか", "てはどう", "ではどう", "たらどう", "だらどう",
    "それとも", "どちらに近", "どっちに近",
)
_LURES = tuple(normalize_for_match(word) for word in LURE_FORMS)
_DIGIT = re.compile(r"[0-9]")
_SENTENCE_END = re.compile(r"[。．！!？?\n]")

STATUS_SHOWN = "shown"
STATUS_STOPPED = "all_stopped"  # Both cards failed the check: no band.
STATUS_UNAVAILABLE = "unavailable"

STOP_LURE = "lure_form"
STOP_NOT_ONE_QUESTION = "not_one_question"
STOP_NUMBER = "number"
STOP_MISSING = "missing"


@dataclass(frozen=True)
class Asked:
    """One AI question as shown: the card's role and its words."""

    role: str
    text: str


@dataclass
class Band:
    status: str
    reason: str = ""  # The model's failure code, if any.
    cards: list[Asked] = field(default_factory=list)  # Shown, in CARDS order.
    asked_roles: tuple[str, ...] = ()  # The cards the model was asked for.
    stopped: Counter = field(default_factory=Counter)  # By reason code.
    answered: str = ""  # The role the student answered; "" when none.
    answer: str = ""


def load_coach(data_dir: Path, seat_ids: set[str]) -> dict[str, bool]:
    """coach.tsv as {seat ID: shown on the map}. No file: {} (no coach card).
    Errors give the line number only."""
    path = data_dir / COACH_FILE
    if not path.exists():
        return {}
    rows = read_table(path, COACH_COLUMNS)
    found: dict[str, bool] = {}
    for number, row in enumerate(rows, start=2):
        if row["席ID"] not in seat_ids or row["地図に出す"] not in ("0", "1") or row["席ID"] in found:
            raise ValueError(f"{COACH_FILE} line {number}: unknown seat or value")
        found[row["席ID"]] = row["地図に出す"] == "1"
    return found


class Record:
    """The student's record up to one round: what the model reads and what
    code checks 「」 against (the questions and answers typed, headings,
    quotes shown, and the titles of the seats in it)."""

    def __init__(self, session, round_no: int):
        seats = {seat.seat_id: seat for seat in session.library.seats}
        self.own_words: list[str] = []
        self.quote_texts: list[str] = []
        self.rounds: list[dict] = []
        for number, result in enumerate(session.rounds[:round_no], start=1):
            if not result.question:
                continue
            self.own_words.append(result.question)
            item = {"round": number, "question": result.question}
            if result.ai_question is not None:
                item["ai_question"] = result.ai_question.text  # Not the student's words.
            item["splits"] = [split.heading for split in result.splits]
            self.own_words += item["splits"]
            item["quotes"] = [{"seat": seats[q.seat_id].title, "text": q.text} for q in result.quotes]
            self.quote_texts += [q.text for q in result.quotes]
            item["silent_seats"] = [seats[s].title for s in result.silent_seats if s in seats]
            self.own_words += [seats[q.seat_id].title for q in result.quotes] + item["silent_seats"]
            self.rounds.append(item)
        # The AI questions shown before this round, in the order they were
        # shown (SPEC 14-61), so the model does not repeat their form. They
        # are the AI's words: never in own_words, so 「」 around them stops.
        self.asked_before: list[dict] = [
            {"role": card.role, "text": card.text}
            for result in session.rounds[:round_no - 1] if result.band is not None
            for card in result.band.cards]

    def holds(self, part: str) -> bool:
        if any(part in words for words in self.own_words):
            return True
        return any(check(part, text).passed for text in self.quote_texts)


def stop_reason(text: str, record: Record, gate: Gate) -> str:
    """"" when the card may be shown, else a reason code."""
    reason = checked(text, record, gate, MAX_CHARS)
    if reason:
        return reason
    text = text.strip()
    outside = _QUOTED.sub("", text)
    body = normalize_for_match(outside)
    if any(lure in body for lure in _LURES):
        return STOP_LURE
    if not text.endswith(("？", "?")) or _SENTENCE_END.search(outside.rstrip("？?")):
        return STOP_NOT_ONE_QUESTION
    if _DIGIT.search(normalize_for_match(outside)):
        return STOP_NUMBER
    return ""


def schema(roles: tuple[str, ...]) -> dict:
    return {
        "type": "object",
        "properties": {role: {"type": "string"} for role in roles},
        "required": list(roles),
        "additionalProperties": False,
    }


def request_for(record: Record, sources: list[str], roles: tuple[str, ...]) -> dict:
    """The instruction part (with the observer's view) is the system text;
    the record and the coach's pieces are the data part (SPEC 6)."""
    system = COACH_PROMPT.format(observer_view=load_text(OBSERVER_VIEW))
    data = {"cards": list(roles), "rounds": record.rounds, "asked_before": record.asked_before}
    if COACH in roles:
        data["coach_sources"] = sources
    return json_request(ROLE, system, json.dumps(data, ensure_ascii=False), schema(roles), max_tokens=4000)


def run(gate: Gate, session, round_no: int, sources: list[str]) -> Band:
    roles = tuple(role for role in CARDS if role != COACH or sources)
    record = Record(session, round_no)
    try:
        answer = json_answer(gate.send(ROLE, request_for(record, sources, roles)))
        if not isinstance(answer, dict):
            raise ModelUnavailable("bad_output")
    except (GateError, ModelUnavailable) as error:
        return Band(STATUS_UNAVAILABLE, reason=str(error), asked_roles=roles)
    band = Band(STATUS_SHOWN, asked_roles=roles)
    for role in roles:
        text = answer.get(role)
        reason = stop_reason(text, record, gate) if isinstance(text, str) else STOP_MISSING
        if reason:
            band.stopped[reason] += 1
        else:
            band.cards.append(Asked(role, text.strip()))
    if not band.cards:
        band.status = STATUS_STOPPED
    return band


def label(role: str) -> str:
    return load_text(LABELS[role])


def card_view(asked: Asked) -> dict:
    return {"role": asked.role, "label": label(asked.role), "badge": load_text(AI_QUESTION_BADGE),
            "question": asked.text}
