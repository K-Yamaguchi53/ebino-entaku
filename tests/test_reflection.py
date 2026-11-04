"""The reflection sheet and its code check (SPEC 5-2, 6, 11, 14-14).
Every record here is invented."""

import json
import random

import pytest
from fake_client import FakeClient, text_response

from conftest import COMPANY, DISPLAY_NAME
from ebino.banned_words import banned_in
from ebino.gate import Gate, NameList
from ebino.records import Records
from ebino.session import Library, Refused, Session
from ebino.texts import ASK_BACK_FALLBACK, NAME_IN_QUESTION, TEXTS_DIR, load_text
from test_session import (ANSWERED, SEATS, SPLIT, UTTERANCES, editor_says, librarian_finds, library,
                          moderator_says, u)

FALLBACK = load_text(ASK_BACK_FALLBACK)
GOOD_ASK = '『休みを"決めて取る"／"空いたら取る"』で割れたまま、次の問いへ進んでいる。いまのあなたは、どちらに近い？'
MOVES = [
    {"direction": "question_shift", "material_id": "Q1", "text": "「休みの日」の何を知りたいのかを絞る"},
    {"direction": "silent_seat", "material_id": "S:S03", "text": "まだ誰も聞いていない「保育士」の席で、休みの取り方を確かめる"},
    {"direction": "left_split", "material_id": "P1-1", "text": "「休みは決めて取ります。」と言う人の決め手を確かめる"},
]


def reflection_says(ask_text=GOOD_ASK, ask_material="P1-1", moves=MOVES):
    return text_response({"ask_back": {"material_id": ask_material, "text": ask_text}, "next_moves": moves})


def sitting(answers, tmp_path=None, press=False):
    client = FakeClient(list(ANSWERED) + list(answers))
    session = Session(library(), Gate(client, NameList.build(SEATS, {})), rng=random.Random(1),
                      records=Records(tmp_path) if tmp_path else None)
    session.ask("休みの日って、みんな何してる？")
    if press:
        session.press_split(1, 0)
    return session, client


def begin(session):
    return session.reflect_begin("a_little", "休みをどう決めるかを知りたい")


def test_a_question_back_and_moves_that_hold_the_records_words_are_shown_in_fixed_order():
    session, client = sitting([reflection_says()])
    assert begin(session) == {"status": "ok", "ask_back": GOOD_ASK}
    moves = session.reflect_answer("決めて取るほうに近い")["moves"]
    assert [m["direction"] for m in moves] == ["left_split", "silent_seat", "question_shift"]
    assert moves[0]["label"] == "置いてきた割れ目"
    request = client.requests[-1]
    assert request["model"] == "claude-opus-5-5" and request["output_config"]["effort"] == "medium"


@pytest.mark.parametrize("text, reason", [
    ("「休みは自由に取る」と言う人がいた。いまのあなたは？", "quote_not_in_record"),
    ("「休みは決めて」と言う人がいた。いまのあなたは？", "quote_not_in_record"),  # Cut mid-sentence.
    ("「休みは決めて取ります。」の人のように、決めて取るべき？", "banned_word"),
    ("谷口さんの言葉を読んで、いまのあなたは？", "name"),
    ("「休みは決めて取ります。と言う人がいた。いまのあなたは？", "unbalanced_quote_marks"),
    ("あ" * 161, "too_long"),
    ("「畑は天気しだいなので」と言う人がいた。いまのあなたは？", "quote_not_in_record"),  # Cut mid-sentence.
    ("「大工」の席の言葉を読んで、いまのあなたは？", "quote_not_in_record"),  # No such seat in the materials.
    ("「休みは決めて取ります。」の人のように、頑張って決める？", "banned_word"),  # Outside 「」.
])
def test_a_question_back_that_fails_the_check_becomes_the_fixed_sentence(text, reason):
    session, _ = sitting([reflection_says(ask_text=text)])
    assert begin(session)["ask_back"] == FALLBACK
    assert session.reflection.ask_back_fallback == reason


@pytest.mark.parametrize("text", [
    "「休みは決めて取ります。」と言う人がいた。いまのあなたは、どう取りたい？",
    # One whole sentence of a long quote: more than the old 120 characters.
    "「畑は天気しだいなので、休みは空いたら取ります。」と話す人と、「休みは決めて取ります。」と話す人がいた。"
    "二人の休みの取り方の違いは、仕事のどんなところから生まれていると思う？"
    "いまのあなたが休みの日を考えるなら、どちらの取り方に近くて、それはなぜ？",
    "まだ誰も聞いていない「農家」の席は、休みをどう決めていると思う？",  # A seat's title.
    "「保育士」の席には、まだ誰も聞いていない。そこで何を聞きたい？",  # A silent seat's title.
])
def test_a_question_back_that_holds_the_records_words_passes(text):
    assert len(text) <= 160
    session, _ = sitting([reflection_says(ask_text=text)])
    assert begin(session)["ask_back"] == text
    assert session.reflection.ask_back_fallback == ""


def test_a_banned_word_inside_a_quote_from_the_record_does_not_stop_the_question_back():
    # An adult's own words may hold 頑張って; code has matched them to the record.
    said = "頑張っても、休みは決めて取ります。"
    answers = [librarian_finds("a3"), moderator_says([("a3", said)])]
    client = FakeClient(answers + [reflection_says(ask_text=f"「{said}」と話す人がいた。いまのあなたは？",
                                                   ask_material="U:a3")])
    lib = Library.build(SEATS, UTTERANCES + [u("a3", "S01", said, voice="spoken")], {}, False)
    session = Session(lib, Gate(client, NameList.build(SEATS, {})), rng=random.Random(1))
    session.ask("休みの日って、みんな何してる？")
    assert begin(session)["ask_back"] == f"「{said}」と話す人がいた。いまのあなたは？"
    assert banned_in(said)  # The same words outside 「」 would stop it.


def test_moves_that_fail_are_not_shown_and_only_their_reasons_are_kept():
    moves = [
        {"direction": "left_split", "material_id": "P1-1", "text": "割れた理由を確かめてみたら"},  # Banned.
        {"direction": "left_split", "material_id": "P1-1", "text": "なぜ割れたのかを確かめる"},
        {"direction": "left_split", "material_id": "P1-1", "text": "もう一つ"},  # Same direction twice.
        {"direction": "silent_seat", "material_id": "S:S01", "text": "まだ誰も答えていない所を確かめる"},  # Not silent.
        {"direction": "question_shift", "material_id": "Q1", "text": "何を知りたいの？"},  # A question.
    ]
    session, _ = sitting([reflection_says(moves=moves)])
    begin(session)
    shown = session.reflect_answer("", declined=True)["moves"]
    assert [m["text"] for m in shown] == ["なぜ割れたのかを確かめる"]
    assert session.reflection.moves_stopped == {
        "banned_word": 1, "same_direction_twice": 1, "wrong_material": 1, "move_is_a_question": 1}


def test_a_pressed_split_is_not_a_left_split():
    session, _ = sitting([reflection_says()], press=True)
    begin(session)
    shown = session.reflect_answer("近い")["moves"]
    assert [m["direction"] for m in shown] == ["silent_seat", "question_shift"]


def test_when_the_model_fails_the_fixed_sentence_is_shown_with_no_moves():
    session, _ = sitting([text_response("", stop_reason="refusal")])
    assert begin(session)["ask_back"] == FALLBACK
    assert session.reflection.unavailable == "refusal"
    assert session.reflect_answer("", declined=True)["moves"] == []


def test_the_moderator_reads_the_whole_record_but_no_company_or_name():
    session, client = sitting([editor_says(), reflection_says()])
    session.write_card("S03", "森川さんは休みに何をしますか")  # A name in a card the student wrote.
    session.mark(1, "b1")
    begin(session)
    data = json.loads(client.requests[-1]["messages"][0]["content"])
    kinds = [m["kind"] for m in data["materials"]]
    assert kinds == ["question", "split", "quote", "quote", "quote", "silent_seat", "now_question"]
    split = data["materials"][1]
    assert split["pressed"] is False and split["side_a"] == ["休みは決めて取ります。"]
    assert [m["marked"] for m in data["materials"] if m["kind"] == "quote"] == [False, False, True]
    assert data["changed"] == "少し" and data["first_question"] == "休みの日って、みんな何してる？"
    sent = client.all_sent()
    for word in (COMPANY, "はるかぜ", "架空農園", DISPLAY_NAME, "山川", "谷口", "森川"):
        assert word not in sent
    assert session.reflection.unavailable == ""


def test_a_name_in_the_now_question_asks_again_without_the_model():
    session, client = sitting([])
    sent = len(client.requests)
    view = session.reflect_begin("same", "谷口さんの休みが知りたい")
    assert view == {"status": "ask_again", "message": load_text(NAME_IN_QUESTION)}
    assert session.reflection is None and len(client.requests) == sent


def test_the_sheet_needs_a_round_and_is_begun_once():
    session = Session(library(), Gate(FakeClient([]), NameList.build(SEATS, {})))
    with pytest.raises(Refused):
        session.reflect_begin("same", "問い")
    session, _ = sitting([reflection_says()])
    with pytest.raises(Refused):
        session.reflect_begin("maybe", "問い")
    with pytest.raises(Refused):
        session.reflect_answer("早すぎる")
    begin(session)
    with pytest.raises(Refused):
        begin(session)


def test_the_whole_sheet_and_its_record(tmp_path):
    session, _ = sitting([reflection_says(ask_text="「休みは自由に取る」の人は？")], tmp_path=tmp_path)
    session.mark(1, "a1")
    session.press_split(1, 0)
    begin(session)
    session.reflect_answer("", declined=True)
    with pytest.raises(Refused):
        session.reflect_finish("left_split", "", "", "S01", "")  # Not shown: the split was pressed.
    with pytest.raises(Refused):
        session.reflect_finish("none", "", "", "Z99", "")
    sheet = session.reflect_finish("own", "畑に行って休みの決め方を見る", "休みは何で決まるのか", "S02", "畑の休みが気になった")
    assert sheet["first_question"] == "休みの日って、みんな何してる？"
    assert sheet["met_lives"] == [{"text": "休みは決めて取ります。", "said": True,
                                   "source": {"title": "理容師", "detail": "", "note": ""}}]
    # The sheet drops 「ここで割れた：」; the round table keeps it.
    assert SPLIT[0].startswith("ここで割れた：")
    assert sheet["splits"] == [{"heading": SPLIT[0].removeprefix("ここで割れた："), "pressed": True}]
    assert session.round_view(1)["splits"][0]["heading"] == SPLIT[0]
    assert (sheet["changed"], sheet["ask_back"], sheet["declined"]) == ("少し", FALLBACK, True)
    assert (sheet["chosen"], sheet["move"], sheet["own_move"]) == ("own", None, "畑に行って休みの決め方を見る")
    assert sheet["meet"]["title"] == "農家" and sheet["meet"]["reason"] == "畑の休みが気になった"

    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    kept = record["reflection"]
    assert (kept["changed"], kept["ask_back_fallback"], kept["declined"]) == ("a_little", "quote_not_in_record", True)
    assert kept["rewrite"] == "休みは何で決まるのか" and kept["meet_seat"] == "S02" and kept["finished"]
    assert [m["direction"] for m in kept["moves_shown"]] == ["silent_seat", "question_shift"]
    assert "自由に取る" not in json.dumps(record, ensure_ascii=False)  # Failed words are not kept.


def test_banned_words_are_found_through_width_and_spaces():
    assert banned_in("それが向いて いる") and banned_in("ｵｽｽﾒ") and not banned_in("休みを決めて取る")


@pytest.mark.parametrize("text", [
    "保育士の席で聞いてみて", "休みの決め方を確かめましょう", "この仕事は向いていない", "向いてないかも",
    "外の仕事は向かない", "進路を考える", "決めておくといい", "読んだらいい", "取ればいい",
    "決めた方が良い", "決めたほうが良い", "確かめてほしい", "偉かった", "えらかったね", "素敵な問い",
    "立派な問い", "いい問いだね", "良い問いになった", "よく考えた", "もう一度しよう", "畑に行こう",
    "農家に聞こう", "決め手を確かめよう", "記事を読もう", "農家に会おう", "記事を読んでみて",
])
def test_the_widened_banned_words_stop_these(text):
    assert banned_in(text)


@pytest.mark.parametrize("text", [
    "休みを決めて取る人が、何を決め手にしたのかを確かめる",
    "まだ誰も聞いていない「保育士」の席で、休みの取り方を確かめる",
    "「休みの日」の何を知りたいのかを絞る",
    "なぜ割れたのかを確かめる",
])
def test_the_widened_banned_words_let_these_moves_through(text):
    assert not banned_in(text)


@pytest.mark.parametrize("text", ["選べばいい", "読めばいい", "行けばいい", "遊べばいい", "頼めばいい"])
def test_ba_ii_stops_the_forms_ra_ba_ii_missed(text):
    assert banned_in(text)


@pytest.mark.parametrize("text", ["休みを決めて取る人が、何を決め手にしたのかを確かめる", "「休みの日」の何を知りたいのかを絞る"])
def test_ba_ii_lets_these_moves_through(text):
    assert not banned_in(text)


# Outside the list: the question examples are the teacher's own samples of a
# student's question (直し31続き-2), not words a model writes to a student.
NOT_A_MODELS_SENTENCE = {"question_examples", "question_examples_lead", "question_examples_end"}


def test_no_screen_text_holds_a_banned_word():
    for path in TEXTS_DIR.glob("*.txt"):
        if path.stem == "planted_fake_quote":  # The fake is meant to be stopped.
            continue
        if path.stem in NOT_A_MODELS_SENTENCE:
            continue
        assert not banned_in(path.read_text(encoding="utf-8")), path.name


def test_the_question_examples_are_the_teachers_words_and_outside_the_list():
    examples = (TEXTS_DIR / "question_examples.txt").read_text(encoding="utf-8")
    assert "進路で迷っている。みんなはどうやって決めた？" in examples
    assert "これからの道" not in examples
