"""直し53 段3 (the teacher, 11/7: 円卓から地図に戻ると、もう円卓には戻れない？):
after 地図にもどす, until the next question, 「円卓にもどる」 opens that round's
table again, the same seats and bubbles (the round as it was kept on the
screen, opened as recompose opens it: at once). A new question takes the
button away. Nothing is sent or kept for it."""

import re

from ebino import app as app_module
from ebino import texts

SCRIPT = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
HTML = (app_module.STATIC_DIR / "index.html").read_text(encoding="utf-8")


def _inner(name):
    start = SCRIPT.index(f"function {name}(")
    return SCRIPT[start:SCRIPT.index("\n  }\n", start) + 5]


def test_the_buttons_word_is_in_texts_beside_the_back():
    words = texts.map_buttons()
    assert words["reopen"] == {"text": "円卓にもどる", "label": "円卓にもどる"}
    assert words["back"]["text"] == "地図にもどす"  # Unchanged.
    assert HTML.index('id="map-back"') < HTML.index('id="map-reopen"') < HTML.index('id="map-heading"')
    assert '<button type="button" id="map-reopen" class="map-back" hidden></button>' in HTML
    assert '["map-reopen", "reopen"]' in _inner("controls")


def test_closing_keeps_the_round_and_shows_the_button_on_the_relief_only():
    close = _inner("closeTable")
    assert close.index("const closing = tableOf;") < close.index("clearTable();")
    assert "if (closing && view && view.relief) {" in close
    assert "lastTable = closing;" in close and '$("map-reopen").hidden = false;' in close


def test_reopening_is_the_same_round_at_once_and_sends_nothing():
    again = _inner("reopenTable")
    assert "if (!again || !view || !view.relief || tableAt || one) return;" in again
    # The same result and order, opened as recompose does (again = true: nothing flies).
    assert "await openTable(again.result, again.order, tableCenter(), () => mine === roundNo, true);" in again
    assert "reduced() ? 0 : 400" in again
    assert "fetch" not in again and "post(" not in again and "app.send" not in again
    assert "forgetLastTable();" in again  # Once: the button goes while the table is open.


def test_a_new_question_takes_the_button_away():
    assert _inner("clearRound").startswith("function clearRound() {\n    forgetLastTable();")
    forget = _inner("forgetLastTable")
    assert "lastTable = null;" in forget and '$("map-reopen").hidden = true;' in forget
    # Nothing of it is kept in the browser.
    assert not re.search(r"(localStorage|sessionStorage)[^\n]*lastTable", SCRIPT)
