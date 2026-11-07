"""直し51 段3 (the teacher, 11/7: a line of home, money or health is not taken
off by a list of words, but by the student, looking at the sheet): the two
lines the student wrote (今日の気づき, 次にやってみること) each have a small
「外す」 on the sheet, and no other line has one. Pressed: off the sheet and
the print, its words gone from the record at once, that it was taken kept
(and the answer picked); 「戻す」 in its place puts it back. Nothing pressed:
the sheet and the record as before. Both lines' hints say what is written
goes on the last sheet. Every word here is invented; the model is a fake one."""

import json

import pytest

from ebino import app as app_module
from ebino import hitokoto
from ebino.session import Refused
from ebino.texts import NAME_IN_QUESTION, load_lines, load_text
from test_hitokoto import sitting, to_scale

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
CHECK = (app_module.STATIC_DIR.parent.parent / "tools" / "check_one_screen.js").read_text(encoding="utf-8")
SHEET_JS = HK[HK.index("  async function toSheet() {"):HK.index("  function setup() {")]
OWN = HK[HK.index("  function ownLine("):HK.index("  async function toSheet() {")]
WORDS = hitokoto.words()
NOTICE = "畑の人は雨の日も休みじゃないと知った"
TRY = "雨の日の畑を見に行く"


def _sheet(tmp_path, notice="yes", next_try="try"):
    session, _, _, _ = sitting(tmp_path=tmp_path)
    to_scale(session)
    session.hitokoto_scale(8)
    session.hitokoto_forward("", skip=True)
    session.hitokoto_notice(notice, NOTICE)
    session.hitokoto_way("", skip=True)
    session.hitokoto_subject("no")
    session.hitokoto_try(next_try, TRY)
    if next_try == "meet":
        session.hitokoto_meet("")
    session.hitokoto_light()
    return session, session.hitokoto_sheet("")


def _kept(tmp_path, session):
    return (tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8")


def test_both_hints_say_it_goes_on_the_last_sheet():
    assert WORDS["sheet_hint"] == "ここに書いたことは、最後の1枚に載ります"
    assert WORDS["notice_hint"] == "1行でいい。書かなくても進めます" and WORDS["try_hint"] == "何を？ 1行でいい"
    ask = HK[HK.index("  function choiceWithLine("):HK.index("  function askNotice(")]
    assert 'hint.append(el("span", "hk-choice-hint-sheet", W.sheet_hint));' in ask
    # One hint for both: 今日の気づき and 次にやってみること go through choiceWithLine.
    assert "hint: W.notice_hint" in HK and "hint: W.try_hint" in HK


def test_drop_takes_the_words_from_the_record_and_keeps_that_it_was_taken(tmp_path):
    session, sheet = _sheet(tmp_path)
    assert sheet["notice"] == NOTICE and NOTICE in _kept(tmp_path, session)
    assert session.hitokoto_drop("notice", True) == {"line": "notice", "dropped": True}
    kept = _kept(tmp_path, session)
    assert NOTICE not in kept
    record = json.loads(kept)["hitokoto"]
    assert record["notice"] == {"answer": "yes", "text": "", "dropped": True}  # The answer picked stays.
    assert record["next_try"] == {"answer": "try", "text": TRY}
    # No copy left beside it (a half-written file, a temporary one).
    assert [p.name for p in (tmp_path / "sessions").iterdir()] == [f"{session.session_id}.json"]
    assert session.talk.notice_text == ""
    session.hitokoto_drop("next_try", True)
    record = json.loads(_kept(tmp_path, session))["hitokoto"]
    assert record["next_try"] == {"answer": "try", "text": "", "dropped": True} and TRY not in _kept(tmp_path, session)


def test_put_back_puts_the_line_back(tmp_path):
    session, _ = _sheet(tmp_path)
    session.hitokoto_drop("notice", True)
    assert session.hitokoto_drop("notice", False, NOTICE) == {"line": "notice", "dropped": False}
    record = json.loads(_kept(tmp_path, session))["hitokoto"]
    assert record["notice"] == {"answer": "yes", "text": NOTICE}
    assert hitokoto.sheet_view(session.talk)["notice"] == NOTICE


def test_a_name_put_back_is_asked_again_and_not_kept(tmp_path):
    session, _ = _sheet(tmp_path)
    session.hitokoto_drop("notice", True)
    assert session.hitokoto_drop("notice", False, "谷口さんの話で気づいた") == {
        "status": "ask_again", "message": load_text(NAME_IN_QUESTION)}
    assert "谷口" not in _kept(tmp_path, session) and session.talk.notice_dropped


def test_only_the_two_lines_on_the_sheet_and_only_with_a_line(tmp_path):
    session, _ = _sheet(tmp_path, notice="not_yet", next_try="later")
    for line in ("notice", "next_try"):
        with pytest.raises(Refused):
            session.hitokoto_drop(line, True)  # まだない・まだ決めない: no line.
    for line in ("way", "forward", "light", "", None):
        with pytest.raises(Refused):
            session.hitokoto_drop(line, True)
    with pytest.raises(Refused):
        session.hitokoto_drop("notice", "yes")
    session, _, _, _ = sitting()
    to_scale(session)
    with pytest.raises(Refused):
        session.hitokoto_drop("notice", True)  # Not before the sheet.


def test_nothing_pressed_the_record_is_as_before(tmp_path):
    session, _ = _sheet(tmp_path)
    record = json.loads(_kept(tmp_path, session))["hitokoto"]
    assert record["notice"] == {"answer": "yes", "text": NOTICE}
    assert record["next_try"] == {"answer": "try", "text": TRY}


def test_no_list_of_words_takes_the_two_lines_off():
    word = load_lines("listener_avoid")[0]
    session, _, _, _ = sitting()
    to_scale(session)
    session.hitokoto_scale(8)
    session.hitokoto_forward("", skip=True)
    session.hitokoto_notice("yes", f"{word}のことも考えた")
    session.hitokoto_way("", skip=True)
    session.hitokoto_subject("no")
    session.hitokoto_try("look", f"{word}で調べる")
    session.hitokoto_light()
    sheet = session.hitokoto_sheet("")
    assert sheet["notice"] == f"{word}のことも考えた" and sheet["next_try"]["text"] == f"{word}で調べる"


def test_the_api_has_its_path(tmp_path):
    session, _ = _sheet(tmp_path)
    app = app_module.App.__new__(app_module.App)
    assert app._hitokoto(session, "drop", {"line": "notice", "drop": True}) == {"line": "notice", "dropped": True}


def test_the_screen_a_button_by_the_two_lines_only():
    # Two calls, one for each line; nowhere else on the sheet.
    assert SHEET_JS.count("ownLine(") == 2
    assert 'ownLine("notice", text, sheet.notice, W.sheet_notice, notice)' in SHEET_JS
    assert 'ownLine("next_try", text, sheet.next_try.text, W.sheet_meet, next)' in SHEET_JS
    assert "hk-drop" not in HK.replace(OWN, "")  # Made in ownLine only.
    # A <button>, read aloud with what it takes off; keyboard: a button is.
    assert 'const toggle = button("hk-drop", W.drop);' in OWN
    assert 'toggle.setAttribute("aria-label", `${W.drop}：${heading}`);' in OWN
    assert 'toggle.setAttribute("aria-label", `${drop ? W.restore : W.drop}：${heading}`);' in OWN
    # Pressed: the line hidden, 戻す in its place; back: the line again.
    assert "text.hidden = drop;" in OWN and "toggle.textContent = drop ? W.restore : W.drop;" in OWN
    assert 'post("drop", drop ? { line, drop: true } : { line, drop: false, text: words })' in OWN
    assert WORDS["drop"] == "外す" and WORDS["restore"] == "戻す"


def test_neither_printed_nor_a_line_taken_off():
    printed = CSS[CSS.index("/* Printed: the one sheet alone"):CSS.index("@page { size: A4;")]
    assert ".hk-drop, .hk-restore, .hk-own-message { display: none !important; }" in printed
    assert ".hk-notice-box.hk-dropped { display: none; }" in printed


def test_the_screen_check_presses_it():
    assert '"hk_sheet_drop"' in CHECK and '.hk-drop").first().click();' in CHECK
    assert "sheet over ${over}" in CHECK
