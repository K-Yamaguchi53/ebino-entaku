import json
from pathlib import Path

import pytest

from conftest import DISPLAY_NAME, PERSON, make_seat, write_article, write_seats
from ebino.ingest.article_docx import ArticleRows, ingest_article_rows
from ebino.ingest.masks import SeatMasks
from ebino.ingest.run import run
from ebino.ingest.scrub import normalize_for_match
from ebino.ingest.seats import COLUMNS, load_seats
from ebino.seat_label import SeatLabel, seat_label, short_company, show_private_labels
from ebino.texts import SPLIT_NOTICE, load_text

SAMPLES = Path(__file__).parent.parent / "samples"


def test_display_name_column_follows_company():
    assert COLUMNS.index("表示名") == COLUMNS.index("会社名") + 1


def test_sample_seats_load_with_display_names():
    seats = {seat.seat_id: seat for seat in load_seats(SAMPLES / "seats.tsv")}
    assert seats["S02"].display_name == "谷さん・森さん"
    assert seats["P01"].display_name == "卒業生"
    assert seats["C01"].title.startswith("県外・海外に出た人")
    assert seats["O01"].display_name == ""


def test_old_seat_table_without_display_name_is_refused(tmp_path):
    old = [c for c in COLUMNS if c != "表示名"]
    path = tmp_path / "seats.tsv"
    path.write_text("\t".join(old) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="columns"):
        load_seats(path)


def test_seat_fields_for_a_model_have_no_company_name_or_year():
    model_view = json.dumps(make_seat().for_model(), ensure_ascii=False)
    assert "はるかぜ" not in model_view
    assert "山川" not in model_view
    assert "2026" not in model_view


def test_model_input_never_holds_the_display_name(tmp_path):
    write_article(tmp_path / "article01.docx")
    seat = make_seat(display_name="山川さん・海野さん")
    write_seats(tmp_path / "seats.tsv", [seat])
    run(tmp_path)
    raw = (tmp_path / "ingested" / "utterances.json").read_text(encoding="utf-8")
    model_input = normalize_for_match(raw + json.dumps(seat.for_model(), ensure_ascii=False))
    for term in ("山川さん", "海野さん", "山川", "海野"):
        assert term not in model_input


def test_family_name_only_in_the_display_name_is_still_masked(seat):
    # The name row lacks this person; the seat table's display name catches it.
    rows = {"1": [PERSON], "8": ["谷さんと店を開けた。"]}
    utterances, _ = ingest_article_rows(ArticleRows(rows), make_seat(display_name="谷さん"))
    assert utterances[0].text == "この方と店を開けた。"


@pytest.mark.parametrize("label", ["卒業生", "1年生"])
def test_grade_labels_are_not_masked(label):
    seat = make_seat(kind="poster", company="", display_name=label, source_file="p.pdf")
    assert SeatMasks().pairs(seat) == []


def test_label_is_title_only_by_default(monkeypatch):
    monkeypatch.delenv("EBINO_SHOW_COMPANY", raising=False)
    assert seat_label(make_seat()) == SeatLabel("理容師", "")


@pytest.mark.parametrize("value", ["", "0", "true", "yes", " 2"])
def test_only_exactly_one_turns_private_labels_on(monkeypatch, value):
    monkeypatch.setenv("EBINO_SHOW_COMPANY", value)
    assert not show_private_labels()
    assert seat_label(make_seat()).detail == ""


def test_in_school_label_has_two_lines(monkeypatch):
    monkeypatch.setenv("EBINO_SHOW_COMPANY", "1")
    assert seat_label(make_seat()) == SeatLabel("理容師", f"はるかぜ理容　{DISPLAY_NAME}")


def test_in_school_label_without_company():
    seat = make_seat(kind="poster", title="探究の先輩（川の水を調べた）", company="", display_name="卒業生")
    assert seat_label(seat, show_private=True) == SeatLabel("探究の先輩（川の水を調べた）", "卒業生")


@pytest.mark.parametrize(
    "company, short",
    [
        ("株式会社はるかぜ", "はるかぜ"),
        ("はるかぜ株式会社", "はるかぜ"),
        ("社会福祉法人 はるかぜ会", "はるかぜ会"),
        ("医療法人はるかぜ", "はるかぜ"),
        ("合同会社はるかぜ", "はるかぜ"),
        ("はるかぜ理容", "はるかぜ理容"),
    ],
)
def test_label_shortens_the_legal_form_only(company, short):
    assert short_company(company) == short


def test_seat_table_keeps_the_full_company():
    seat = make_seat()
    seat_label(seat, show_private=True)
    assert seat.company == "有限会社はるかぜ理容"


def test_split_notice_is_read_from_the_text_file():
    assert load_text(SPLIT_NOTICE) == "どちらが正しいかではありません。考えが分かれるところです"
