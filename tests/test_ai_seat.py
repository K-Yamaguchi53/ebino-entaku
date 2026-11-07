"""直し32-3: コーチ and オブザーバー sit at the AI's seat, out of the round
table's ring, in another shape and colour than the town's people: a rounded
square in the AI's blue with 「AI」 on it, its name, and the newest round's
questions. Their questions never come as the table's bubbles. Pressing one,
the box at the foot answers it. The first time, one line says they are the
AI's; after that the name only. How they are kept is unchanged."""

import json
import re
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


def _rule(selector):
    found = re.search(re.escape(selector) + r" \{[^}]*\}", CSS)
    assert found, selector
    return found.group(0)


def test_its_words_are_the_teachers_drafts_in_texts():
    shown = texts.screen_texts()
    assert shown["ai_seat_label"] == "AI（町の人ではありません）"
    assert shown["ai_seat_note"] == "この問いは、AI が作りました。地図の人の言葉ではありません。"
    assert shown["ai_seat_mark"] == "AI"
    assert shown["bubble_answer"] == "答える"  # The word under the rounds' AI cards, as before.


def test_it_sits_on_the_one_screen_apart_from_the_table():
    stage = HTML[HTML.index('<div id="stage"'):HTML.index('<aside id="drawer"')]
    assert 'id="ai-seat"' in stage and 'id="ai-seat-cards"' in stage
    # 直し48 段2 (the teacher, 11/7): no heading 「AI（町の人ではありません）」
    # nor note (the first look says both are AI); the seat named for reading out only.
    assert 'id="ai-seat-mark"' not in stage and 'id="ai-seat-note"' not in stage
    assert '<span\n          id="ai-seat-label" class="visually-hidden"></span>' in stage
    assert stage.index('id="map"') < stage.index('id="ai-seat"')  # Not in the map's frame: off the table.


def test_no_ai_sits_at_the_table_nor_speaks_in_its_bubbles():
    for gone in ("seatBand", "aiBubble", "openAnswer", "aiAngles", "AI_FLAME", "table-bubble ai", "band: setBand"):
        assert gone not in MAP, gone
    band = _top("loadBand")
    assert "map.band" not in band and "renderAiSeat(roundNo, band)" in band
    # The map's cards keep off the AI's seat where it lies over the map's side.
    assert '#inside:not([hidden]), #ai-seat:not([hidden])' in MAP


def test_its_shape_and_colour_are_not_a_seats():
    mark = _rule(".ai-mark")
    assert "border-radius: 9px" in mark and "background: var(--ai)" in mark
    question = _rule(".ai-question")
    assert "var(--ai" in question and "var(--paper" not in question and "var(--lamp" not in question
    # 直し48 段2: its words in a bubble in the AI's blue, from its robot.
    words = _rule(".ai-question .words")
    assert "border: 1px solid var(--ai);" in words and "var(--paper" not in words and "var(--lamp" not in words
    seat = _rule(".ai-seat")
    assert "border: 2px solid var(--ai)" in seat and "background: var(--ai-deep)" in seat
    # The seats' bubbles at the table are paper, never the AI's blue.
    for rule in re.findall(r"\.table-bubble[^{]*\{[^}]*\}", CSS):
        assert "var(--ai" not in rule, rule


def test_pressing_a_question_the_box_answers_it_and_reflecting_goes_to_it_first():
    seat = _top("renderAiSeat")
    assert 'button.addEventListener("click", () => answerTo(roundNo, card.role));' in seat
    assert 'class: "ai-question"' in seat
    first = _top("answerable")
    assert first.index('seat.querySelector(".ai-question:not(:disabled)")') < first.index("state.bands")
    assert '`#ai-seat-cards .ai-question[data-round="${roundNo}"]`' in _top("bandAnswered")


HARNESS = """
const made = {};
const part = (id) => made[id] || (made[id] = { id, textContent: "", hidden: true, children: [], attrs: {}, folded: null,
  classList: { toggle(name, on) { if (name === "folded") made[id].folded = on; } },
  setAttribute(k, v) { this.attrs[k] = v; },
  replaceChildren(...kids) { this.children = kids; if (kids.length && kids.every((kid) => typeof kid === "string")) this.textContent = kids.join(""); },
  append(kid) { this.children.push(kid); }, after() {} });
const $ = part;
function el(tag, attrs, ...kids) { return { tag, attrs, kids, classList: { add() {} }, addEventListener() {} }; }
function mapMoved() {}
const EbinoRobot = { make: (role) => ({ robot: role }) };  // robot.js (直し47).
const phrased = (text) => text;  // Kept whole in its phrases (直し33-5): here, as it is.
const state = { texts: { ai_seat_mark: "AI", ai_seat_label: "LABEL", ai_seat_note: "NOTE" } };
%(source)s
const band = { cards: [{ role: "coach", label: "C", question: "Q1" }, { role: "observer", label: "O", question: "Q2" }],
  answered: null };
renderAiSeat(1, band);
const first = [$("ai-seat").hidden, $("ai-seat-note").hidden, $("ai-seat-note").textContent, $("ai-seat-cards").children.length];
renderAiSeat(2, band);
const second = [$("ai-seat-note").hidden];
renderAiSeat(2, band);
foldAiSeat(true);
const folded = [$("ai-seat").folded, $("ai-seat-open").hidden, $("ai-seat-open").attrs["aria-expanded"]];
renderAiSeat(3, band);
const opened = [$("ai-seat").folded, $("ai-seat-open").hidden, $("ai-seat-open").attrs["aria-expanded"]];
process.stdout.write(JSON.stringify({ first, second, folded, opened, label: $("ai-seat-label").textContent,
  faces: $("ai-seat-faces").children }));
"""


@node
def test_no_heading_nor_note_the_seat_named_by_the_roles_names():
    """直し48 段2 (the teacher, 11/7): the heading and the note are gone
    (said on the first look); the seat is named by コーチ（AI）・オブザーバー（AI）
    for reading out, and folded its head is their robots."""
    program = HARNESS % {"source": _top("renderAiSeat") + _top("foldAiSeat") + _top("openAiSeat") + "\n"
                         + "function showAiPick() {}  // 直し53 段5: tests/test_ai_answer_53.py.\n"}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    assert got["first"] == [False, True, "", 2]  # The note never shown, never filled.
    assert got["second"] == [True] and got["label"] == "C・O"
    assert got["faces"] == [{"robot": "coach"}, {"robot": "observer"}]
    seat = _top("renderAiSeat")
    assert "ai_seat_label" not in seat and "ai_seat_note" not in seat and "ai_seat_mark" not in seat
    assert ".ai-seat:not(.folded) .ai-seat-head { display: none; }" in CSS
    # 直し37-2: folded back at the map, the button that opens it shown; a round's questions open it.
    assert got["folded"] == [True, False, "false"] and got["opened"] == [False, True, "true"]
