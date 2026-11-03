"""Today's harvest card ① and ② (SPEC 5-3, 14-1). Every record is invented."""

import json
import random

import pytest
from fake_client import FakeClient

from conftest import make_seat
from ebino import harvest
from ebino.banned_words import banned_in
from ebino.gate import Gate, NameList
from ebino.harvest import Found, pick
from ebino.records import Records
from ebino.session import Library, Refused, Session
from ebino.texts import WORK_QUESTIONS, load_lines
from test_reflection import reflection_says
from test_session import ANSWERED, SEATS, SPLIT, UTTERANCES, editor_says, librarian_finds, moderator_says, u

FIRST = "休みの日って、みんな何してる？"
SILENT = [librarian_finds(), editor_says()]
HEADING = SPLIT[0].removeprefix("ここで割れた：")
FAR_SEAT = make_seat(seat_id="X01", kind="cross", title="県外に出た先輩（看護の研修）", company="", display_name="")
FAR_WORDS = u("x1", "X01", "外に出て、休みの考え方が変わった。", voice="own", kind="cross", section="p1")


def sitting(rounds, tmp_path=None, wide=False):
    """rounds: (question, answers) in order; answers go to the fake model."""
    seats = SEATS + [FAR_SEAT] if wide else SEATS
    lib = Library.build(seats, UTTERANCES + ([FAR_WORDS] if wide else []), {}, False)
    client = FakeClient([answer for _, answers in rounds for answer in answers])
    session = Session(lib, Gate(client, NameList.build(seats, {})), rng=random.Random(1),
                      records=Records(tmp_path) if tmp_path else None)
    session.client = client
    for question, _ in rounds:
        session.ask(question)
    return session


def finish(session, meet="S02", rewrite=""):
    session.client._answers.append(reflection_says())
    session.reflect_begin("a_little", "休みをどう決めるかを知りたい")
    session.reflect_answer("", declined=True)
    return session.reflect_finish("none", "", rewrite, meet, "")


def found_codes(session):
    return [f.code for f in harvest.found_moves(session, lambda heading: heading.removeprefix("ここで割れた："))]


def test_a_common_sitting_shows_the_first_question_and_the_seat_to_meet():
    session = sitting([(FIRST, ANSWERED)])
    sheet = finish(session)
    assert [use["force"] for use in sheet["uses"]] == ["1", "3", "4", "5"]  # One kind of seat: no ②.
    card = session.harvest("5")
    assert card["moves"] == (f"今日の動き：最初の問い「{FIRST}」を自分の言葉で入れた（① 自走する力）"
                             "／農家に会いに行きたいと選んだ（④ 向かう力の、手前の動き）")
    assert card["meet"] == "会いに行きたい1人：農家　／　会うときに：⑤ 割れていた所を、本人に確かめる"


def test_a_rewrite_comes_first_and_a_card_at_a_silent_seat_makes_the_pair():
    session = sitting([(FIRST, ANSWERED + [editor_says(["S03"])])])
    session.write_card("S03", "子どもが休みの日は、どう過ごしますか")
    finish(session, rewrite="休みは何で決まるのか")
    card = session.harvest("none")
    assert card["moves"] == ("今日の動き：問いを「休みは何で決まるのか」に書き直した（① 自走する力）"
                             "／保育士の席に質問カードを書いた（③ 合わせる力）")
    assert card["meet"] == "会いに行きたい1人：農家"


def test_a_card_first_holds_the_cards_own_words():
    session = sitting([(FIRST, ANSWERED + [editor_says(["S03"])])])
    session.write_card("S03", "子どもが休みの日は、どう過ごしますか")
    finish(session)
    assert session.harvest("none")["moves"].startswith(
        "今日の動き：保育士の席に、質問カード「子どもが休みの日は、どう過ごしますか」を書いた（③ 合わせる力）／最初の問い")


def test_a_pressed_split_asked_again_pairs_with_the_seat_to_meet_not_with_the_first_question():
    session = sitting([(FIRST, ANSWERED)])
    session.press_split(1, 0)
    session.client._answers.extend(SILENT)
    session.ask(HEADING)
    finish(session)
    words = HEADING if len(HEADING) <= 30 else HEADING[:30] + "…"
    # ⑤ and ① never pair; ④ does.
    assert session.harvest("none")["moves"] == (f"今日の動き：割れた見出し「{words}」を押して、もう一度聞いた（⑤ 解き明かす力）"
                                                "／農家に会いに行きたいと選んだ（④ 向かう力の、手前の動き）")


def test_a_split_pressed_but_not_asked_again_is_not_counted():
    session = sitting([(FIRST, ANSWERED)])
    session.press_split(1, 0)
    finish(session)
    assert "pressed_split" not in found_codes(session)


def test_asking_on_after_no_seat_answered_holds_the_next_question():
    session = sitting([("やってみて合わなかった人は？", SILENT), ("休みはどう決める？", ANSWERED)])
    finish(session)
    assert found_codes(session)[:2] == ["asked_after_silence", "silent_question"]
    assert session.harvest("none")["moves"] == (
        "今日の動き：どの席も答えなかったあとも、「休みはどう決める？」と問いを続けた（① 自走する力）"
        "／農家に会いに行きたいと選んだ（④ 向かう力の、手前の動き）")


def test_an_unavailable_round_is_not_a_silent_one():
    session = sitting([(FIRST, ANSWERED)])
    session.ask("休みは？")  # The fake model has nothing left: unavailable.
    assert session.rounds[-1].status == "unavailable"
    finish(session)
    assert not {"silent_question", "asked_after_silence"} & set(found_codes(session))


def test_a_first_question_from_the_work_buttons_is_not_own_words():
    work = load_lines(WORK_QUESTIONS)[0]
    session = sitting([(work, ANSWERED)])
    finish(session)
    assert found_codes(session) == ["chose_to_meet"]
    # Never none: the seat to meet is always picked.
    assert session.harvest("none")["moves"] == "今日の動き：農家に会いに行きたいと選んだ（④ 向かう力の、手前の動き）"


def test_long_words_in_the_first_move_are_cut_at_30_characters():
    rewrite = "休みの取り方は、仕事の中身と、一緒に働く人の数と、季節の忙しさで決まるのか"
    session = sitting([(FIRST, ANSWERED)])
    finish(session, rewrite=rewrite)
    assert len(rewrite) > 30
    assert session.harvest("none")["moves"].startswith(f"今日の動き：問いを「{rewrite[:30]}…」に書き直した（")


def test_three_kinds_of_seat_and_four_questions_are_counted():
    far = [librarian_finds("x1", "p1"), moderator_says([("x1", "外に出て、休みの考え方が変わった。"),
                                                       ("p1", "川のにごりは何で決まるのかを知る。")])]
    session = sitting([(FIRST, ANSWERED), ("外では？", far), ("川は？", SILENT), ("畑は？", SILENT)], wide=True)
    sheet = finish(session)
    assert [use["force"] for use in sheet["uses"]] == ["1", "2", "3", "4", "5"]
    assert found_codes(session) == ["asked_after_silence", "silent_question", "kinds_met", "many_rounds",
                                    "own_first_question", "chose_to_meet"]
    found = {f.code: f for f in harvest.found_moves(session, str)}
    # One title per kind, in the order the seats were first met.
    assert found["kinds_met"].words == "理容師・県外に出た先輩（看護の研修）・探究の先輩（川の水を調べた）"
    assert found["many_rounds"].count == 4


def test_no_split_met_means_no_fifth_use():
    session = sitting([(FIRST, [librarian_finds("a1"), moderator_says([("a1", "休みは決めて取ります。")])])])
    assert [use["force"] for use in finish(session)["uses"]] == ["1", "3", "4"]


@pytest.mark.parametrize("codes, kept", [
    (["pressed_split", "own_first_question"], ["pressed_split"]),  # ⑤ and ① never pair: one only.
    (["pressed_split", "kinds_met", "chose_to_meet"], ["pressed_split", "chose_to_meet"]),
    (["card_at_silent_seat", "pressed_split"], ["card_at_silent_seat", "pressed_split"]),  # ③⑤
    (["kinds_met", "own_first_question", "chose_to_meet"], ["kinds_met", "chose_to_meet"]),  # ② pairs with ④ only.
    (["rewrote", "many_rounds", "kinds_met", "chose_to_meet"], ["rewrote", "chose_to_meet"]),
    ([], []),
])
def test_the_second_move_makes_an_allowed_pair_or_is_left_out(codes, kept):
    assert [f.code for f in pick([Found(code) for code in codes])] == kept


def test_only_the_allowed_pairs_are_kept_and_six_is_never_a_force():
    assert harvest.ALLOWED_PAIRS == {frozenset(p) for p in ((1, 3), (1, 4), (2, 4), (3, 5), (4, 5))}
    assert set(harvest.FORCES) == {1, 2, 3, 4, 5} and set(harvest.USES) == {1, 2, 3, 4, 5}
    assert {row.force for row in harvest.MOVE_TABLE} <= {1, 2, 3, 4, 5}


def test_no_wording_of_the_card_holds_a_banned_word_or_a_lab_name():
    words = [row.with_words for row in harvest.MOVE_TABLE] + [row.short for row in harvest.MOVE_TABLE]
    words += list(harvest.USES.values()) + list(harvest.FORCE_IN_MOVES.values())
    for text in words:
        assert not banned_in(text), text
        assert not any(lab in text for lab in ("Quest", "Action", "Creation", "Lab")), text


def test_the_harvest_comes_once_after_the_sheet_and_only_with_a_use_offered():
    session = sitting([(FIRST, [librarian_finds("a1"), moderator_says([("a1", "休みは決めて取ります。")])])])
    with pytest.raises(Refused):
        session.harvest("none")  # No reflection yet.
    finish(session)
    for use in ("5", "2", "6", "", None, "1 "):
        with pytest.raises(Refused):
            session.harvest(use)
    session.harvest("3")
    with pytest.raises(Refused):
        session.harvest("1")


def test_the_record_keeps_the_moves_shown_and_the_use_picked(tmp_path):
    session = sitting([(FIRST, ANSWERED)], tmp_path=tmp_path)
    finish(session)
    session.harvest("5")
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert record["reflection"]["harvest_moves"] == ["own_first_question", "chose_to_meet"]
    assert record["reflection"]["harvest_use"] == "5"
