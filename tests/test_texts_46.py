"""直し46: the teacher's words decided on 11/7, as they are (the other lines
of the same tables are left as they were)."""


from ebino import hitokoto, texts


def test_the_one_to_one_line_is_the_teachers():
    assert texts.now_lines()["one"]["text"] == "この人に聞こう。質問を選ぼう。"


def test_the_trails_marks_are_fusen_and_the_three_kinds_stay():
    words = texts.id_table(texts.TRAIL_MARK_WORDS, texts.TRAIL_MARK_WORD_IDS)
    assert words["lead"] == "今日の道すじ。ふせんを貼りたい所があれば、貼ってみよう（貼らなくてもいい）。"
    assert words["sheet"] == "ふせんを貼った所"
    assert list(texts.id_table(texts.TRAIL_MARKS, texts.TRAIL_MARK_IDS).values()) == [
        "いちばんおどろいた", "問いが深まった", "もっと聞きたかった"]


def test_the_three_hitokoto_lines_and_the_ones_left_as_they_were():
    words = hitokoto.words()
    assert words["ask_self"] == "その人の話の、どこが自分にも当てはまりそう？"
    assert words["scale_up"] == "迷いが増えたね。どこが増えた？"
    assert words["way_q"] == "まだ決めなくていい。気になっている進み方は？"
    assert words["story_way"] == "頭に置いておきたい道は{*text}。"
    assert words["way_ok"] == "置いておく" and words["way_example"] == "例：農業もおもしろいかも"
    assert words["who_teacher"] == "先生の問い"
