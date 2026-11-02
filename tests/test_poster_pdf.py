import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from conftest import make_seat
from ebino.ingest.poster_pdf import (
    Fragment, heading_of, ingest_poster, ingest_poster_fragments, split_sections,
)
from ebino.ingest.utterance import IngestError, VOICE_OWN

STUDENT = "川辺 三郎"


@pytest.fixture
def poster_seat():
    return make_seat(seat_id="P01", kind="poster", company="", source_file="poster01.pdf", year="2025")


def single_column():
    return [
        Fragment("架空の川の水を調べる", 50, 10),
        Fragment(STUDENT, 400, 12),
        Fragment("背景と課題", 50, 60),
        Fragment("川の水が減っていると聞いた。", 50, 80),
        Fragment("目的", 50, 120),
        Fragment("なぜ減ったのかを確かめる。", 50, 140),
        Fragment("手法", 50, 180),
        Fragment("十か所で測った。", 50, 200),
        Fragment("結果", 50, 240),
        Fragment("上流だけ減っていた。", 50, 260),
        Fragment("結論と展望", 50, 300),
        Fragment("下流の調査はまだ手つかずだ。", 50, 320),
    ]


def test_name_above_the_first_heading_is_dropped(poster_seat):
    utterances = ingest_poster_fragments(single_column(), poster_seat)
    text = "".join(u.text + u.paragraph for u in utterances)
    assert "川辺" not in text
    assert "三郎" not in text


def test_all_sections_are_separated():
    sections = split_sections(single_column())
    assert sections["目的"] == "なぜ減ったのかを確かめる。"
    assert sections["結論と展望"] == "下流の調査はまだ手つかずだ。"
    assert len(sections) == 5


def test_poster_words_are_the_authors_own(poster_seat):
    utterances = ingest_poster_fragments(single_column(), poster_seat)
    assert {u.voice for u in utterances} == {VOICE_OWN}
    assert {u.section for u in utterances} >= {"目的"}


def test_two_columns_keep_text_under_their_own_heading():
    fragments = [
        Fragment(STUDENT, 50, 10),
        Fragment("目的", 50, 60),
        Fragment("左の段の文。", 50, 80),
        Fragment("結果", 300, 60),
        Fragment("右の段の文。", 300, 80),
    ]
    sections = split_sections(fragments)
    assert sections == {"目的": "左の段の文。", "結果": "右の段の文。"}


def test_lines_inside_a_section_keep_reading_order():
    fragments = [
        Fragment("目的", 50, 60),
        Fragment("二行目。", 50, 100),
        Fragment("一行目。", 50, 80),
    ]
    assert split_sections(fragments)["目的"] == "一行目。二行目。"


@pytest.mark.parametrize("text", ["目的", "1. 目的", "【目的】", "■目的", "目 的", "目的："])
def test_decorated_headings_are_found(text):
    assert heading_of(text) == "目的"


@pytest.mark.parametrize("text", ["目的は水を調べること", "結果として減った"])
def test_body_lines_are_not_headings(text):
    assert heading_of(text) is None


def test_no_purpose_heading_fails_closed(poster_seat):
    with pytest.raises(IngestError, match="purpose_heading_missing"):
        ingest_poster_fragments([Fragment(STUDENT, 50, 10), Fragment("本文", 50, 80)], poster_seat)


def write_poster(path, pages=1):
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    pdf = canvas.Canvas(str(path), pagesize=A4)
    for _ in range(pages):
        pdf.setFont("HeiseiKakuGo-W5", 12)
        pdf.drawString(380, 800, STUDENT)
        pdf.drawString(50, 740, "目的")
        pdf.drawString(50, 720, "なぜ減ったのかを確かめる。")
        pdf.drawString(50, 680, "結果")
        pdf.drawString(50, 660, "上流だけ減っていた。")
        pdf.showPage()
    pdf.save()
    return path


def test_real_pdf_file_is_read_without_the_name(tmp_path, poster_seat):
    utterances = ingest_poster(write_poster(tmp_path / "poster01.pdf"), poster_seat)
    assert {u.section: u.text for u in utterances} == {
        "目的": "なぜ減ったのかを確かめる。",
        "結果": "上流だけ減っていた。",
    }


def test_multi_page_poster_fails(tmp_path, poster_seat):
    with pytest.raises(IngestError, match="poster_not_one_page"):
        ingest_poster(write_poster(tmp_path / "p.pdf", pages=2), poster_seat)
