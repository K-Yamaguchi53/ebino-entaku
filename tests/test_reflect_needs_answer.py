"""Before the reflection, one answer to コーチ or オブザーバー (直し30-1): in any
round, once. Not yet: 「ふりかえりへ」 stays and can be pressed, a line comes
by it, and the newest card that can still be answered is brought into view
with its 「答える」 focused. No student is ever held: with no card to answer
anywhere, or once the model was out, the reflection opens. The server never
refuses for it; the record keeps one mark of an answer given after the line."""

import json
import random
import shutil
import subprocess

import pytest
from fake_client import FakeClient

from ebino import app as app_module
from ebino import texts
from ebino.app import App
from ebino.gate import Gate, NameList
from test_coach import GOOD_COACH, GOOD_OBSERVER, round_one
from test_session import ANSWERED, SEATS, library

APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
HTML = (app_module.STATIC_DIR / "index.html").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


_RUN = """
%(source)s
const line = { hidden: true, textContent: "" };
const $ = (id) => (id === "reflect-needs-answer" ? line : id === "ai-seat" ? { hidden: true } : null);
let opened = 0, focused = 0, scrolled = [];
function openReflection() { opened += 1; }
const card = { classList: { add() {}, remove() {}, contains: () => false }, scrollIntoView(o) { scrolled.push(o.behavior); } };
const entry = { closest: () => card, focus() { focused += 1; } };
const band = (open) => ({ querySelector: () => (open ? entry : null) });
globalThis.document = { querySelectorAll: () => [] };
globalThis.window = { matchMedia: () => ({ matches: %(still)s }) };
const openDrawer = () => {};  // The drawer (直し32-1): the card is in it.
const state = { texts: { reflect_needs_answer: "LINE" }, bands: %(bands)s,
  aiAnswered: %(answered)s, aiUnavailable: %(unavailable)s, needsShown: false };
toReflection();
process.stdout.write(JSON.stringify({ opened, focused, scrolled, line: line.hidden ? "" : line.textContent,
  needsShown: state.needsShown }));
"""


def run(bands="{1: band(true)}", answered="false", unavailable="false", still="false"):
    program = _RUN % {"source": _top("toReflection") + _top("answerable"), "bands": bands,
                      "answered": answered, "unavailable": unavailable, "still": still}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    return json.loads(out.stdout.decode("utf-8"))


@node
def test_never_answered_it_does_not_go_on_and_the_line_shows():
    assert run() == {"opened": 0, "focused": 1, "scrolled": ["smooth"], "line": "LINE", "needsShown": True}
    # Motion reduced: the page moves at once.
    assert run(still="true")["scrolled"] == ["auto"]


@node
def test_once_answered_it_goes_on():
    assert run(answered="true") == {"opened": 1, "focused": 0, "scrolled": [], "line": "", "needsShown": False}


@node
def test_with_no_card_to_answer_anywhere_it_goes_on():
    # No card came (or /api/coach failed): no band at all.
    assert run(bands="{}")["opened"] == 1
    # Only bands already answered (no 「答える」 left).
    assert run(bands="{1: band(false), 2: band(false)}")["opened"] == 1
    # An older round's card that can still be answered is found too.
    assert run(bands="{1: band(true), 2: band(false)}")["opened"] == 0


@node
def test_after_the_model_was_out_once_it_goes_on():
    assert run(unavailable="true")["opened"] == 1


def test_only_an_answer_that_started_the_next_round_counts():
    form = _top("sendAnswer")  # The one box at the foot answers it (直し32-2).
    assert 'if (round.status === "unavailable") state.aiUnavailable = true;' in form
    sent = form.index("after_notice: state.needsShown")
    turned = form.index('if (round.status === "ask_again" || round.status === "unavailable") {')
    counted = form.index("state.aiAnswered = true;")
    assert sent < turned < counted < form.index("renderRound(round);")
    assert "aiAnswered: false, aiUnavailable: false, needsShown: false" in APP


def test_the_button_stays_and_the_line_is_the_teachers():
    assert '$("to-reflect").addEventListener("click", toReflection);' in APP
    assert "disabled" not in _top("toReflection") and "to-reflect" not in _top("toReflection")
    # At the foot of the one screen (直し32-1): the line just over the box, the button beside it.
    foot = HTML[HTML.index('class="input-area"'):]
    assert foot.index('id="reflect-needs-answer"') < foot.index('id="ask-form"') < foot.index('id="to-reflect"')
    assert texts.screen_texts()["reflect_needs_answer"] == \
        "ふりかえりの前に、コーチかオブザーバーの問いに、1つだけ答えてください。"


def test_the_server_never_refuses_the_reflection_for_it():
    the_app = App(library(), Gate(FakeClient(list(ANSWERED)), NameList.build(SEATS, {})), rng=random.Random(1))
    the_app.start({"lab": "action"})
    the_app.handle("/api/ask", {"question": "休みの日って、みんな何してる？"})
    begun = the_app.handle("/api/reflect/begin", {"changed": "same", "now_question": "休みは？"})
    assert "status" in begun or "ask_back" in begun


def _saved(tmp_path, session):
    return json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))


def test_the_record_keeps_one_mark_of_an_answer_after_the_line(tmp_path):
    session, _ = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER}, tmp_path=tmp_path, more=ANSWERED)
    session.coach_band(1)
    assert _saved(tmp_path, session)["ai_answered_after_notice"] is False
    session.coach_answer(1, "observer", "店を開ける人の役に立っていると思う", after_notice=True)
    record = _saved(tmp_path, session)
    assert record["ai_answered_after_notice"] is True
    text = json.dumps(record, ensure_ascii=False)
    assert "谷口" not in text and ":" not in record["date"]


def test_an_answer_the_model_could_not_take_leaves_no_mark(tmp_path):
    session, _ = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER}, tmp_path=tmp_path, more=[])
    session.coach_band(1)
    view = session.coach_answer(1, "coach", "決めて取るほう", after_notice=True)
    assert view["status"] == "unavailable"
    assert _saved(tmp_path, session)["ai_answered_after_notice"] is False


def test_the_screen_sends_the_mark_to_the_server():
    src = (app_module.STATIC_DIR.parent / "app.py").read_text(encoding="utf-8")
    assert 'after_notice=body.get("after_notice") is True' in src
