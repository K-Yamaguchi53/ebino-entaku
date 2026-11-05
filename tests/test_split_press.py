"""直し40-1: the split's heading pressed where it is seen: the tag on the
flat map (.split-tag) and the heading under the round table (#map-heading,
on a map TAG_ON_MAP wide or wider); on a narrower one, the drawer's button
only, as before. Pressed, the box writes to everyone again (what was being
written to a seat or an AI's question stays in state.drafts), then, as
before, /api/split and the heading into the box (fill); one line over the
box (#input-done) until the question is asked, the box is emptied or whom
it writes to changes. 「いまやること」 says the split can be pressed while
the latest round's split is not. At one to one neither heading, nor the
dashed line down the table, is seen. Everything here is invented."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts
from test_session import ANSWERED, sitting

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
TOOL = (STATIC.parent.parent / "tools" / "check_split_press.js").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def test_the_maps_tag_and_the_heading_under_the_table_are_buttons_that_press_the_split():
    button = _inner("splitButton")
    assert 'document.createElement("button")' in button and 'press.type = "button";' in button
    assert "press.append(app.phrased(app.shownQuotes(split.heading)));" in button  # The words as they were shown.
    assert 'press.setAttribute("aria-label", app.splitLabel(split.heading));' in button
    assert 'press.addEventListener("click", () => app.pressSplit(roundNo, split.index));' in button
    assert 'const tag = splitButton(result.round, split, "split-tag");' in _inner("drawSplits")
    assert ('if (split && overlay.clientWidth >= TAG_ON_MAP) $("map-heading").replaceChildren(splitButton(result.round, split, '
            '"map-heading-press"));') in MAP
    # The drawer's button presses the same way.
    assert "onclick: () => pressSplit(roundNo, split.index)" in _top("renderSplit")
    assert "pressSplit, splitLabel };" in APP


def test_read_aloud_as_this_split_to_the_next_question_and_its_heading():
    assert 'const SPLIT_PRESS = "この割れ目を次の問いにする";' in APP
    assert "return `${SPLIT_PRESS}：${shownQuotes(heading)}`;" in _top("splitLabel")


def test_they_take_a_press_over_the_map_and_look_as_they_did():
    assert ".map-overlay { position: absolute; inset: 0; pointer-events: none; }" in CSS
    tag = CSS[CSS.index("button.split-tag {"):]
    tag = tag[:tag.index("}")]
    assert "pointer-events: auto; cursor: pointer;" in tag and "min-height: 0;" in tag and "margin: 0;" in tag
    assert ".map-bar .map-heading-press { all: unset; cursor: pointer;" in CSS
    assert "button.split-tag:focus-visible { outline: 2px solid var(--lamp);" in CSS
    # The heading's box scrolls: the ring inside it, or it is cut off.
    assert ".map-bar .map-heading-press:focus-visible { outline: 2px solid var(--lamp); outline-offset: -2px;" in CSS
    assert "body:has(#table:not([hidden])):has(#map:not([hidden])) .map-heading { flex: 0 1 auto; min-height: 0; overflow: auto;" in CSS


def test_the_flat_maps_tag_keeps_off_every_seats_point_when_drawn_and_put_again():
    assert "placeSplitTags();" in _inner("drawSplits")
    assert "[...fixedBoxes(frameBox), ...counted, ...others, ...seenPoints(frameBox)]" in _inner("placeSplitTags")
    assert ('put([...overlay.querySelectorAll(".split-tag")], (items) => planLabels(frameSize, items, '
            '[...fixed, ...seenPoints(frameBox)]));') in _inner("relayout")
    assert 'svg.querySelectorAll(".points .pt .shape")' in _inner("seenPoints")


def test_the_tag_keeps_off_the_seniors_count():
    again = _inner("relayout")
    assert 'const count = frame.querySelector(".school-count:not([hidden])");' in again
    assert "fixed.push(boxIn(count, frameBox));" in again
    assert again.index("placeSchoolCount(") < again.index("fixed.push(boxIn(count, frameBox));") < again.index(
        'put([...overlay.querySelectorAll(".split-tag")]')


def test_pressed_the_box_writes_to_everyone_first_then_the_heading_goes_in_as_before():
    press = _top("pressSplit")
    assert press.index('setTo({ kind: "all" }, { focus: false });') < press.index('call("/api/split"')
    assert press.index('call("/api/split"') < press.index("fill(heading);")
    assert 'showDone(state.texts.input_done.split, "split");' in press
    assert "if (sending()) return;" in press
    # fill() is as it was.
    assert _top("fill") == 'function fill(text) {\n  $("question").value = text;\n  $("question").focus();\n}\n'
    # Whom it wrote to keeps its words (setTo keeps every target's draft).
    assert "if (state.to) state.drafts[draftKey(state.to)] = box.value;" in _top("setTo")


_HARNESS = r"""
const calls = [];
const state = { to: { kind: "seat", seatId: "S01" }, drafts: {}, lastRound: 2, splitOpen: true,
  texts: { input_done: { split: "LINE" } } };
let box = "休みに何をしますか";
const sending = () => false;
const draftKey = (to) => to.kind === "seat" ? `seat:${to.seatId}` : to.kind === "ai" ? `ai:${to.roundNo}:${to.role}` : "all";
function setTo(next) {
  state.drafts[draftKey(state.to)] = box;
  state.to = next;
  box = state.drafts[draftKey(next)] || "";
  calls.push("setTo:" + next.kind);
}
async function call(path, body) { calls.push(`call:${path}:${body.round}:${body.index}`); return { heading: "見出し" }; }
function fill(text) { box = text; calls.push("fill:" + text); }
function showDone(text, kind) { calls.push(`done:${text}:${kind}`); }
function setNow() { calls.push("now:" + state.splitOpen); }
function showMessage() {}
function sendFailed() {}
%s
(async () => {
  await pressSplit(2, 0);
  calls.push("|");
  state.to = { kind: "ai", roundNo: 2, role: "coach" };
  box = "答えの書きかけ";
  await pressSplit(2, 0);
  process.stdout.write(JSON.stringify({ calls, drafts: state.drafts, to: state.to, box }));
})();
"""


@node
def test_pressed_from_a_seats_card_or_an_ai_answer_the_box_goes_to_everyone_and_the_draft_stays():
    program = _HARNESS % ("async " + _top("pressSplit"))
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    got = json.loads(done.stdout.decode("utf-8"))
    first = ["setTo:all", "call:/api/split:2:0", "fill:見出し", "done:LINE:split", "now:false"]
    assert got["calls"] == first + ["|"] + first
    assert got["drafts"]["seat:S01"] == "休みに何をしますか" and got["drafts"]["ai:2:coach"] == "答えの書きかけ"
    assert got["to"] == {"kind": "all"} and got["box"] == "見出し"


def test_pressed_it_is_kept_as_before():
    session, _ = sitting(ANSWERED)
    session.ask("休みの日って、みんな何してる？")
    assert session.press_split(1, 0).startswith("ここで割れた")
    assert session.pressed_splits == {(1, 0)}


def test_the_line_after_pressing_goes_when_asked_emptied_or_written_to_another():
    assert texts.screen_texts()["input_done"]["split"] == "この割れ目を、自分の言葉に直して聞いてもいい。"
    assert 'if (state.doneKind === "split") hideDone();' in _top("setTo")
    assert 'if (state.doneKind === "split" && !$("question").value.trim()) hideDone();' in APP
    assert "hideDone();" in _top("send")  # Asked: it goes.
    assert 'state.doneKind = "";' in _top("hideDone") and "state.doneKind = kind;" in _top("showDone")
    assert '<p id="input-done" class="input-done" role="status" hidden></p>' in (
        STATIC / "index.html").read_text(encoding="utf-8")


def test_at_one_to_one_neither_heading_nor_the_tables_dashed_line_is_seen_and_back_they_are():
    assert ".one-on .split-tag," in CSS  # The map's tag (visibility: hidden: neither seen nor pressed).
    assert "body.one-open #map-heading { visibility: hidden; }" in CSS
    assert ".one-on .table-split { visibility: hidden; }" in CSS
    # Back at the meeting the classes go, so both are seen again.
    end = _inner("endOne")
    assert 'frame.classList.remove("one-on");' in end and 'document.body.classList.remove("one-open");' in end


def test_the_flat_maps_splits_stay_when_the_map_is_drawn_again():
    again = _inner("recompose")
    assert "const splits = splitsDrawn;" in again and "drawSplits(splits);" in again
    assert "splitsDrawn = result;" in _inner("drawSplits") and "splitsDrawn = null;" in MAP


def test_the_now_line_has_its_split_row_and_the_ids_agree():
    assert "split" in texts.NOW_LINE_IDS
    assert texts.now_lines()["split"] == {"step": "ask", "text": "割れたところを押すと、そこから次の問いを作れる。"}
    assert "state.splitOpen = round.splits.length > 0;" in _top("renderRound")
    assert "if (roundNo === state.lastRound) state.splitOpen = false;" in _top("pressSplit")


def test_the_check_counts_what_a_heading_covers_and_reaches_it_by_keyboard():
    for what in ("points:", "chairs:", "bubbles:", "labels:", "ai:", "count:"):
        assert what in TOOL
    assert 'await p.keyboard.press("Tab");' in TOOL and 'await p.keyboard.press("Enter");' in TOOL
    for size in ("[768, 1024]", "[1180, 820]", "[1366, 650]", "[1536, 760]", "[1920, 1080]"):
        assert size in TOOL
    for outside in ("fetch(", "XMLHttpRequest", "https://"):
        assert outside not in TOOL
