"""「もっと聞く」 under the round's last word (the teacher's call on 11/3).
Every seat and piece here is invented."""

import json

import pytest

from ebino import editor, harvest
from ebino.reflection import Reflection
from ebino.session import Refused
from ebino.texts import MORE_CARD_DONE, MORE_END, load_text
from test_closing import QUESTION, says, sitting
from test_session import ANSWERED, UTTERANCES, editor_says, u

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


RANKING = [
    u("r0", "S02", "好きな場所ベスト3", section="ランキング"),
    u("r1", "S02", "１位　川の駅", section="ランキング"),
    u("r2", "S02", "２位　山の上の展望台から見る夕日。", section="ランキング"),
    u("n1", "S02", "畑の朝は、静かで気持ちがいい。", voice="spoken", section="本文"),
    u("n2", "S02", "雨の日は、道具の手入れをします。", voice="spoken", section="本文"),
]


def test_a_ranking_item_gets_the_title_before_it_and_other_pieces_get_none():
    from ebino.closing import ranking_titles

    titles = ranking_titles(UTTERANCES + RANKING)
    assert titles["r1"] == titles["r2"] == "好きな場所ベスト3"
    assert "r0" not in titles and "n1" not in titles and "n2" not in titles


def test_a_ranking_item_heard_has_its_title_over_it_and_the_title_is_not_counted():
    session, client = sitting(ANSWERED + [says(("r2", "２位　山の上の展望台から見る夕日。"),
                                               ("a9", "地元にも、面白い仕事はたくさんあります。"))],
                              kinds={"r2": "joy", "a9": "to_students", "n1": "joy"}, pieces=PIECES + RANKING)
    session.ask(QUESTION)
    view = session.close_round(1)
    word = next(w for w in view["words"] if w["utterance_id"] == "r2")
    assert word["ranking_title"] == "好きな場所ベスト3"
    assert next(w for w in view["words"] if w["utterance_id"] == "a9")["ranking_title"] == ""
    assert "r0" not in session.seen_ids()


def test_more_shows_the_title_over_a_ranking_item_and_nothing_over_other_pieces():
    pieces = PIECES + RANKING + [u("r3", "S02", "３位　駅前の古い本屋さんです。", section="ランキング")]
    session, _ = sitting(ANSWERED + [says(("r2", "２位　山の上の展望台から見る夕日。"))],
                         kinds={"r2": "joy"}, pieces=pieces)
    session.ask(QUESTION)
    session.close_round(1)
    heard = session.hear_more("r2")
    assert heard["piece"]["utterance_id"] == "r3" and heard["piece"]["ranking_title"] == "好きな場所ベスト3"
    assert "r0" not in session.seen_ids() and session.mores["r2"].shown == ["r3"]
    session, _ = sitting(ANSWERED + [says(("n1", "畑の朝は、静かで気持ちがいい。"))], kinds={"n1": "joy"}, pieces=pieces)
    session.ask(QUESTION)
    session.close_round(1)
    assert session.hear_more("n1")["piece"]["ranking_title"] == ""


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
