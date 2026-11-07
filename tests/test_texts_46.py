"""直し46: the teacher's words decided on 11/7, as they are (the other lines
of the same tables are left as they were)."""


import pytest

from ebino import hitokoto, texts


def test_the_one_to_one_line_is_the_teachers():
    assert texts.now_lines()["one"]["text"] == "この人に聞こう。質問を選ぼう。"


def test_the_trails_marks_are_fusen_and_the_three_kinds_stay():
    words = texts.id_table(texts.TRAIL_MARK_WORDS, texts.TRAIL_MARK_WORD_IDS)
    assert words["lead"] == "今日の道すじ。ふせんを貼りたい所があれば、貼ってみよう（貼らなくてもいい）。"
    assert words["sheet"] == "ふせんを貼った所"
    assert list(texts.id_table(texts.TRAIL_MARKS, texts.TRAIL_MARK_IDS).values()) == [
        "はじめて知った・気づいた", "問いが深まった", "もっと聞きたかった"]  # 直し49 段3: surprised's words.


def test_the_three_hitokoto_lines_and_the_ones_left_as_they_were():
    words = hitokoto.words()
    assert words["ask_self"] == "その人の話の、どこが自分にも当てはまりそう？"
    assert words["scale_up"] == "迷いが増えたね。どこが増えた？"
    # 直し48 段7 (叩き台; the teacher, 11/7: 「伝わりにくい」).
    assert words["way_q"] == "まだ決めなくていい。このあと、どうやって進んでみたい？"
    assert words["story_way"] == "頭に置いておきたい進み方は{*text}。"
    assert words["way_ok"] == "置いておく" and words["way_example"] == "例：農業もおもしろいかも"
    assert words["who_teacher"] == "先生の問い"


def test_the_ais_cards_on_the_host_page_are_the_teachers_and_a_row_missing_stops(tmp_path, monkeypatch):
    intro = texts.ai_roles_intro()
    assert intro == {
        "coach": {"knows": "学校の先生たちが、生徒に大事にしてほしいと思っている考え方を知っている。",
                  "does": "→ その考え方から、あなた自身に1つ問う。"},
        "observer": {"knows": "会社を経営する人・人を採る人・大学で研究する人の見方を知っている。",
                     "does": "→ その見方から、あなたの考えを1つ聞く。"}}
    lines = (texts.TEXTS_DIR / "ai_roles_intro.tsv").read_text(encoding="utf-8").splitlines()
    (tmp_path / "ai_roles_intro.tsv").write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    monkeypatch.setattr(texts, "TEXTS_DIR", tmp_path)
    with pytest.raises(ValueError):
        texts.ai_roles_intro()


def test_the_guides_note_under_the_cards_is_a_row_of_its_own():
    assert "roles_note" in texts.GUIDE_IDS
    assert texts.id_table(texts.GUIDE, texts.GUIDE_IDS)["roles_note"] == "どちらも AI です。町の人ではありません。"
