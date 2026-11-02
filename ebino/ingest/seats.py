"""Read the human-made seat table (seats.tsv)."""

import csv
from dataclasses import dataclass
from pathlib import Path

KINDS = ("adult", "poster", "cross", "outsider_teacher")
COLUMNS = (
    "席ID", "種類", "肩書き", "会社名", "地区", "年度", "元ファイル", "使う表", "越境の線の先",
)


@dataclass(frozen=True)
class Seat:
    seat_id: str
    kind: str
    title: str
    company: str
    district: str
    year: str
    source_file: str
    table_no: int | None
    is_crossing_target: bool


def load_seats(path: Path) -> list[Seat]:
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError("seats.tsv columns do not match")
        seats = []
        for row in reader:
            if row["種類"] not in KINDS:
                raise ValueError(f"unknown seat kind for seat {row['席ID']}")
            table = (row["使う表"] or "").strip()
            seats.append(
                Seat(
                    seat_id=row["席ID"].strip(),
                    kind=row["種類"],
                    title=row["肩書き"].strip(),
                    company=(row["会社名"] or "").strip(),
                    district=(row["地区"] or "").strip(),
                    year=(row["年度"] or "").strip(),
                    source_file=row["元ファイル"].strip(),
                    table_no=int(table) if table else None,
                    is_crossing_target=(row["越境の線の先"] or "").strip() == "1",
                )
            )
    return seats
