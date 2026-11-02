"""Run every ingested piece through the quote guard. The teacher runs this.

    python -m ebino.guard_check

Reads EBINO_DATA_DIR/ingested/utterances.json (made by python -m ebino.ingest.run)
and prints counts, reason codes and utterance IDs only, never text, so the
output is safe to paste into chat.

Two checks, both with the guard's own code:
  1. Each piece against its paragraph: the piece is real source text.
  2. Each piece as a quote naming its own ID, through Guard.screen: the ID
     leads to the piece, and the text the screen would show is the piece itself.
  3. Each sentence of each piece as a quote (SPEC 14-51): the guard's sentence
     breaks are found in the real text.
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .guard import Guard, Quote, Tally, contains, sentences
from .ingest.run import OUTPUT_DIR, OUTPUT_FILE
from .ingest.utterance import Utterance


def run(data_dir: Path) -> "Checked":
    rows = json.loads((data_dir / OUTPUT_DIR / OUTPUT_FILE).read_text(encoding="utf-8"))
    utterances = [Utterance(**row) for row in rows]

    in_paragraph = Tally()
    for utterance in utterances:
        verdict = contains(utterance.text, utterance.paragraph)
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

    # SPEC 14-51: each sentence of a piece, as the guard cuts them, must pass.
    by_sentence = Guard(utterances)
    by_sentence.screen([Quote(u.id, s) for u in utterances for s in sentences(u.text)])
    return Checked(len(utterances), in_paragraph, guard.tally, mismatched, by_sentence.tally)


@dataclass
class Checked:
    pieces: int
    in_paragraph: Tally
    screened: Tally
    mismatched: int  # Shown text that differs from the piece.
    by_sentence: Tally

    @property
    def failed(self) -> bool:
        return bool(
            self.in_paragraph.stopped
            or self.screened.stopped
            or self.screened.answers_stopped
            or self.mismatched
            or self.by_sentence.stopped
            or self.by_sentence.answers_stopped
        )

    def lines(self) -> list[str]:
        sentence = self.by_sentence
        return [
            f"pieces checked: {self.pieces}",
            "piece inside its paragraph, passed / stopped: "
            f"{self.in_paragraph.passed} / {self.in_paragraph.stopped}",
            f"piece inside its paragraph, stop reasons: {dict(self.in_paragraph.reasons)}",
            f"piece inside its paragraph, stopped utterance ids: {self.in_paragraph.stopped_ids}",
            *self.screened.lines()[:4],
            f"shown text differs from the piece: {self.mismatched}",
            "sentences one by one, passed / stopped: "
            f"{sentence.passed + sentence.answers_passed} / "
            f"{sentence.stopped + sentence.answers_stopped}",
            f"sentences one by one, stop reasons: {dict(sentence.reasons)}",
            f"sentences one by one, stopped utterance ids: {sorted(set(sentence.stopped_ids))}",
        ]


def main() -> int:
    data_dir = os.environ.get("EBINO_DATA_DIR")
    if not data_dir:
        print("EBINO_DATA_DIR is not set", file=sys.stderr)
        return 2
    try:
        checked = run(Path(data_dir))
    except FileNotFoundError:
        print("ingested utterances not found: run python -m ebino.ingest.run first", file=sys.stderr)
        return 2
    except (ValueError, TypeError) as error:  # Never print the row itself.
        print(f"ingested utterances could not be read: {type(error).__name__}", file=sys.stderr)
        return 2
    print("\n".join(checked.lines()))
    return 1 if checked.failed else 0


if __name__ == "__main__":
    sys.exit(main())
