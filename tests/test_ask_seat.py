"""「司会が○○に聞いてみる」 (SPEC 14-53 B). Every seat and piece is invented."""

import json
from dataclasses import replace

import pytest

from ebino import ask_seat, editor, harvest
from ebino.ingest.utterance import TEACHER_ARTICLE_NOTE
from ebino.reflection import Reflection
from ebino.session import Refused
from ebino.texts import (ASK_ANSWER_SAID, ASK_ANSWER_WRITTEN, ASK_NOT_ANSWERED, ASK_OTHER_SIDE,
                         ASK_OTHER_SIDE_COMPANY, ASK_OTHER_SIDE_SENIOR, ASK_OTHER_SIDE_WRITTEN, ASK_WHY,
                         ASK_WHY_COMPANY, ASK_WHY_SENIOR, ASK_WHY_WRITTEN, load_text)
from test_closing import QUESTION, says, sitting
from test_session import ANSWERED, SPLIT, editor_says, librarian_finds, moderator_says, u

PIECES = [
    u("b7", "S02", "雨の日は、畑に出ないで休みます。", voice="spoken"),
    u("b6", "S02", "この方は、休みを天気で決めている。"),
    u("a6", "S01", "店を継いだのは、父の背中を見ていたからです。", voice="spoken"),
]
OTHER_SIDE = "『休みは決めて取ります。』と言った人がいる。あなたは？"


def round_one(answers=(), tmp_path=None, pieces=PIECES):
    session, client = sitting(ANSWERED + list(answers), tmp_path=tmp_path, kinds={}, pieces=pieces)
    session.ask(QUESTION)
    return session, client


def test_the_card_passes_a_split_quote_to_the_other_side_and_asks_nothing_until_pressed():
    session, client = round_one()
    before = len(client.requests)
    view = session.ask_card(1)
    # The split: 「休みは決めて取ります。」 (S01) against 「空いたら取る」 (S02).
    assert view["card"] == {"form": "other_side", "seat_id": "S02", "header": "司会が、農家に聞いてみる",
                            "question": OTHER_SIDE}
    assert view["asked"] is None
    assert len(client.requests) == before  # No model is called for the card.
    assert session.rounds[0].ask_seat is None


def test_not_pressing_means_nothing_happens_and_nothing_is_recorded(tmp_path):
    session, client = round_one(tmp_path=tmp_path)
    session.ask_card(1)
    session.ask_card(1)
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert record["rounds"][0]["ask_seat"] is None
    assert len(client.requests) == 2  # The round's librarian and moderator only.


def test_a_marked_quote_comes_first_and_is_asked_back_to_its_own_seat():
    session, _ = round_one()
    session.mark(1, "b1")
    card = session.ask_card(1)["card"]
    assert card["form"] == "why" and card["seat_id"] == "S02"
    assert card["question"] == "『畑は天気しだいなので、休みは空いたら取ります。』　そう考えるのは、なぜですか？"


B7 = ("b7", "雨の日は、畑に出ないで休みます。")


def picked_ids(client):
    return [p["utterance_id"] for p in json.loads(client.requests[-1]["messages"][0]["content"])["pieces"]]


HEADING = SPLIT[0]
A2 = ("a2", "月曜は必ず店を閉める。")  # An article's words (S01).
B6 = ("b6", "この方は、休みを天気で決めている。")  # An article's words (S02).
B1 = ("b1", "畑は天気しだいなので、休みは空いたら取ります。")  # Said (S02).


def split_round(quotes, side_a, side_b, pieces=PIECES):
    session, _ = sitting([librarian_finds(*[i for i, _ in quotes]),
                          moderator_says(list(quotes), [(HEADING, side_a, side_b)])], kinds={}, pieces=pieces)
    session.ask(QUESTION)
    return session


# The teacher's own article (SPEC 14-50): voice own, but shown with a note.
T1 = ("t1", "休みの日は、朝から店の前を掃いている。")
WITH_TEACHER = PIECES + [replace(u("t1", "S01", T1[1], voice="own"), source_note=TEACHER_ARTICLE_NOTE)]


def test_the_teachers_article_is_asked_in_the_written_form_by_its_note_not_its_voice():
    session = split_round([T1, B6], ["t1"], ["b6"], pieces=WITH_TEACHER)
    card = session.ask_card(1)["card"]
    assert card["seat_id"] == "S02"
    assert card["question"] == "『休みの日は、朝から店の前を掃いている。』と記事に書かれた人がいる。あなたは？"


def test_a_marked_teachers_article_asks_why_in_the_written_form():
    session = split_round([T1, B6], ["t1"], ["b6"], pieces=WITH_TEACHER)
    session.mark(1, "t1")
    card = session.ask_card(1)["card"]
    assert card["form"] == "why" and card["seat_id"] == "S01"
    assert card["question"] == "『休みの日は、朝から店の前を掃いている。』と記事に書かれています。そう考えるのは、なぜですか？"


C9 = ("c9", "当社は、雨の日を社員の休みにしています。")  # A company's introduction (S02).
WITH_COMPANY = PIECES + [u("c9", "S02", C9[1], voice="company")]


def test_a_companys_introduction_is_never_called_an_article():
    session = split_round([C9, A2], ["c9"], ["a2"], pieces=WITH_COMPANY)
    card = session.ask_card(1)["card"]
    assert card["seat_id"] == "S01"
    assert card["question"] == "『当社は、雨の日を社員の休みにしています。』と会社の紹介に書かれています。あなたは？"
    assert "記事" not in card["question"]
    session.mark(1, "c9")
    card = session.ask_card(1)["card"]
    assert card["form"] == "why" and "記事" not in card["question"]
    assert card["question"] == "『当社は、雨の日を社員の休みにしています。』と会社の紹介に書かれています。そう考えるのは、なぜですか？"
    assert load_text(ASK_OTHER_SIDE_COMPANY) != load_text(ASK_OTHER_SIDE_WRITTEN)
    assert load_text(ASK_WHY_COMPANY) != load_text(ASK_WHY_WRITTEN)


E5 = ("e5", "朝のあいさつで、その日の調子が分かります。")  # A senior employee's words (S02).
WITH_SENIOR = PIECES + [u("e5", "S02", E5[1], voice="senior")]


def test_a_senior_employees_words_get_the_senior_form_and_never_article():
    session = split_round([E5, A2], ["e5"], ["a2"], pieces=WITH_SENIOR)
    card = session.ask_card(1)["card"]
    assert card["form"] == "other_side" and card["seat_id"] == "S01"
    assert card["question"] == "『朝のあいさつで、その日の調子が分かります。』と、この職場の先輩社員が書いています。あなたは？"
    assert "記事" not in card["question"]
    session.mark(1, "e5")
    card = session.ask_card(1)["card"]
    assert card["form"] == "why" and card["seat_id"] == "S02" and "記事" not in card["question"]
    assert card["question"] == ("『朝のあいさつで、その日の調子が分かります。』と、この職場の先輩社員が書いています。"
                                "そう書いたのは、なぜだと思いますか？")
    assert "そう考えるのは" not in card["question"]
    assert load_text(ASK_OTHER_SIDE_SENIOR) not in {load_text(ASK_OTHER_SIDE_WRITTEN), load_text(ASK_OTHER_SIDE_COMPANY)}
    assert load_text(ASK_WHY_SENIOR) not in {load_text(ASK_WHY_WRITTEN), load_text(ASK_WHY_COMPANY)}


A6 = ("a6", "店を継いだのは、父の背中を見ていたからです。")  # Said (S01).


def test_words_with_no_note_come_before_a_senior_employees_words():
    session = split_round([E5, A6], ["e5"], ["a6"], pieces=WITH_SENIOR)
    card = session.ask_card(1)["card"]
    assert card["seat_id"] == "S02"
    assert card["question"] == "『店を継いだのは、父の背中を見ていたからです。』と言った人がいる。あなたは？"


E4 = ("e4", "休みの日は、先輩と釣りに行きます。")  # A senior employee's words (S01).


def test_an_article_and_a_company_keep_their_forms_beside_a_senior_employee():
    session = split_round([A2, E5], ["a2"], ["e5"], pieces=WITH_SENIOR)
    assert session.ask_card(1)["card"]["question"] == "『月曜は必ず店を閉める。』と記事に書かれた人がいる。あなたは？"
    pieces = WITH_COMPANY + [u("e4", "S01", E4[1], voice="senior")]
    session = split_round([C9, E4], ["c9"], ["e4"], pieces=pieces)
    card = session.ask_card(1)["card"]
    assert card["seat_id"] == "S01"
    assert card["question"] == "『当社は、雨の日を社員の休みにしています。』と会社の紹介に書かれています。あなたは？"


def test_an_interview_articles_quote_keeps_the_article_form_beside_a_company():
    session = split_round([A2, C9], ["a2"], ["c9"], pieces=WITH_COMPANY)
    card = session.ask_card(1)["card"]
    assert card["question"] == "『月曜は必ず店を閉める。』と記事に書かれた人がいる。あなたは？"


def test_words_with_no_note_come_before_the_teachers_article():
    session = split_round([T1, B1], ["t1"], ["b1"], pieces=WITH_TEACHER)
    card = session.ask_card(1)["card"]
    assert card["seat_id"] == "S01"
    assert card["question"] == "『畑は天気しだいなので、休みは空いたら取ります。』と言った人がいる。あなたは？"


def test_an_articles_quote_never_gets_someone_said_it():
    session = split_round([A2, B6], ["a2"], ["b6"])
    card = session.ask_card(1)["card"]
    assert card["form"] == "other_side" and card["seat_id"] == "S02"
    assert card["question"] == "『月曜は必ず店を閉める。』と記事に書かれた人がいる。あなたは？"
    assert "と言った人がいる" not in card["question"]
    assert load_text(ASK_OTHER_SIDE_WRITTEN) != load_text(ASK_OTHER_SIDE)


def test_the_persons_own_words_on_either_side_come_first():
    # Side A holds only an article's words; side B holds the person's own.
    session = split_round([A2, B1], ["a2"], ["b1"])
    card = session.ask_card(1)["card"]
    assert card["seat_id"] == "S01"
    assert card["question"] == "『畑は天気しだいなので、休みは空いたら取ります。』と言った人がいる。あなたは？"


def test_a_marked_articles_quote_asks_why_in_the_written_form():
    session, _ = round_one()
    session.mark(1, "a2")
    card = session.ask_card(1)["card"]
    assert card["form"] == "why" and card["seat_id"] == "S01"
    assert card["question"] == "『月曜は必ず店を閉める。』と記事に書かれています。そう考えるのは、なぜですか？"
    assert load_text(ASK_WHY_WRITTEN) != load_text(ASK_WHY)


def test_pressed_the_librarian_gathers_that_seats_pieces_and_the_moderator_picks_one():
    # Another seat's piece (a6) and a piece already shown (b1) are not on the
    # librarian's shelf, so naming them gives nothing.
    session, client = round_one([librarian_finds("a6", "b1", "b7", "b6"), says(B7)])
    view = session.ask_the_seat(1)
    assert client.requests[-2]["model"] == "claude-sonnet-5-5"
    assert OTHER_SIDE in json.dumps(client.requests[-2], ensure_ascii=False)
    assert client.requests[-1]["model"] == "claude-sonnet-5-5"  # The moderator picks, by ID.
    assert client.requests[-1]["output_config"]["format"]["type"] == "json_schema"
    assert picked_ids(client) == ["b7", "b6"]
    assert OTHER_SIDE in client.requests[-1]["messages"][0]["content"]
    assert view["status"] == "answered" and view["piece"]["utterance_id"] == "b7"
    assert view["label"] == load_text(ASK_ANSWER_SAID) == "この人が、別の所で話したこと"
    assert view["piece"]["said"] and view["question"] == OTHER_SIDE


def test_when_no_gathered_piece_answers_the_question_it_says_not_answered_yet():
    # The librarian gathers widely: here only a piece of background, which
    # the moderator does not pick.
    session, client = round_one([librarian_finds("b6"), says()])
    view = session.ask_the_seat(1)
    assert view["status"] == "not_found" and view["piece"] is None
    assert view["not_answered"] == load_text(ASK_NOT_ANSWERED)
    assert client.requests[-1]["model"] == "claude-sonnet-5-5"


@pytest.mark.parametrize("pick", [("a6", "店を継いだのは、父の背中を見ていたからです。"), ("b7", "雨の日は畑に出ない。")])
def test_a_pick_not_gathered_or_a_copy_the_guard_stops_is_not_shown(pick):
    session, _ = round_one([librarian_finds("b7"), says(pick)])
    view = session.ask_the_seat(1)
    assert view["status"] == "not_found" and view["piece"] is None
    assert session.rounds[0].ask_seat.guard_stopped == (1 if pick[0] == "b7" else 0)


def test_a_fragment_is_not_on_the_librarians_shelf():
    pieces = PIECES + [u("b5", "S02", "と話していた。"), u("b4", "S02", "うれしかった", voice="spoken")]
    session, client = round_one([librarian_finds("b5", "b4", "b7"), says(B7)], pieces=pieces)
    view = session.ask_the_seat(1)
    assert picked_ids(client) == ["b7"]  # b5 and b4, named first, are not on the shelf.
    assert view["piece"]["utterance_id"] == "b7"


def test_a_ranking_item_given_as_the_answer_has_its_title_over_it():
    pieces = PIECES + [u("r0", "S02", "好きな場所ベスト3", section="ランキング"),
                       u("r1", "S02", "１位　雨の日の畑の小屋の中です。", section="ランキング")]
    session, _ = round_one([librarian_finds("r1"), says(("r1", "１位　雨の日の畑の小屋の中です。"))], pieces=pieces)
    view = session.ask_the_seat(1)
    assert view["piece"]["utterance_id"] == "r1" and view["piece"]["ranking_title"] == "好きな場所ベスト3"
    assert "r0" not in session.seen_ids()


def test_an_articles_piece_never_gets_this_person_spoke_over_it():
    session, _ = round_one([librarian_finds("b6"), says(B6)])
    view = session.ask_the_seat(1)
    assert view["piece"]["utterance_id"] == "b6" and not view["piece"]["said"]
    assert view["label"] == load_text(ASK_ANSWER_WRITTEN) != load_text(ASK_ANSWER_SAID)
    assert "この人が" not in view["label"]
    assert view["piece"]["source"]["note"] == "取材記事（本人確認済み）"


def test_once_per_round():
    session, _ = round_one([librarian_finds("b7"), says(B7)])
    session.ask_the_seat(1)
    with pytest.raises(Refused, match="already_asked"):
        session.ask_the_seat(1)
    assert session.ask_card(1)["card"] is None and session.ask_card(1)["asked"]["status"] == "answered"


def test_nothing_found_says_not_answered_yet_and_makes_no_card(tmp_path):
    session, client = round_one([librarian_finds()], tmp_path=tmp_path)
    view = session.ask_the_seat(1)
    assert view["status"] == "not_found" and view["piece"] is None
    assert view["not_answered"] == load_text(ASK_NOT_ANSWERED) == "まだ答えていない"
    assert not view["carded"] and session.cards == []
    # No way from the card's question to a question card is left.
    assert not hasattr(session, "ask_card_to_seat") and not hasattr(editor, "ORIGIN_ASK_SEAT")
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert record["rounds"][0]["ask_seat"] == {
        "form": "other_side", "seat_id": "S02", "quote_id": "a1", "status": "not_found", "reason": "",
        "answer_id": "", "guard_stopped": 0}
    assert record["cards"] == []


def test_under_not_answered_yet_the_student_writes_their_own_card_to_that_seat():
    session, _ = round_one([librarian_finds(), editor_says(["S02"])])
    session.ask_the_seat(1)
    card = session.write_card("S02", "雨の日は何をしていますか？")
    assert card["seat_id"] == "S02" and card["origin"] == editor.ORIGIN_STUDENT
    assert card["text"] == "雨の日は何をしていますか？" and OTHER_SIDE not in card["text"]
    assert session.asked_view(1)["carded"]
    # Written at a seat that spoke, it is not the move 「黙っていた席に質問カードを書いた」.
    session.reflection = Reflection("same", "休みは何で決まるのか")
    assert "card_at_silent_seat" not in [f.code for f in harvest.found_moves(session, str)]


def test_with_an_answer_found_a_card_to_that_seat_is_one_to_a_seat_that_spoke():
    # S02 spoke in the round: its lamp card at the table opens the same card
    # (直し26-2), so it is taken; it is still not 「黙っていた席」's.
    session, _ = round_one([librarian_finds("b7"), says(B7)])
    session.ask_the_seat(1)
    card = session.write_card("S02", "雨の日は何をしていますか？")
    assert card["seat_id"] == "S02" and card["origin"] == editor.ORIGIN_STUDENT
    assert "S02" in session.spoken_seats() and "S02" not in session.silent_seats()


def test_a_failed_model_shows_the_fixed_sentence_and_keeps_the_reason():
    session, _ = round_one()  # Nothing left for the librarian.
    view = session.ask_the_seat(1)
    assert view["status"] == "unavailable" and view["message"]
    assert session.rounds[0].ask_seat.reason


@pytest.mark.parametrize("template", [
    "『{quote}』と『休みはいらない』と言った人がいる。あなたは？",  # Words not in the record.
    "『{quote}』と言った人がいる。頑張って答えて。",  # A banned word outside the quote marks.
    "『{quote}』と言った人がいる。山川さんは？",  # A name.
    "『{quote}と言った人がいる。あなたは？",  # Unbalanced.
])
def test_a_question_whose_quote_marks_do_not_match_the_record_gives_no_card(monkeypatch, template):
    monkeypatch.setattr(ask_seat, "load_text", lambda name: template)
    session, _ = round_one()
    assert session.ask_card(1)["card"] is None
    with pytest.raises(Refused, match="no_ask_card"):
        session.ask_the_seat(1)


def test_no_split_and_no_mark_gives_no_card():
    session, _ = sitting([librarian_finds("a1"), moderator_says([("a1", "休みは決めて取ります。")])],
                         kinds={}, pieces=PIECES)
    session.ask(QUESTION)
    assert session.ask_card(1) == {"round": 1, "card": None, "asked": None}


def test_more_can_be_pressed_under_the_answer():
    pieces = PIECES + [u("b5", "S02", "晴れたら、朝から畑です。", voice="spoken")]
    session, _ = round_one([librarian_finds("b7"), says(B7)], pieces=pieces)
    session.ask_the_seat(1)
    heard = session.hear_more("b7")
    assert heard["pieces"][0]["utterance_id"] == "b6"  # Next in the same section, as recorded.


def test_a_silent_round_has_no_card():
    session, _ = sitting([librarian_finds(), editor_says()], kinds={}, pieces=PIECES)
    session.ask(QUESTION)
    with pytest.raises(Refused, match="no_seat_spoke"):
        session.ask_card(1)
