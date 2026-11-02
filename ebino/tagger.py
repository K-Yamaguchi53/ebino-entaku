"""Tag every ingested piece with topics (the tagger role, SPEC 6).

    python -m ebino.tagger

Run by hand once .env holds the API key (SPEC 14-51). Reads the ingested
pieces from EBINO_DATA_DIR, sends them in batches through the gate to the
tagger model, and saves the topics with the model name and date to
EBINO_DATA_DIR/ingested/topics.json. Pieces already tagged are skipped, so a
second run fills only the gaps. Prints counts and reason codes only.
"""

import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .config import PlaceError, data_dir, load_env_file
from .gate import MODELS, Gate, GateError, ModelUnavailable, NameList, json_answer, json_request, load_allowed
from .index import TOPICS_FILE, load_topics, load_utterances
from .ingest.masks import load_masks
from .ingest.run import OUTPUT_DIR
from .ingest.seats import load_seats
from .ingest.utterance import Utterance
from .prompts import TAGGER
from .saved_output import save_output

BATCH = 40
MAX_TOPICS = 3
MAX_TOPIC_CHARS = 12
SCHEMA = {
    "type": "object",
    "properties": {
        "tags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "topics": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "topics"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["tags"],
    "additionalProperties": False,
}


@dataclass
class TagReport:
    """A piece is in one of three states (SPEC 14-52): it has topics, the
    model answered with no topics (a right answer for a short piece, so it is
    not sent again), or it has not been answered yet."""

    pieces: int = 0
    already: int = 0  # Answered on an earlier run, with or without topics.
    tagged: int = 0  # Answered now with at least one topic.
    empty: int = 0  # Answered now with no topics.
    with_topics: int = 0  # All runs.
    empty_total: int = 0  # All runs.
    untagged: int = 0  # Not answered yet.
    batches: int = 0
    failures: Counter = field(default_factory=Counter)

    def lines(self) -> list[str]:
        return [
            f"pieces: {self.pieces}",
            f"answered before: {self.already}",
            f"answered now with topics: {self.tagged}",
            f"answered now with no topics: {self.empty}",
            f"all runs: with topics {self.with_topics}  no topics {self.empty_total}",
            f"not answered yet: {self.untagged}",
            f"batches sent: {self.batches}",
            f"failed batches by reason: {dict(self.failures)}",
        ]


def _clean(topics: list) -> list[str]:
    kept = []
    for topic in topics:
        if isinstance(topic, str) and 0 < len(topic.strip()) <= MAX_TOPIC_CHARS:
            if topic.strip() not in kept:
                kept.append(topic.strip())
    return kept[:MAX_TOPICS]


def tag_pieces(
    gate: Gate, utterances: list[Utterance], known: dict[str, list[str]], report: TagReport
) -> dict[str, list[str]]:
    topics = dict(known)
    todo = [u for u in utterances if u.id not in topics]
    report.pieces = len(utterances)
    report.already = len(utterances) - len(todo)
    for start in range(0, len(todo), BATCH):
        batch = todo[start : start + BATCH]
        content = json.dumps([{"id": u.id, "text": u.text} for u in batch], ensure_ascii=False)
        report.batches += 1
        try:
            answer = json_answer(gate.send("tagger", json_request("tagger", TAGGER, content, SCHEMA)))
        except (GateError, ModelUnavailable) as error:
            report.failures[str(error)] += 1
            continue
        wanted = {u.id for u in batch}
        for tag in answer.get("tags", []) if isinstance(answer, dict) else []:
            if isinstance(tag, dict) and tag.get("id") in wanted:
                kept = _clean(tag.get("topics") or [])
                topics[tag["id"]] = kept
                if kept:
                    report.tagged += 1
                else:
                    report.empty += 1
                wanted.discard(tag["id"])
    answered = [topics[u.id] for u in utterances if u.id in topics]
    report.with_topics = sum(bool(kept) for kept in answered)
    report.empty_total = len(answered) - report.with_topics
    report.untagged = len(utterances) - len(answered)
    return topics


def run(folder: Path, client) -> TagReport:
    seats = load_seats(folder / "seats.tsv")
    masks = load_masks(folder / "masks.tsv", {seat.seat_id for seat in seats})
    gate = Gate(client, NameList.build(seats, masks, load_allowed(folder)))
    report = TagReport()
    topics = tag_pieces(gate, load_utterances(folder), load_topics(folder), report)
    save_output(folder / OUTPUT_DIR / TOPICS_FILE, MODELS["tagger"], topics)
    return report


def main() -> int:
    load_env_file()
    try:
        folder = data_dir()
    except PlaceError as error:
        print(error, file=sys.stderr)
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set (put it in .env)", file=sys.stderr)
        return 2
    import anthropic

    try:
        report = run(folder, anthropic.Anthropic())
    except FileNotFoundError:
        print("ingested pieces not found: run python -m ebino.ingest.run first", file=sys.stderr)
        return 2
    print("\n".join(report.lines()))
    return 1 if report.untagged or report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
