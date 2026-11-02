"""Poster purposes as sample questions (SPEC 5-1 hint 3, 8, 14-42, 14-44).

A senior's poster names the question they set out to answer. The round table
shows it, with its source, as a sample of a real question a senior asked.
This is part of the core and is never dropped (SPEC 8).

Which section is the purpose is decided by code at ingest
(poster_pdf.purpose_examples: 目的, else 研究仮説 and the like, else テーマ設定の
理由). No model picks, writes or rewords a sample: what is shown is the
stored piece itself, and it goes through the guard's check like every quote
on the screen. Samples are not counted in the guard's tally of round quotes.
"""

import random
from dataclasses import dataclass

from .guard import check
from .ingest.poster_pdf import purpose_examples
from .ingest.seats import Seat
from .ingest.utterance import Utterance

SHOWN_AT_ONCE = 3


@dataclass(frozen=True)
class PurposeSample:
    seat_id: str
    utterance_ids: tuple[str, ...]
    texts: tuple[str, ...]  # The pieces' own words, in poster order.


def samples(utterances: list[Utterance], seats: list[Seat]) -> list[PurposeSample]:
    found = []
    for seat in seats:
        if seat.kind != "poster":
            continue
        pieces = purpose_examples([u for u in utterances if u.seat_id == seat.seat_id])
        kept = [(u.id, check(u.text, u.text).shown) for u in pieces]
        kept = [(i, text) for i, text in kept if text]
        if kept:
            found.append(PurposeSample(seat.seat_id, tuple(i for i, _ in kept), tuple(t for _, t in kept)))
    return found


class PurposeShelf:
    """Hands out samples a few at a time, each once before any comes back.
    The order is shuffled per session, never ranked by a model."""

    def __init__(self, found: list[PurposeSample], rng: random.Random | None = None):
        self._order = list(found)
        (rng or random.Random()).shuffle(self._order)
        self._next = 0

    def next(self, n: int = SHOWN_AT_ONCE) -> list[PurposeSample]:
        if not self._order:
            return []
        n = min(n, len(self._order))
        picked = [self._order[(self._next + k) % len(self._order)] for k in range(n)]
        self._next = (self._next + n) % len(self._order)
        return picked
