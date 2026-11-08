"""直し49 段2 (the teacher, 11/7): 「次に会うなら」 widened to 次にやってみること.
Before the seat to meet, 「このあと、やってみたいことは？」 with four to pick:
会って聞いてみる goes on to the seat as before (and ② after it, ⑤ only on a
day with a split); 自分で調べてみる and 試してみる open a line, optional, no
seat; まだ決めない goes on, with no dead end. The sheet's sheet_meet box reads
次にやってみること and holds what was picked (none for まだ決めない); 次の一歩に
なりそうなこと is not shown beside it. Every record and word here is invented;
the model is a fake one."""

import json

import pytest

from ebino import app as app_module
from ebino import harvest, hitokoto
from ebino.session import Refused
from ebino.texts import NAME_IN_QUESTION, load_text
from test_hitokoto import Model, sitting, to_scale

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
ASK = HK[HK.index("  function askTry() {"):HK.index("  // --- 段4: what to keep")]
WORDS = hitokoto.words()


def to_try(session, scale=8, forward="先輩にもう一回聞く"):
    to_scale(session)
    session.hitokoto_scale(scale)
    session.hitokoto_forward(forward)
    session.hitokoto_notice("not_yet")
    session.hitokoto_way("", skip=True)
    assert session.hitokoto_subject("no") == {"next": "try"}
    assert session.talk.stage == hitokoto.TRY


def sheet(session):
    session.hitokoto_light()
    return session.hitokoto_sheet("")


def test_four_to_pick_and_one_that_goes_on_without_deciding():
    assert hitokoto.TRY_ANSWERS == ("meet", "look", "try", "later")
    assert [WORDS[f"try_{key}"] for key in hitokoto.TRY_ANSWERS] == [
        "会って聞いてみる", "自分で調べてみる", "試してみる", "まだ決めない"]
    assert WORDS["try_q"] == "このあと、やってみたいことは？"
    assert ('answers: [["meet", W.try_meet], ["look", W.try_look], ["try", W.try_try], ["later", W.try_later]],'
            in ASK)
    assert 'step: "try", question: W.try_q, hint: W.try_hint, write: ["look", "try"],' in ASK


def test_it_comes_after_the_lesson_and_before_the_seat():
    session, _, _, _ = sitting()
    to_try(session)
    with pytest.raises(Refused):
        session.hitokoto_meet("S02")  # Not before 次にやってみること.
    other, _, _, _ = sitting()
    to_scale(other)
    other.hitokoto_scale(8)
    other.hitokoto_forward("", skip=True)
    other.hitokoto_notice("no_answer")
    other.hitokoto_way("", skip=True)
    other.hitokoto_subject("yes")
    assert other.hitokoto_subject_note("家庭科")["next"] == "try"
    assert "askTry();" in HK and "askMeet();" not in HK[HK.index("  async function askSubject() {"):HK.index("  // ③ under")]


def test_meet_goes_on_to_the_seat_and_the_force_to_use():
    session, _, _, _ = sitting()  # A day with a split.
    to_try(session)
    assert session.hitokoto_try("meet") == {"next": "meet"}
    uses = session.hitokoto_meet("S02")["uses"]
    assert uses and "5" in [u["force"] for u in uses]  # ⑤ on a day with a split, as before.
    line = session.hitokoto_use(uses[0]["force"])["meet"]
    view = sheet(session)["next_try"]
    assert view == {"answer": "meet", "label": "会って聞いてみる", "text": "", "meet": line}
    assert "(key === \"meet\" ? askMeet() : atEnd())" in ASK


def test_the_force_to_use_is_not_offered_on_a_day_with_no_split():
    session, _, _, _ = sitting(Model(split=False))
    to_try(session)
    session.hitokoto_try("meet")
    assert "5" not in [u["force"] for u in session.hitokoto_meet("S02")["uses"]]


@pytest.mark.parametrize("answer", ["look", "try"])
def test_look_and_try_take_a_line_and_no_seat_and_no_force(answer):
    session, _, client, _ = sitting()
    to_try(session)
    called = len(client.requests)
    assert session.hitokoto_try(answer, "雨の日の<畑>を、一回見に行ってみる") == {"next": "end"}
    assert len(client.requests) == called  # No model for the line.
    with pytest.raises(Refused):
        session.hitokoto_meet("S02")
    with pytest.raises(Refused):
        session.hitokoto_use("none")
    view = sheet(session)
    assert view["next_try"] == {"answer": answer, "label": WORDS[f"try_{answer}"],
                                "text": "雨の日の<畑>を、一回見に行ってみる", "meet": ""}
    assert "雨の日の<畑>を、一回見に行ってみる" not in client.all_sent()


def test_the_line_is_optional_and_has_no_example():
    session, _, _, _ = sitting()
    to_try(session)
    session.hitokoto_try("look", "", skip=True)
    assert sheet(session)["next_try"]["text"] == ""
    assert WORDS["try_hint"] == "何を？ 1行でいい"
    body = HK[HK.index("  function choiceWithLine("):HK.index("  // --- 段4: what to keep")]
    assert "placeholder" not in body


def test_not_deciding_goes_on_and_shows_no_box():
    session, _, _, _ = sitting()
    to_try(session)
    assert session.hitokoto_try("later", "これは残らない") == {"next": "end"}
    assert session.talk.next_try_text == ""
    view = sheet(session)
    assert view["next_try"] is None
    # On the screen: on to the light's button, as after the others (no dead end).
    assert "atEnd()" in ASK


def test_a_name_in_the_line_is_neither_kept_nor_sent(tmp_path):
    session, _, _, _ = sitting(tmp_path=tmp_path)
    to_try(session)
    view = session.hitokoto_try("try", "谷口さんの店に行ってみる")
    assert view == {"status": "ask_again", "message": load_text(NAME_IN_QUESTION)}
    assert session.talk.stage == hitokoto.TRY
    assert "谷口" not in (tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8")


def test_an_answer_not_of_the_four_is_refused():
    session, _, _, _ = sitting()
    to_try(session)
    for answer in ("none", "", None, "試してみる"):
        with pytest.raises(Refused):
            session.hitokoto_try(answer)


def test_the_sheet_box_reads_next_try_and_the_next_step_is_not_said_twice():
    assert WORDS["sheet_meet"] == "次にやってみること"
    # With something to try: one next step on the sheet, not two. The 前
    # answer stays in 自分の言葉の動き.
    session, _, _, _ = sitting()
    to_try(session, scale=8, forward="先輩にもう一回聞く")
    session.hitokoto_try("try", "畑を見に行く")
    view = sheet(session)
    assert view["next_try"]["text"] == "畑を見に行く" and view["next_step"] == ""
    assert "先輩にもう一回聞く" in view["moves"]
    # まだ決めない: 次の一歩になりそうなこと as before.
    other, _, _, _ = sitting()
    to_try(other, scale=8, forward="先輩にもう一回聞く")
    other.hitokoto_try("later")
    assert sheet(other)["next_step"] == "先輩にもう一回聞く"
    sheet_js = HK[HK.index("  async function toSheet() {"):HK.index("  function setup() {")]
    assert "if (sheet.next_try) {" in sheet_js and 'el("p", "hk-label", W.sheet_meet)' in sheet_js
    assert "if (sheet.meet) {" not in sheet_js


def test_the_record_keeps_what_was_picked_and_the_line(tmp_path):
    session, _, _, _ = sitting(tmp_path=tmp_path)
    to_try(session)
    session.hitokoto_try("look", "畑の休みを調べる")
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert record["hitokoto"]["next_try"] == {"answer": "look", "text": "畑の休みを調べる"}
    assert record["hitokoto"]["meet_seat"] == "" and record["hitokoto"]["meet_use"] == ""


def test_the_api_has_its_path():
    session, _, _, _ = sitting()
    to_try(session)
    app = app_module.App.__new__(app_module.App)
    assert app._hitokoto(session, "try", {"answer": "later"}) == {"next": "end"}
    assert harvest.CHOSE_NO_USE == "none"
