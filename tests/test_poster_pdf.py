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
from pdf_text import write_text_pdf

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


# --- SPEC 14-48: the third real-data run ---------------------------------------


@pytest.mark.parametrize(
    "text, label, role",
    [
        ("１ なぜ公園の遊具は古いのか（探究テーマ設定理由）", "探究テーマ設定理由", "背景と課題"),
        ("2. 店が減ったのはなぜか（研究仮説）", "研究仮説", "目的"),
        ("1. 背景と課題 (Background and Issues)", "背景と課題", "背景と課題"),
        ("5. 結論と展望 (Conclusion and Outlook)", "結論と展望", "結論と展望"),
        ("１ なぜこのようなテーマにしたのか？", "なぜこのようなテーマにしたのか?", "背景と課題"),
        ("1.なぜ手話？", "なぜ手話?", "背景と課題"),
        ("２．なぜこのテーマにしたのか", "なぜこのテーマにしたのか", "背景と課題"),
        ("2.研究仮設", "研究仮設", "目的"),
        ("探究仮設", "探究仮設", "目的"),
    ],
)
def test_third_run_heading_shapes(text, label, role):
    assert heading_of(text) == Heading(label, role)


@pytest.mark.parametrize(
    "text",
    [
        "なぜこのテーマにしたのか",  # A question without a number is body text.
        "なぜ手話？",
        "2. なぜ店が減ったのかを町の人に聞いて回った",  # Not a question: no か or ？ at the end.
        "町の人に聞いた（結果）",  # Brackets without a number.
    ],
)
def test_third_run_body_lines_are_not_headings(text):
    assert heading_of(text) is None


@pytest.mark.parametrize("text", ["1. なぜなら町に店がないからだ", "3. 町の人に聞いた（地域の人）"])
def test_numbered_lines_outside_the_new_shapes_get_no_role(text):
    # A short numbered line is still a heading of its own (SPEC 14-42), but neither
    # 「なぜなら」 nor a bracket word outside the heading list gives it a role.
    assert heading_of(text).role is None


def test_question_and_hypothesis_on_one_line_become_two_columns():
    text, xs = char_positions(("１．なぜこのテーマにしたのか", 50), (" ", 218), ("２．研究仮説", 300))
    fragments = [
        Fragment(STUDENT, 50, 10),
        Fragment(text, 50, 60, xs),
        Fragment("左の段の文。", 50, 80),
        Fragment("右の段の文。", 300, 80),
    ]
    sections = [(s.label, s.role, s.text) for s in split_sections(fragments)]
    assert sections == [
        ("なぜこのテーマにしたのか", "背景と課題", "左の段の文。"),
        ("研究仮説", "目的", "右の段の文。"),
    ]


def test_english_gloss_heading_is_not_split():
    fragment = Fragment("1. 背景と課題 (Background and Issues)", 50, 60)
    assert split_fragment(fragment) == [fragment]


def test_why_question_is_the_third_purpose_source(poster_seat):
    fragments = lines("1. なぜ手話？", "町に手話の分かる人が少ない。", "2. 調査活動", "十人に聞いた。")
    examples = purpose_examples(ingest_poster_fragments(fragments, poster_seat))
    assert [(u.section, u.heading) for u in examples] == [("背景と課題", "なぜ手話?")]


def test_misspelled_hypothesis_is_a_hypothesis(poster_seat):
    fragments = lines("1. なぜ手話？", "少ない。", "2.研究仮設", "教室を開けば広まる。")
    examples = purpose_examples(ingest_poster_fragments(fragments, poster_seat))
    assert [(u.section, u.heading) for u in examples] == [("目的", "研究仮設")]


def write_third_run_poster(path):
    """Topmost heading in a form that used to map to no role (SPEC 14-48)."""
    return write_text_pdf(
        path,
        [
            (50, 800, "【架空の町の手話を広める】"),
            (380, 800, STUDENT),
            (50, 740, "１．なぜこのテーマにしたのか ２．研究仮設"),
            (50, 720, "町に手話の分かる人が少ない。"),
            (290, 720, "教室を開けば広まる。"),
            (50, 680, "3. 背景と課題 (Background and Issues)"),
            (50, 660, "聞こえない人が町に住んでいる。"),
            (50, 620, "４ なぜ教室なのか（探究テーマ設定理由）"),
            (50, 600, "人が集まる場所だから。"),
        ],
    )


def test_real_pdf_keeps_the_body_under_the_topmost_question(tmp_path, poster_seat):
    utterances = ingest_poster(write_third_run_poster(tmp_path / "poster01.pdf"), poster_seat)
    assert [(u.section, u.heading, u.text) for u in utterances] == [
        ("背景と課題", "なぜこのテーマにしたのか", "町に手話の分かる人が少ない。"),
        ("目的", "研究仮設", "教室を開けば広まる。"),
        ("背景と課題", "背景と課題", "聞こえない人が町に住んでいる。"),
        ("背景と課題", "探究テーマ設定理由", "人が集まる場所だから。"),
    ]
    everything = "".join(u.text + u.heading for u in utterances)
    assert "川辺" not in everything and "手話を広める" not in everything


# --- SPEC 14-49 ------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, label",
    [
        ("探究テーマの理由", "探究テーマの理由"),
        ("テーマの理由", "テーマの理由"),
        ("探究テーマの理由①", "探究テーマの理由"),
        ("１．探究テーマの理由", "探究テーマの理由"),
        ("【探究テーマの理由】", "探究テーマの理由"),
    ],
)
def test_theme_reason_without_settei_is_background(text, label):
    assert heading_of(text) == Heading(label, "背景と課題")


def test_body_under_a_topmost_theme_reason_without_settei_survives(poster_seat):
    fragments = [
        Fragment(STUDENT, 50, 10),
        *lines("探究テーマの理由", "公園の遊具が古いと聞いた。", "調査活動", "三十人に聞いた。"),
    ]
    utterances = ingest_poster_fragments(fragments, poster_seat)
    assert [(u.section, u.text) for u in utterances] == [
        ("背景と課題", "公園の遊具が古いと聞いた。"),
        ("手法", "三十人に聞いた。"),
    ]
    examples = purpose_examples(utterances)
    assert [u.heading for u in examples] == ["探究テーマの理由"]


GUTTER = "　" * 8


def write_two_column_theme_poster(path):
    """Two theme headings side by side, and their bodies, each read as one line."""
    return write_text_pdf(
        path,
        [
            (380, 800, STUDENT),
            (50, 740, f"探究テーマ設定理由①{GUTTER}探究テーマ設定理由②"),
            (50, 720, f"公園の遊具が古い。{GUTTER}　町に子どもが多い。"),
            (50, 700, "去年から気になった。"),
            (290, 700, "遊ぶ場所が少ない。"),
            (50, 660, "スポーツイベントの開催による効果、研究仮説"),
            (50, 640, "大会を開けば人が集まる。"),
            (50, 600, "結果"),
            (50, 580, "人が 二倍に 増えた。 町の 人も 喜んだ。 次も 開きたい。"),
        ],
    )


def test_two_column_theme_reasons_keep_both_bodies_and_the_hypothesis(tmp_path, poster_seat):
    utterances = ingest_poster(write_two_column_theme_poster(tmp_path / "poster01.pdf"), poster_seat)
    assert [(u.section, u.heading, u.text) for u in utterances] == [
        ("背景と課題", "探究テーマ設定理由", "公園の遊具が古い。去年から気になった。"),
        ("背景と課題", "探究テーマ設定理由", "町に子どもが多い。遊ぶ場所が少ない。"),
        ("目的", "スポーツイベントの開催による効果、研究仮説", "大会を開けば人が集まる。"),
        ("結果", "結果", "人が 二倍に 増えた。 町の 人も 喜んだ。 次も 開きたい。"),
    ]
    examples = purpose_examples(utterances)
    assert [u.heading for u in examples] == ["スポーツイベントの開催による効果、研究仮説"]


def test_a_full_width_line_below_two_columns_is_not_cut():
    text, xs = char_positions(("左の見出しの下の行 右まで 続く 長い 本文", 50))
    fragments = [
        Fragment("目的", 50, 60),
        Fragment("結果", 300, 60),
        Fragment("結論", 50, 100),
        Fragment(text, 50, 120, xs),
    ]
    assert by_name(fragments)["結論と展望"] == text


# --- After 506fb3a: figures, times and ratios at the head of a line --------------


@pytest.mark.parametrize(
    "text",
    [
        "９％",
        "1%",
        "3.9%",
        "１．９％",
        "1. 9%",
        "12:25〜12:40 開会",
        "10:30〜",
        "１０：３０～",
        "1:1:0.5:2",
        "3〜5人",
    ],
)
def test_a_figure_time_or_ratio_is_not_a_heading(text):
    assert heading_of(text) is None


def test_a_colon_and_a_word_is_still_a_heading():
    assert heading_of("２：目的") == Heading("目的", "目的")


def test_pie_chart_labels_do_not_become_sections(poster_seat):
    fragments = lines("目的", "町の声を聞く。", "3.9%", "1. 1%", "結果", "増えた。")
    assert [(u.section, u.text) for u in ingest_poster_fragments(fragments, poster_seat)] == [
        ("目的", "町の声を聞く。3.9%1. 1%"),
        ("結果", "増えた。"),
    ]


# --- After 506fb3a: headings set in from their columns --------------------------


def write_centred_heading_poster(path):
    """Headings set in from their columns, and a hypothesis heading centred over
    a full-width body. The body starts left of every heading above it."""
    return write_text_pdf(
        path,
        [
            (380, 820, STUDENT),
            (64, 784, "探究テーマ設定理由①"),
            (374, 784, "探究テーマ設定理由②"),
            (24, 768, "公園の遊具が古いと聞いた。"),
            (301, 768, "町に子どもが多いと聞いた。"),
            (32, 756, "町"),
            (198, 756, "広場も少ない。"),
            (312, 756, "外"),
            (462, 756, "遊ぶ所がない。"),
            (159, 730, "スポーツイベントの開催による効果、研究仮説"),
            (27, 714, "大会を開けば町の外から人が集まり、遊具を新しくする話も進む。"),
            (27, 700, "公園に人が来れば、店も増える。"),
            (16, 670, "調査活動"),
            (16, 654, "三十人に聞いた。"),
        ],
    )


def test_body_left_of_a_set_in_heading_stays_under_it(tmp_path, poster_seat):
    utterances = ingest_poster(write_centred_heading_poster(tmp_path / "poster01.pdf"), poster_seat)
    assert [(u.section, u.heading, u.text) for u in utterances] == [
        ("背景と課題", "探究テーマ設定理由", "公園の遊具が古いと聞いた。町広場も少ない。"),
        ("背景と課題", "探究テーマ設定理由", "町に子どもが多いと聞いた。外遊ぶ所がない。"),
        (
            "目的",
            "スポーツイベントの開催による効果、研究仮説",
            "大会を開けば町の外から人が集まり、遊具を新しくする話も進む。公園に人が来れば、店も増える。",
        ),
        ("手法", "調査活動", "三十人に聞いた。"),
    ]
    examples = purpose_examples(utterances)
    assert [u.heading for u in examples] == ["スポーツイベントの開催による効果、研究仮説"]


def test_a_right_column_heading_does_not_take_the_left_column():
    # 「結論」 starts the right column further down. The left column's lines
    # below it still belong to 「目的」.
    left, left_xs = char_positions(("左の段の長い文。", 50))
    fragments = [
        Fragment(STUDENT, 50, 10),
        Fragment("目的", 50, 60, char_positions(("目的", 50))[1]),
        Fragment("結果", 300, 60, char_positions(("結果", 300))[1]),
        Fragment("右の段の文。", 300, 80, char_positions(("右の段の文。", 300))[1]),
        Fragment("結論", 300, 200, char_positions(("結論", 300))[1]),
        Fragment(left, 50, 250, left_xs),
        Fragment("右の段の次の文。", 300, 220, char_positions(("右の段の次の文。", 300))[1]),
    ]
    assert by_name(fragments) == {
        "目的": left,
        "結果": "右の段の文。",
        "結論と展望": "右の段の次の文。",
    }


def test_two_columns_read_as_one_line_are_no_evidence_for_a_lone_heading():
    # Below 「結論」 (right column only), the two columns come out as one line.
    # That line reaches under 「結論」 but must not pull the column left.
    merged, merged_xs = char_positions(("左の文。", 50), ("　" * 12, 98), ("右の文。", 300))
    fragments = [
        Fragment("目的", 50, 60, char_positions(("目的", 50))[1]),
        Fragment("左の段の文。", 50, 80, char_positions(("左の段の文。", 50))[1]),
        Fragment("結論", 300, 200, char_positions(("結論", 300))[1]),
        Fragment(merged, 50, 220, merged_xs),
    ]
    assert by_name(fragments) == {"目的": "左の段の文。左の文。", "結論と展望": "右の文。"}


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
