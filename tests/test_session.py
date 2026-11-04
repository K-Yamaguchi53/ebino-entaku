"""One sitting at the round table and what the screen is sent (SPEC 5-1,
14-12, 14-39, 14-40). Everything here is invented."""

import json
import random

import pytest
from fake_client import FakeClient, text_response

from conftest import COMPANY, DISPLAY_NAME, make_seat
from ebino.gate import Gate, NameList
from ebino.ingest.utterance import Utterance
from ebino.session import Library, Refused, Session

SEATS = [
    make_seat(seat_id="S01"),  # 理容師, はるかぜ理容, 山川さん.
    make_seat(seat_id="S02", title="農家", company="架空農園", display_name="谷口さん", district="北地区"),
    make_seat(seat_id="S03", title="保育士", company="架空保育園", display_name="森川さん", district="南地区"),
    make_seat(seat_id="P01", kind="poster", title="探究の先輩（川の水を調べた）", company="", display_name="先輩"),
]


def u(i, seat, text, voice="article", paragraph="", kind="adult", section="本文", heading=""):
    return Utterance(id=i, seat_id=seat, kind=kind, section=section, voice=voice, text=text,
                     paragraph=paragraph or text, heading=heading)


UTTERANCES = [
    u("a1", "S01", "休みは決めて取ります。", voice="spoken", paragraph="この方は「休みは決めて取ります。」と話す。"),
    u("a2", "S01", "月曜は必ず店を閉める。"),
    u("b1", "S02", "畑は天気しだいなので、休みは空いたら取ります。", voice="spoken"),
    u("c1", "S03", "子どもの声で元気が出ます。", voice="spoken"),
    u("p1", "P01", "川のにごりは何で決まるのかを知る。", voice="own", kind="poster", section="目的", heading="目的"),
]


def library(show_private=False):
    return Library.build(SEATS, UTTERANCES, {}, show_private)


def librarian_finds(*ids):
    return text_response({"utterance_ids": list(ids)})


def moderator_says(quotes, splits=(), silent=()):
    return text_response({
        "quotes": [{"utterance_id": i, "text": t} for i, t in quotes],
        "splits": [{"heading": h, "side_a": list(a), "side_b": list(b)} for h, a, b in splits],
        "silent_seat_ids": list(silent),
    })


def editor_says(ask=(), rephrase=""):
    return text_response({"ask_seat_ids": list(ask), "rephrase": rephrase})


def sitting(answers, show_private=False):
    client = FakeClient(list(answers))  # FakeClient uses up the list it gets.
    lib = library(show_private)
    session = Session(lib, Gate(client, NameList.build(SEATS, {})), rng=random.Random(1))
    return session, client


SPLIT = ('ここで割れた：休みを"決めて取る"人と"空いたら取る"人', ["a1"], ["b1"])
ANSWERED = [
    librarian_finds("a1", "a2", "b1"),
    moderator_says([("a1", "休みは決めて取ります。"), ("a2", "月曜は必ず店を閉める。"),
                    ("b1", "畑は天気しだいなので、休みは空いたら取ります。")], [SPLIT], silent=["S03"]),
]


def test_a_round_view_has_the_words_their_kind_of_source_and_the_order():
    session, _ = sitting(ANSWERED)
    view = session.ask("休みの日って、みんな何してる？")
    assert view["round"] == 1 and view["status"] == "answered"
    assert view["seat_order"] == ["S01", "S02"] and view["answered_seats"] == 2
    said = {q["utterance_id"]: (q["said"], q["source"]["note"]) for q in view["quotes"]}
    assert said == {"a1": (True, ""), "a2": (False, "取材記事（本人確認済み）"), "b1": (True, "")}
    assert view["quotes"][0]["source"] == {"title": "理容師", "detail": "", "note": ""}
    assert view["splits"][0]["side_a"] == ["a1"] and view["silent_seats"] == ["S03"]
    assert view["steps"] == {"found": 3, "passed": 3, "stopped": 0}
    assert view["card"] is None


def test_nothing_the_screen_gets_holds_a_company_name_or_year_off_the_school_screen():
    session, _ = sitting(ANSWERED)
    sent = json.dumps([session.library.seat_list(), session.ask("休みは？"), session.next_purposes()],
                      ensure_ascii=False)
    for word in (COMPANY, "はるかぜ", "架空農園", DISPLAY_NAME, "山川", "谷口", "2026"):
        assert word not in sent


def test_the_school_screen_adds_company_and_name_on_the_second_line_only():
    session, _ = sitting(ANSWERED, show_private=True)
    seats = {s["seat_id"]: s for s in session.library.seat_list()}
    assert seats["S01"] == {"seat_id": "S01", "kind": "adult", "title": "理容師", "detail": "はるかぜ理容　山川さん"}
    assert seats["P01"]["detail"] == "先輩"
    view = session.ask("休みは？")
    assert view["quotes"][0]["source"]["detail"] == "はるかぜ理容　山川さん"


def test_seats_are_listed_by_kind_in_the_explainer_order():
    lib = Library.build([SEATS[3], SEATS[0]], UTTERANCES, {})
    assert [s["kind"] for s in lib.seat_list()] == ["adult", "poster"]


def test_met_seats_gather_across_rounds_in_the_order_first_met():
    session, _ = sitting(ANSWERED + [
        librarian_finds("c1", "a2"),
        moderator_says([("c1", "子どもの声で元気が出ます。"), ("a2", "月曜は必ず店を閉める。")]),
    ])
    session.ask("休みは？")
    view = session.ask("元気が出るときは？")
    assert view["round"] == 2 and view["met_seats"] == ["S01", "S02", "S03"]


def test_one_marked_quote_per_seat_and_marking_again_takes_it_off():
    session, _ = sitting(ANSWERED)
    session.ask("休みは？")
    assert session.mark(1, "a1") == {"S01": "a1"}
    assert session.mark(1, "a2") == {"S01": "a2"}  # Same seat: replaced.
    assert session.mark(1, "b1") == {"S01": "a2", "S02": "b1"}
    assert session.mark(1, "a2") == {"S02": "b1"}
    with pytest.raises(Refused):
        session.mark(1, "c1")  # Not shown in that round.
    with pytest.raises(Refused):
        session.mark(2, "a1")


def test_pressing_a_split_gives_its_heading_and_is_kept_apart_from_those_left():
    session, _ = sitting(ANSWERED)
    session.ask("休みは？")
    assert session.press_split(1, 0) == SPLIT[0]
    assert session.pressed_splits == {(1, 0)}
    with pytest.raises(Refused):
        session.press_split(1, 1)


def test_a_card_can_be_written_at_a_seat_shown_as_not_asked_yet_or_one_that_spoke():
    session, client = sitting(ANSWERED + [editor_says(["S03"])])
    with pytest.raises(Refused):
        session.write_card("S03", "子どもと話すとき、何に気をつけますか")  # No round yet.
    session.ask("休みは？")
    with pytest.raises(Refused):
        session.write_card("P01", "問い")  # Neither silent nor quoted in a round.
    spoke = session.write_card("S01", "休みの日は、何時に起きますか")  # S01 answered (直し26-2).
    assert spoke["seat_id"] == "S01" and len(session.cards) == 1
    session.cards.clear()
    front = session.write_card("S03", "子どもと話すとき、何に気をつけますか")
    assert (front["origin"], front["seat_id"]) == ("student", "S03")
    assert "back" not in front and len(session.cards) == 1
    with pytest.raises(Refused):
        session.write_card("S03", "   ")


def test_a_silent_round_keeps_its_card():
    session, _ = sitting([librarian_finds(), editor_says()])
    view = session.ask("やってみて合わなかった人は？")
    assert view["status"] == "silent" and view["answered_seats"] == 0
    assert view["card"]["text"] == "やってみて合わなかった人は？"
    assert session.cards[0].card_id == view["card"]["card_id"]


def test_a_name_in_the_question_comes_back_as_ask_again_with_no_question():
    session, client = sitting([])
    view = session.ask("谷口さんの休みは？")
    assert (view["status"], view["reason"], view["question"]) == ("ask_again", "name_in_question", "")
    assert client.requests == []


def test_an_empty_or_long_question_is_refused_before_any_model():
    session, client = sitting([])
    for question in ("  ", "あ" * 201):
        with pytest.raises(Refused):
            session.ask(question)
    assert client.requests == [] and session.rounds == []


def test_the_paragraph_is_given_only_for_a_quote_already_shown():
    session, _ = sitting(ANSWERED)
    with pytest.raises(Refused):
        session.paragraph("a1")
    session.ask("休みは？")
    assert session.paragraph("a1")["paragraph"] == "この方は「休みは決めて取ります。」と話す。"
    with pytest.raises(Refused):
        session.paragraph("c1")


def test_purpose_samples_come_with_their_source():
    session, _ = sitting([])
    [sample] = session.next_purposes()
    assert sample["texts"] == ["川のにごりは何で決まるのかを知る。"]
    assert sample["source"]["title"] == "探究の先輩（川の水を調べた）"


def test_the_lab_choice_is_one_of_four():
    session, _ = sitting([])
    session.set_lab("creation")
    assert session.lab == "creation"
    with pytest.raises(Refused):
        session.set_lab("lab")


def test_the_planted_fake_shows_as_stopped():
    session, _ = sitting(ANSWERED)
    session.plant = True
    view = session.ask("休みは？")
    assert len(view["planted_stopped"]) == 1 and view["steps"]["stopped"] == 0
