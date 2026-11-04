"""One line just over the two cards of コーチ and オブザーバー (直し30の続き-0):
「コーチかオブザーバーの問いに、1つ答えよう。」 while no AI question has been
answered in this session. Once one is (counted as in 直し30-1), it goes from
over every round's cards. A round with no cards has none; the round table's
bubbles are left as they are."""

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
const state = { texts: { ai_answer_hint: "HINT" }, bands: {}, aiAnswered: %(answered)s };
const box = el("div", {});
async function call() { return %(band)s; }
loadBand(1, box).then(() => {
  const part = box.kids[0];
  process.stdout.write(JSON.stringify(part ? part.kids.map((k) => k.cls + ":" + (k.text || "")) : null));
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
def test_before_any_answer_the_line_is_just_over_the_two_cards():
    assert run(CARDS % "null") == ["ai-hint:HINT", "ai-card:", "ai-card:"]


@node
def test_once_one_is_answered_it_is_not_shown_and_goes_from_every_round():
    assert run(CARDS % "null", answered="true") == ["ai-card:", "ai-card:"]
    assert run(CARDS % '"coach"') == ["ai-card:", "ai-card:"]
    # On the answer that counts, every round's line goes, with the lamp on the cards.
    form = _top("answerForm")
    assert form.index("state.aiAnswered = true;") \
        < form.index('for (const node of document.querySelectorAll(".ai-hint")) node.remove();') \
        < form.index("renderRound(round);")


@node
def test_a_round_with_no_cards_has_no_line():
    assert run("{ cards: [], answered: null }") is None


def test_the_line_is_the_teachers_and_not_at_the_round_table():
    assert texts.screen_texts()["ai_answer_hint"] == "コーチかオブザーバーの問いに、1つ答えよう。"
    assert "答えよう" not in APP
    assert "ai_answer_hint" not in (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
