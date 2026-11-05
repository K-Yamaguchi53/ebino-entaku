"""Batch ingest. The teacher runs this by hand against the real data.

    python -m ebino.ingest.run

Output is counts and reason codes only, so it is safe to paste into chat.
File names never appear: they can contain a person's name.
"""

import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .. import one_to_one
from .article_docx import ingest_article
from .masks import SeatMasks, load_masks
from .pdf_chars import PdfTextStats, leftover_supplement_chars
from .poster_pdf import (
    PURPOSE_FROM_HYPOTHESIS,
    PURPOSE_FROM_THEME_REASON,
    ROLES,
    ingest_poster,
    pdf_page_count,
    purpose_examples,
    purpose_rank,
)
from . import poster_text
from .seats import Seat, load_seats
from .slides_pdf import ingest_slides
from .utterance import IngestError, Utterance, VOICE_ARTICLE

OUTPUT_DIR = "ingested"
OUTPUT_FILE = "utterances.json"
# Scraps left when 「」 cut an article into pieces (SPEC 14-50).
SHORT_ARTICLE_CHARS = 6


@dataclass
class Report:
    seats: int = 0
    ingested_by_kind: Counter = field(default_factory=Counter)
    utterances_by_voice: Counter = field(default_factory=Counter)
    failures: Counter = field(default_factory=Counter)
    failed_seats: list[str] = field(default_factory=list)
    skipped_slide_seats: int = 0
    unsplit_names: int = 0
    single_char_names: int = 0
    dropped_rows: int = 0
    wrapped_lines_joined: int = 0
    poster_sections_by_role: Counter = field(default_factory=Counter)
    posters_purpose_from_hypothesis: int = 0
    posters_purpose_from_theme_reason: int = 0
    multi_page_works_read: int = 0
    multi_page_works_skipped: int = 0
    leftover_radical_chars: int = 0
    pdf_text: PdfTextStats = field(default_factory=PdfTextStats)
    short_article_pieces: int = 0
    short_article_seats: int = 0
    copied_posters: int = 0  # Read from a hand-made text copy (poster_text).
    # One to one's tables (直し34-2): counts only, no seat, name or words.
    ask_tables: dict = field(default_factory=dict)

    def lines(self) -> list[str]:
        lines = [
            f"seats: {self.seats}",
            f"ingested by kind: {dict(self.ingested_by_kind)}",
            f"utterances by voice: {dict(self.utterances_by_voice)}",
            f"skipped slide seats (no rows in masks.tsv): {self.skipped_slide_seats}",
            f"failures: {dict(self.failures)}",
            f"failed seat ids: {self.failed_seats}",
            f"names without separator (check by hand): {self.unsplit_names}",
            f"one-character name parts (check by hand): {self.single_char_names}",
            f"table rows dropped: {self.dropped_rows}",
            f"article lines joined back into paragraphs: {self.wrapped_lines_joined}",
            f"copied posters (text) read: {self.copied_posters}",
            f"poster sections by role: {dict(self.poster_sections_by_role)}",
            f"posters whose purpose comes from 仮説/経緯: {self.posters_purpose_from_hypothesis}",
            "posters whose purpose comes from テーマ設定の理由: "
            f"{self.posters_purpose_from_theme_reason}",
            "multi-page inquiry works (read / skipped, no rows in masks.tsv): "
            f"{self.multi_page_works_read} / {self.multi_page_works_skipped}",
            "radical-supplement chars left (not in the table): "
            f"{self.leftover_radical_chars}",
            f"control chars removed from PDF text: {self.pdf_text.control_chars_removed}",
            f"article-voice pieces of {SHORT_ARTICLE_CHARS} chars or less (seats): "
            f"{self.short_article_pieces} ({self.short_article_seats})",
        ]
        if self.ask_tables:
            t = self.ask_tables
            lines += [
                f"one to one, seats with pages only: {t['pages_only_seats']} (pages {t['pages']}), "
                f"pages by axis (the teacher's table): {t['pages_by_axis']}",
                f"one to one, ranking questions: {t['ranking_questions']} of {t['ranking_seats']}, "
                f"none by reason: {t['ranking_without']}",
                f"one to one, tables written to fill (the teacher's kept): {t['written']}",
            ]
        return lines


def _count_poster(utterances: list[Utterance], report: Report) -> list[Utterance]:
    """Sections by role and where the purpose sample came from, for a one-page
    poster read from a PDF or copied to text."""
    for utterance in utterances:
        role = utterance.section if utterance.section in ROLES else "(other)"
        report.poster_sections_by_role[role] += 1
    examples = purpose_examples(utterances)
    if examples:
        rank = purpose_rank(examples[0].section, examples[0].heading)
        report.posters_purpose_from_hypothesis += rank == PURPOSE_FROM_HYPOTHESIS
        report.posters_purpose_from_theme_reason += rank == PURPOSE_FROM_THEME_REASON
    return utterances


def _ingest_seat(
    seat: Seat, data_dir: Path, masks: SeatMasks, report: Report
) -> list[Utterance] | None:
    path = data_dir / seat.source_file
    suffix = path.suffix.lower()
    if suffix == ".docx" and seat.kind in ("adult", "outsider_teacher"):
        utterances, stats = ingest_article(path, seat, masks)
        report.unsplit_names += stats.unsplit_name
        report.single_char_names += stats.single_char_name
        report.dropped_rows += stats.dropped_rows
        report.wrapped_lines_joined += stats.wrapped_lines_joined
        return utterances
    if suffix == ".pdf" and seat.kind == "poster":
        if pdf_page_count(path) > 1:
            # Talk slides and multi-page posters: names are scattered, so they are
            # read like slides and only after a person wrote rows (SPEC 14-45).
            if not masks:
                report.multi_page_works_skipped += 1
                raise IngestError("poster_not_one_page")
            utterances = ingest_slides(path, seat, masks, report.pdf_text)
            report.multi_page_works_read += 1
            return utterances
        return _count_poster(ingest_poster(path, seat, masks, report.pdf_text), report)
    if suffix == poster_text.SUFFIX and seat.kind == "poster":
        utterances = _count_poster(poster_text.ingest_text_poster(path, seat, masks), report)
        report.copied_posters += 1
        return utterances
    if suffix == ".pdf" and seat.kind in ("cross", "outsider_teacher"):
        if not masks:
            report.skipped_slide_seats += 1
            return None
        return ingest_slides(path, seat, masks, report.pdf_text)
    raise IngestError("kind_and_file_type_mismatch")


def run(data_dir: Path) -> Report:
    report = Report()
    seats = load_seats(data_dir / "seats.tsv")
    report.seats = len(seats)
    masks = load_masks(data_dir / "masks.tsv", {seat.seat_id for seat in seats})
    utterances: list[Utterance] = []
    for seat in seats:
        try:
            result = _ingest_seat(
                seat, data_dir, masks.get(seat.seat_id, SeatMasks()), report
            )
        except IngestError as error:
            report.failures[str(error)] += 1
            report.failed_seats.append(seat.seat_id)
            continue
        except Exception as error:  # A parser message could quote document text.
            report.failures[type(error).__name__] += 1
            report.failed_seats.append(seat.seat_id)
            continue
        if result is None:
            continue
        report.ingested_by_kind[seat.kind] += 1
        short = sum(
            u.voice == VOICE_ARTICLE and len(u.text) <= SHORT_ARTICLE_CHARS for u in result
        )
        report.short_article_pieces += short
        report.short_article_seats += short > 0
        for utterance in result:
            report.utterances_by_voice[utterance.voice] += 1
            report.leftover_radical_chars += leftover_supplement_chars(
                utterance.text + utterance.heading
            )
        utterances.extend(result)

    output = data_dir / OUTPUT_DIR
    output.mkdir(exist_ok=True)
    (output / OUTPUT_FILE).write_text(
        json.dumps([u.to_dict() for u in utterances], ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    # One to one's tables to fill, when not there; never over the teacher's (直し34-2).
    report.ask_tables = one_to_one.write_tables(output, utterances, {seat.seat_id: seat.kind for seat in seats})
    return report


def main() -> int:
    data_dir = os.environ.get("EBINO_DATA_DIR")
    if not data_dir:
        print("EBINO_DATA_DIR is not set", file=sys.stderr)
        return 2
    try:
        report = run(Path(data_dir))
    except ValueError as error:  # Table errors give line numbers, never values.
        print(error, file=sys.stderr)
        return 2
    print("\n".join(report.lines()))
    return 1 if report.failed_seats else 0


if __name__ == "__main__":
    sys.exit(main())
