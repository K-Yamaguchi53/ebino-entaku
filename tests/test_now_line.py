"""「いまやること」 (直し31-5): the four steps with the one now lit, and under
them one line for the state the screen is in; the first screen's line of
what this is for; over the first question box, whose words are in the app
as counts from the seat table, and examples of questions. Everything here
is invented."""

import json
import shutil
import subprocess

import pytest

from conftest import make_seat
from ebino import app as app_module
from ebino import inside, texts
from test_session import library, sitting

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


# --- the counts, from the seat table ---

def seat(seat_id, kind, company="", crossing="", display_name=""):
    return make_seat(seat_id=seat_id, kind=kind, title=f"架空の席{seat_id}", company=company,
                     display_name=display_name, district="", crossing_to=crossing)


def test_the_counts_are_taken_from_the_seat_table():
    seats = [seat("A1", "adult", "架空理容"), seat("A2", "adult", "架空理容", display_name="山川さん"),
             seat("A3", "adult", "架空農園"), seat("A4", "adult"),  # No company: its own.
             seat("P1", "poster"), seat("P2", "poster"), seat("C1", "cross"), seat("O1", "outsider_teacher")]
    assert inside.counts(seats) == [("adult", "adult", 3), ("poster", "poster", 2), ("cross", "cross", 1),
                                    ("outsider_teacher", "outsider_teacher", 1)]


def test_a_kind_with_none_is_left_out():
    assert inside.counts([seat("P1", "poster")]) == [("poster", "poster", 1)]


def test_kengai_and_kaigai_are_split_when_the_column_says_so_else_one_count():
    split = [seat("C1", "cross", crossing="県外"), seat("C2", "cross", crossing="海外"),
             seat("C3", "cross", crossing="海外"), seat("C4", "cross")]
    assert inside.counts(split) == [("cross_kengai", "cross", 1), ("cross_kaigai", "cross", 2), ("cross", "cross", 1)]
    together = [seat("C1", "cross"), seat("C2", "cross", crossing="1")]  # "1": the crossing line's target only.
    assert inside.counts(together) == [("cross", "cross", 2)]


def test_no_company_or_display_name_reaches_the_screen():
    seats = [seat("A1", "adult", "架空理容", display_name="山川さん"), seat("C1", "cross", crossing="海外")]
    view = inside.view(seats)
    shown = json.dumps(view, ensure_ascii=False)
    assert "架空理容" not in shown and "山川" not in shown
    assert view[0] == {"id": "adult", "kind": "adult", "before": "地域で働く大人", "number": 1,
                       "after": "の事業所（地域の大人への取材記事）"}
    assert view[1]["before"] == "海外研修" and view[1]["number"] == 1


def test_setup_sends_the_counts_of_the_seats_on_the_map():
    app = app_module.App(library(), sitting([])[0].gate)
    rows = app.setup()["inside"]
    assert [(row["id"], row["number"]) for row in rows] == [("adult", 3), ("poster", 1)]


# --- the words ---

def test_the_steps_and_the_lines_are_the_teachers_words_in_texts():
    sent = texts.screen_texts()
    assert [step["id"] for step in sent["now_steps"]] == ["write", "read", "ask", "reflect"]
    assert sent["now_steps"][0]["text"] == "① 問いを書く"
    lines = sent["now_line"]
    assert set(lines) == set(texts.NOW_LINE_IDS) | {"answer_ai"}
    # The line for an AI question is the one 直し30の続き-0 put over the cards.
    assert lines["answer_ai"] == {"step": "ask", "text": "コーチかオブザーバーの問いに、1つ答えよう。"}
    assert lines["start"]["step"] == "" and lines["write"]["text"].endswith("何を聞いてもいい。")
    assert sent["start_purpose"] and sent["question_examples"] and sent["question_examples_lead"]


# --- which line, when ---

_STATE = """
const hidden = %(hidden)s;
const $ = (id) => ({ hidden: hidden[id] !== undefined ? hidden[id] : true });
const state = %(state)s;
const cardOpen = () => Boolean(state.cardOpen);
state.to = state.to || { kind: "all" };
%(source)s
process.stdout.write(JSON.stringify(nowState()));
"""


def now(state, start=True, reflect=True):
    full = {"aiAnswered": False, "firstQuestion": "q",
            "now": {"asking": False, "reading": False, "choices": False, "pressed": False, "table": False,
                    "band": False}}
    full["now"].update(state.pop("now", {}))
    full.update(state)
    program = _STATE % {"hidden": json.dumps({"start": start, "reflect": reflect}), "state": json.dumps(full),
                        "source": _top("nowState")}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    return json.loads(out.stdout.decode("utf-8"))


@node
def test_one_state_at_a_time_in_order():
    assert now({}, start=False) == "start"
    assert now({}, reflect=False) == "reflect"
    assert now({"firstQuestion": ""}) == "write"
    assert now({"firstQuestion": "", "now": {"asking": True}}) == "asking"
    assert now({"now": {"reading": True, "band": True}}) == "reading"
    assert now({"now": {"table": True, "band": True}}) == "table"
    assert now({"now": {"choices": True, "pressed": True, "table": True, "band": True}}) == "pressed"
    assert now({"now": {"pressed": True, "table": True, "band": True}}) == "answer_ai"
    assert now({"now": {"band": True}}) == "answer_ai"  # No table to press (the flat map).
    assert now({"aiAnswered": True, "now": {"pressed": True, "table": True, "band": True}}) == "after"
    # A card's box open: its own line, over the pressed bubble's and the AI's (直し31続き-3).
    assert now({"cardOpen": True, "now": {"choices": True, "pressed": True, "table": True, "band": True}}) == "card"
    assert now({"cardOpen": True, "now": {"band": True}}) == "card"
    assert now({"cardOpen": True, "now": {"reading": True}}) == "reading"
    # The box at the foot answering an AI's question (直し32-2).
    assert now({"to": {"kind": "ai"}, "now": {"choices": True, "pressed": True, "table": True}}) == "answer_ai"
    # 直し40-1: the latest round's split not pressed yet: only where it would be 「after」.
    done = {"pressed": True, "table": True, "band": True}
    assert now({"aiAnswered": True, "splitOpen": True, "now": dict(done)}) == "split"
    assert now({"aiAnswered": True, "splitOpen": False, "now": dict(done)}) == "after"
    assert now({"splitOpen": True, "now": {"table": True, "band": True}}) == "table"
    assert now({"splitOpen": True, "now": {"band": True}}) == "answer_ai"
    assert now({"splitOpen": True, "now": {"one": True}}) == "one"
    assert now({"splitOpen": True, "cardOpen": True}) == "card"


def test_the_screen_changes_the_state_where_it_happens():
    ask = _top("ask")
    assert "setNow({ asking: true });" in ask and '$("inside-fold").open = false;' in ask
    assert "showMessage(state.texts.waiting_ask)" not in APP  # The waiting line is the one at the top.
    assert "setNow({ reading: false, choices: false, pressed: false, table: false, band: false });" in _top("renderRound")
    assert "setNow({ band: true })" in _top("loadBand")
    assert "app.setNow({ reading: true });" in MAP and "app.setNow({ reading: false, table: true });" in MAP
    assert "app.setNow({ choices: true, pressed: true });" in MAP and "app.setNow({ choices: false });" in MAP


def test_the_band_says_the_step_in_words_not_by_colour_alone():
    show = _top("setNow")
    assert 'step.setAttribute("aria-current", "step")' in show
    assert '<p id="now-line" class="now-line" aria-live="polite">' in HTML
    lit = CSS[CSS.index(".now-steps li.lit {"):]
    lit = lit[:lit.index("}")]
    assert "font-weight: bold" in lit and "border-bottom-color" in lit
    # Kept at the top, outside the start and the table, so it stays when both change.
    assert ".now { position: sticky; top: 0;" in CSS
    assert HTML.index('<nav id="now"') < HTML.index("<main>")


def test_the_purpose_is_over_the_seven_promises_and_the_counts_over_the_question_box():
    assert HTML.index('id="start-purpose"') < HTML.index('id="start-notice"')
    assert HTML.index('id="inside"') < HTML.index('id="ask-form"')
    assert '<details id="inside-fold">' in HTML  # Shut until asked for (直し33-1).
    # Examples are shown only: never put in the box.
    render = _top("renderInside")
    assert "fill(" not in render and "onclick" not in render and "#question" not in render
    assert "EbinoMap.markOf(row.kind)" in render and "function markOf(kind)" in MAP


# --- 直し31続き-3: the words that disagreed ---

def test_a_card_box_open_has_its_own_line():
    from ebino.texts import now_lines
    lines = now_lines()
    assert lines["card"]["step"] == "ask" and lines["card"]["text"]
    app = (STATIC / "app.js").read_text(encoding="utf-8")
    assert 'if (cardOpen()) return "card";' in app
    # Before the pressed bubble's line: the box is what is in front of the student.
    assert app.index('if (cardOpen()) return "card";') < app.index('if (now.choices) return "pressed";')
    # The box at the foot writes to one seat (直し32-2).
    assert 'return state.to.kind === "seat";' in app


def test_the_quote_cards_button_says_what_the_bubbles_button_says():
    app = (STATIC / "app.js").read_text(encoding="utf-8")
    assert 'text: "元の段落"' not in app
    assert "text: state.texts.bubble_choices.paragraph" in app


def test_no_name_of_the_schools_booklet_is_in_the_repository():
    """直し31続き-4: until the school says its name may be shown, the
    booklet's name is not in the repository's words."""
    root = STATIC.parent.parent
    name = "".join(chr(c) for c in (0x5FD7, 0x4E8B, 0x56F3, 0x9451))  # Not written out, so this file is clean too.
    for path in [root / "README.md", *(root / "texts").glob("*.*"), *(root / "docs").glob("*.md"),
                 *(root / "ebino").rglob("*.py"), *(root / "ebino" / "static").glob("*.*")]:
        if path.suffix in (".py", ".md", ".txt", ".tsv", ".js", ".css", ".html"):
            assert name not in path.read_text(encoding="utf-8"), path.name


# --- 直し31続き-5: the band off the map, and Japanese broken between words ---

def test_the_map_fits_under_the_band():
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    rule = css[css.index(".map {"):]
    rule = rule[:rule.index("}")]
    assert "var(--now-h, 0px)" in rule  # The band's height is kept out of the map's.
    assert 'setProperty("--now-h"' in (STATIC / "app.js").read_text(encoding="utf-8")


def test_the_boxes_a_student_reads_break_between_words():
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    at = css.index("word-break: auto-phrase;")
    head = css[css.rindex("*/", 0, at) + 2:css.index("{", css.rindex("*/", 0, at))]
    boxes = {name.strip() for name in head.replace("\n", " ").split(",")}
    for box in (".now-line", ".inside", ".harvest", ".sheet", ".quote", ".table-bubble", ".map-bubble", ".map-choices",
                ".round", ".ai-card", ".closing", ".map-hint", ".heavy-talk", ".seats", "#reflect"):
        assert box in boxes, box
    assert '<html lang="ja">' in (STATIC / "index.html").read_text(encoding="utf-8")  # auto-phrase needs the language.
