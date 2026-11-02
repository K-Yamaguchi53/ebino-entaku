"""Read the human-made seat table (seats.tsv)."""

import csv
from dataclasses import dataclass
from pathlib import Path

KINDS = ("adult", "poster", "cross", "outsider_teacher")
# Seats whose display name is a family name; students show only their grade.
KINDS_WITH_PERSONAL_NAME = ("adult", "outsider_teacher")
COLUMNS = (
    "席ID", "種類", "肩書き", "会社名", "表示名", "地区", "年度", "元ファイル", "使う表",
    "越境の線の先",
)


@dataclass(frozen=True)
class Seat:
    seat_id: str
    kind: str
    title: str
    company: str
    display_name: str
    district: str
    year: str  # Kept in the table, never shown (SPEC 14-34).
    source_file: str
    table_no: int | None
    is_crossing_target: bool

    def for_model(self) -> dict:
        """The only seat fields a model may see: no company, name or year."""
        return {
            "seat_id": self.seat_id,
            "kind": self.kind,
            "title": self.title,
            "district": self.district,
        }


def load_seats(path: Path) -> list[Seat]:
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError("seats.tsv columns do not match")
        seats = []
        for row in reader:
            if row["種類"] not in KINDS:
                raise ValueError(f"seats.tsv line {reader.line_num}: unknown kind")
            table = (row["使う表"] or "").strip()
            seats.append(
                Seat(
                    seat_id=row["席ID"].strip(),
                    kind=row["種類"],
                    title=row["肩書き"].strip(),
                    company=(row["会社名"] or "").strip(),
                    display_name=(row["表示名"] or "").strip(),
                    district=(row["地区"] or "").strip(),
                    year=(row["年度"] or "").strip(),
                    source_file=row["元ファイル"].strip(),
                    table_no=int(table) if table else None,
                    is_crossing_target=(row["越境の線の先"] or "").strip() == "1",
                )
            )
    return seats
