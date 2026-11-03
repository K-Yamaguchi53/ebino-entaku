"""「司会が○○に聞いてみる」 (SPEC 14-53 B; the teacher's call on 11/3: the
moderator is there, so it should help the talk go further).

At the end of a round in which seats spoke (before the last word), a card
offers one question to one seat. Nothing runs by itself: only when the
student presses the card is the seat asked, and only once per round.

The question has one of two forms only, built by code from a fixed sentence
in texts/ (the teacher's wording) and the record's own words; no model
writes it, and no new topic is made:
  - why: the quote the student marked in this round, asked back to its own
    seat (「なぜ」);
  - other_side: a split's first quote, passed to a seat on the other side
    (「『〇〇』と言った人がいる。あなたは？」).
A marked quote comes first: it is the student's own pick. The quote is the
first sentence of the words shown, whole. Before the card is shown, the
question goes through the same check as the reflection's question back
(SPEC 5-2): every 「」『』 must hold the record's own words, no name from the
gate's list anywhere, no banned word outside 「」『』. If it fails, no card.

The answer is looked for only among that seat's pieces this student has not
been shown, fragments left out (closing.is_fragment): the librarian gathers
the pieces near the question, the moderator picks the one that answers it by
ID (or none), and the copy goes through the guard. Its line says
whose words they are, by the piece's voice: the person's own words get
「この人が、別の所で話したこと」, an article's or a senior employee's words
another line, so an article never reads as the person speaking. When nothing
is found, 「まだ答えていない」; a press on it makes a question card to that
seat holding the question (SPEC 2-2).
"""

import json
import re
from dataclasses import dataclass

from . import closing, librarian, reflection
from .gate import GateError, ModelUnavailable, json_answer, json_request
from .prompts import ASK_SEAT
from .texts import ASK_OTHER_SIDE, ASK_WHY, load_text

FORM_WHY = "why"
FORM_OTHER_SIDE = "other_side"
TEMPLATES = {FORM_WHY: ASK_WHY, FORM_OTHER_SIDE: ASK_OTHER_SIDE}
MAX_CHARS = reflection.MAX_ASK_BACK_CHARS

ANSWERED = "answered"
NOT_FOUND = "not_found"
UNAVAILABLE = "unavailable"

_FIRST_SENTENCE = re.compile(r"[^。！？!?]+[。！？!?]*")


@dataclass(frozen=True)
class Plan:
    form: str
    seat_id: str
    quote_id: str  # The shown quote the question holds.
    text: str


@dataclass
class AskSeat:
    form: str
    seat_id: str
    quote_id: str
    text: str  # The question; kept in the sitting for the card, not in the record.
    status: str = ""
    answer_id: str = ""
    answer_text: str = ""
    reason: str = ""  # Reason code when unavailable.
    guard_stopped: int = 0
    card_id: str = ""


def first_sentence(text: str) -> str:
    match = _FIRST_SENTENCE.search(text)
    return match.group(0).strip() if match else text.strip()


def question_for(form: str, quote_text: str) -> str:
    return load_text(TEMPLATES[form]).format(quote=first_sentence(quote_text))


def plan(session, round_no: int) -> Plan | None:
    """The card for a round, or None: no marked quote and no split, or the
    question fails the check."""
    result = session.rounds[round_no - 1]
    shown = {quote.utterance_id: quote for quote in result.quotes}
    tries = []
    marked = next((q for q in result.quotes if session.marks.get(q.seat_id) == q.utterance_id), None)
    if marked is not None:
        tries.append((FORM_WHY, marked.seat_id, marked))
    for split in result.splits:
        quote = shown.get(split.side_a[0])
        other = next((shown[i].seat_id for i in split.side_b
                      if i in shown and quote and shown[i].seat_id != quote.seat_id), None)
        if quote and other:
            tries.append((FORM_OTHER_SIDE, other, quote))
            break
    record = reflection.Record(session)
    for form, seat_id, quote in tries:
        text = question_for(form, quote.text)
        if not reflection.checked(text, record, session.gate, MAX_CHARS):
            return Plan(form, seat_id, quote.utterance_id, text)
    return None


def pick_request(question: str, pieces: list) -> dict:
    data = {"question": question, "pieces": [entry.for_model() for entry in pieces]}
    return json_request("moderator", ASK_SEAT, json.dumps(data, ensure_ascii=False), closing.SCHEMA)


def run(session, card: Plan) -> AskSeat:
    """The librarian gathers the seat's pieces near the question (widely, so
    some do not answer it); the moderator picks the one piece that answers
    it, by ID, copying its words (structured output), or none; the guard
    checks the copy. No pick, or a copy the guard stops: 「まだ答えていない」."""
    asked = AskSeat(card.form, card.seat_id, card.quote_id, card.text)
    seen = session.seen_ids()
    entries = [e for e in session.library.entries if e.seat_id == card.seat_id and e.utterance_id not in seen
               and not closing.is_fragment(e.text)]
    by_id = {entry.utterance_id: entry for entry in entries}
    if not entries:
        asked.status = NOT_FOUND
        return asked
    try:
        found = librarian.find(session.gate, entries, card.text)
        gathered = [by_id[i] for i in dict.fromkeys(found.utterance_ids) if i in by_id]
        if not gathered:
            asked.status = NOT_FOUND
            return asked
        answer = json_answer(session.gate.send("moderator", pick_request(card.text, gathered)))
        quotes, _ = closing.clean(answer, gathered)
    except (GateError, ModelUnavailable) as error:
        asked.status, asked.reason = UNAVAILABLE, str(error)
        return asked
    asked.status = NOT_FOUND
    if quotes:
        verdict = session.guard.screen(quotes[:1])[0]
        if verdict.passed:
            asked.status, asked.answer_id, asked.answer_text = ANSWERED, verdict.quote.utterance_id, verdict.shown
        else:
            asked.guard_stopped += 1
    return asked
