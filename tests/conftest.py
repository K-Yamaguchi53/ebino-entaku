"""Fixtures. Every name, company, phone number and address here is invented."""

import pytest
from docx import Document

from ebino.ingest.seats import COLUMNS, Seat

PERSON = "山川 太郎"
INTERVIEWER = "海野 花子"
COMPANY = "有限会社はるかぜ理容"
PHONE = "0984-00-0000"
ADDRESS = "えびの市大字架空町123番地"

ROWS = [
    ("番号", "項目", "記事", "字数"),
    ("1", "名前", PERSON, ""),
    ("2", "会社名・役職", f"{COMPANY} 代表", ""),
    ("3", "キャッチコピー", "髪を切る時間は、話す時間。", ""),
    ("4-1", "プロフィール", "やまかわ たろう 50歳", ""),
    ("4-2", "プロフィール", "県外で修業して、えびのに戻った。", ""),
    ("5", "仕事の内容", "はるかぜ理容で、髪を切り、顔をそる。", ""),
    ("6-1", "所在地", ADDRESS, ""),
    ("6-2", "電話番号", PHONE, ""),
    ("6-3", "ホームページ", "https://example.invalid/", ""),
    ("7", "本文タイトル", "鏡の前の話", ""),
    (
        "8",
        "本文",
        "山川さんは休みの日も店に立つ。「太郎と呼ばれるのが好きです」と笑う。"
        f"お店は{ADDRESS}にあり、電話は{PHONE}です。取材では海野さんが聞いた。",
        "400",
    ),
    ("9", "ランキング", "1位 朝の光", ""),
    ("10", "取材者名", INTERVIEWER, ""),
]


def make_seat(**overrides) -> Seat:
    values = dict(
        seat_id="S01",
        kind="adult",
        title="理容師",
        company=COMPANY,
        district="架空地区",
        year="2026",
        source_file="article01.docx",
        table_no=None,
        is_crossing_target=False,
    )
    values.update(overrides)
    return Seat(**values)


def add_table(document, rows):
    table = document.add_table(rows=len(rows), cols=len(rows[0]))
    for row, values in zip(table.rows, rows):
        for cell, value in zip(row.cells, values):
            cell.text = value
    return table


def write_article(path, rows=None):
    document = Document()
    document.add_paragraph(f"表の外の段落 {PERSON}")
    add_table(document, rows or ROWS)
    document.save(path)
    return path


def write_seats(path, seats):
    lines = ["\t".join(COLUMNS)]
    for s in seats:
        lines.append(
            "\t".join(
                [
                    s.seat_id, s.kind, s.title, s.company, s.district, s.year,
                    s.source_file, str(s.table_no or ""),
                    "1" if s.is_crossing_target else "",
                ]
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def seat():
    return make_seat()
