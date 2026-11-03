"""The round's last word, 「最後に、何か伝えたいことはありますか」 (SPEC 14-53 A,
widened by the teacher on 11/3: the piece is picked by its kind of talk).
Every seat, piece and kind here is invented."""

import json
import random

import pytest
from fake_client import FakeClient, text_response

from conftest import COMPANY, DISPLAY_NAME, make_seat
from ebino import closing
from ebino.closing import is_ranking_title
from ebino.gate import Gate, NameList
from ebino.records import Records
from ebino.session import Library, Refused, Session
from ebino.texts import CLOSING_QUESTION, load_text
from test_session import ANSWERED, SEATS, UTTERANCES, librarian_finds, moderator_says, u

QUESTION = "休みの日って、みんな何してる？"

MORE_SEATS = [
    make_seat(seat_id="O02", kind="outsider_teacher", title="先生（架空）", company="", display_name="",
              source_file="teacher01.docx"),
]
ALL_SEATS = SEATS + MORE_SEATS
PIECES = [
    u("a9", "S01", "地元にも、面白い仕事はたくさんあります。休みの日も、町を歩いてみてください。",
      voice="spoken", section="高校生に一言"),
    u("a8", "S01", "やってよかったことベスト3", section="ランキング"),
    u("a7", "S01", "休みの日は、川で釣りをします。"),
    u("a6", "S01", "店を継いだのは、父の背中を見ていたからです。", voice="spoken"),
    u("a5", "S01", "店は駅の近くにあります。"),
    u("b9", "S02", "畑は毎日ちがう顔をします。", voice="senior", section="先輩社員からのメッセージ"),
    u("b8", "S02", "朝は四時に起きて、畑を見回ります。"),
    u("p9", "P01", "川は町の鏡だと分かった。これからも調べ続けたい。", voice="own", kind="poster",
      section="結論と展望", heading="結論と展望"),
    u("o9", "O02", "迷う時間も、大事な時間です。", voice="own", kind="outsider_teacher", section="高校生に一言"),
]
KINDS = {
    "a9": "to_students", "a8": "joy", "a7": "refresh", "a6": "reason", "a5": "none",
    "b9": "joy", "b8": "daily", "p9": "future", "o9": "to_students",
    "a1": "values",  # Shown as a quote in the round: never again in the last word.
    # a2, b1, c1, p1: never answered by the tagger, so none.
}


def says(*picks):
    return text_response({"picks": [{"utterance_id": i, "text": t} for i, t in picks]})


def sitting(answers, tmp_path=None, kinds=KINDS, pieces=PIECES):
    client = FakeClient(list(answers))
    lib = Library.build(ALL_SEATS, UTTERANCES + pieces, {}, False, kinds)
    session = Session(lib, Gate(client, NameList.build(ALL_SEATS, {})), rng=random.Random(1),
                      records=Records(tmp_path) if tmp_path else None)
    return session, client


def sent_ids(client):
    return [p["utterance_id"] for p in json.loads(client.requests[-1]["messages"][0]["content"])["pieces"]]


# --- which pieces may answer: by kind, in code ---

@pytest.mark.parametrize("text, title", [
    ("やってよかったことベスト3", True),
    ("好きな場所ランキング５", True),
    ("休みの日にしたいことベスト３！", True),
    ("ベスト3に入るのは、朝の静けさです。", False),
    ("ランキングは気にしません", False),
    ("1位　朝の店の静けさ", False),
])
def test_a_rankings_title_alone_is_known_by_code(text, title):
    assert is_ranking_title(text) is title


def test_pieces_of_kind_none_unanswered_and_ranking_titles_never_answer():
    session, _ = sitting([])
    held = session.library.closing_pieces
    assert {kind: [e.utterance_id for e in pieces] for kind, pieces in held["S01"].items()} == {
        "to_students": ["a9"], "refresh": ["a7"], "reason": ["a6"], "values": ["a1"]}
    assert "a8" not in json.dumps({s: {k: [e.utterance_id for e in v] for k, v in by.items()}
                                   for s, by in held.items()})
    assert set(held) == {"S01", "S02", "P01", "O02"}  # S03 holds only an unanswered piece.
    assert session.library.kind_order[0] == "to_students" and session.library.kind_order[-1] == "none"


@pytest.mark.parametrize("text, fragment", [
    ("と話していた。", True), ("うれしかった", True), ("って笑っていました。", True),
    ("休みの日は、川で釣りをします。", False), ("いつも楽しく働いています", False),
])
def test_a_fragment_is_known_by_code(text, fragment):
    assert closing.is_fragment(text) is fragment


def test_a_fragment_never_gives_the_last_word():
    pieces = [u("a9", "S01", "と話していた。", voice="article"), u("a8", "S01", "うれしかった", voice="spoken"),
              u("a7", "S01", "休みの日は、川で釣りをします。")]
    kinds = {"a9": "to_students", "a8": "joy", "a7": "refresh"}
    session, client = sitting(ANSWERED + [says(("a7", "休みの日は、川で釣りをします。"))], kinds=kinds, pieces=pieces)
    assert {k: [e.utterance_id for e in v] for k, v in session.library.closing_pieces["S01"].items()} == {
        "refresh": ["a7"]}
    session.ask(QUESTION)
    view = session.close_round(1)
    assert sent_ids(client) == ["a7"]
    assert [w["utterance_id"] for w in view["words"]] == ["a7"]


# --- the round's last word ---

def test_each_lit_seat_answers_with_one_piece_of_the_kind_code_picked():
    session, client = sitting(ANSWERED + [says(("a9", "地元にも、面白い仕事はたくさんあります。"),
                                                ("b9", "畑は毎日ちがう顔をします。"))])
    session.ask(QUESTION)
    view = session.close_round(1)
    # Fewest shown, then the table's order: 高校生へ for S01, 楽しいところ for S02.
    assert session.rounds[0].closing.kinds_asked == ["to_students", "joy"]
    assert sorted(sent_ids(client)) == ["a9", "b9"]
    assert client.requests[-1]["model"] == "claude-opus-5-5"
    assert view["question"] == load_text(CLOSING_QUESTION) == "最後に、何か伝えたいことはありますか"
    assert [(w["seat_id"], w["utterance_id"], w["kind"], w["label"]) for w in view["words"]] == [
        ("S01", "a9", "to_students", "高校生に向けた言葉"), ("S02", "b9", "joy", "楽しいところ・魅力")]
    assert view["words"][0]["said"] and view["words"][0]["source"]["title"] == "理容師"
    assert not view["words"][1]["said"] and view["words"][1]["source"]["note"] == "先輩社員の言葉（本人確認済み）"


def test_the_same_students_next_round_shows_other_kinds_and_never_the_same_piece():
    session, client = sitting(ANSWERED + [says(("a9", "地元にも、面白い仕事はたくさんあります。"),
                                                ("b9", "畑は毎日ちがう顔をします。"))]
                              + ANSWERED + [says(("a6", "店を継いだのは、父の背中を見ていたからです。"),
                                                 ("b8", "朝は四時に起きて、畑を見回ります。"))])
    session.ask(QUESTION)
    first = session.close_round(1)
    session.ask("休みはどう決める？")
    second = session.close_round(2)
    assert session.rounds[1].closing.kinds_asked == ["reason", "daily"]
    assert sorted(sent_ids(client)) == ["a6", "b8"]
    assert {w["kind"] for w in first["words"]}.isdisjoint(w["kind"] for w in second["words"])


def test_a_seat_whose_pieces_were_all_shown_is_not_asked_again():
    pieces = [u("a9", "S01", "地元にも、面白い仕事はたくさんあります。", voice="spoken")]
    session, client = sitting(ANSWERED + [says(("a9", "地元にも、面白い仕事はたくさんあります。"))] + ANSWERED,
                              kinds={"a9": "to_students"}, pieces=pieces)
    session.ask(QUESTION)
    assert session.close_round(1)["words"][0]["utterance_id"] == "a9"
    session.ask("休みはどう決める？")
    before = len(client.requests)
    assert session.close_round(2)["words"] == []
    assert len(client.requests) == before  # No seat left with a piece not shown: no call.
    assert session.rounds[1].closing.status == closing.NONE_HOLD


def test_a_piece_shown_as_a_quote_in_a_round_is_not_sent():
    session, client = sitting(ANSWERED + [says()])
    session.ask(QUESTION)
    session.close_round(1)
    assert "a1" not in sent_ids(client)  # Tagged 仕事で大事にしていること, but already shown.


def test_two_seats_in_one_round_lean_to_different_kinds():
    pieces = [u("a9", "S01", "地元にも、面白い仕事はたくさんあります。", voice="spoken"),
              u("a7", "S01", "休みの日は、川で釣りをします。"),
              u("b9", "S02", "畑は毎日ちがう顔をします。", voice="senior"),
              u("b7", "S02", "休みの日は、山に登ります。")]
    kinds = {"a9": "to_students", "a7": "refresh", "b9": "to_students", "b7": "refresh"}
    session, _ = sitting(ANSWERED + [says()], kinds=kinds, pieces=pieces)
    session.ask(QUESTION)
    session.close_round(1)
    assert session.rounds[0].closing.kinds_asked == ["to_students", "refresh"]


def test_at_most_three_seats_in_the_order_they_spoke():
    four = [librarian_finds("c1", "a1", "b1", "p1"),
            moderator_says([("c1", "子どもの声で元気が出ます。"), ("a1", "休みは決めて取ります。"),
                            ("b1", "畑は天気しだいなので、休みは空いたら取ります。"),
                            ("p1", "川のにごりは何で決まるのかを知る。")])]
    session, client = sitting(four + [says(("p9", "川は町の鏡だと分かった。"), ("b9", "畑は毎日ちがう顔をします。"))])
    session.ask(QUESTION)
    assert session.rounds[0].seat_order == ["S03", "S01", "S02", "P01"]
    view = session.close_round(1)
    # S03 holds no piece that may answer; S01, S02, P01 are asked.
    assert session.rounds[0].closing.seats_asked == ["S01", "S02", "P01"]
    assert [w["seat_id"] for w in view["words"]] == ["S02", "P01"]


def test_with_no_lit_seat_holding_a_piece_no_model_is_called():
    session, client = sitting([librarian_finds("c1"), moderator_says([("c1", "子どもの声で元気が出ます。")])])
    session.ask(QUESTION)
    before = len(client.requests)
    assert session.close_round(1) == {"round": 1, "question": "", "words": []}
    assert len(client.requests) == before
    assert session.rounds[0].closing.status == closing.NONE_HOLD


@pytest.mark.parametrize("bad", ["地元にも、面白い仕事", "地元にも面白い仕事がある。", "休みの日も"])
def test_a_copy_the_guard_stops_is_not_shown(bad):
    session, _ = sitting(ANSWERED + [says(("a9", bad), ("b9", "畑は毎日ちがう顔をします。"))])
    session.ask(QUESTION)
    view = session.close_round(1)
    assert [w["seat_id"] for w in view["words"]] == ["S02"]
    assert session.rounds[0].closing.guard_stopped == 1


def test_a_pick_of_a_piece_not_sent_or_a_second_for_one_seat_is_dropped():
    session, _ = sitting(ANSWERED + [says(("a9", "地元にも、面白い仕事はたくさんあります。"),
                                          ("a7", "休みの日は、川で釣りをします。"),
                                          ("a9", "地元にも、面白い仕事はたくさんあります。"))])
    session.ask(QUESTION)
    assert [w["utterance_id"] for w in session.close_round(1)["words"]] == ["a9"]
    assert session.rounds[0].closing.dropped == 2  # a7 was not of the kind sent; a9 twice.


def test_a_failed_model_shows_nothing_and_keeps_the_reason():
    session, _ = sitting(ANSWERED)  # Nothing left for the closing call.
    session.ask(QUESTION)
    assert session.close_round(1)["words"] == []
    assert session.rounds[0].closing.status == closing.UNAVAILABLE and session.rounds[0].closing.reason


def test_asked_once_per_round_and_only_after_seats_spoke():
    session, client = sitting(ANSWERED + [says(("b9", "畑は毎日ちがう顔をします。"))]
                              + [librarian_finds()] + [text_response({"ask_seat_ids": [], "rephrase": ""})])
    session.ask(QUESTION)
    first = session.close_round(1)
    count = len(client.requests)
    assert session.close_round(1) == first and len(client.requests) == count
    session.ask("ほかには？")  # No piece found: silent.
    with pytest.raises(Refused, match="no_seat_spoke"):
        session.close_round(2)
    with pytest.raises(Refused):
        session.close_round(3)


def test_nothing_sent_to_the_model_holds_a_company_or_a_name():
    session, client = sitting(ANSWERED + [says(("b9", "畑は毎日ちがう顔をします。"))])
    session.ask(QUESTION)
    session.close_round(1)
    sent = json.dumps(client.requests[-1], ensure_ascii=False)
    for word in (COMPANY, DISPLAY_NAME, "架空農園", "谷口"):
        assert word not in sent


def test_the_record_keeps_the_kinds_and_the_pieces_ids_only(tmp_path):
    session, _ = sitting(ANSWERED + [says(("a9", "地元にも、面白い仕事はたくさんあります。"))], tmp_path=tmp_path)
    session.ask(QUESTION)
    session.close_round(1)
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    kept = record["rounds"][0]["closing"]
    assert kept == {"status": "shown", "reason": "", "seats_asked": ["S01", "S02"],
                    "kinds_asked": ["to_students", "joy"], "seats_shown": ["S01"], "utterance_ids": ["a9"],
                    "kinds_shown": ["to_students"], "guard_stopped": 0, "dropped": 0}
    assert "面白い仕事" not in json.dumps(record, ensure_ascii=False)
