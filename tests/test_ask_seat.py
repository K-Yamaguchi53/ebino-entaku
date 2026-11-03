"""「司会が○○に聞いてみる」 (SPEC 14-53 B). Every seat and piece is invented."""

import json

import pytest

from ebino import ask_seat, editor
from ebino.session import Refused
from ebino.texts import ASK_ANSWER_SAID, ASK_ANSWER_WRITTEN, ASK_NOT_ANSWERED, load_text
from test_closing import QUESTION, sitting
from test_session import ANSWERED, editor_says, librarian_finds, moderator_says, u

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


def test_pressed_the_librarian_looks_only_in_that_seats_pieces_and_the_guard_passes_it():
    # Another seat's piece (a6) and a piece already shown (b1) are not on the
    # librarian's shelf, so naming them gives nothing.
    session, client = round_one([librarian_finds("a6", "b1", "b7")])
    view = session.ask_the_seat(1)
    assert client.requests[-1]["model"] == "claude-sonnet-5-5"
    assert OTHER_SIDE in json.dumps(client.requests[-1], ensure_ascii=False)
    assert view["status"] == "answered" and view["piece"]["utterance_id"] == "b7"
    assert view["label"] == load_text(ASK_ANSWER_SAID) == "この人が、別の所で話したこと"
    assert view["piece"]["said"] and view["question"] == OTHER_SIDE


def test_a_fragment_is_not_on_the_librarians_shelf():
    pieces = PIECES + [u("b5", "S02", "と話していた。"), u("b4", "S02", "うれしかった", voice="spoken")]
    session, _ = round_one([librarian_finds("b5", "b4", "b7")], pieces=pieces)
    view = session.ask_the_seat(1)
    assert view["piece"]["utterance_id"] == "b7"  # b5 and b4, named first, are not on the shelf.


def test_an_articles_piece_never_gets_this_person_spoke_over_it():
    session, _ = round_one([librarian_finds("b6")])
    view = session.ask_the_seat(1)
    assert view["piece"]["utterance_id"] == "b6" and not view["piece"]["said"]
    assert view["label"] == load_text(ASK_ANSWER_WRITTEN) != load_text(ASK_ANSWER_SAID)
    assert "この人が" not in view["label"]
    assert view["piece"]["source"]["note"] == "取材記事（本人確認済み）"


def test_once_per_round():
    session, _ = round_one([librarian_finds("b7")])
    session.ask_the_seat(1)
    with pytest.raises(Refused, match="already_asked"):
        session.ask_the_seat(1)
    assert session.ask_card(1)["card"] is None and session.ask_card(1)["asked"]["status"] == "answered"


def test_nothing_found_says_not_answered_yet_and_a_press_makes_a_card(tmp_path):
    session, client = round_one([librarian_finds(), editor_says(["S02"])], tmp_path=tmp_path)
    view = session.ask_the_seat(1)
    assert view["status"] == "not_found" and view["piece"] is None
    assert view["not_answered"] == load_text(ASK_NOT_ANSWERED) == "まだ答えていない"
    card = session.ask_card_to_seat(1)
    assert card["seat_id"] == "S02" and card["text"] == OTHER_SIDE and card["origin"] == editor.ORIGIN_ASK_SEAT
    with pytest.raises(Refused, match="not_ready_for_card"):
        session.ask_card_to_seat(1)
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert record["rounds"][0]["ask_seat"] == {
        "form": "other_side", "seat_id": "S02", "quote_id": "a1", "status": "not_found", "reason": "",
        "answer_id": "", "guard_stopped": 0, "card_id": card["card_id"]}


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
    session, _ = round_one([librarian_finds("b7")], pieces=pieces)
    session.ask_the_seat(1)
    heard = session.hear_more("b7")
    assert heard["piece"]["utterance_id"] == "b6"  # Next in the same section, as recorded.


def test_a_silent_round_has_no_card():
    session, _ = sitting([librarian_finds(), editor_says()], kinds={}, pieces=PIECES)
    session.ask(QUESTION)
    with pytest.raises(Refused, match="no_seat_spoke"):
        session.ask_card(1)
