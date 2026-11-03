"""Long purpose samples, summarized once after ingest (the teacher's call on
11/3: many seniors' purposes run over 120 characters, some with PDF debris).

    python -m ebino.purpose_summary

Run by hand once after ingest, like talk_kinds. Only samples longer than
MAX_SAMPLE_CHARS are sent, one by one, through the gate to the editor model
(Sonnet), which answers with structured output holding the summary only. A
summary is saved only when it passes the same check as the reflection's
question back (reflection.checked: no name from the gate's list, no banned
word outside 「」『』, every 「」『』 holding the sample's own words, and the
length, here MAX_SAMPLE_CHARS). Saved to EBINO_DATA_DIR/ingested/
purpose_summaries.json with the model name and date, output being seat ID ->
summary, so the teacher can read and correct each one by hand; "sources"
keeps the piece IDs each summary was made from. Only what is missing is made:
a seat whose sample changed on re-ingest (new piece IDs) is made again, and a
summary stopped by the check or not answered is not saved and is asked again
on the next run. Prints counts, reason codes and seat IDs only.

When the app starts, the file is read and every summary checked again (the
teacher may have edited it): a long sample with no summary, a summary that
fails the check, or one made from other pieces is not shown.
"""

import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path

from .config import PlaceError, data_dir, load_env_file
from .gate import MODELS, Gate, GateError, ModelUnavailable, NameList, json_answer, json_request, load_names
from .guard import check
from .index import load_utterances
from .ingest.run import OUTPUT_DIR
from .ingest.seats import load_seats
from .prompts import PURPOSE_SUMMARY
from .purpose import PurposeSample, samples
from .reflection import checked
from .saved_output import load_output, save_output

SUMMARY_FILE = "purpose_summaries.json"
MAX_SAMPLE_CHARS = 120
ROLE = "editor"  # Sonnet.
SOURCES = "sources"
STOP_OTHER_PIECES = "made_from_other_pieces"

SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
    "additionalProperties": False,
}


def sample_text(sample: PurposeSample) -> str:
    """The sample as the screen shows it: its pieces joined."""
    return "".join(sample.texts)


def is_long(sample: PurposeSample) -> bool:
    return len(sample_text(sample)) > MAX_SAMPLE_CHARS


class _Original:
    """The sample's own words, for the check of 「」『』 in a summary."""

    def __init__(self, text: str):
        self.text = text

    def holds(self, part: str) -> bool:
        return part in self.text or check(part, self.text).passed


@dataclass(frozen=True)
class _Names:
    names: NameList


def stopped(summary: str, sample: PurposeSample, names: NameList) -> str:
    """"" when the summary may be shown, else a reason code."""
    return checked(summary, _Original(sample_text(sample)), _Names(names), MAX_SAMPLE_CHARS)


@dataclass
class Saved:
    summaries: dict[str, str] = field(default_factory=dict)  # seat ID -> summary
    sources: dict[str, list[str]] = field(default_factory=dict)  # seat ID -> piece IDs


def load_saved(folder: Path) -> Saved:
    path = folder / OUTPUT_DIR / SUMMARY_FILE
    if not path.exists():
        return Saved()
    output = load_output(path).output
    sources = json.loads(path.read_text(encoding="utf-8")).get(SOURCES, {})
    return Saved({k: v for k, v in output.items() if isinstance(v, str)} if isinstance(output, dict) else {},
                 sources if isinstance(sources, dict) else {})


def _made_from(saved: Saved, sample: PurposeSample) -> bool:
    return saved.sources.get(sample.seat_id) == list(sample.utterance_ids)


def shown_samples(found: list[PurposeSample], saved: Saved, names: NameList) -> list[PurposeSample]:
    """The samples the screen may show: a short one as it is; a long one as
    its saved summary, marked, when the summary was made from these pieces
    and passes the check; otherwise not at all."""
    shown = []
    for sample in found:
        if not is_long(sample):
            shown.append(sample)
            continue
        summary = saved.summaries.get(sample.seat_id, "").strip()
        if summary and _made_from(saved, sample) and not stopped(summary, sample, names):
            shown.append(replace(sample, texts=(summary,), summarized=True))
    return shown


@dataclass
class SummaryReport:
    samples: int = 0
    long: int = 0
    already: int = 0  # Made on an earlier run, from the same pieces.
    made: int = 0  # Made now and passed the check.
    stopped: Counter = field(default_factory=Counter)  # By reason code.
    failures: Counter = field(default_factory=Counter)  # The model or the gate, by reason code.
    missing: list[str] = field(default_factory=list)  # Seat IDs with no summary yet.

    def lines(self) -> list[str]:
        return [
            f"samples: {self.samples}",
            f"longer than {MAX_SAMPLE_CHARS} characters: {self.long}",
            f"summarized before: {self.already}",
            f"summarized now: {self.made}",
            f"stopped by the check, by reason: {dict(self.stopped)}",
            f"failed requests, by reason: {dict(self.failures)}",
            f"seats with no summary yet (not shown): {len(self.missing)} {self.missing}",
        ]


def request_for(sample: PurposeSample) -> dict:
    content = json.dumps({"text": sample_text(sample)}, ensure_ascii=False)
    return json_request(ROLE, PURPOSE_SUMMARY.format(limit=MAX_SAMPLE_CHARS), content, SCHEMA)


def summarize(gate: Gate, found: list[PurposeSample], saved: Saved, report: SummaryReport) -> Saved:
    long = [sample for sample in found if is_long(sample)]
    report.samples, report.long = len(found), len(long)
    kept = Saved()
    for sample in long:
        summary = saved.summaries.get(sample.seat_id, "").strip()
        if summary and _made_from(saved, sample):
            kept.summaries[sample.seat_id] = saved.summaries[sample.seat_id]
            kept.sources[sample.seat_id] = list(sample.utterance_ids)
            report.already += 1
            continue
        try:
            answer = json_answer(gate.send(ROLE, request_for(sample)))
        except (GateError, ModelUnavailable) as error:
            report.failures[str(error)] += 1
            report.missing.append(sample.seat_id)
            continue
        summary = answer.get("summary", "") if isinstance(answer, dict) else ""
        summary = summary.strip() if isinstance(summary, str) else ""
        reason = stopped(summary, sample, gate.names)
        if reason:
            report.stopped[reason] += 1
            report.missing.append(sample.seat_id)
            continue
        kept.summaries[sample.seat_id] = summary
        kept.sources[sample.seat_id] = list(sample.utterance_ids)
        report.made += 1
    return kept


def run(folder: Path, client) -> SummaryReport:
    seats = load_seats(folder / "seats.tsv")
    gate = Gate(client, load_names(folder, seats))
    report = SummaryReport()
    found = samples(load_utterances(folder), seats)
    kept = summarize(gate, found, load_saved(folder), report)
    save_output(folder / OUTPUT_DIR / SUMMARY_FILE, MODELS[ROLE], kept.summaries, extra={SOURCES: kept.sources})
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
    return 1 if report.missing else 0


if __name__ == "__main__":
    sys.exit(main())
