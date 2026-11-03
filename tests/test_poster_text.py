"""Posters copied by hand to text (the teacher's call on 11/3). Every poster,
name and company here is invented."""

import json

import pytest

from conftest import make_seat, write_seats
from ebino.ask_seat import first_sentence
from ebino.guard import check
from ebino.ingest.masks import SeatMasks
from ebino.ingest.poster_pdf import ROLE_BACKGROUND, ROLE_RESULT, heading_of, purpose_examples
from ebino.ingest.poster_text import ingest_text_poster, text_sections
from ebino.ingest.run import run
from ebino.ingest.utterance import IngestError, VOICE_OWN

TITLE = "ひまわり美容室で学んだこと　3年　川辺三郎"
THEME = "お客さんが帰りに笑顔になるのはなぜかを知りたかった。"
WINDOW = "開店前に窓をふいた。"
POSTER = f"""{TITLE}

## テーマ設定の理由
{THEME}

## 【窓そうじ】
{WINDOW}
"""


@pytest.fixture
def seat():
    return make_seat(seat_id="P01", kind="poster", title="探究の先輩（美容室）", company="",
                     display_name="先輩", source_file="posters/P01.txt")


def write(tmp_path, text, encoding="utf-8"):
    path = tmp_path / "P01.txt"
    path.write_text(text, encoding=encoding)
    return path


def test_two_headings_make_two_sections_and_the_purpose_comes_from_the_theme_reason(tmp_path, seat):
    utterances = ingest_text_poster(write(tmp_path, POSTER), seat)
    assert [(u.heading, u.text) for u in utterances] == [("テーマ設定の理由", THEME), ("窓そうじ", WINDOW)]
    assert utterances[0].section == ROLE_BACKGROUND
    assert utterances[1].section == "窓そうじ"  # No role: the heading's own name.
    assert all(u.voice == VOICE_OWN and u.kind == "poster" for u in utterances)
    assert purpose_examples(utterances) == [utterances[0]]


def test_body_lines_are_kept_apart_by_a_line_break_with_nothing_added():
    sections = text_sections("## 成果\n・周りを見て動いた\n・進んで取り組めた\n")
    assert [s.text for s in sections] == ["・周りを見て動いた\n・進んで取り組めた"]


ROW_1 = "迷っていた→聞けるようになった"
ROW_2 = "一人でやっていた→頼れるようになった"
TABLE = f"## 目的\n働くと何が変わるかを知りたい。\n## 実習の成果\n{ROW_1}\n{ROW_2}\n"


def test_a_tables_rows_stay_apart_and_a_quote_cannot_run_across_them(tmp_path, seat):
    rows = ingest_text_poster(write(tmp_path, TABLE), seat)[1]
    assert rows.text == f"{ROW_1}\n{ROW_2}"  # The line break is kept in the piece.
    assert not check("聞けるようになった一人でやっていた", rows.text).passed  # Across the rows.
    assert not check("迷っていた→聞けるようになった一人でやっていた", rows.text).passed
    assert check(ROW_2, rows.text).shown == ROW_2  # One row on its own passes.
    assert check(ROW_1, rows.text).shown == ROW_1
    assert first_sentence(rows.text) == ROW_1  # The question's quote stops at the row's end.


def test_lines_before_the_first_heading_are_in_no_utterance(tmp_path, seat):
    raw = json.dumps([u.to_dict() for u in ingest_text_poster(write(tmp_path, POSTER), seat)],
                     ensure_ascii=False)
    assert "川辺" not in raw and "学んだこと" not in raw


def test_a_long_marked_heading_is_a_heading_with_its_role():
    long = "企画を実践してみての職場の反応と実習の成果"
    assert heading_of(long) is None  # Too long for a PDF line on its own.
    sections = text_sections(f"## 目的\n知りたい。\n## {long}\n喜ばれた。\n")
    assert [(s.label, s.role, s.text) for s in sections][1] == (long, ROLE_RESULT, "喜ばれた。")


def test_a_why_question_is_background_and_a_purpose_source(tmp_path, seat):
    utterances = ingest_text_poster(write(tmp_path, "## なぜ美容室なのか\nお客さんと話せるから。\n"), seat)
    assert utterances[0].section == ROLE_BACKGROUND
    assert purpose_examples(utterances) == utterances


@pytest.mark.parametrize("line, label", [
    ("＜テーマ設定の理由＞", "テーマ設定の理由"),
    ("１．研究仮説", "研究仮説"),
    ("■ 結果と考察 ：", "結果と考察"),
    ("3つの課題", "3つの課題"),  # A number with no separator stays.
])
def test_heading_names_are_found_as_for_a_pdf(line, label):
    assert text_sections(f"## {line}\n本文。\n")[0].label == label


def test_a_heading_with_no_body_is_no_section_and_a_blank_line_adds_nothing():
    sections = text_sections("## 目的\n\n知りたい。\n\n## まとめ\n\n")
    assert [(s.role, s.text) for s in sections] == [("目的", "知りたい。")]


def test_a_full_width_space_after_the_mark_is_taken():
    assert text_sections("##　目的\n知りたい。\n")[0].role == "目的"


def test_no_heading_stops(tmp_path, seat):
    with pytest.raises(IngestError, match="poster_heading_missing"):
        ingest_text_poster(write(tmp_path, "目的\n知りたい。\n#目的\n"), seat)


def test_a_mark_with_no_name_stops():
    with pytest.raises(IngestError, match="poster_heading_empty"):
        text_sections("## 目的\n知りたい。\n## 【】\n喜ばれた。\n")


def test_no_purpose_or_theme_reason_heading_stops(tmp_path, seat):
    with pytest.raises(IngestError, match="purpose_heading_missing"):
        ingest_text_poster(write(tmp_path, f"## 【窓そうじ】\n{WINDOW}\n## 成果\n喜ばれた。\n"), seat)


def test_a_company_word_to_hide_is_gone_from_the_body(tmp_path, seat):
    text = "## 目的\nひまわり美容室のお客さんが笑顔になるわけを知りたい。\n"
    utterances = ingest_text_poster(write(tmp_path, text), seat, SeatMasks(words=("ひまわり美容室",)))
    assert "ひまわり" not in utterances[0].text and "お客さんが笑顔" in utterances[0].text


def test_the_page_mask_drops_the_whole_poster(tmp_path, seat):
    assert ingest_text_poster(write(tmp_path, POSTER), seat, SeatMasks(pages=frozenset({1}))) == []
    with pytest.raises(IngestError, match="mask_page_out_of_range"):
        ingest_text_poster(write(tmp_path, POSTER), seat, SeatMasks(pages=frozenset({2})))


def test_a_bom_does_not_hide_the_first_heading(tmp_path, seat):
    utterances = ingest_text_poster(write(tmp_path, "## 目的\n知りたい。\n", encoding="utf-8-sig"), seat)
    assert [(u.section, u.text) for u in utterances] == [("目的", "知りたい。")]


def test_the_batch_reads_a_copied_poster_and_counts_it(tmp_path, seat):
    (tmp_path / "posters").mkdir()
    (tmp_path / "posters" / "P01.txt").write_text(POSTER, encoding="utf-8")
    write_seats(tmp_path / "seats.tsv", [seat])
    report = run(tmp_path)
    assert not report.failed_seats and report.ingested_by_kind["poster"] == 1
    assert report.copied_posters == 1
    assert report.poster_sections_by_role == {ROLE_BACKGROUND: 1, "(other)": 1}
    assert report.posters_purpose_from_theme_reason == 1
    assert "copied posters (text) read: 1" in report.lines()
    rows = json.loads((tmp_path / "ingested" / "utterances.json").read_text(encoding="utf-8"))
    assert [row["heading"] for row in rows] == ["テーマ設定の理由", "窓そうじ"]


def test_a_text_file_on_a_seat_that_is_not_a_poster_still_stops(tmp_path):
    (tmp_path / "a.txt").write_text("## 目的\n知りたい。\n", encoding="utf-8")
    write_seats(tmp_path / "seats.tsv", [make_seat(source_file="a.txt")])
    assert run(tmp_path).failures["kind_and_file_type_mismatch"] == 1
