"""Run every ingested piece through the quote guard. The teacher runs this.

    python -m ebino.guard_check

Reads EBINO_DATA_DIR/ingested/utterances.json (made by python -m ebino.ingest.run)
and prints counts, reason codes and utterance IDs only, never text, so the
output is safe to paste into chat.

Two checks, both with the guard's own code:
  1. Each piece against its paragraph: the piece is real source text.
  2. Each piece as a quote naming its own ID, through Guard.screen: the ID
     leads to the piece, and the text the screen would show is the piece itself.
"""

import json
import os
import sys
from pathlib import Path

from .guard import Guard, Quote, Tally, check
from .ingest.run import OUTPUT_DIR, OUTPUT_FILE
from .ingest.utterance import Utterance


def run(data_dir: Path) -> tuple[int, Tally, Tally, int]:
    """(pieces, piece-in-paragraph tally, screen tally, shown-text mismatches)."""
    rows = json.loads((data_dir / OUTPUT_DIR / OUTPUT_FILE).read_text(encoding="utf-8"))
    utterances = [Utterance(**row) for row in rows]

    in_paragraph = Tally()
    for utterance in utterances:
        verdict = check(utterance.text, utterance.paragraph)
        if verdict.passed:
            in_paragraph.passed += 1
        else:
            in_paragraph.stopped += 1
            in_paragraph.stopped_ids.append(utterance.id)
            in_paragraph.reasons[verdict.reason] += 1

    guard = Guard(utterances)
    mismatched = 0
    for utterance, verdict in zip(
        utterances, guard.screen([Quote(u.id, u.text) for u in utterances])
    ):
        if verdict.passed and verdict.shown != utterance.text.strip():
            mismatched += 1
    return len(utterances), in_paragraph, guard.tally, mismatched


def main() -> int:
    data_dir = os.environ.get("EBINO_DATA_DIR")
    if not data_dir:
        print("EBINO_DATA_DIR is not set", file=sys.stderr)
        return 2
    try:
        pieces, in_paragraph, screened, mismatched = run(Path(data_dir))
    except FileNotFoundError:
        print("ingested utterances not found: run python -m ebino.ingest.run first", file=sys.stderr)
        return 2
    except (ValueError, TypeError) as error:  # Never print the row itself.
        print(f"ingested utterances could not be read: {type(error).__name__}", file=sys.stderr)
        return 2
    print(f"pieces checked: {pieces}")
    print(
        "piece inside its paragraph, passed / stopped: "
        f"{in_paragraph.passed} / {in_paragraph.stopped}"
    )
    print(f"piece inside its paragraph, stop reasons: {dict(in_paragraph.reasons)}")
    print(f"piece inside its paragraph, stopped utterance ids: {in_paragraph.stopped_ids}")
    print("\n".join(screened.lines()[:4]))
    print(f"shown text differs from the piece: {mismatched}")
    failed = in_paragraph.stopped or screened.stopped or screened.answers_stopped or mismatched
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
