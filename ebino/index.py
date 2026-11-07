"""The index the librarian searches: one entry per ingested piece (SPEC 6).

An entry is tagged 人・場所・話題. 人 is the seat (its ID, kind and title),
場所 is the seat's district, both from the seat table; the year is kept out
(SPEC 14-34). 話題 comes from the tagger. Company and display name are never
here, so nothing built from the index can carry them (SPEC 14-3, 14-39).
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .ingest.run import OUTPUT_DIR, OUTPUT_FILE
from .ingest.seats import Seat
from .ingest.utterance import Utterance, mended
from .saved_output import load_output

TOPICS_FILE = "topics.json"


@dataclass(frozen=True)
class Entry:
    utterance_id: str
    seat_id: str
    kind: str
    title: str
    district: str
    voice: str
    section: str
    topics: tuple[str, ...]
    text: str

    def for_model(self) -> dict:
        return asdict(self) | {"topics": list(self.topics)}


def load_utterances(data_dir: Path) -> list[Utterance]:
    rows = json.loads((data_dir / OUTPUT_DIR / OUTPUT_FILE).read_text(encoding="utf-8"))
    # 直し54f: mended here, so the round table, one to one and every tool read
    # the same words, without ingesting again. The ID stays as ingested.
    return [mended(Utterance(**row)) for row in rows]


def load_topics(data_dir: Path) -> dict[str, list[str]]:
    path = data_dir / OUTPUT_DIR / TOPICS_FILE
    if not path.exists():
        return {}
    return load_output(path).output


def build_index(
    utterances: list[Utterance], seats: list[Seat], topics: dict[str, list[str]]
) -> list[Entry]:
    """Pieces of seats missing from the table are left out."""
    by_id = {seat.seat_id: seat for seat in seats}
    entries = []
    for utterance in utterances:
        seat = by_id.get(utterance.seat_id)
        if seat is None:
            continue
        entries.append(
            Entry(
                utterance_id=utterance.id,
                seat_id=seat.seat_id,
                kind=seat.kind,
                title=seat.title,
                district=seat.district,
                voice=utterance.voice,
                section=utterance.section,
                topics=tuple(topics.get(utterance.id, ())),
                text=utterance.text,
            )
        )
    return entries
