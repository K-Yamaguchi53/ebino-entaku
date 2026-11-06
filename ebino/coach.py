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
never kept. When the model cannot be used, or does not answer within
TIMEOUT_SECONDS (no retry; SPEC 14-62), the band is not shown.

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

from .banned_words import BANNED_WORDS
from .gate import Gate, GateError, ModelUnavailable, json_answer, json_request
from .guard import check
from .ingest.scrub import normalize_for_match
from .prompts import COACH as COACH_PROMPT
from .prompts import ONE_COACH as ONE_COACH_PROMPT
from .reflection import (_QUOTED, STOP_BANNED, STOP_EMPTY, STOP_NAME, STOP_QUOTE, STOP_TOO_LONG, STOP_UNBALANCED,
                         checked)
from .texts import (AI_ABSTRACT_WORDS, AI_QUESTION_BADGE, AI_ROLE_SUFFIX, COACH_LABEL, OBSERVER_LABEL, OBSERVER_VIEW,
                    LISTENER_AVOID, load_lines, load_text, read_table)

ROLE = "coach"  # The gate's role (MODELS, EFFORT) for both cards.
COACH = "coach"
OBSERVER = "observer"
CARDS = (COACH, OBSERVER)  # The fixed order on screen, never a ranking.
LABELS = {COACH: COACH_LABEL, OBSERVER: OBSERVER_LABEL}
MAX_CHARS = 60
# The wait for the model, with no retry (SPEC 14-62). The app runs one
# sitting's requests one at a time, so a long band would hold back the next
# question's round; past this the band is not shown, as when the model cannot
# be used.
TIMEOUT_SECONDS = 30.0

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


# --- コーチ（AI） at one to one (直し45 段3) ---
# After a person's words came out for a question picked at one to one: one
# short question to the student about them, outward (to the person, to
# others) and inward (to the student) in turn, at most ONE_MAX with one
# person. The model reads the student's record as the band does, the words
# just shown and this one to one's questions and answers; never the Lab, the
# subjects or a name. Checked as the band's are (stop_reason, MAX_CHARS
# unchanged), and here only, by code as well: at most AI_QUESTION_MAX_CHARS,
# none of the abstract words (texts/ai_abstract_words.txt) and none of the
# words of home, money or health (texts/listener_avoid.txt) outside 「」.
# The choices to answer with are the teacher's table (texts/
# one_coach_choices.tsv), never the model's. The wait is its own, shorter
# than the band's: the next question is already on screen.
AI_QUESTION_MAX_CHARS = 30
ONE_TIMEOUT_SECONDS = 12.0
ONE_MAX = 3
OUTSIDE = "outside"
INSIDE = "inside"
STOP_ONE_TOO_LONG = "one_too_long"
STOP_ABSTRACT = "abstract_word"
STOP_AVOID = "avoid_word"
ONE_SHOWN = "shown"
ONE_STOPPED = "stopped"
ONE_UNAVAILABLE = "unavailable"
ONE_DROPPED = "dropped"  # The student picked the next question first: not shown.
# Stops by a check, apart from the model failing or being too slow.
ONE_STOPS = (STOP_EMPTY, STOP_TOO_LONG, STOP_NAME, STOP_UNBALANCED, STOP_BANNED, STOP_QUOTE, STOP_LURE, STOP_NOT_ONE_QUESTION,
             STOP_NUMBER, STOP_MISSING, STOP_ONE_TOO_LONG, STOP_ABSTRACT, STOP_AVOID)
ONE_SCHEMA = {
    "type": "object",
    "properties": {"question": {"type": "string"}},
    "required": ["question"],
    "additionalProperties": False,
}


class OneRecord(Record):
    """The band's record up to the last round, with the words just shown at
    one to one (「」 may hold one of their sentences, as a quote's) and this
    one to one's earlier answers (the student's own words)."""

    def __init__(self, session, words: list[str], answers: list[dict]):
        super().__init__(session, len(session.rounds))
        self.words = list(words)
        self.answers = [dict(answer) for answer in answers]
        self.quote_texts += self.words
        self.own_words += [answer["note"] for answer in answers if answer.get("note")]


def next_direction(asked: list[str]) -> str:
    """Outward first; then never the same way twice in a row."""
    return INSIDE if asked and asked[-1] == OUTSIDE else OUTSIDE


def one_stop_reason(text: str, record: OneRecord, gate: Gate) -> str:
    """"" when the question may be shown at one to one, else a reason code:
    the band's checks first, then this one's own."""
    reason = stop_reason(text, record, gate)
    if reason:
        return reason
    text = text.strip()
    if len(text) > AI_QUESTION_MAX_CHARS:
        return STOP_ONE_TOO_LONG
    body = normalize_for_match(_QUOTED.sub("", text))
    if any(normalize_for_match(word) in body for word in load_lines(AI_ABSTRACT_WORDS)):
        return STOP_ABSTRACT
    if any(normalize_for_match(word) in body for word in load_lines(LISTENER_AVOID)):
        return STOP_AVOID
    return ""


def one_request(record: OneRecord, direction: str) -> dict:
    system = ONE_COACH_PROMPT.format(abstract="・".join(load_lines(AI_ABSTRACT_WORDS)), banned="・".join(BANNED_WORDS))
    data = {"direction": direction, "words": record.words, "answers": record.answers, "rounds": record.rounds}
    return json_request(ROLE, system, json.dumps(data, ensure_ascii=False), ONE_SCHEMA, max_tokens=1000)


def one_send(gate: Gate, request: dict) -> tuple[str, str]:
    """(the model's question, "") or ("", the failure code). No retry; past
    ONE_TIMEOUT_SECONDS, nothing."""
    try:
        answer = json_answer(gate.send(ROLE, request, timeout=ONE_TIMEOUT_SECONDS))
    except (GateError, ModelUnavailable) as error:
        return "", str(error) or ONE_UNAVAILABLE
    text = answer.get("question") if isinstance(answer, dict) else None
    return (text, "") if isinstance(text, str) else ("", STOP_MISSING)


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
    system = COACH_PROMPT.format(observer_view=load_text(OBSERVER_VIEW), banned="・".join(BANNED_WORDS))
    data = {"cards": list(roles), "rounds": record.rounds, "asked_before": record.asked_before}
    if COACH in roles:
        data["coach_sources"] = sources
    return json_request(ROLE, system, json.dumps(data, ensure_ascii=False), schema(roles), max_tokens=4000)


def run(gate: Gate, session, round_no: int, sources: list[str]) -> Band:
    roles = roles_for(sources)
    record = Record(session, round_no)
    try:
        answer = json_answer(gate.send(ROLE, request_for(record, sources, roles), timeout=TIMEOUT_SECONDS))
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


def ai_label(role: str) -> str:
    """「コーチ（AI）」「オブザーバー（AI）」 (直し45): the name in the card's
    line (before its ｜) and texts/ai_role_suffix.txt, put together by code;
    coach_label.txt and observer_label.txt are not rewritten."""
    return label(role).split("｜")[0].strip() + load_text(AI_ROLE_SUFFIX)


def roles_for(sources: list[str]) -> tuple[str, ...]:
    """The cards asked for, in CARDS order: the coach only with its pieces."""
    return tuple(role for role in CARDS if role != COACH or sources)


def roles_shown(on: bool, sources: list[str]) -> list[str]:
    """The cards' lines (their files, the same words as on the cards) for the
    host's page (the teacher, 11/6): none with the band off."""
    return [label(role) for role in roles_for(sources)] if on else []


def card_view(asked: Asked) -> dict:
    return {"role": asked.role, "label": label(asked.role), "badge": load_text(AI_QUESTION_BADGE),
            "question": asked.text}
