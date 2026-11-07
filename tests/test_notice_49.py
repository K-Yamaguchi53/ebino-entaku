"""直し49 段1 (the teacher, 11/7: 「気づきがある、または行動などのきっかけが作れれば
良い」): 帰る前に、ひとこと asks 今日の気づき after the scale. Four answers to
pick, 「答えない」 always there; a line to write (optional) only after 「あった」
or 「ちょっとあった」; the line is kept and put near the top of the sheet as
written, and no model is called for it or sent it. Every record and word here
is invented; the model is a fake one."""

import json

import pytest

from ebino import app as app_module
from ebino import hitokoto
from ebino.session import Refused
from ebino.texts import NAME_IN_QUESTION, load_text
from test_hitokoto import sitting, to_scale

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
ASK = HK[HK.index("  function choiceWithLine("):HK.index("  // --- 段4: what to keep")]
WORDS = hitokoto.words()


def to_notice(session, scale=8):
    to_scale(session)
    session.hitokoto_scale(scale)
    if scale:
        session.hitokoto_forward("", skip=True)
    assert session.talk.stage == hitokoto.NOTICE


def to_sheet(session):
    session.hitokoto_way("", skip=True)
    session.hitokoto_subject("no")
    session.hitokoto_try("later")
    session.hitokoto_light()
    return session.hitokoto_sheet("")


def test_four_answers_to_pick_and_dont_answer_is_one_of_them():
    assert hitokoto.NOTICE_ANSWERS == ("yes", "some", "not_yet", "no_answer")
    assert [WORDS[f"notice_{key}"] for key in hitokoto.NOTICE_ANSWERS] == ["あった", "ちょっとあった", "まだない", "答えない"]
    assert WORDS["notice_q"] == "今日、気づいたことや、はじめて知ったことはあった？"
    assert ('answers: [["yes", W.notice_yes], ["some", W.notice_some], ["not_yet", W.notice_not_yet], '
            '["no_answer", W.notice_no_answer]],') in ASK
    assert 'step: "notice", question: W.notice_q, hint: W.notice_hint, write: ["yes", "some"],' in ASK
    assert 'say("teacher", question, box);' in ASK


@pytest.mark.parametrize("scale", [0, 8, 10, 13])
def test_it_comes_after_the_scale_and_its_next_question_and_before_the_way(scale):
    session, _, _, _ = sitting()
    to_scale(session)
    result = session.hitokoto_scale(scale)
    if scale:
        assert session.hitokoto_forward("", skip=True) == {"next": "notice"}
    else:
        assert result["next"] == "notice"
    with pytest.raises(Refused):
        session.hitokoto_way("農業")  # Not before 今日の気づき.
    assert session.hitokoto_notice("not_yet") == {"next": "way"}
    assert session.talk.stage == hitokoto.WAY
    assert "lineBox(\"forward\", { send: W.send, skip: W.skip }, () => askNotice());" in HK


def test_an_answer_not_of_the_four_is_refused():
    session, _, _, _ = sitting()
    to_notice(session)
    for answer in ("no", "", None, "あった", 1):
        with pytest.raises(Refused):
            session.hitokoto_notice(answer)


def test_the_line_is_only_for_there_was_and_a_little():
    # The screen: the line is hidden until 「あった」 or 「ちょっとあった」; the others go on at once.
    assert "form.hidden = true;" in ASK
    assert "if (write.includes(key)) {" in ASK and "form.hidden = false;" in ASK
    assert 'go(key, label, pick, "");' in ASK
    # The server: a line sent with the others is not kept.
    for answer in ("not_yet", "no_answer"):
        session, _, _, _ = sitting()
        to_notice(session)
        session.hitokoto_notice(answer, "畑のことを知った")
        assert session.talk.notice == answer and session.talk.notice_text == ""
    for answer in ("yes", "some"):
        session, _, _, _ = sitting()
        to_notice(session)
        session.hitokoto_notice(answer, "畑のことを知った")
        assert session.talk.notice_text == "畑のことを知った"


def test_the_line_has_no_example_in_it_and_says_it_may_be_left_empty():
    assert "placeholder" not in ASK  # An example is copied.
    assert WORDS["notice_hint"] == "1行でいい。書かなくても進めます"
    assert 'const hint = el("p", "hk-choice-hint", hintText);' in ASK
    assert 'input.setAttribute("aria-describedby", hint.id);' in ASK
    assert 'const pass = button("quiet", W.skip,' in ASK


TRICKY = "<b>雨の日</b>も畑の人は休みじゃない&ことを、はじめて知った。「天気しだい」って本当だった"


def test_the_line_written_is_on_the_sheet_word_for_word_near_the_top():
    session, _, _, _ = sitting()
    to_notice(session)
    session.hitokoto_notice("yes", TRICKY)
    sheet = to_sheet(session)
    assert sheet["notice"] == TRICKY
    # Set as text, never as HTML, near the top: right under the sheet's title.
    sheet_js = HK[HK.index("  async function toSheet() {"):HK.index("  function setup() {")]
    title = sheet_js.index('box.replaceChildren(el("h3", "", W.sheet_title));')
    notice = sheet_js.index("if (sheet.notice) {")
    assert title < notice < sheet_js.index('const questions = el("div", "hk-qq");')
    assert 'el("p", "hk-lit hk-notice-text", `「${sheet.notice}」`)' in sheet_js
    assert "innerHTML" not in HK and "insertAdjacentHTML" not in HK


@pytest.mark.parametrize("answer, text, skip", [
    ("not_yet", "", False), ("no_answer", "", False),
    ("yes", "", True), ("some", "", False),  # 「あった」 and nothing written.
    ("yes", "ない", False),  # 「ない」 alone is not a line.
])
def test_with_nothing_written_there_is_no_box(answer, text, skip):
    session, _, _, _ = sitting()
    to_notice(session)
    session.hitokoto_notice(answer, text, skip=skip)
    assert to_sheet(session)["notice"] == ""
    assert "なし" not in WORDS["sheet_notice"]


def test_no_model_is_called_for_it_or_sent_it():
    session, model, client, _ = sitting()
    to_notice(session)
    called = len(client.requests)
    session.hitokoto_notice("yes", TRICKY)
    assert len(client.requests) == called  # The fake model's count: not one call.
    to_sheet(session)
    assert TRICKY not in client.all_sent()  # Nor sent later, to the light or the tie.
    assert session.talk.written == [w for w in session.talk.written if w["text"] != TRICKY]
    assert TRICKY not in hitokoto.own_moves(session.talk)  # Not twice on the sheet.


def test_a_name_in_the_line_is_neither_kept_nor_sent(tmp_path):
    session, _, client, _ = sitting(tmp_path=tmp_path)
    to_notice(session)
    called = len(client.requests)
    view = session.hitokoto_notice("yes", "谷口さんの話で気づいた")
    assert view == {"status": "ask_again", "message": load_text(NAME_IN_QUESTION)}
    assert session.talk.stage == hitokoto.NOTICE and session.talk.notice_text == ""
    assert len(client.requests) == called
    kept = (tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8")
    assert "谷口" not in kept


def test_the_record_keeps_the_answer_and_the_line(tmp_path):
    session, _, _, _ = sitting(tmp_path=tmp_path)
    to_notice(session)
    session.hitokoto_notice("some", "畑は天気で決まると知った")
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert record["hitokoto"]["notice"] == {"answer": "some", "text": "畑は天気で決まると知った"}


def test_the_api_has_its_path():
    session, _, _, _ = sitting()
    to_notice(session)
    app = app_module.App.__new__(app_module.App)
    assert app._hitokoto(session, "notice", {"answer": "no_answer"}) == {"next": "way"}
