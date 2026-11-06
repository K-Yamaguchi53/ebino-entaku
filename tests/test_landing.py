"""直し32-5: the paper plane, seen from straight above as it lands, read as
an umbrella; for the last of its way it is seen more from the side. And a
slow /api/start: the opening skipped (or over) before the server is ready,
the table comes with the box shut and 「準備しています。…」 as the line, and
the keyboard goes to the box once it is ready."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _top(name):
    start = APP.index(f"function {name}(")
    if APP[start - 6:start] == "async ":
        start -= 6
    return APP[start:APP.index("\n}\n", start) + 3]


def _const(name):
    start = APP.index(f"const {name} = ")
    return APP[start:APP.index(";", start) + 1] + "\n"


def _run(body):
    program = "\n".join([_const("PLANE"), _const("PLANE_LIGHT"), _const("LANDING_FROM"), _const("LANDING_ELEV"),
                         _top("planeFaces"), _top("landing"), body])
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    return json.loads(out.stdout.decode("utf-8"))


@node
def test_only_the_last_of_the_way_is_seen_from_the_side_and_smoothly():
    got = _run("process.stdout.write(JSON.stringify([0, 0.5, 0.8, 0.9, 1].map(landing)));")
    assert got[0] == 0 and got[1] == 0 and got[2] == 0 and 0 < got[3] < 1 and got[4] == 1


@node
def test_flying_up_the_screen_it_is_an_umbrella_from_above_and_a_profile_as_it_lands():
    # Its nose up the screen (away to the north): from above, its wings
    # spread taller than wide (the umbrella); in the landing's pose (nose
    # turned across, seen nearly from the side) it is a long, low profile.
    got = _run("""
const span = (pose) => {
  const faces = planeFaces(Object.assign({ x: 0, y: 0, size: 100, roll: 0, pitch: 0.32 }, pose));
  const ys = faces.flatMap((f) => f.points.map((p) => p[1])), xs = faces.flatMap((f) => f.points.map((p) => p[0]));
  return (Math.max(...xs) - Math.min(...xs)) / (Math.max(...ys) - Math.min(...ys));
};
const out = [];
for (const a of [-Math.PI / 2, -Math.PI / 3]) {
  const across = Math.cos(a) >= 0 ? 0 : Math.PI, turn = Math.atan2(Math.sin(across - a), Math.cos(across - a));
  out.push([span({ a }), span({ a: a + turn * 0.75, elev: LANDING_ELEV })]);
}
process.stdout.write(JSON.stringify(out));
""")
    for above, landing_pose in got:
        assert above < 1 and landing_pose > 1.5


def test_the_landing_turns_its_nose_across_and_keeps_the_time():
    drawn = _top("drawOpening")
    assert "const side = landing(fly);" in drawn
    assert "elev: Math.PI / 4 - (Math.PI / 4 - LANDING_ELEV) * side" in drawn
    assert "const OPENING = { fly: 1400, land: 600, title: 800 };" in APP  # The time, as before.


def test_a_slow_start_shows_the_table_shut_with_the_line_and_then_the_box_takes_the_keyboard():
    lines = texts.now_lines()
    assert lines["preparing"]["text"] == "準備しています。少し待ってください。"
    begun = _top("start")
    assert "if (opening) opening.then(() => { if (!ready) preparing(true); });" in begun
    assert begun.index("preparing(false);\n  $(\"start\").hidden = true;") < begun.index('$("question").focus();')
    shut = _top("preparing")
    assert '$("question").disabled = on;' in shut and '$("ask-button").disabled = on;' in shut
    assert "setNow({ preparing: on });" in shut
    assert 'if (now.preparing) return "preparing";' in _top("nowState")


SLOW_START = """
const made = {};
const $ = (id) => made[id] || (made[id] = { id, hidden: id === "table", disabled: false, focused: 0, children: [],
  classList: { remove() {} }, querySelectorAll: () => [], focus() { this.focused += 1; focusedOn = id; } });
let focusedOn = null;
const state = { now: { preparing: false } };
const seen = [];
function setNow(changes = {}) { Object.assign(state.now, changes); seen.push(state.now.preparing ? "preparing" : "other"); }
globalThis.window = { matchMedia: () => ({ matches: false }) };
let endOpening = () => {}, onMap = () => {}, renderPurposes = () => {}, placeInside = () => {}, firstLook = () => {};
let finish;
const playOpening = () => new Promise((done) => { finish = done; });
let reply;
const call = () => new Promise((done) => { reply = done; });
%(source)s
(async () => {
  const going = start("quest", null);
  finish();  // The opening skipped: 「とばす」 or Esc.
  await new Promise((done) => setTimeout(done, 0));
  const waiting = { line: state.now.preparing, box: $("question").disabled, button: $("ask-button").disabled,
    table: !$("table").hidden, focus: focusedOn };
  reply({ purposes: [] });  // The server ready.
  await going;
  process.stdout.write(JSON.stringify({ waiting, ready: { line: state.now.preparing, box: $("question").disabled,
    focus: focusedOn } }));
})();
"""


@node
def test_a_slow_start_run_with_a_false_slow_server():
    program = SLOW_START % {"source": _top("start") + _top("preparing")}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    assert got["waiting"] == {"line": True, "box": True, "button": True, "table": True, "focus": None}
    assert got["ready"] == {"line": False, "box": False, "focus": "question"}
