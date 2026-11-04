"""最初にもどる (直し30-2): once the reflection sheet is out, a button at its
foot takes the screen back to the first one for the next student, asked once
more on the page itself (never the browser's own box). Going back reads the
page afresh, so nothing of the last student's words is left; the last
sitting's record stays on the server, and the next Lab starts a new one."""

import json
import random

from fake_client import FakeClient

from ebino import app as app_module
from ebino import texts
from ebino.app import App
from ebino.gate import Gate, NameList
from ebino.records import Records
from test_session import ANSWERED, SEATS, library

APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
HTML = (app_module.STATIC_DIR / "index.html").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


def test_its_words_are_the_teachers():
    shown = texts.screen_texts()
    assert shown["back_to_start"] == "最初にもどる"
    assert shown["back_to_start_confirm"] == "最初の画面にもどります。ここまでの記録は残ります。"
    assert (shown["back_to_start_yes"], shown["back_to_start_no"]) == ("もどる", "やめる")
    for word in ("最初にもどる", "もどる", "やめる"):
        assert f'"{word}"' not in APP and f">{word}<" not in HTML


def test_it_comes_at_the_sheets_foot_once_the_sheet_is_out():
    assert HTML.index('id="sheet"') < HTML.index('id="back-to-start"') < HTML.index("</section>", HTML.index('id="sheet"'))
    assert '<div id="back-to-start" class="back-to-start" hidden>' in HTML
    assert _top("renderSheet").rstrip().endswith("showBackToStart();\n}")
    # Where ② is asked, the sheet (and so the button) comes after the card.
    pick = _top("pickUse")
    assert pick.index("showHarvest(card);") < pick.index("renderSheet(state.sheet);")


def test_it_asks_on_the_page_and_never_in_the_browsers_box():
    assert "confirm(" not in APP and "alert(" not in APP
    ask = _top("askBackToStart")
    assert '$("back-confirm").hidden = false;' in ask and '$("back-no").focus();' in ask
    stay = _top("stayHere")
    assert '$("back-confirm").hidden = true;' in stay and '$("back-start").focus();' in stay
    assert '$("back-start").addEventListener("click", askBackToStart);' in APP
    assert '$("back-yes").addEventListener("click", backToStart);' in APP
    assert '$("back-no").addEventListener("click", stayHere);' in APP
    assert 'if (event.key === "Escape") stayHere();' in APP
    # Buttons, so the keyboard reaches them and their focus ring shows.
    assert '<button type="button" id="back-yes">' in HTML and '<button type="button" id="back-no">' in HTML
    assert "button:focus-visible" in CSS


def test_going_back_reads_the_page_afresh_and_leaves_no_words():
    back = _top("backToStart")
    assert 'document.querySelectorAll("input, textarea")' in back and 'node.value = "";' in back
    assert "window.location.replace(window.location.pathname);" in back
    # Nothing of a student is kept in the browser.
    for kept in ("localStorage", "sessionStorage", "indexedDB", "document.cookie"):
        assert kept not in APP


def test_the_last_sitting_is_kept_and_the_next_lab_starts_a_new_one(tmp_path):
    client = FakeClient(list(ANSWERED))
    app = App(library(), Gate(client, NameList.build(SEATS, {})), Records(tmp_path), rng=random.Random(1))
    app.handle("/api/start", {"lab": "action"})
    app.handle("/api/ask", {"question": "休みの日って、みんな何してる？"})
    first = app.session.session_id
    path = tmp_path / "sessions" / f"{first}.json"
    kept = path.read_text(encoding="utf-8")
    # 最初にもどる reads the page again; the next student presses a Lab.
    app.handle("/api/start", {"lab": "quest"})
    assert app.session.session_id != first
    assert path.read_text(encoding="utf-8") == kept
    assert json.loads(kept)["rounds"][0]["question"] == "休みの日って、みんな何してる？"
    new = json.loads((tmp_path / "sessions" / f"{app.session.session_id}.json").read_text(encoding="utf-8"))
    assert new["lab"] == "quest" and new["rounds"] == []
