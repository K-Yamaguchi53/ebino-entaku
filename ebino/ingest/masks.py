"""Read the human-made mask table (masks.tsv): words to hide, pages to drop.

A typo here would silently leave a name in place, so every malformed row stops
the run. Errors give line numbers only, never the value.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .scrub import COMPANY_MASK, PERSON_MASK, company_terms, display_name_terms
from .seats import KINDS_WITH_PERSONAL_NAME, Seat
from .utterance import IngestError

COLUMNS = ("席ID", "種類", "値")
KIND_WORD = "語"
KIND_COMPANY = "社名"
KIND_PAGE = "ページ"
# A person checked the work and found no names in its text (SPEC 14-45).
# The value is empty. It counts as "has rows" but hides nothing.
KIND_CONFIRMED = "確認済み"
_VALUE_SEPARATOR = re.compile(r"[、,，/／;；|｜]")


@dataclass(frozen=True)
class SeatMasks:
    words: tuple[str, ...] = ()
    pages: frozenset[int] = frozenset()
    companies: tuple[str, ...] = ()
    confirmed: bool = False

    def __bool__(self) -> bool:
        """True when a person has looked at this seat (any row in masks.tsv)."""
        return bool(self.words or self.pages or self.companies or self.confirmed)

    def pairs(self, seat: Seat) -> list[tuple[str, str]]:
        """(term, replacement) from the seat table and masks.tsv.

        Every term here also goes into the final leak check.
        """
        result: list[tuple[str, str]] = []
        for company in (seat.company, *self.companies):
            result.extend((term, COMPANY_MASK) for term in company_terms(company))
        if seat.kind in KINDS_WITH_PERSONAL_NAME:
            result.extend(
                (term, PERSON_MASK) for term in display_name_terms(seat.display_name)
            )
        result.extend((word, PERSON_MASK) for word in self.words)
        return result

    def check_pages(self, page_count: int) -> None:
        if any(page > page_count for page in self.pages):
            raise IngestError("mask_page_out_of_range")


def load_masks(path: Path, seat_ids: set[str]) -> dict[str, SeatMasks]:
    if not path.exists():
        return {}
    words: dict[str, list[str]] = {}
    companies: dict[str, list[str]] = {}
    pages: dict[str, set[int]] = {}
    confirmed: set[str] = set()
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError("masks.tsv columns do not match")
        for row in reader:
            line = reader.line_num
            if row.get("値") is None and (row.get("種類") or "").strip() == KIND_CONFIRMED:
                row["値"] = ""  # 「確認済み」 may be written without the empty third column.
            if None in row or None in row.values():
                raise ValueError(f"masks.tsv line {line}: wrong column count")
            seat_id = row["席ID"].strip()
            kind = row["種類"].strip()
            value = re.sub(r"\s+", "", row["値"])
            if seat_id not in seat_ids:
                raise ValueError(f"masks.tsv line {line}: unknown seat")
            if kind == KIND_CONFIRMED:
                if value:
                    raise ValueError(f"masks.tsv line {line}: confirmed takes no value")
                confirmed.add(seat_id)
                continue
            if not value:
                raise ValueError(f"masks.tsv line {line}: empty value")
            if kind in (KIND_WORD, KIND_COMPANY):
                if _VALUE_SEPARATOR.search(value):
                    raise ValueError(f"masks.tsv line {line}: one value per line")
                target = words if kind == KIND_WORD else companies
                target.setdefault(seat_id, []).append(value)
            elif kind == KIND_PAGE:
                if not value.isascii() or not value.isdigit() or int(value) < 1:
                    raise ValueError(f"masks.tsv line {line}: bad page number")
                pages.setdefault(seat_id, set()).add(int(value))
            else:
                raise ValueError(f"masks.tsv line {line}: unknown kind")
    return {
        seat_id: SeatMasks(
            words=tuple(words.get(seat_id, ())),
            pages=frozenset(pages.get(seat_id, ())),
            companies=tuple(companies.get(seat_id, ())),
            confirmed=seat_id in confirmed,
        )
        for seat_id in {*words, *companies, *pages, *confirmed}
    }
