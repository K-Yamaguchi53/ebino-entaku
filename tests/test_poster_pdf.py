"""Fictional posters in the shapes found in the real ones (SPEC 14-42)."""

import logging

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from conftest import make_seat
from ebino.ingest.poster_pdf import (
    Fragment,
    Heading,
    heading_of,
    split_fragment,
    ingest_poster,
    ingest_poster_fragments,
    purpose_examples,
    split_sections,
)
from ebino.ingest.utterance import IngestError, VOICE_OWN

STUDENT = "川辺 三郎"


@pytest.fixture
def poster_seat():
    return make_seat(seat_id="P01", kind="poster", company="", display_name="卒業生", source_file="poster01.pdf")


def by_name(fragments):
    return {section.name: section.text for section in split_sections(fragments)}


def lines(*texts, top=60, step=20, x0=50):
    return [Fragment(text, x0, top + i * step) for i, text in enumerate(texts)]


def old_style():
    return [
        Fragment("架空の川の水を調べる", 50, 10),
        Fragment(STUDENT, 400, 12),
        *lines(
            "背景と課題", "川の水が減っていると聞いた。",
            "目的", "なぜ減ったのかを確かめる。",
            "手法", "十か所で測った。",
            "結果", "上流だけ減っていた。",
            "結論と展望", "下流の調査はまだ手つかずだ。",
        ),
    ]


def quest_style():
    """Quest type: no 目的 heading; 研究仮説 plays that role."""
    return [
        Fragment("【架空の町の朝市を調べる】", 50, 10),
        Fragment(STUDENT, 400, 10),
        *lines(
            "１　経緯", "朝市が減ったと聞いた。",
            "２　研究仮説", "若い人が来ないから減ったのではないか。",
            "３．調査活動", "三十人に聞いた。",
            "4. 実践 (Practice)", "朝市を一回開いた。",
            "5.実践後の課題", "人が集まる時間が分からない。",
            "６　成果と今後の展望", "次は夕方に開きたい。",
        ),
    ]


def action_style():
    """Action type, with every bracket style and one heading of no role."""
    return [
        Fragment(STUDENT, 50, 10),
        *lines(
            "＜背景＞", "店が少ない。",
            "【企画の目的】", "店を知ってもらう。",
            "《活動内容》", "地図を作った。",
            "◎考えた企画", "地図を配る。",
            "〈成果と反省〉", "百枚配れた。",
            "1企画実践の背景", "去年も試した。",
            "７．地域の声", "店の人が喜んだ。",
            "＜ 反省・展望 ＞", "また作りたい。",
        ),
    ]


def test_name_above_the_first_heading_is_dropped(poster_seat):
    for fragments in (old_style(), quest_style(), action_style()):
        utterances = ingest_poster_fragments(fragments, poster_seat)
        text = "".join(u.text + u.paragraph + u.heading for u in utterances)
        assert "川辺" not in text and "三郎" not in text


def test_title_above_the_first_role_heading_goes_with_the_name(poster_seat):
    utterances = ingest_poster_fragments(quest_style(), poster_seat)
    assert "朝市を調べる" not in "".join(u.text + u.heading for u in utterances)


def test_old_style_sections():
    sections = by_name(old_style())
    assert sections["目的"] == "なぜ減ったのかを確かめる。"
    assert sections["結論と展望"] == "下流の調査はまだ手つかずだ。"
    assert len(sections) == 5


def test_quest_style_maps_to_roles():
    sections = [(s.label, s.role) for s in split_sections(quest_style())]
    assert sections == [
        ("経緯", "背景と課題"),
        ("研究仮説", "目的"),
        ("調査活動", "手法"),
        ("実践", "手法"),
        ("実践後の課題", "結論と展望"),
        ("成果と今後の展望", "結論と展望"),
    ]


def test_action_style_maps_to_roles_and_keeps_the_odd_heading():
    sections = [(s.label, s.role, s.text) for s in split_sections(action_style())]
    assert sections == [
        ("背景", "背景と課題", "店が少ない。"),
        ("企画の目的", "目的", "店を知ってもらう。"),
        ("活動内容", "手法", "地図を作った。"),
        ("考えた企画", "手法", "地図を配る。"),
        ("成果と反省", "結果", "百枚配れた。"),
        ("企画実践の背景", "背景と課題", "去年も試した。"),
        ("地域の声", None, "店の人が喜んだ。"),
        ("反省・展望", "結論と展望", "また作りたい。"),
    ]


def test_odd_heading_becomes_its_own_section(poster_seat):
    utterances = ingest_poster_fragments(action_style(), poster_seat)
    odd = [u for u in utterances if u.heading == "地域の声"]
    assert [(u.section, u.text) for u in odd] == [("地域の声", "店の人が喜んだ。")]


def test_quest_purpose_sample_comes_from_the_hypothesis(poster_seat):
    examples = purpose_examples(ingest_poster_fragments(quest_style(), poster_seat))
    assert [(u.heading, u.text) for u in examples] == [
        ("研究仮説", "若い人が来ないから減ったのではないか。")
    ]


def test_a_real_purpose_heading_wins_over_a_hypothesis(poster_seat):
    fragments = lines("研究仮説", "仮説の文。", "目的", "目的の文。")
    examples = purpose_examples(ingest_poster_fragments(fragments, poster_seat))
    assert [u.heading for u in examples] == ["目的"]


def test_background_and_purpose_heading_counts_as_fallback(poster_seat):
    fragments = lines("1 経緯・目的", "経緯と目的の文。", "2 調査活動", "聞いた。")
    examples = purpose_examples(ingest_poster_fragments(fragments, poster_seat))
    assert [u.heading for u in examples] == ["経緯・目的"]


def test_poster_words_are_the_authors_own(poster_seat):
    utterances = ingest_poster_fragments(old_style(), poster_seat)
    assert {u.voice for u in utterances} == {VOICE_OWN}


def test_two_columns_keep_text_under_their_own_heading():
    fragments = [
        Fragment(STUDENT, 50, 10),
        Fragment("目的", 50, 60),
        Fragment("左の段の文。", 50, 80),
        Fragment("結果", 300, 60),
        Fragment("右の段の文。", 300, 80),
    ]
    assert by_name(fragments) == {"目的": "左の段の文。", "結果": "右の段の文。"}


def test_lines_inside_a_section_keep_reading_order():
    fragments = [Fragment("目的", 50, 60), Fragment("二行目。", 50, 100), Fragment("一行目。", 50, 80)]
    assert by_name(fragments)["目的"] == "一行目。二行目。"


@pytest.mark.parametrize(
    "text, label",
    [
        ("目的", "目的"),
        ("目 的", "目的"),
        ("目的：", "目的"),
        ("1. 目的", "目的"),
        ("■目的", "目的"),
        ("【目的】", "目的"),
        ("２　研究仮説", "研究仮説"),
        ("2.活動内容", "活動内容"),
        ("2. 活動内容", "活動内容"),
        ("２．探究仮説", "探究仮説"),
        ("１、背景", "背景"),
        ("①経緯・目的", "経緯・目的"),
        ("1企画実践の背景", "企画実践の背景"),
        ("＜背景＞", "背景"),
        ("＜ 調査活動 ＞", "調査活動"),
        ("〈結果〉", "結果"),
        ("《活動内容》", "活動内容"),
        ("◎活動内容", "活動内容"),
        ("4. 結果 (Results)", "結果"),
        ("３．地域の声", "地域の声"),
    ],
)
def test_heading_shapes_are_found(text, label):
    assert heading_of(text).label == label


@pytest.mark.parametrize(
    "text",
    [
        "目的は水を調べること",
        "結果として減った",
        "10か所で測った",
        "2025年に調べた",
        "3つの課題がある",
        "1回目の活動",
        "「楽しかった」と言われた",
        "２．この文は長くて十六字をこえる本文の行です",
        "2. 十か所で測った。",
    ],
)
def test_body_lines_are_not_headings(text):
    assert heading_of(text) is None


def test_no_role_heading_fails_closed(poster_seat):
    fragments = [Fragment(STUDENT, 50, 10), Fragment("３．地域の声", 50, 60), Fragment("本文。", 50, 80)]
    with pytest.raises(IngestError, match="poster_heading_missing"):
        ingest_poster_fragments(fragments, poster_seat)


def test_no_purpose_role_still_stops(poster_seat):
    with pytest.raises(IngestError, match="purpose_heading_missing"):
        ingest_poster_fragments(lines("結果", "減っていた。"), poster_seat)


# --- SPEC 14-44: the second real-data run -------------------------------------


def theme_reason_style():
    """テーマ設定理由 is the topmost heading; the hypothesis has words before it."""
    return [
        Fragment("【架空の公園の遊具を調べる】", 50, 10),
        Fragment(STUDENT, 400, 10),
        *lines(
            "探究テーマ設定理由①", "公園の遊具が古いと聞いた。",
            "スポーツイベントの開催による効果、研究仮説", "大会を開けば人が集まるのではないか。",
            "②実習活動を通して", "大会を一回開いた。",
            "企画実践前の課題", "道具が足りなかった。",
            "◎10:30〜スタート",
            "これからの課題", "次は道具を借りたい。",
        ),
    ]


def test_body_under_a_topmost_theme_reason_survives(poster_seat):
    utterances = ingest_poster_fragments(theme_reason_style(), poster_seat)
    texts = [u.text for u in utterances]
    assert "公園の遊具が古いと聞いた。" in texts
    everything = "".join(u.text + u.heading for u in utterances)
    assert "川辺" not in everything and "三郎" not in everything
    assert "遊具を調べる" not in everything  # The title still goes with the name.


def test_theme_reason_style_maps_to_roles():
    sections = [(s.label, s.role, s.text) for s in split_sections(theme_reason_style())]
    assert sections == [
        ("探究テーマ設定理由", "背景と課題", "公園の遊具が古いと聞いた。"),
        ("スポーツイベントの開催による効果、研究仮説", "目的", "大会を開けば人が集まるのではないか。"),
        ("実習活動を通して", "手法", "大会を一回開いた。"),
        ("企画実践前の課題", "背景と課題", "道具が足りなかった。◎10:30〜スタート"),
        ("これからの課題", "結論と展望", "次は道具を借りたい。"),
    ]


@pytest.mark.parametrize(
    "text, label, role",
    [
        ("テーマ設定理由", "テーマ設定理由", "背景と課題"),
        ("テーマ設定の理由", "テーマ設定の理由", "背景と課題"),
        ("探究テーマ設定理由①", "探究テーマ設定理由", "背景と課題"),
        ("１．探究テーマ設定理由②", "探究テーマ設定理由", "背景と課題"),
        ("はじめに", "はじめに", "背景と課題"),
        ("初めに", "初めに", "背景と課題"),
        ("動機", "動機", "背景と課題"),
        ("きっかけ", "きっかけ", "背景と課題"),
        ("企画実践前の課題", "企画実践前の課題", "背景と課題"),
        ("実践後の課題", "実践後の課題", "結論と展望"),
        ("これからの課題", "これからの課題", "結論と展望"),
        ("目標", "目標", "目的"),
        ("【目標】", "目標", "目的"),
        ("②実習活動を通して", "実習活動を通して", "手法"),
        ("スポーツイベントの開催による効果、研究仮説", "スポーツイベントの開催による効果、研究仮説", "目的"),
        ("3. 地域の祭りを続けるための探究仮説", "地域の祭りを続けるための探究仮説", "目的"),
    ],
)
def test_second_run_heading_shapes(text, label, role):
    assert heading_of(text) == Heading(label, role)


@pytest.mark.parametrize(
    "text",
    [
        "◎10:30〜スタート",
        "◆1:0.5:2",
        "【2025年の記録】",
        "この町の公園には古い遊具が多く残っていると聞いた",  # long, no purpose ending
        "公園の遊具が古いので新しくすることがこの探究の目的。",  # has 。
        "町の人に何度も話を聞きに行き考えを深めていくことがこの探究の目的",  # over 30
    ],
)
def test_second_run_body_lines_are_not_headings(text):
    assert heading_of(text) is None


def test_heading_and_body_on_one_line_are_split():
    fragments = [
        Fragment(STUDENT, 50, 10),
        Fragment("背景　自由な園児が多く集団行動が", 50, 60),
        Fragment("苦手だった。", 50, 80),
        Fragment("目標 小学校に進級したとき困らない", 50, 100),
        Fragment("ようにする。", 50, 120),
    ]
    sections = [(s.label, s.role, s.text) for s in split_sections(fragments)]
    assert sections == [
        ("背景", "背景と課題", "自由な園児が多く集団行動が苦手だった。"),
        ("目標", "目的", "小学校に進級したとき困らないようにする。"),
    ]


def test_bracketed_heading_with_inner_spaces_is_not_split():
    assert split_fragment(Fragment("＜ 調査活動 ＞", 50, 60)) == [Fragment("＜ 調査活動 ＞", 50, 60)]


def test_unknown_word_and_space_is_not_split():
    fragment = Fragment("地域 の人に聞いた", 50, 60)
    assert split_fragment(fragment) == [fragment]


def char_positions(*runs):
    """(text, x0) runs laid out at 12pt per character."""
    text = "".join(run for run, _ in runs)
    xs = tuple(x0 + 12 * i for run, x0 in runs for i in range(len(run)))
    return text, xs


def test_two_headings_on_one_line_become_two_columns():
    text, xs = char_positions(("探究テーマ設定理由①", 50), ("　", 170), ("探究テーマ設定理由②", 300))
    fragments = [
        Fragment(STUDENT, 50, 10),
        Fragment(text, 50, 60, xs),
        Fragment("左の段の文。", 50, 80),
        Fragment("右の段の文。", 300, 80),
    ]
    sections = [(s.label, s.text) for s in split_sections(fragments)]
    assert sections == [("探究テーマ設定理由", "左の段の文。"), ("探究テーマ設定理由", "右の段の文。")]


def test_purpose_sample_falls_back_to_the_theme_reason(poster_seat):
    fragments = lines("探究テーマ設定理由", "遊具が古いから選んだ。", "調査活動", "三十人に聞いた。")
    examples = purpose_examples(ingest_poster_fragments(fragments, poster_seat))
    assert [(u.section, u.heading, u.text) for u in examples] == [
        ("背景と課題", "探究テーマ設定理由", "遊具が古いから選んだ。")
    ]


def test_a_hypothesis_wins_over_the_theme_reason(poster_seat):
    examples = purpose_examples(ingest_poster_fragments(theme_reason_style(), poster_seat))
    assert [u.heading for u in examples] == ["スポーツイベントの開催による効果、研究仮説"]


def test_plain_background_is_not_a_purpose_sample(poster_seat):
    with pytest.raises(IngestError, match="purpose_heading_missing"):
        ingest_poster_fragments(lines("背景", "店が少ない。", "結果", "増えた。"), poster_seat)


def write_theme_reason_poster(path):
    """A real PDF: two headings on one line, and a heading with its body beside it."""
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setFont("HeiseiKakuGo-W5", 12)
    pdf.drawString(380, 800, STUDENT)
    pdf.drawString(50, 740, "探究テーマ設定理由①　探究テーマ設定理由②")
    pdf.drawString(50, 720, "左の段の文。")
    pdf.drawString(194, 720, "右の段の文。")
    pdf.drawString(50, 680, "目標　小学校で困らないようにする。")
    pdf.save()
    return path


def test_real_pdf_splits_headings_by_character_position(tmp_path, poster_seat):
    utterances = ingest_poster(write_theme_reason_poster(tmp_path / "poster01.pdf"), poster_seat)
    assert [(u.section, u.heading, u.text) for u in utterances] == [
        ("背景と課題", "探究テーマ設定理由", "左の段の文。"),
        ("背景と課題", "探究テーマ設定理由", "右の段の文。"),
        ("目的", "目標", "小学校で困らないようにする。"),
    ]
    assert "川辺" not in "".join(u.text for u in utterances)


def write_poster(path, pages=1):
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    pdf = canvas.Canvas(str(path), pagesize=A4)
    for _ in range(pages):
        pdf.setFont("HeiseiKakuGo-W5", 12)
        pdf.drawString(380, 800, STUDENT)
        pdf.drawString(50, 740, "２　研究仮説")
        pdf.drawString(50, 720, "なぜ減ったのかを確かめる。")
        pdf.drawString(50, 680, "4. 結果 (Results)")
        pdf.drawString(50, 660, "上流だけ減っていた。")
        pdf.showPage()
    pdf.save()
    return path


def test_real_pdf_file_is_read_without_the_name(tmp_path, poster_seat):
    utterances = ingest_poster(write_poster(tmp_path / "poster01.pdf"), poster_seat)
    assert {(u.section, u.heading): u.text for u in utterances} == {
        ("目的", "研究仮説"): "なぜ減ったのかを確かめる。",
        ("結果", "結果"): "上流だけ減っていた。",
    }


def test_multi_page_poster_fails(tmp_path, poster_seat):
    with pytest.raises(IngestError, match="poster_not_one_page"):
        ingest_poster(write_poster(tmp_path / "p.pdf", pages=2), poster_seat)


def test_font_warnings_are_silenced(tmp_path, poster_seat):
    ingest_poster(write_poster(tmp_path / "poster01.pdf"), poster_seat)
    assert logging.getLogger("pdfminer").getEffectiveLevel() >= logging.ERROR
    logging.getLogger("pdfminer.pdffont").warning("Could not get FontBBox from font descriptor")
    assert not logging.getLogger("pdfminer.pdffont").isEnabledFor(logging.WARNING)
