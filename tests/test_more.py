"""「もっと聞く」 under the round's last word (the teacher's call on 11/3).
Every seat and piece here is invented."""

import json

import pytest

from ebino import editor, harvest
from ebino.reflection import Reflection
from ebino.session import Refused
from ebino.texts import MORE_CARD_DONE, MORE_END, load_text
from test_closing import QUESTION, says, sitting
from test_session import ANSWERED, editor_says, u

PIECES = [
    u("a9", "S01", "地元にも、面白い仕事はたくさんあります。", voice="spoken", section="高校生に一言"),
    u("x1", "S01", "店は駅の近くにあります。", section="会社PR"),  # Another section between.
    u("a9b", "S01", "だから、外に出る前に、町を歩いてほしい。", section="高校生に一言"),
    u("a9c", "S01", "店に来てくれたら、話します。", voice="spoken", section="高校生に一言"),
    u("a9d", "S01", "それが私の願いです。", voice="spoken", section="高校生に一言"),
    u("b9", "S02", "畑は毎日ちがう顔をします。", voice="senior", section="先輩社員からのメッセージ"),
]
KINDS = {"a9": "to_students", "b9": "joy"}
LAST_WORDS = [says(("a9", "地元にも、面白い仕事はたくさんあります。"), ("b9", "畑は毎日ちがう顔をします。"))]


def closed(tmp_path=None, more_answers=()):
    session, client = sitting(ANSWERED + LAST_WORDS + list(more_answers), tmp_path=tmp_path,
                              kinds=KINDS, pieces=PIECES)
    session.ask(QUESTION)
    session.close_round(1)
    return session, client


def test_a_press_shows_the_next_piece_of_the_same_seat_and_section_as_recorded():
    session, client = closed()
    before = len(client.requests)
    heard = session.hear_more("a9")
    assert heard["piece"]["utterance_id"] == "a9b"  # x1 is in another section.
    assert heard["piece"]["text"] == "だから、外に出る前に、町を歩いてほしい。"
    assert not heard["piece"]["said"] and heard["piece"]["source"]["note"] == "取材記事（本人確認済み）"
    assert heard["can_press"] and not heard["ended"]
    assert len(client.requests) == before  # No model is used.


def test_two_presses_from_one_piece_and_no_more():
    session, _ = closed()
    session.hear_more("a9")
    second = session.hear_more("a9")
    assert second["piece"]["utterance_id"] == "a9c" and second["piece"]["said"]
    assert not second["can_press"]
    with pytest.raises(Refused, match="no_more_presses"):
        session.hear_more("a9")


def test_the_end_of_the_section_says_not_heard_yet_and_a_press_makes_a_card():
    session, client = closed(more_answers=[editor_says(["S02"])])
    heard = session.hear_more("b9")
    assert heard == {"utterance_id": "b9", "piece": None, "ended": True, "can_press": False}
    assert load_text(MORE_END) == "ここから先は、まだ聞いていない"
    assert load_text(MORE_CARD_DONE)
    card = session.more_card("b9")
    assert card["seat_id"] == "S02" and card["text"] == QUESTION and card["origin"] == editor.ORIGIN_NOT_HEARD
    assert session.cards[-1].card_id == card["card_id"]
    assert client.requests[-1]["model"] == "claude-sonnet-5-5"  # The editor writes the back, as for any card.
    with pytest.raises(Refused, match="not_ready_for_card"):
        session.more_card("b9")  # Once.


def test_a_card_is_made_only_after_the_section_ended():
    session, _ = closed()
    session.hear_more("a9")
    with pytest.raises(Refused, match="not_ready_for_card"):
        session.more_card("a9")


@pytest.mark.parametrize("piece", ["a1", "a9b", "x1", "zz", ["a9"]])
def test_only_a_last_word_can_be_pressed_under(piece):
    session, _ = closed()
    with pytest.raises(Refused, match="not_a_last_word"):
        session.hear_more(piece)


def test_pieces_heard_are_not_shown_again_as_a_last_word():
    session, client = closed()
    session.hear_more("a9")
    assert "a9b" in session.seen_ids()


def test_presses_and_the_card_are_recorded_without_words_and_are_not_moves(tmp_path):
    session, _ = closed(tmp_path=tmp_path, more_answers=[editor_says()])
    session.hear_more("a9")
    session.hear_more("b9")
    session.more_card("b9")
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert record["more"] == [
        {"origin_id": "a9", "round": 1, "presses": 1, "shown_ids": ["a9b"], "ended": False, "card_id": ""},
        {"origin_id": "b9", "round": 1, "presses": 1, "shown_ids": [], "ended": True,
         "card_id": session.cards[-1].card_id},
    ]
    assert "町を歩いて" not in json.dumps(record["more"], ensure_ascii=False)
    session.reflection = Reflection("same", "休みは何で決まるのか")
    codes = [f.code for f in harvest.found_moves(session, str)]
    assert "card_at_silent_seat" not in codes
