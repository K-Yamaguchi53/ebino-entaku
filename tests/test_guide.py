"""The guide (the teacher, 11/6: the students could not go on without being
told). Whose words are in comes up by itself in the middle of the screen
once the table is out, before the first question; the line at the top is
larger; and a bubble by the one thing to press now points at it (the
bubble's choices: the button itself lit, so no bubble covers the card)."""

import json
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
    return APP[start:APP.index("\n}\n", start) + 3]


def test_its_words_are_the_teachers_file_every_row_there():
    words = texts.screen_texts()["guide"]
    assert tuple(words) == texts.GUIDE_IDS
    assert all(words.values())
    assert words["first_look_go"] and words["write"]


def test_the_first_look_is_one_dialog_of_two_pages_what_the_app_is_then_whose_words():
    assert '<dialog id="first-look" class="first-look" aria-labelledby="first-look-about-title">' in HTML
    look = HTML[HTML.index('<dialog id="first-look"'):HTML.index("</dialog>")]
    assert look.index('<section id="first-look-about" class="first-look-page">') < look.index(
        '<section id="first-look-inside" class="first-look-page" hidden>')
    assert '<button type="button" id="first-look-next" class="first-look-go" autofocus></button>' in look
    assert '<button type="button" id="first-look-go" class="first-look-go"></button>' in look
    # 次へ: the second page in place of the first, the keyboard and the name on it.
    page = _top("firstLook")
    assert '$("first-look-about").hidden = true;' in page and '$("first-look-inside").hidden = false;' in page
    assert 'look.setAttribute("aria-labelledby", "first-look-title");' in page and '$("first-look-title").focus();' in page
    # With no words in, the first page alone, its button the last one.
    assert '$("first-look-next").textContent = body ? words.about_next : words.first_look_go;' in page
    assert "if (!body) return done();" in page
    # The guide is never read out (the line at the top is) and never pressed.
    assert '<div id="guide" class="guide" aria-hidden="true" hidden>' in HTML
    rule = CSS[CSS.index(".guide { position: fixed;"):]
    assert "pointer-events: none;" in rule[:rule.index("}")]


def test_the_first_look_comes_once_when_the_table_is_out_and_goes_back_to_the_column():
    begun = _top("start")
    assert begun.index('$("question").focus();') < begun.index("firstLook();")
    look = _top("firstLook")
    assert "if (state.firstLooked ||" in look and "state.firstLooked = true;" in look
    # The same words as in the map's column, moved, not copied (no id twice).
    assert 'if (body) $("first-look-body").append(body);' in look
    assert 'if (body) $("inside-fold").append(body);' in look
    assert '$("inside").classList.remove("beckon");' in look
    assert '$("question").focus({ preventScroll: true });' in look
    assert "look.showModal();" in look
    # Every way out (its button, Esc, the browser's close) the same, once:
    # the close event does not always come, so Esc is handled here.
    assert 'look.addEventListener("cancel", (event) => { event.preventDefault(); done(); });' in look
    assert '$("first-look-go").onclick = done;' in look and "if (over) return;" in look
    # An example pressed fills the box; then the box is next.
    assert 'event.target.closest("#work-questions button")' in look


def test_the_top_line_is_larger_and_the_guide_follows_every_change():
    line = CSS[CSS.index(".now-line { margin: 4px 0 0;"):]
    assert "font-size: 26px;" in line[:line.index("}")]
    assert ".now-line { margin-top: 2px; padding: 3px 12px; font-size: 22px; }" in CSS
    assert "drawGuide();\n}" in _top("setNow")


def test_its_movement_is_once_and_still_with_motion_reduced():
    block = CSS[CSS.index("@media (prefers-reduced-motion: no-preference) {\n  .guide.fresh"):]
    block = block[:block.index("\n}\n")]
    assert "animation: guide-fresh 1.4s ease-out 1;" in block and "infinite" not in block
    rule = CSS[CSS.index(".guide { position: fixed;"):]
    assert "animation" not in rule[:rule.index("}")]


PLACE = """
const made = {};
const node = (id, box) => ({ id, box, hidden: id === "guide", dataset: {}, style: { setProperty(k, v) { this[k] = v; } },
  classList: { set: new Set(), add(c) { this.set.add(c); }, remove(c) { this.set.delete(c); } },
  offsetWidth: 280, offsetHeight: 44, open: false, textContent: "",
  getBoundingClientRect() { return this.box; } });
const box = (left, top, width, height) => ({ left, top, width, height, right: left + width, bottom: top + height });
const $ = (id) => made[id] || (made[id] = node(id, box(0, 0, 0, 0)));
let now = "write", choice = null;
const document = { documentElement: { clientWidth: 1366, clientHeight: 650 },
  querySelector: (q) => q.includes('data-choice="card"') ? choice : null,
  querySelectorAll: (q) => choice && choice.classList.set.has("guide-here") ? [choice] : [] };
const state = { texts: { now_line: {}, guide: { write: "W", table: "T", pressed: "P", answer_ai: "A", after: "F" } } };
function nowState() { return now; }
%(source)s
const out = {};
made.question = node("question", box(150, 581, 1100, 45));
drawGuide();
out.write = { hidden: $("guide").hidden, side: $("guide").dataset.side, top: $("guide").style.top, left: $("guide").style.left,
  text: $("guide-text").textContent };
made.question.box = box(150, 20, 1100, 45);  // No room over it: under it.
now = "card"; drawGuide();
out.under = { side: $("guide").dataset.side, top: $("guide").style.top, text: $("guide-text").textContent };
made["to-reflect"] = node("to-reflect", box(1300, 590, 60, 40));  // By the window's edge: kept inside it.
now = "after"; drawGuide();
out.edge = { left: $("guide").style.left, point: $("guide").style["--point"] };
choice = node("choice", box(500, 300, 180, 40));
now = "pressed"; drawGuide();
out.pressed = { hidden: $("guide").hidden, lit: choice.classList.set.has("guide-here") };
now = "reading"; drawGuide();
out.none = { hidden: $("guide").hidden, lit: choice.classList.set.has("guide-here") };
process.stdout.write(JSON.stringify(out));
"""


@node
def test_the_bubble_goes_over_what_to_press_under_it_or_kept_in_the_window():
    source = APP[APP.index("const GUIDE = {"):APP.index("// What it points at moves with the window")]
    out = subprocess.run(["node", "-"], input=(PLACE % {"source": source}).encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    # Over the box, its middle over the box's middle, 14px clear of it.
    assert got["write"] == {"hidden": False, "side": "above", "top": f"{581 - 14 - 44}px",
                            "left": f"{round(150 + 550 - 140)}px", "text": "W"}
    assert got["under"] == {"side": "below", "top": f"{20 + 45 + 14}px", "text": "W"}
    # 「ふりかえりへ」 by the right edge: the bubble inside, its point still at the button.
    assert got["edge"]["left"] == f"{1366 - 8 - 280}px"
    assert got["edge"]["point"] == f"{1330 - (1366 - 8 - 280)}px"
    # The bubble's choices: the button lit, no bubble; nothing to press, neither.
    assert got["pressed"] == {"hidden": True, "lit": True}
    assert got["none"] == {"hidden": True, "lit": False}


def test_what_the_app_is_and_how_it_goes_come_right_before_whose_words_are_in():
    screen = texts.screen_texts()
    assert "AI" in screen["start_about"] and "本人" in screen["start_about"]  # Not the person answering now.
    assert tuple(screen["start_flow"]) == texts.NOW_STEP_IDS and all(screen["start_flow"].values())
    # On the first look's first page, not on the first screen (the teacher, 11/6).
    start = HTML[HTML.index('<section id="start">'):HTML.index("</section>", HTML.index('<section id="start">'))]
    assert "start-about" not in start and "start-flow" not in start
    page = HTML[HTML.index('<section id="first-look-about"'):HTML.index('<section id="first-look-inside"')]
    assert page.index('id="start-about"') < page.index('<ol id="start-flow" class="start-flow" aria-label="すすみ方">')
    # The step names are the band's own (the same words light up there later).
    filled = APP[APP.index("// The host's words, a paragraph for each of its lines."):APP.index('$("lab-question").textContent')]
    assert "for (const step of data.texts.now_steps)" in filled and "data.texts.start_flow[step.id]" in filled
    # Four in a row, two rows when narrow; broken between words.
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in CSS
    assert ".first-look, .guide, .wait-sign {\n  word-break: auto-phrase;" in CSS


def test_the_first_page_is_said_by_the_host_an_ai_in_the_ais_colour():
    screen = texts.screen_texts()
    said = screen["start_about"]
    # The host says it is an AI, and that the people are not answering now.
    assert "司会" in said and "AI" in said and "本人がいま答えているのではありません" in said
    assert screen["guide"]["host_mark"] and "AI" in screen["guide"]["about_title"]
    page = HTML[HTML.index('<section id="first-look-about"'):HTML.index('<section id="first-look-inside"')]
    assert 'class="ai-mark host-mark"' in page and 'class="start-about host-says"' in page
    assert ".host-says { position: relative;" in CSS and "border: 2px solid var(--ai);" in CSS
    # Stronger than .ai-mark, which comes later in the file.
    assert ".host-head .host-mark { width: 52px; height: 52px;" in CSS
    # A paragraph for each of its lines.
    assert r'data.texts.start_about.split("\n")' in APP


def test_the_host_page_has_a_card_for_the_coach_and_the_observer():
    from ebino import coach
    # 直し46: a card each, the name as on the cards and what it knows and
    # does (ai_roles_intro.tsv); the coach only with its pieces; none with the band off.
    intro = texts.ai_roles_intro()
    assert coach.roles_shown(True, ["片"]) == [
        {"role": "coach", "name": "コーチ（AI）", **intro["coach"]},
        {"role": "observer", "name": "オブザーバー（AI）", **intro["observer"]}]
    assert [r["role"] for r in coach.roles_shown(True, [])] == [coach.OBSERVER]
    assert coach.roles_shown(False, ["片"]) == []
    assert coach.roles_for([]) == (coach.OBSERVER,)
    guide = texts.screen_texts()["guide"]
    assert guide["roles_lead"] == "円卓で人の言葉を読んだあと、この2つの AI から問いが届きます。届いた問いに、1回答えてみよう。"
    assert guide["roles_note"] == "どちらも AI です。町の人ではありません。"
    roles = APP[APP.index("// コーチとオブザーバー (直し46)"):APP.index("renderInside(data.inside")]
    assert 'class: "ai-mark role-mark", "aria-hidden": "true", text: data.texts.ai_seat_mark' in roles
    assert "role.name" in roles and "role.knows" in roles and "role.does" in roles and "｜" not in roles
    assert '$("start-roles-note").textContent = data.texts.guide.roles_note;' in roles
    # On the first page, under the flow, hidden with none.
    page = HTML[HTML.index('<section id="first-look-about"'):HTML.index('<section id="first-look-inside"')]
    assert page.index('<ol id="start-flow"') < page.index('<div id="start-roles" class="start-roles" hidden>')
    assert page.index('id="start-roles-list"') < page.index('id="start-roles-note"') < page.index('id="first-look-next"')
    assert '$("start-roles").hidden = !roles.length;' in APP and "data.ai_roles || []" in APP
    assert ".start-roles[hidden] { display: none; }" in CSS
    # From its heading, on a low screen too (1366×650: the heading had gone up out of sight).
    assert "look.showModal();\n  look.scrollTop = 0;" in _top("firstLook")
    low = CSS[CSS.index("/* The host's page on a low screen"):]
    assert ".start-roles { margin-top: 10px;" in low[:low.index("\n}\n")]
