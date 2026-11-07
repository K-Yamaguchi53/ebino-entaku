"""直し45 段5: 帰る前に、ひとこと starts from today's trail and three marks
(each optional); the first word is looked for at the step marked; the
questions' cards are コーチ（AI） and オブザーバー（AI）. Everything is invented."""

import pytest

from ebino import app as app_module, hitokoto
from ebino.session import Refused
from test_one_to_one import Kept
from test_session import ANSWERED
from test_trail import FIRST, SECOND, sitting

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")


def walked(kept=None):
    session, _ = sitting([*ANSWERED, *ANSWERED], kept)
    session.ask(FIRST)
    session.bubble_opened(1, "a1")  # Step 2.
    session.bubble_opened(1, "b1")  # Step 3.
    session.ask(SECOND)  # Step 4.
    return session


def test_no_marks_the_map_as_before():
    session = walked()
    view = session.hitokoto_begin(["a1", "b1"], [])
    assert view["start"] is None and session.talk.marks == []
    assert walked().hitokoto_begin(["a1"])["start"] is None  # Sent with none at all.


def test_the_first_word_is_looked_for_at_more_then_deeper_then_surprised():
    session = walked()
    view = session.hitokoto_begin(["a1", "b1"], [{"n": 2, "mark": "surprised"}, {"n": 3, "mark": "more", "note": "畑の話"},
                                                 {"n": 4, "mark": "deeper"}])
    assert view["start"] == 0 and view["people"][0]["seat_id"] == "S02"  # The step marked もっと聞きたかった.
    session = walked()
    view = session.hitokoto_begin([], [{"n": 4, "mark": "more"}, {"n": 2, "mark": "deeper"}])
    assert view["start"] == 0 and view["people"][0]["seat_id"] == "S01"  # A question: not a person's words.


def test_a_mark_once_a_step_once_and_known_marks_only():
    for marks in ([{"n": 2, "mark": "more"}, {"n": 3, "mark": "more"}],
                  [{"n": 2, "mark": "more"}, {"n": 2, "mark": "deeper"}],
                  [{"n": 2, "mark": "best"}], [{"n": 99, "mark": "more"}], "more"):
        with pytest.raises(Refused):
            walked().hitokoto_begin([], marks)


def test_a_line_with_a_name_is_asked_again_and_nothing_starts():
    from conftest import DISPLAY_NAME, make_seat
    from ebino.gate import NameList
    from test_session import SEATS
    session = walked()
    session.gate.names = NameList.build([*SEATS, make_seat(seat_id="X99")], {})
    view = session.hitokoto_begin([], [{"n": 2, "mark": "more", "note": f"{DISPLAY_NAME}の話"}])
    assert view["status"] == "ask_again" and session.talk is None


def test_the_sheet_and_the_record_keep_the_marks_with_the_line():
    kept = Kept()
    session = walked(kept)
    session.hitokoto_begin(["a1"], [{"n": 4, "mark": "deeper", "note": "仕事のことに変わった"}])
    assert kept.sessions[-1]["hitokoto"]["marks"] == [{"n": 4, "mark": "deeper", "note": "仕事のことに変わった"}]
    session.talk.stage = hitokoto.LIT
    sheet = session.hitokoto_sheet("")
    # 直し53 段6: the same line, parted (the student's own question: own).
    assert sheet["marks"] == [{"label": "問いが深まった", "text": SECOND, "note": "仕事のことに変わった", "head": "", "own": SECOND}]
    assert sheet["first_question"] == FIRST  # The top as before.


def test_the_questions_cards_say_coach_ai_and_the_teachers_question():
    words = hitokoto.screen_words()
    # 直し53 段9: ① by オブザーバー（AI）, ② by コーチ（AI） (with the listener, コーチ（AI） as before).
    assert words["who_coach"] == "コーチ（AI）" and words["who_observer"] == "オブザーバー（AI）"
    assert hitokoto.words()["who_teacher"] == "先生の問い"
    assert set(words["marks"].values()) == {"はじめて知った・気づいた", "問いが深まった", "もっと聞きたかった"}
    say = HK[HK.index("  function say(who, text, extra"):HK.index("  function clearInput(")]
    # 直し53 段9: オブザーバー（AI） for ①, its robot by the name; else コーチ（AI） as before.
    assert "H.who_coach" in say and 'role === "observer" ? H.who_observer' in say and "W.who_teacher" in say
    assert "head.prepend(EbinoRobot.make(role));" in say
    # 直し46: ③ (the scale's next question, the teacher's fixed words) is
    # 先生の問い in the teacher's card, not the AI's colour.
    assert 'say("teacher", result.question);\n      lineBox("forward"' in HK
    assert 'say("observer"' not in HK
    assert 'const marks = await markTrail();' in HK and 'post("begin", { opened: app.state.opened || [], marks })' in HK
