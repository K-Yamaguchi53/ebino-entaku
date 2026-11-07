"""直し48 段1 (the teacher, 11/7: the more on one page, the more is
skipped): 司会（AI）から、はじめに in five pages, one thing each, turned
with 次へ and 戻る: the host's hello, how it goes, コーチ and オブザーバー
(left out with none), whose words are in, examples of questions (both left
out with none). Run in node on a small stand-in for the page."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module

APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


HARNESS = """
const made = {};
const part = (id) => made[id] || (made[id] = { id, hidden: id !== "first-look-about", textContent: "", disabled: false,
  attrs: {}, children: [], scrollTop: 5, open: false, focused: false, listeners: {},
  classList: { set: new Set(), toggle(c, on) { if (on) this.set.add(c); else this.set.delete(c); }, remove() {}, add() {} },
  setAttribute(k, v) { this.attrs[k] = v; }, replaceChildren(...kids) { this.children = kids; },
  append(...kids) { this.children.push(...kids); }, focus() { focusedId = this.id; },
  querySelector(q) { return q === ".first-look-pages" ? part("pages") : q === ".inside-counts-part" ? part("counts")
    : q === ".inside-examples" ? part("examples") : null; },
  addEventListener(name, fn) { this.listeners[name] = fn; }, showModal() { this.open = true; }, close() { this.open = false; } });
let focusedId = null;
const $ = part;
function el(tag) { return { tag, classList: { set: new Set(), toggle(c, on) { if (on) this.set.add(c); else this.set.delete(c); } } }; }
const EbinoRobot = { make: (role) => ({ robot: role }) };
function drawGuide() {}
const ROLES = %(roles)s, INSIDE = %(inside)s;
part("start-roles").hidden = !ROLES;
part("inside").hidden = !INSIDE;
const document = { querySelector: (q) => INSIDE && q === "#inside-fold .inside-body" ? part("body") : null };
part("inside-fold");
const state = { texts: { guide: { about_title: "司会（AI）から、はじめに", first_look_title: "T", back: "戻る", next: "次へ",
  first_look_go: "見た。聞きたいことを書く" } } };
%(source)s
firstLook();
const look = part("first-look");
const seen = () => ({ shown: ["first-look-about", "first-look-flow", "first-look-roles", "first-look-inside", "first-look-examples"]
    .filter((id) => !part(id).hidden),
  dot: [...part("first-look-dots").children].findIndex((d) => d.classList.set.has("here")),
  dots: part("first-look-dots").children.length, named: look.attrs["aria-labelledby"],
  back: part("first-look-back").disabled, next: part("first-look-next").textContent, focus: focusedId, open: look.open });
const out = [seen()];
for (let n = 0; n < 6 && look.open; n++) { part("first-look-next").onclick(); out.push(seen()); }
process.stdout.write(JSON.stringify({ out, host: part("host-mark").children, put_back: part("body").children.map((k) => k.id) }));
"""

BACK = """
firstLook();
const look = part("first-look");
part("first-look-next").onclick(); part("first-look-next").onclick();
const at2 = ["first-look-about", "first-look-flow", "first-look-roles"].filter((id) => !part(id).hidden);
part("first-look-back").onclick();
const after = { shown: ["first-look-about", "first-look-flow", "first-look-roles"].filter((id) => !part(id).hidden),
  focus: focusedId };
part("first-look-back").onclick();
const first = { shown: ["first-look-about", "first-look-flow"].filter((id) => !part(id).hidden),
  back: part("first-look-back").disabled, focus: focusedId, open: look.open };
process.stdout.write(JSON.stringify({ at2, after, first }));
"""


def _run(roles, inside, tail=None):
    source = _top("firstLookPages") + _top("firstLook")
    program = HARNESS % {"roles": json.dumps(roles), "inside": json.dumps(inside), "source": source}
    if tail:
        program = program[:program.index("firstLook();\nconst look")] + tail
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    return json.loads(out.stdout.decode("utf-8"))


@node
def test_five_pages_in_turn_one_at_a_time_the_last_button_closes_it():
    got = _run(True, True)
    pages = got["out"]
    order = ["first-look-about", "first-look-flow", "first-look-roles", "first-look-inside", "first-look-examples"]
    names = ["first-look-about-title", "first-look-flow-title", "start-roles-lead", "first-look-title", "examples-lead"]
    for n, page in enumerate(pages[:5]):
        assert page["shown"] == [order[n]] and page["dot"] == n and page["dots"] == 5
        assert page["named"] == names[n] and page["back"] == (n == 0) and page["open"]
        assert page["next"] == ("見た。聞きたいことを書く" if n == 4 else "次へ")
        assert page["focus"] in (None, "first-look-next")  # The keyboard stays on 次へ.
    # The last button: closed, the two parts of whose words are in put back, the box next.
    assert len(pages) == 6 and not pages[5]["open"] and pages[5]["focus"] == "question"
    assert got["put_back"] == ["counts", "examples"]
    assert got["host"] == [{"robot": "host"}]


@node
def test_back_goes_one_page_back_and_off_on_the_first():
    got = _run(True, True, BACK)
    assert got["at2"] == ["first-look-roles"]
    assert got["after"] == {"shown": ["first-look-flow"], "focus": "first-look-back"}
    # On the first page 戻る is off: the keyboard to 次へ, still open.
    assert got["first"] == {"shown": ["first-look-about"], "back": True, "focus": "first-look-next", "open": True}


@node
def test_pages_with_nothing_are_left_out():
    no_roles = _run(False, True)["out"]
    assert [p["shown"][0] for p in no_roles[:4]] == ["first-look-about", "first-look-flow", "first-look-inside",
                                                     "first-look-examples"]
    assert no_roles[0]["dots"] == 4
    nothing_in = _run(True, False)["out"]
    assert [p["shown"][0] for p in nothing_in[:3]] == ["first-look-about", "first-look-flow", "first-look-roles"]
    assert nothing_in[2]["next"] == "見た。聞きたいことを書く" and not nothing_in[3]["open"]


def test_no_movement_between_pages_and_the_foot_always_in_the_window():
    # The pages scroll inside; the foot (dots, 戻る, 次へ) never scrolls away.
    assert ".first-look[open] { display: flex; flex-direction: column; overflow: hidden; }" in CSS
    assert ".first-look-pages { flex: 1 1 auto; min-height: 0; overflow: auto;" in CSS
    assert ".first-look-foot { flex: none;" in CSS
    block = CSS[CSS.index("/* 直し48 段1: five pages"):CSS.index(".first-look-title:focus")]
    assert "animation" not in block and "transition" not in block
