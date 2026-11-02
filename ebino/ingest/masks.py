"""Read the human-made mask table (masks.tsv): words to hide, pages to drop.

A typo here would silently leave a name in place, so every malformed row stops
the run. Errors give line numbers only, never the value.
"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .scrub import COMPANY_MASK, PERSON_MASK, company_terms, normalize_for_match
from .utterance import IngestError

COLUMNS = ("席ID", "種類", "値")
KIND_WORD = "語"
KIND_PAGE = "ページ"
_VALUE_SEPARATOR = re.compile(r"[、,，/／;；|｜]")


@dataclass(frozen=True)
class SeatMasks:
    words: tuple[str, ...] = ()
    pages: frozenset[int] = frozenset()

    def __bool__(self) -> bool:
        return bool(self.words or self.pages)

    def pairs(self, company: str) -> list[tuple[str, str]]:
        """(term, replacement) for the seat's company and all mask words."""
        companies = company_terms(company)
        result = [(term, COMPANY_MASK) for term in companies]
        for word in self.words:
            mask = COMPANY_MASK if _is_company_word(word, companies) else PERSON_MASK
            result.append((word, mask))
        return result

    def check_pages(self, page_count: int) -> None:
        if any(page > page_count for page in self.pages):
            raise IngestError("mask_page_out_of_range")


def _is_company_word(word: str, companies: list[str]) -> bool:
    """A word that overlaps the seat's company name is a short form of it."""
    key = normalize_for_match(word)
    return any(
        key in name or name in key for name in map(normalize_for_match, companies)
    )


def load_masks(path: Path, seat_ids: set[str]) -> dict[str, SeatMasks]:
    if not path.exists():
        return {}
    words: dict[str, list[str]] = {}
    pages: dict[str, set[int]] = {}
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError("masks.tsv columns do not match")
        for row in reader:
            line = reader.line_num
            if None in row or None in row.values():
                raise ValueError(f"masks.tsv line {line}: wrong column count")
            seat_id = row["席ID"].strip()
            kind = row["種類"].strip()
            value = re.sub(r"\s+", "", row["値"])
            if seat_id not in seat_ids:
                raise ValueError(f"masks.tsv line {line}: unknown seat")
            if not value:
                raise ValueError(f"masks.tsv line {line}: empty value")
            if kind == KIND_WORD:
                if _VALUE_SEPARATOR.search(value):
                    raise ValueError(f"masks.tsv line {line}: one value per line")
                words.setdefault(seat_id, []).append(value)
            elif kind == KIND_PAGE:
                if not value.isascii() or not value.isdigit() or int(value) < 1:
                    raise ValueError(f"masks.tsv line {line}: bad page number")
                pages.setdefault(seat_id, set()).add(int(value))
            else:
                raise ValueError(f"masks.tsv line {line}: unknown kind")
    return {
        seat_id: SeatMasks(
            tuple(words.get(seat_id, ())), frozenset(pages.get(seat_id, ()))
        )
        for seat_id in {*words, *pages}
    }
