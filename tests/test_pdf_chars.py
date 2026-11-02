"""Look-alike kanji from PDFs (SPEC 14-48). Names here are invented."""

import json

import pytest

from conftest import make_seat, write_seats
from ebino.ingest.masks import SeatMasks
from ebino.ingest.pdf_chars import (
    PdfTextStats, fold_radicals, leftover_supplement_chars, remove_controls,
)
from ebino.ingest.poster_pdf import ingest_poster
from ebino.ingest.run import run
from ebino.ingest.slides_pdf import ingest_slides
from pdf_text import write_text_pdf

KANGXI_EYE = "⽬"  # ⽬ looks like 目
KANGXI_MOUNTAIN = "⼭"  # ⼭ looks like 山
KANGXI_FIELD = "⽥"  # ⽥ looks like 田
COMPAT_RO = "朗"  # 朗 (compatibility ideograph) looks like 朗
SUPPLEMENT_LONG = "⻑"  # ⻑ looks like 長
SUPPLEMENT_UNMAPPED = "⺌"  # ⺌ has no ordinary kanji to go to


@pytest.mark.parametrize(
    "raw, folded",
    [
        (f"{KANGXI_EYE}的", "目的"),
        (f"{KANGXI_MOUNTAIN}川太{COMPAT_RO}", "山川太朗"),
        (f"{SUPPLEMENT_LONG}野", "長野"),
        ("⻄⻘⻲⻁", "西青亀虎"),
        ("⺟", "母"),  # Folded by NFKC though it is in the supplement range.
    ],
)
def test_look_alike_kanji_become_ordinary(raw, folded):
    assert fold_radicals(raw) == folded


@pytest.mark.parametrize("text", ["ＡＢＣ１２３", "①②", "（）【】＜＞", "ｱｲｳ", "㈱", "ふつうの文。"])
def test_everything_else_is_left_alone(text):
    assert fold_radicals(text) == text


def test_length_never_changes():
    raw = f"{KANGXI_EYE}的{COMPAT_RO}{SUPPLEMENT_LONG}{SUPPLEMENT_UNMAPPED}"
    assert len(fold_radicals(raw)) == len(raw)


def test_unmapped_supplement_char_is_kept_and_counted():
    text = fold_radicals(f"小{SUPPLEMENT_UNMAPPED}")
    assert text == f"小{SUPPLEMENT_UNMAPPED}"
    assert leftover_supplement_chars(text) == 1
    assert leftover_supplement_chars(fold_radicals(f"{SUPPLEMENT_LONG}野")) == 0


def test_control_chars_are_removed_and_counted():
    stats = PdfTextStats()
    assert remove_controls("\x00目的\x01\x7f", stats) == "目的"
    assert remove_controls("一行目\n\t二行目", stats) == "一行目\n\t二行目"
    assert stats.control_chars_removed == 3


NUL_GAP = "\x00" * 9  # Nine NUL glyphs bridge the left heading to the right one.


def control_char_poster(path):
    return write_text_pdf(
        path,
        [
            (380, 800, "川辺 三郎"),
            (50, 740, f"探究テーマ設定理由①{NUL_GAP}探究テーマ設定理由②"),
            (50, 720, "左の段の本文。"),
            (290, 720, "右の段の本文。"),
            (50, 680, "\x01スポーツイベントの開催による効果、研究仮説"),
            (50, 660, "仮説の本文。"),
            (50, 620, "\x011.実務体験 \x012.コンテンツ制作 \x013.SNS発信"),
            (50, 600, "三つを試した。"),
        ],
    )


def test_poster_with_control_chars_keeps_both_columns_and_the_hypothesis(tmp_path):
    stats = PdfTextStats()
    path = control_char_poster(tmp_path / "poster01.pdf")
    utterances = ingest_poster(path, poster_seat(), stats=stats)
    assert [(u.section, u.heading, u.text) for u in utterances][:3] == [
        ("背景と課題", "探究テーマ設定理由", "左の段の本文。"),
        ("背景と課題", "探究テーマ設定理由", "右の段の本文。"),
        ("目的", "スポーツイベントの開催による効果、研究仮説", "仮説の本文。"),
    ]
    everything = "".join(u.text + u.heading + u.paragraph for u in utterances)
    assert not any(ch < " " for ch in everything)
    assert "三つを試した。" in everything
    assert stats.control_chars_removed == 9 + 1 + 3


def test_slides_lose_control_chars(tmp_path):
    path = write_text_pdf(tmp_path / "slide01.pdf", [(50, 780, "\x00町の\x01話")])
    seat = make_seat(seat_id="C01", kind="cross", company="", source_file="slide01.pdf")
    stats = PdfTextStats()
    utterances = ingest_slides(path, seat, SeatMasks(pages=frozenset()), stats)
    assert [u.text for u in utterances] == ["町の話"]
    assert stats.control_chars_removed == 2


def test_batch_reports_removed_control_chars(tmp_path):
    control_char_poster(tmp_path / "poster01.pdf")
    write_seats(tmp_path / "seats.tsv", [poster_seat()])
    report = run(tmp_path)
    assert not report.failed_seats
    assert "control chars removed from PDF text: 13" in report.lines()
    raw = (tmp_path / "ingested" / "utterances.json").read_text(encoding="utf-8")
    assert "\\u0000" not in raw and "\\u0001" not in raw


def radical_poster(path, body_extra=""):
    return write_text_pdf(
        path,
        [
            (380, 800, f"{KANGXI_MOUNTAIN}川 太{COMPAT_RO}"),
            (50, 740, f"{KANGXI_EYE}的"),
            (50, 720, f"{SUPPLEMENT_LONG}野さんと{KANGXI_FIELD}んぼを調べる。{body_extra}"),
            (50, 680, "結果"),
            (50, 660, "水が少なかった。"),
        ],
    )


def poster_seat():
    return make_seat(
        seat_id="P01", kind="poster", company="", display_name="卒業生", source_file="poster01.pdf"
    )


def test_poster_written_in_radicals_masks_the_name_and_finds_the_purpose(tmp_path):
    path = radical_poster(tmp_path / "poster01.pdf")
    utterances = ingest_poster(path, poster_seat(), SeatMasks(words=("長野",)))
    sections = {u.section: u.text for u in utterances}
    assert sections["目的"] == "この方と田んぼを調べる。"
    everything = "".join(u.text + u.heading for u in utterances)
    assert "長野" not in everything and SUPPLEMENT_LONG not in everything
    assert "山川" not in everything  # The author line above the first heading is gone.


def test_slides_written_in_radicals_mask_the_name(tmp_path):
    path = write_text_pdf(
        tmp_path / "slide01.pdf",
        [(50, 780, f"{KANGXI_MOUNTAIN}川太{COMPAT_RO}の発表"), (50, 740, f"{KANGXI_FIELD}んぼの話")],
    )
    seat = make_seat(seat_id="C01", kind="cross", company="", source_file="slide01.pdf")
    utterances = ingest_slides(path, seat, SeatMasks(words=("山川太朗",)))
    assert [u.text for u in utterances] == ["この方の発表\n田んぼの話"]


def test_batch_reports_supplement_chars_left_over(tmp_path):
    radical_poster(tmp_path / "poster01.pdf", body_extra=f"{SUPPLEMENT_UNMAPPED}")
    write_seats(tmp_path / "seats.tsv", [poster_seat()])
    (tmp_path / "masks.tsv").write_text("席ID\t種類\t値\nP01\t語\t長野\n", encoding="utf-8")
    report = run(tmp_path)
    assert not report.failed_seats
    assert report.leftover_radical_chars == 1
    assert "radical-supplement chars left (not in the table): 1" in report.lines()
    raw = (tmp_path / "ingested" / "utterances.json").read_text(encoding="utf-8")
    assert "長野" not in raw
    assert json.loads(raw)
