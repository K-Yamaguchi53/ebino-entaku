"""行き止まりの道案内 (直し45 段4): when no seat answered a question.

The question still becomes a question card, as before. Under it, two or
three ways to go on, made from the kinds of talk (talk_kinds.py), never by a
model: of the kinds this student has not been shown yet, the MAX_WAYS that
most pieces have (ties in the teacher's table order), shown in the table's
order. No such kind: no way is offered.

A way pressed: from every seat, in the seat table's order, the seats holding
a piece of that kind not shown to this student yet, at most closing.MAX_SEATS;
for each, the piece nearest the question (the characters in common, two by
two), cut at a sentence's end past CUT_CHARS, checked by the guard and the
name list. No model is asked; no word is made. Shown as a round of its own at
the table, without a question of the student's.
"""

from .closing import MAX_SEATS
from .guard import Guard, Quote, sentences
from .ingest.scrub import normalize_for_match

MAX_WAYS = 3
CUT_CHARS = 90


def offered(held: dict, kind_order: list[str], shown_kinds: set[str]) -> list[str]:
    """The kinds to offer: of the kinds not shown yet, the MAX_WAYS with the
    most pieces, in the table's order."""
    counts: dict[str, int] = {}
    for by_kind in held.values():
        for kind, pieces in by_kind.items():
            counts[kind] = counts.get(kind, 0) + len(pieces)
    rank = {kind: index for index, kind in enumerate(kind_order)}
    unseen = [k for k in counts if counts[k] and k not in shown_kinds]
    most = sorted(unseen, key=lambda k: (-counts[k], rank.get(k, len(rank))))[:MAX_WAYS]
    return sorted(most, key=lambda k: rank.get(k, len(rank)))


def _pairs(text: str) -> set[str]:
    body = normalize_for_match(text)
    return {body[i:i + 2] for i in range(len(body) - 1)}


def nearest(question: str, pieces: list):
    """The piece with the most two-character runs in common with the
    question; the first in reading order on a tie."""
    asked = _pairs(question)
    return max(pieces, key=lambda entry: (len(asked & _pairs(entry.text)), -pieces.index(entry)))


def cut(text: str) -> str:
    """Whole sentences from the start, past CUT_CHARS no more (one at least)."""
    out = ""
    for sentence in sentences(text) or [text]:
        if out and len(out) + len(sentence) > CUT_CHARS:
            break
        out += sentence
    return out.strip() or text


def pick(held: dict, seat_order: list[str], kind: str, seen: set[str], question: str, guard: Guard,
         names) -> list[tuple[str, str, str]]:
    """[(seat, piece ID, words)] for a way pressed, in the seats' order."""
    out = []
    for seat_id in seat_order:
        if len(out) == MAX_SEATS:
            break
        pieces = [e for e in held.get(seat_id, {}).get(kind, []) if e.utterance_id not in seen]
        if not pieces:
            continue
        entry = nearest(question, pieces)
        words = cut(entry.text)
        verdict = guard.screen([Quote(entry.utterance_id, words)])[0]
        if not verdict.passed or names.hits(verdict.shown):
            continue
        out.append((seat_id, entry.utterance_id, verdict.shown))
    return out
