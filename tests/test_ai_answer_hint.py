"""「コーチかオブザーバーの問いに、1つ答えよう。」 (直し30の続き-0), said once in
one place (直し31-5): it is now the line of 「いまやること」 at the top while
the newest round has AI questions and none has been answered in this
session, and no longer over the cards as well. A round with no cards does
not ask for it; the round table's bubbles are left as they are."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


_RUN = """
%(source)s
function el(tag, attrs, ...kids) { return { tag, cls: attrs.class, text: attrs.text, kids, dataset: {},
  append(...more) { this.kids.push(...more); }, classList: { add() {} } }; }
function answerEntry() { return el("button", { class: "quiet" }); }
const onMap = () => {};
const asked = [];
function setNow(changes) { asked.push(changes); }
const state = { texts: { ai_answer_hint: "HINT" }, bands: {}, aiAnswered: %(answered)s, lastRound: 1 };
const box = el("div", {});
async function call() { return %(band)s; }
loadBand(1, box).then(() => {
  const part = box.kids[0];
  process.stdout.write(JSON.stringify({ kids: part ? part.kids.map((k) => k.cls + ":" + (k.text || "")) : null, asked }));
});
"""

CARDS = '{ cards: [{ role: "coach", label: "C", badge: "", question: "Q1" }, ' \
        '{ role: "observer", label: "O", badge: "", question: "Q2" }], answered: %s }'


def run(band, answered="false"):
    program = _RUN % {"source": "async " + _top("loadBand"), "band": band, "answered": answered}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    return json.loads(out.stdout.decode("utf-8"))


@node
def test_cards_to_answer_ask_for_the_line_at_the_top_and_not_over_the_cards():
    got = run(CARDS % "null")
    assert got["kids"] == ["ai-card:", "ai-card:"]  # No second line over the cards.
    assert got["asked"] == [{"band": True}]


@node
def test_once_answered_it_is_not_asked_for():
    assert run(CARDS % '"coach"')["asked"] == []
    # The state that shows it holds only until one AI question is answered.
    form = _top("answerForm")
    assert form.index("state.aiAnswered = true;") < form.index("renderRound(round);")
    assert '!state.aiAnswered && now.band' in _top("nowState")


@node
def test_a_round_with_no_cards_asks_for_nothing():
    assert run("{ cards: [], answered: null }") == {"kids": None, "asked": []}


def test_the_line_is_the_teachers_and_not_at_the_round_table():
    assert texts.screen_texts()["ai_answer_hint"] == "コーチかオブザーバーの問いに、1つ答えよう。"
    assert texts.screen_texts()["now_line"]["answer_ai"]["text"] == "コーチかオブザーバーの問いに、1つ答えよう。"
    assert "答えよう" not in APP and ".ai-hint" not in APP
    assert "ai_answer_hint" not in (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
