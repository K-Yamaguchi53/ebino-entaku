"""Tag every ingested piece with one kind of talk (the tagger role, SPEC 6,
14-53 A as the teacher widened it on 11/3).

    python -m ebino.talk_kinds

The kinds are the teacher's table, texts/talk_kinds.tsv (columns ID・名前・
説明); the 説明 is what the model is told. Run by hand once .env holds the API
key, like the topic tagger and by the same road: the pieces go in batches
through the gate to the tagger model (Haiku), which answers with structured
output holding only each piece's ID and one kind ID, never words. The kinds
are saved with the model name and date to EBINO_DATA_DIR/ingested/
talk_kinds.json. A piece the model did not answer for, or answered with a kind
not in the table, is not saved: it counts as 「なし」 (none) and is sent again
on the next run. Prints counts and reason codes only.
"""

import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .config import PlaceError, data_dir, load_env_file
from .gate import MODELS, Gate, GateError, ModelUnavailable, NameList, json_answer, json_request, load_allowed
from .index import load_utterances
from .ingest.masks import load_masks
from .ingest.run import OUTPUT_DIR
from .ingest.seats import load_seats
from .ingest.utterance import Utterance
from .prompts import TALK_KIND
from .saved_output import load_output, save_output
from .texts import TALK_KINDS, load_table

KINDS_FILE = "talk_kinds.json"
COLUMNS = ("ID", "名前", "説明")
NONE = "none"
BATCH = 40


@dataclass(frozen=True)
class TalkKind:
    kind_id: str
    name: str
    description: str


def load_kinds() -> list[TalkKind]:
    """The teacher's table, in its order. It must hold 「なし」 (none)."""
    kinds = [TalkKind(row["ID"], row["名前"], row["説明"]) for row in load_table(TALK_KINDS, COLUMNS)]
    ids = [kind.kind_id for kind in kinds]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{TALK_KINDS}.tsv: an ID appears twice")
    if NONE not in ids:
        raise ValueError(f"{TALK_KINDS}.tsv: no row for {NONE}")
    return kinds


def load_saved(folder: Path) -> dict[str, str]:
    path = folder / OUTPUT_DIR / KINDS_FILE
    if not path.exists():
        return {}
    return load_output(path).output


def kind_of(saved: dict[str, str], utterance_id: str, kinds: list[TalkKind]) -> str:
    """A piece's kind; none when it was never answered or its kind left the table."""
    kind = saved.get(utterance_id, NONE)
    return kind if kind in {k.kind_id for k in kinds} else NONE


def system_text(kinds: list[TalkKind]) -> str:
    table = "\n".join(f"- {kind.kind_id}：{kind.name}。{kind.description}" for kind in kinds)
    return TALK_KIND.format(kinds=table, none=NONE)


def schema(kinds: list[TalkKind]) -> dict:
    return {
        "type": "object",
        "properties": {
            "kinds": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "kind": {"type": "string", "enum": [kind.kind_id for kind in kinds]},
                    },
                    "required": ["id", "kind"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["kinds"],
        "additionalProperties": False,
    }


@dataclass
class KindReport:
    pieces: int = 0
    dropped: int = 0  # Kinds of pieces no longer ingested, taken out.
    already: int = 0  # Answered on an earlier run.
    answered: int = 0  # Answered now.
    unanswered: int = 0  # Not answered yet: they count as none.
    batches: int = 0
    by_kind: Counter = field(default_factory=Counter)  # All runs.
    failures: Counter = field(default_factory=Counter)

    def lines(self) -> list[str]:
        return [
            f"pieces: {self.pieces}",
            f"kinds of pieces no longer ingested, removed: {self.dropped}",
            f"answered before: {self.already}",
            f"answered now: {self.answered}",
            f"not answered yet (counted as {NONE}): {self.unanswered}",
            f"pieces by kind, all runs: {dict(self.by_kind)}",
            f"batches sent: {self.batches}",
            f"failed batches by reason: {dict(self.failures)}",
        ]


def kind_pieces(gate: Gate, utterances: list[Utterance], known: dict[str, str], kinds: list[TalkKind],
                report: KindReport) -> dict[str, str]:
    ids = {kind.kind_id for kind in kinds}
    current = {u.id for u in utterances}
    # A piece whose words changed has a new ID; a kind that left the table is asked again.
    saved = {i: kind for i, kind in known.items() if i in current and kind in ids}
    report.dropped = len(known) - len(saved)
    todo = [u for u in utterances if u.id not in saved]
    report.pieces = len(utterances)
    report.already = len(utterances) - len(todo)
    system, answer_schema = system_text(kinds), schema(kinds)
    for start in range(0, len(todo), BATCH):
        batch = todo[start : start + BATCH]
        content = json.dumps([{"id": u.id, "text": u.text} for u in batch], ensure_ascii=False)
        report.batches += 1
        try:
            answer = json_answer(gate.send("tagger", json_request("tagger", system, content, answer_schema)))
        except (GateError, ModelUnavailable) as error:
            report.failures[str(error)] += 1
            continue
        wanted = {u.id for u in batch}
        for item in answer.get("kinds", []) if isinstance(answer, dict) else []:
            if isinstance(item, dict) and item.get("id") in wanted and item.get("kind") in ids:
                saved[item["id"]] = item["kind"]
                report.answered += 1
                wanted.discard(item["id"])
    report.unanswered = sum(1 for u in utterances if u.id not in saved)
    report.by_kind = Counter(saved.get(u.id, NONE) for u in utterances)
    return saved


def run(folder: Path, client) -> KindReport:
    seats = load_seats(folder / "seats.tsv")
    masks = load_masks(folder / "masks.tsv", {seat.seat_id for seat in seats})
    gate = Gate(client, NameList.build(seats, masks, load_allowed(folder)))
    report = KindReport()
    saved = kind_pieces(gate, load_utterances(folder), load_saved(folder), load_kinds(), report)
    save_output(folder / OUTPUT_DIR / KINDS_FILE, MODELS["tagger"], saved)
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
    return 1 if report.unanswered or report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
