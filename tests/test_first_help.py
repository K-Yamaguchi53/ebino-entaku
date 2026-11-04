"""直し32-4: the first time a student presses a bubble, a line under each
of its buttons says what it does; after that the buttons alone; 「最初に
もどる」 reads the page afresh, so the next student has them again. 「元の
段落を読む」 puts the paragraph in the drawer, not by the map; 閉じる or Esc
closes it, the keyboard back on the button."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _top(name):
    start = APP.index(f"function {name}(")
    if APP[start - 6:start] == "async ":
        start -= 6
    return APP[start:APP.index("\n}\n", start) + 3]


def _first_help_twice(state="{ texts: { bubble_choices_help: { mark: 'M' } } }"):
    program = f"const state = {state};\n{_top('firstHelp')}\n" \
              "process.stdout.write(JSON.stringify([firstHelp(), firstHelp(), firstHelp()]));"
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    return json.loads(out.stdout.decode("utf-8"))


@node
def test_the_help_comes_the_first_time_only():
    assert _first_help_twice() == [{"mark": "M"}, None, None]


@node
def test_from_the_start_again_it_comes_again():
    # 「最初にもどる」 reads the page afresh: a new state, the help again.
    assert "window.location.replace(window.location.pathname);" in _top("backToStart")
    assert "helpShown" not in APP[:APP.index("const $ = ")]  # Not kept past a page.
    assert _first_help_twice()[0] == {"mark": "M"}


def test_each_button_has_its_line_and_the_words_are_in_texts():
    help_words = texts.screen_texts()["bubble_choices_help"]
    assert set(help_words) == {"paragraph", "mark", "card", "read"}
    opened = MAP[MAP.index("function openChoices("):MAP.index("function moveInChoices(")]
    assert "const help = app.firstHelp();" in opened
    assert 'div("help", help[key])' in opened and 'item.setAttribute("aria-describedby", line.id)' in opened


def test_the_help_says_what_the_buttons_do():
    help_words = texts.screen_texts()["bubble_choices_help"]
    # The paragraph goes to the drawer, with its source.
    assert "引き出し" in help_words["paragraph"] and "出どころ" in help_words["paragraph"]
    assert "app.openParagraph(utteranceId" in MAP
    # A mark is kept for the reflection's sheet (sheet_view's met_lives), one a seat.
    assert "ふりかえりの1枚" in help_words["mark"]
    # 「この人に聞きたいことを書く」 makes a question card from the box at the foot; nothing is sent to the person.
    assert "質問カード" in help_words["card"] and "下の欄" in help_words["card"] and "送ります" not in help_words["card"]


def test_the_paragraph_is_in_the_drawer_and_closing_goes_back_to_the_button():
    opened = _top("openParagraph")
    assert '$("drawer-paragraph").replaceChildren(' in opened and 'openDrawer("paragraph", from);' in opened
    assert "await app.openParagraph(utteranceId, paragraph.querySelector(\".whose\").textContent, read);" in MAP
    # closeDrawer gives the keyboard back to what opened it (the button).
    assert "back.focus({ preventScroll: true })" in _top("closeDrawer")
