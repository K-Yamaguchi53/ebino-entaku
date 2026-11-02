"""Seat labels for the screen. Company and display names are added here only,
from the seat table, and only on the in-school screen (SPEC 14-3, 14-39, 14-40).
"""

import os
import re
from dataclasses import dataclass

from .ingest.seats import Seat

SHOW_COMPANY_ENV = "EBINO_SHOW_COMPANY"
_LEGAL_FORMS = (
    "株式会社", "有限会社", "合同会社", "合資会社", "合名会社", "社会福祉法人", "医療法人",
    "一般社団法人", "一般財団法人", "公益社団法人", "公益財団法人", "特定非営利活動法人",
    "NPO法人", "学校法人", "農事組合法人", "（株）", "(株)", "（有）", "(有)", "㈱", "㈲",
)
_FORM = "|".join(re.escape(form) for form in _LEGAL_FORMS)
_HEAD_OR_TAIL = re.compile(rf"^(?:{_FORM})[\s　]*|[\s　]*(?:{_FORM})$")


# The four kinds of seat, with the names on the explainer sheet (SPEC 14-6,
# 14-41). The screen lists seats in this order.
KIND_LABELS = {
    "adult": "地域で働く大人",
    "poster": "探究をした先輩",
    "cross": "県外・海外に出た人",
    "outsider_teacher": "外から来た大人・先生",
}


@dataclass(frozen=True)
class SeatLabel:
    title: str  # First line, large.
    detail: str  # Second line, small. Empty off the in-school screen.


def show_private_labels() -> bool:
    """Anything but exactly "1" keeps the public label, so a typo stays safe."""
    return os.environ.get(SHOW_COMPANY_ENV, "").strip() == "1"


def short_company(company: str) -> str:
    """For the label only; the seat table keeps the full name."""
    return _HEAD_OR_TAIL.sub("", company.strip()).strip()


def seat_label(seat: Seat, show_private: bool | None = None) -> SeatLabel:
    if show_private is None:
        show_private = show_private_labels()
    if not show_private:
        return SeatLabel(seat.title, "")
    parts = [short_company(seat.company), seat.display_name]
    return SeatLabel(seat.title, "　".join(part for part in parts if part))
