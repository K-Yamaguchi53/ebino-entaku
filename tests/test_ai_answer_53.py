"""直し53 段5 (the teacher, 11/7: 「あの余白に回答を書く方がわかりやすい」):
the room under コーチ（AI）'s and オブザーバー（AI）'s questions in their
frame was empty and looked like a box to write in. Before a question is
picked it says 「答えたい問いを押してね」 (叩き台); picked, the question is lit
and a box (1 to 3 lines) with 送る・やめる comes right under it, in the frame.
It sends what the box at the foot sent (/api/coach_answer); the box at the
foot stays 「町の大人に聞く」 and no longer answers the AI (one way, not two)."""

import json
import re
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _top(name):
    start = APP.index(f"function {name}(")
    if APP[start - 6:start] == "async ":
        start -= 6
    return APP[start:APP.index("\n}\n", start) + 3]


def test_the_words_are_the_teachers_draft_in_texts():
    words = texts.screen_texts()["ai_answer_words"]
    assert words == {"pick": "答えたい問いを押してね", "send": "送る", "cancel": "やめる"}
    # Read out as whose question it answers: the words there were (input_to).
    assert "state.texts.input_to[`ai_${role}`]" in _top("answerTo")


def test_the_box_is_in_the_ai_seat_under_the_questions():
    seat = HTML[HTML.index('<section id="ai-seat"'):HTML.index("</section>", HTML.index('<section id="ai-seat"'))]
    assert seat.index('id="ai-seat-cards"') < seat.index('id="ai-seat-pick"') < seat.index('<form id="ai-answer"')
    assert '<textarea id="ai-answer-text" rows="2" maxlength="120"></textarea>' in seat
    assert 'type="button" id="ai-answer-cancel"' in seat and 'type="submit" id="ai-answer-send"' in seat
    assert '<p id="ai-seat-pick" class="ai-seat-pick" hidden></p>' in seat  # A line, never a box that takes nothing.
    # Picked, it goes right under that question; the seat scrolls in itself, never the page.
    answer = _top("answerTo")
    assert "if (picked) picked.after(form);" in answer and "seat.scrollTop" in answer
    assert "text.focus({ preventScroll: true });" in answer
    # Before the cards are made again, the box is taken out of them.
    seat_js = _top("renderAiSeat")
    assert seat_js.index('$("ai-seat-pick").after($("ai-answer"));') < seat_js.index("cards.replaceChildren();")
    # Words 14px or more; buttons 44px to press; folded, not shown.
    # 直し54 (the teacher, 11/8: 小さいと気付かない): 18px and bold now.
    assert re.search(r"\.ai-seat-pick \{[^}]*font-size: 18px; font-weight: 700;", CSS)
    assert ".ai-answer-buttons button { min-height: 44px;" in CSS
    assert ".ai-seat.folded .ai-seat-pick,\n.ai-seat.folded .ai-answer { display: none; }" in CSS


def test_one_way_to_answer_the_same_body_as_before():
    send = _top("send")
    assert "sendAnswer" not in send and 'state.to.kind === "ai"' not in send  # The box at the foot: the town's only.
    form = _top("sendAnswer")
    assert 'const button = $("ai-answer-send");' in form and 'const answer = $("ai-answer-text").value.trim();' in form
    assert 'call("/api/coach_answer", { round: roundNo, role, answer, after_notice: state.needsShown },' in form
    # As before: asking again keeps the words; the next round starts; the band's mark; the draft gone.
    assert form.index('round.status === "ask_again"') < form.index("bandAnswered(roundNo, role);")
    assert "delete state.drafts[`ai:${roundNo}:${role}`];" in form and "renderRound(round);" in form
    assert "setTo(" not in _top("answerTo")
    assert '$("ai-answer").addEventListener("submit"' in APP and '$("ai-answer-cancel").addEventListener("click"' in APP
    # Esc in it: やめる.
    keys = APP[APP.index('$("ai-answer-text").addEventListener("keydown"'):]
    assert 'event.key === "Escape"' in keys[:200] and "closeAiAnswer();" in keys[:300]


def test_no_sign_over_the_box_while_writing():
    assert _top("guideState").index("if (state.aiAnswer) return \"\";") < _top("guideState").index("nowState()")
    assert 'if (state.aiAnswer) return "answer_ai";' in _top("nowState")


PICK = """
const made = {};
const part = (id) => made[id] || (made[id] = { id, textContent: "", hidden: false, value: "", attrs: {}, focused: 0,
  setAttribute(k, v) { this.attrs[k] = v; }, focus() { this.focused += 1; }, after() {},
  querySelectorAll: () => buttons });
const $ = part;
let buttons = [];
const button = (role, disabled) => ({ dataset: { role }, disabled, cls: {}, attrs: {}, focused: 0,
  classList: { toggle(name, on) { this.owner.cls[name] = on; } }, setAttribute(k, v) { this.attrs[k] = v; },
  focus() { this.focused += 1; }, after() {} });
globalThis.document = { querySelectorAll: () => buttons, querySelector: (q) => buttons.find((b) => q.includes(b.dataset.role)) };
const state = { texts: %(texts)s, drafts: {}, aiAnswer: null };
const setNow = () => {};
const sending = () => false;
const foldAiSeat = () => {};
const hideDone = () => {};
%(source)s
buttons = [button("coach", false), button("observer", false)];
for (const b of buttons) b.classList.owner = b;
showAiPick();
const before = [$("ai-seat-pick").hidden, $("ai-seat-pick").textContent];
answerTo(4, "observer");
const picked = [$("ai-seat-pick").hidden, $("ai-answer").hidden, buttons.map((b) => [b.cls.chosen, b.attrs["aria-pressed"]])];
$("ai-answer-text").value = "まだ途中";
closeAiAnswer();
const closed = [state.aiAnswer, $("ai-answer").hidden, $("ai-seat-pick").hidden, state.drafts["ai:4:observer"],
  buttons[1].focused];
answerTo(4, "observer");
const again = $("ai-answer-text").value;
buttons = buttons.map((b) => ({ ...b, disabled: true }));
state.aiAnswer = null;
showAiPick();
process.stdout.write(JSON.stringify({ before, picked, closed, again, answered: $("ai-seat-pick").hidden }));
"""


@node
def test_the_line_until_one_is_picked_and_the_draft_kept_on_cancel():
    source = "\n".join(_top(name) for name in ("draftKey", "answerTo", "keepAiDraft", "closeAiAnswer", "showAiPick",
                                                 "markAiChosen"))
    program = PICK % {"texts": json.dumps(texts.screen_texts(), ensure_ascii=False), "source": source}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    assert got["before"] == [False, "答えたい問いを押してね"]
    assert got["picked"] == [True, False, [[False, "false"], [True, "true"]]]
    assert got["closed"] == [None, True, False, "まだ途中", 1]  # Back on the question, its words kept.
    assert got["again"] == "まだ途中"
    assert got["answered"] is True  # Once answered, no line asking to pick.
