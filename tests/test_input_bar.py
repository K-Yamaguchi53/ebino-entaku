"""直し32-2: one box to write in, at the foot of the one screen. To the
town's adults (/api/ask), to one seat (/api/card, a question card), or an
AI's question (/api/coach_answer, the next round): a label on its left says
which, × or Esc goes back to everyone, its button's word follows, and the
button waits while a send is out. Run in node against app.js's own
functions, the page's parts made by hand."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _top(name):
    start = APP.index(f"function {name}(")
    if APP[start - 6:start] == "async ":
        start -= 6
    return APP[start:APP.index("\n}\n", start) + 3]


FUNCTIONS = ("seatName", "draftKey", "setTo", "sending", "askSeat", "answerTo", "backToEveryone", "showDone", "hideDone",
             "send", "sendCard", "sendAnswer", "ask", "cardOpen")

HARNESS = """
const made = {};
const part = (id) => made[id] || (made[id] = { id, textContent: "", hidden: false, value: "", disabled: false,
  dataset: {}, maxLength: 0, placeholder: "", title: "", attrs: {}, focused: 0,
  setAttribute(k, v) { this.attrs[k] = v; }, focus() { this.focused += 1; },
  replaceChildren(...kids) { this.textContent = kids.join(""); } });
const $ = part;
// Its words kept whole in their phrases (直し33-5): here, the words as they are.
const phrased = (text) => text;
const sent = [];
let answer = null, release = null;
async function call(path, body) {
  sent.push({ path, body, disabledWhileOut: $("ask-button").disabled });
  if (release) await new Promise((done) => { release = done; });
  return answer;
}
globalThis.document = { querySelectorAll: () => [] };
const state = { texts: %(texts)s, seatById: { S1: { title: "理容師", detail: "" } }, carded: new Set(),
  cardAgain: {}, drafts: {}, to: null, needsShown: false, aiAnswered: false, firstQuestion: "q", now: {} };
const log = [];
const setNow = (c) => log.push(["now", c || {}]);
const hideMessage = () => {}, showMessage = (t) => log.push(["message", t]);
const sendFailed = (e) => String(e);
const renderRound = (r) => log.push(["round", r.round]);
const renderSeats = () => log.push(["seats"]);
const bandAnswered = (r, role) => log.push(["answered", r, role]);
const cardDone = () => ({});
%(source)s
"""


def run(steps):
    words = texts.screen_texts()
    source = "\n".join(_top(name) for name in FUNCTIONS)
    program = HARNESS % {"texts": json.dumps(words, ensure_ascii=False), "source": source} + steps
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    return json.loads(out.stdout.decode("utf-8"))


EVENT = "{ preventDefault() {} }"


@node
def test_each_of_the_three_goes_to_its_own_way_with_its_own_words():
    out = run(f"""
(async () => {{
  setTo({{ kind: "all" }}, {{ focus: false }});
  const first = [$("input-to-label").textContent, $("ask-button").textContent, $("input-to-clear").hidden];
  $("question").value = "休みの日って、みんな何してる？";
  answer = {{ status: "answered", round: 1, question: "q" }};
  await send({EVENT});
  askSeat("S1");
  const seat = [$("input-to-label").textContent, $("ask-button").textContent, $("input-to-clear").hidden,
    $("question").focused, $("question").value];
  $("question").value = "休みの日に、店のことを考えますか？";
  answer = {{ card_id: "q-1", text: "休みの日に、店のことを考えますか？", again: false }};
  await send({EVENT});
  const afterCard = [state.to.kind, $("input-done").textContent, state.carded.has("S1")];
  answerTo(1, "coach");
  const ai = [$("input-to-label").textContent, $("ask-button").textContent, $("question").maxLength];
  $("question").value = "決めて取るほうに近い";
  answer = {{ status: "answered", round: 2, question: "q" }};
  await send({EVENT});
  process.stdout.write(JSON.stringify({{ first, seat, afterCard, ai, sent, to: state.to.kind, log }}));
}})();
""")
    to, send_words, done = texts.id_table("input_to", texts.INPUT_TO_IDS), \
        texts.id_table("input_send", texts.INPUT_SEND_IDS), texts.id_table("input_done", texts.INPUT_DONE_IDS)
    assert out["first"] == [to["all"], send_words["all"], True]
    assert out["seat"][0] == to["seat"].replace("{seat}", "理容師") and out["seat"][1] == send_words["seat"]
    assert out["seat"][2] is False and out["seat"][3] >= 1 and out["seat"][4] == ""  # Empty, the keyboard in it.
    assert out["afterCard"] == ["all", done["seat"].replace("{seat}", "理容師"), True]
    assert out["ai"] == [to["ai"], send_words["ai"], 120]
    assert [s["path"] for s in out["sent"]] == ["/api/ask", "/api/card", "/api/coach_answer"]
    assert out["sent"][0]["body"] == {"question": "休みの日って、みんな何してる？"}
    assert out["sent"][1]["body"] == {"seat_id": "S1", "text": "休みの日に、店のことを考えますか？"}
    assert out["sent"][2]["body"] == {"round": 1, "role": "coach", "answer": "決めて取るほうに近い", "after_notice": False}
    assert out["to"] == "all" and ["answered", 1, "coach"] in out["log"] and ["round", 2] in out["log"]


@node
def test_the_cross_and_esc_go_back_to_everyone_each_keeping_its_own_words():
    out = run("""
setTo({ kind: "all" }, { focus: false });
$("question").value = "みんなへの問い";
askSeat("S1");
$("question").value = "この人への問い";
backToEveryone();
const back = [state.to.kind, $("question").value, $("input-to-clear").hidden];
askSeat("S1");
process.stdout.write(JSON.stringify({ back, again: $("question").value }));
""")
    assert out["back"] == ["all", "みんなへの問い", True]
    assert out["again"] == "この人への問い"
    assert '$("input-to-clear").addEventListener("click", backToEveryone);' in APP
    keys = APP[APP.index('$("question").addEventListener("keydown"'):]
    assert 'event.key === "Escape" && state.to.kind !== "all"' in keys[:300] and "backToEveryone();" in keys[:300]


@node
def test_while_a_send_is_out_the_button_waits_and_a_second_press_sends_nothing():
    out = run(f"""
(async () => {{
  askSeat("S1");
  $("question").value = "休みの日に、店のことを考えますか？";
  answer = {{ card_id: "q-1", text: "x", again: false }};
  release = () => {{}};
  const first = send({EVENT});
  await Promise.resolve();
  const waiting = $("ask-button").disabled;
  await send({EVENT});  // Pressed again while the first is out.
  const count = sent.length;
  answerTo(1, "coach");  // Another to write to, while it is out: not yet.
  backToEveryone();
  const kept = state.to.kind;
  release();
  await first;
  process.stdout.write(JSON.stringify({{ waiting, count, kept, after: $("ask-button").disabled }}));
}})();
""")
    assert out == {"waiting": True, "count": 1, "kept": "seat", "after": False}


def test_every_way_to_write_goes_to_the_one_box():
    assert "card-form-template" not in HTML and 'class="card-form"' not in HTML
    assert HTML.count("<textarea") == 3  # The box, and the reflection's two.
    entry = _top("cardEntry")
    assert "askSeat(seatId)" in entry and "card-form" not in entry
    assert "askSeat(seatId);" in _top("openCardFor")
    assert "answerTo(roundNo, role)" in _top("answerEntry")
    # From a card at the table, one to one (直し34-3), which writes to that seat.
    assert 'button("card", () => openOne(seatId, card))' in MAP and "app.askSeat(seatId);  // The box at the foot" in MAP
    assert "answerTo(roundNo, card.role);" in _top("renderAiSeat")  # The AI's seat (直し32-3).
    assert "app.askSeat(seatId);" in MAP[MAP.index("function press("):]
    assert "function answerForm" not in APP and "putUnderLine" not in APP and "keptDraft" not in APP


def test_the_200_letters_names_and_the_one_card_stay():
    # The server's own limits and name removal are unchanged; the box keeps 200 (an AI answer 120).
    assert 'maxlength="200"' in HTML[HTML.index('id="question"') - 80:HTML.index('id="question"') + 80]
    assert 'box.maxLength = next.kind === "ai" ? 120 : 200;' in _top("setTo")
    assert "card.again" in _top("sendCard") and "state.texts.card_already" in _top("sendCard")


def test_the_words_are_in_texts():
    assert texts.id_table("input_to", texts.INPUT_TO_IDS)["seat"].count("{seat}") == 1
    shown = texts.screen_texts()
    assert set(shown["input_to"]) == {"all", "seat", "ai", "clear"}
    assert set(shown["input_send"]) == {"all", "seat", "ai"} and set(shown["input_done"]) == {"seat", "ai"}
