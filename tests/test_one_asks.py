"""直し34-4 on the screen: the three questions under the person's words, a
question picked asks the server for that item, a question written goes to
/api/one/free; not found shows the teacher's line and 「質問カードにする」.
The routes reach the session's one to one only."""

import random

import pytest
from fake_client import FakeClient
from test_one_to_one import SEATS, UTTERANCES

from ebino import app as app_module, texts
from ebino.app import App
from ebino.gate import Gate, NameList
from ebino.session import Library, Session

STATIC = app_module.STATIC_DIR
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
APP = (STATIC / "app.js").read_text(encoding="utf-8")


def _body(source, name):
    part = source[source.index(name):]
    return part[:part.index("\n  }\n") if source is MAP else part.index("\n}\n")]


@pytest.fixture
def the_app(monkeypatch):
    monkeypatch.setenv("EBINO_SPEAKER", "0")
    lib = Library.build(SEATS, UTTERANCES, {})
    lib.ask_tables = {"pages": {"C01": {"p1": ["行く前"]}}, "ranking": {}}
    gate = Gate(FakeClient([]), NameList.build(SEATS, {}))
    app = App(lib, gate, rng=random.Random(1))
    app.session = Session(lib, gate, rng=random.Random(1))
    return app


def test_the_routes_open_ask_and_write(the_app, monkeypatch):
    view = the_app.handle("/api/one/open", {"seat_id": "A01"})
    assert len(view["questions"]) == 3
    picked = the_app.handle("/api/one/ask", {"seat_id": "A01", "item": view["questions"][0]["item"]})
    assert picked["pieces"] and picked["item"] == view["questions"][0]["item"]
    from ebino import librarian
    from ebino.librarian import Found
    monkeypatch.setattr(librarian, "find", lambda *a, **k: Found([], "none"))
    assert the_app.handle("/api/one/free", {"seat_id": "A01", "question": "好きな色は？"})["found"] is False


def test_the_words_of_one_to_one_are_the_teachers_and_in_texts():
    words = texts.screen_texts()["one_words"]
    assert words["not_found"] == "記事には書いてありませんでした。" and words["to_card"] == "質問カードにする"
    # From texts/, never written in the code (comments may name them).
    code = "\n".join(line for line in (MAP + APP).splitlines() if not line.strip().startswith("//"))
    for word in ("記事には書いてありませんでした", "質問カードにする"):
        assert word not in code


def test_the_questions_are_buttons_and_a_written_one_goes_to_free():
    asks = _body(MAP, "function showAsks(")
    assert 'document.createElement("button")' in asks and "view.questions" in asks
    assert "app.oneAsk(mine.seatId, item)" in asks
    answer = _body(MAP, "function oneAnswer(")
    assert "app.state.texts.one_words.not_found" in answer and "app.state.texts.one_words.to_card" in answer
    assert "app.cardFromOne(mine.seatId, question)" in answer
    assert 'if (state.to.kind === "seat" && state.now.one) return sendOne(state.to.seatId);' in APP
    assert 'call("/api/one/free"' in _body(APP, "async function sendOne(")


def test_done_shows_the_teachers_line_and_one_choice_that_thanks_and_closes(the_app):
    # 直し34-5.
    words = texts.screen_texts()["one_words"]
    assert words["done"] == "聞き終えました" and words["thanks"] == "ありがとうございました"
    asks = _body(MAP, "function showAsks(")
    assert "if (view.done)" in asks and "app.state.texts.one_words.done" in asks and "app.state.texts.one_words.thanks" in asks
    assert "await app.oneThanks(mine.seatId);" in asks and "closeOne();" in asks
    assert 'node.classList.toggle("thanked", app.state.thanked.has(id));' in MAP
    for item in ("目的", "結果"):
        the_app.handle("/api/one/ask", {"seat_id": "P01", "item": item})
    assert the_app.handle("/api/one/thanks", {"seat_id": "P01"}) == {"thanked": ["P01"]}


def test_the_keyboard_starts_at_the_first_question_and_the_chairs_step_aside():
    opened = _body(MAP, "function standUp(")
    assert 'overlay.querySelector(".one-asks .one-ask")' in opened and "first.focus(" in opened
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    assert ".one-on .table .chair { visibility: hidden; }" in css
