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


def test_the_first_look_is_one_dialog_of_five_pages_one_thing_each():
    """直し48 段1 (the teacher, 11/7: the more on one page, the more is
    skipped): the host's hello, how it goes, コーチ and オブザーバー, whose
    words are in, examples of questions; one at a time, 次へ and 戻る at the
    foot, the dots saying which."""
    assert '<dialog id="first-look" class="first-look" aria-labelledby="first-look-about-title">' in HTML
    look = HTML[HTML.index('<dialog id="first-look"'):HTML.index("</dialog>")]
    order = ['<section id="first-look-about" class="first-look-page" data-page="hello">',
             '<section id="first-look-flow" class="first-look-page" data-page="flow" hidden>',
             '<section id="first-look-roles" class="first-look-page" data-page="roles" hidden>',
             '<section id="first-look-inside" class="first-look-page" data-page="inside" hidden>',
             '<section id="first-look-examples" class="first-look-page" data-page="examples" hidden>',
             '<div class="first-look-foot">']
    assert [look.index(part) for part in order] == sorted(look.index(part) for part in order)
    foot = look[look.index('<div class="first-look-foot">'):]
    assert '<ol id="first-look-dots" class="first-look-dots" aria-hidden="true"></ol>' in foot
    assert '<button type="button" id="first-look-back" class="quiet first-look-back" disabled></button>' in foot
    assert '<button type="button" id="first-look-next" class="first-look-go" autofocus></button>' in foot
    assert 'id="first-look-go"' not in look and "first-look-row" not in look
    # One page at a time, named by its heading; 戻る off on the first; the
    # last 次へ is 「見た。聞きたいことを書く」 and closes it.
    page = _top("firstLook")
    assert 'pages.forEach(([id], n) => { $(id).hidden = n !== at; });' in page
    assert 'look.setAttribute("aria-labelledby", pages[at][1]);' in page
    assert '$("first-look-back").disabled = at === 0;' in page
    assert '$("first-look-next").textContent = at === pages.length - 1 ? words.first_look_go : words.next;' in page
    assert "if (at === pages.length - 1) return done();" in page
    assert '$("first-look-back").textContent = words.back;' in page
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
    assert 'if (counts) $("first-look-body").append(counts);' in look
    assert 'if (examples) $("first-look-examples-body").append(examples);' in look
    assert "if (counts) body.append(counts);" in look and "if (examples) body.append(examples);" in look
    assert '$("inside").classList.remove("beckon");' in look
    assert '$("question").focus({ preventScroll: true });' in look
    assert "look.showModal();" in look
    # Every way out (its button, Esc, the browser's close) the same, once:
    # the close event does not always come, so Esc is handled here.
    assert 'look.addEventListener("cancel", (event) => { event.preventDefault(); done(); });' in look
    assert "if (over) return;" in look
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
  classList: { set: new Set(), add(c) { this.set.add(c); }, remove(c) { this.set.delete(c); },
    toggle(c, on) { if (on) this.set.add(c); else this.set.delete(c); }, contains(c) { return this.set.has(c); } },
  offsetWidth: 280, offsetHeight: 44, open: false, textContent: "",
  replaceChildren(...kids) { this.textContent = kids.join(""); },  // 直し53 段7: the box's sign keeps clear (guideSpot).
  getBoundingClientRect() { return this.box; } });
const phrased = (text) => text;
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
    # 直し48 段1: the hello on the first page, how it goes on the second,
    # headed by the host's last line (「進み方は、この4つです。」).
    assert page.index('id="start-about"') < page.index('<section id="first-look-flow"') < page.index('id="start-flow"')
    assert 'const flowTitle = about.length > 1 ? about.pop() : "";' in APP
    assert '$("first-look-flow-title").textContent = flowTitle;' in APP
    assert screen["start_about"].strip().splitlines()[-1] == "進み方は、この4つです。"
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
    assert 'class="host-mark"' in page and 'class="start-about host-says"' in page
    assert ".host-says { position: relative;" in CSS and "border: 2px solid var(--ai);" in CSS
    # 直し48: 司会（AI）'s robot (robot.js) by its name, in place of the square mark.
    assert '$("host-mark").replaceChildren(EbinoRobot.make("host"));' in _top("firstLook")
    assert ".host-head .host-mark { display: inline-block; flex: none; width: 64px; height: 64px;" in CSS
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
    # Its robot (直し47, robot.js; aria-hidden there), 「AI」 on its body, in place of the square mark.
    assert 'EbinoRobot.make(role.role, { tag: data.texts.ai_seat_mark })' in roles
    assert "role.name" in roles and "role.knows" in roles and "role.does" in roles and "｜" not in roles
    assert '$("start-roles-note").textContent = data.texts.guide.roles_note;' in roles
    # 直し48 段1: a page of their own, the third, after how it goes; left
    # out with none. Its heading the lead; the note says both are AI.
    page = HTML[HTML.index('<section id="first-look-roles"'):HTML.index('<section id="first-look-inside"')]
    assert HTML.index('<ol id="start-flow"') < HTML.index('<section id="first-look-roles"')
    assert '<div id="start-roles" class="start-roles" hidden>' in page
    assert '<h2 id="start-roles-lead" class="first-look-title start-roles-lead" tabindex="-1"></h2>' in page
    assert page.index('id="start-roles-list"') < page.index('id="start-roles-note"')
    assert 'withRoles && ["first-look-roles", "start-roles-lead"]' in APP
    assert 'firstLookPages(!$("start-roles").hidden, Boolean(counts && examples))' in _top("firstLook")
    assert '$("start-roles").hidden = !roles.length;' in APP and "data.ai_roles || []" in APP
    assert ".start-roles[hidden] { display: none; }" in CSS
    # From its heading, on a low screen too (1366×650: the heading had gone up out of sight).
    assert "look.showModal();\n  look.scrollTop = 0;" in _top("firstLook")
    low = CSS[CSS.index("/* The host's page on a low screen"):]
    assert ".start-roles { margin-top: 10px;" in low[:low.index("\n}\n")]


PLACE_AI = """
const made = {};
const node = (id, box, cls) => ({ id, box, hidden: id === "guide", dataset: {}, style: { setProperty(k, v) { this[k] = v; } },
  classList: { set: new Set(cls ? [cls] : []), add(c) { this.set.add(c); }, remove(c) { this.set.delete(c); },
    toggle(c, on) { if (on) this.set.add(c); else this.set.delete(c); }, contains(c) { return this.set.has(c); } },
  get offsetWidth() { return this.classList.set.has("narrow") ? 220 : 280; },
  get offsetHeight() { return this.classList.set.has("narrow") ? 70 : 44; }, open: false, textContent: "",
  replaceChildren(x) { this.textContent = x.phrased; }, getBoundingClientRect() { return this.box; } });
const box = (left, top, width, height) => ({ left, top, width, height, right: left + width, bottom: top + height });
const $ = (id) => made[id] || (made[id] = node(id, box(0, 0, 0, 0)));
let now = "answer_ai", card = null, other = null, bubbles = [];
const view = { clientWidth: 1366, clientHeight: 650 };
const document = { documentElement: view,
  querySelector: (q) => q.includes("#ai-seat-cards .ai-question") ? card : null,
  querySelectorAll: (q) => q.includes("#ai-seat-cards .ai-question") ? [card, other] : q.includes(".table-bubble") ? bubbles : [] };
const state = { texts: { now_line: {}, guide: { answer_ai: "A" } } };
function nowState() { return now; }
function phrased(text) { return { phrased: text }; }
%(source)s
const area = (g, k) => { const l = parseInt(g.style.left), t = parseInt(g.style.top);
  return Math.max(0, Math.min(l + g.offsetWidth, k.right) - Math.max(l, k.left))
    * Math.max(0, Math.min(t + g.offsetHeight, k.bottom) - Math.max(t, k.top)); };
const overlaps = (g, k) => area(g, k) > 0;
const out = {};
// The two cards one over the other (in the map's column, or its corner),
// or side by side (as at 1366×650 and 1920×1080).
for (const [name, x, by] of [["column", 1100, false], ["corner", 8, false], ["row", 30, true]]) {
  made["ai-seat-label"] = node("ai-seat-label", box(x, 100, 200, 30));
  made["ai-seat-note"] = node("ai-seat-note", box(x, 136, 400, 20));
  card = node("card", by ? box(x + 8, 160, 185, 110) : box(x, 186, 240, 60));
  other = node("other", by ? box(x + 201, 160, 185, 110) : box(x, 254, 240, 60));
  drawGuide();
  const g = $("guide");
  out[name] = { hidden: g.hidden, side: g.dataset.side, point: g.style["--point"],
    over: [card.box, other.box].filter((k) => overlaps(g, k)).length };
}
out.text = $("guide-text").textContent;
// Room over the card clear of the heading and the note: over it, as before.
made["ai-seat-label"].box = box(8, 20, 200, 30); made["ai-seat-note"].box = box(8, 56, 240, 40);
card.box = box(8, 300, 240, 60); other.box = box(8, 368, 240, 60);
drawGuide();
out.room = { side: $("guide").dataset.side, top: $("guide").style.top };
// As at 768×1024: the seat over the map's corner, the bubble pressed right
// under the card; nowhere clear of it, so slid along the card as far as its
// point stays on it, over the least of the pressed bubble.
view.clientWidth = 768; view.clientHeight = 1024;
made["ai-seat-label"].box = box(25, 180, 240, 30); made["ai-seat-note"].box = box(25, 215, 400, 20);
card.box = box(35, 238, 185, 104); other.box = box(229, 238, 186, 104);
const pressed = node("pressed", box(20, 345, 220, 110), "marked");
bubbles = [pressed, node("b1", box(500, 210, 190, 108)), node("b2", box(528, 403, 220, 100)), node("b3", box(37, 458, 220, 110))];
drawGuide();
{ const g = $("guide"), l = parseInt(g.style.left);
  out.pressed = { side: g.dataset.side, left: g.style.left, narrow: g.classList.set.has("narrow"),
    kept: [card.box, other.box].filter((k) => overlaps(g, k)).length,
    on_pressed: area(g, pressed.box), on_others: bubbles.slice(1).filter((b) => overlaps(g, b.box)).length,
    tip: l + parseInt(g.style["--point"]) }; }
// Clear of the bubbles when it can be: slid along under the card.
bubbles = [node("p2", box(20, 345, 120, 110), "marked")];
drawGuide();
out.slid = { side: $("guide").dataset.side, on: area($("guide"), bubbles[0].box) };
// As at 900×800: the seat low by the map's left, its card cut off by the
// window's foot; wide, no side is clear: narrower, by its left.
view.clientWidth = 900; view.clientHeight = 800; bubbles = [];
made["ai-seat-label"].box = box(290, 505, 300, 30); made["ai-seat-note"].box = box(290, 540, 360, 40);
card.box = box(280, 590, 170, 200); other.box = box(458, 590, 170, 200);
drawGuide();
{ const g = $("guide");
  out.narrow = { side: g.dataset.side, narrow: g.classList.set.has("narrow"),
    kept: [card.box, other.box].filter((k) => overlaps(g, k)).length }; }
process.stdout.write(JSON.stringify(out));
"""


@node
def test_the_hint_to_answer_the_ai_keeps_its_questions_clear():
    """直し46: 「AI の問いはここ。押して答えよう」 never over the AI's
    questions (the other card's words). 直し48 段2: the seat's heading and
    note are gone (the first look says they are AI), so with that room over
    the card the hint is there, its point on the card; still over none of
    the two questions (their robots, names and bubbles) nor over the bubble
    pressed (768×1024)."""
    source = APP[APP.index("const GUIDE = {"):APP.index("// What it points at moves with the window")]
    out = subprocess.run(["node", "-"], input=(PLACE_AI % {"source": source}).encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    for name in ("column", "corner", "row"):
        assert got[name]["hidden"] is False and got[name]["over"] == 0, name
        assert got[name]["side"] == "above", name
    assert got["text"] == "A"  # Broken between phrases (phrased).
    assert got["room"] == {"side": "above", "top": f"{300 - 14 - 44}px"}
    # 768×1024: never over the cards nor any of the people's bubbles; its point on the card.
    p = got["pressed"]
    assert p["kept"] == 0 and p["on_others"] == 0 and p["on_pressed"] == 0 and not p["narrow"]
    assert 35 < p["tip"] <= 35 + 185
    assert got["slid"]["on"] == 0
    assert got["narrow"]["kept"] == 0
    # The heading and the note are no more among what it keeps clear: the questions are.
    assert 'clear: () => [...document.querySelectorAll("#ai-seat-cards .ai-question"), $("now-line"),' in APP
    assert 'document.querySelector(".map-controls")],' in APP  # The screen check's 差し戻し: the top line and the column.
    assert ".guide.narrow { max-width: min(11em, calc(100vw - 16px)); }" in CSS
    assert '.guide[data-side="right"]::after { right: 100%;' in CSS and '.guide[data-side="left"]::after { left: 100%;' in CSS


def test_the_hint_to_press_a_bubble_keeps_off_the_ais_questions():
    """直し48 (the screen check): 「吹き出しを1つ押してみよう」 hid the end of
    オブザーバー's question at 768×1024."""
    # 直し52 段3: and the AI's seat's frame.
    assert ('clear: () => [...document.querySelectorAll("#ai-seat-cards .ai-question"), $("now-line"), $("ai-seat"),\n'
            '      ...document.querySelectorAll("#map-svg .token, #map-svg .chair")],\n'
            '    sides: ["above", "below", "right", "left"] },') in APP  # 直し53 段5: the seats' marks too.
