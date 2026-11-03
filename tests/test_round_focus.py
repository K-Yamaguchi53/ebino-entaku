"""After 「聞く」 the keyboard's focus goes to the new round's question
(直し25-5), so Tab goes on to the round's answer, not through the map's
points first; the page does not jump for it, and the focus shows."""

import re

from ebino import app as app_module

SCRIPT = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")


def test_a_new_round_takes_the_focus_on_its_question_without_a_jump():
    start = SCRIPT.index("function renderRound(")
    render = SCRIPT[start:SCRIPT.index("\n}\n", start)]
    focus = render.index('box.querySelector(".round-question")')
    assert render.index('$("rounds").prepend(box);') < focus  # On the page first.
    assert "asked.tabIndex = -1;" in render  # Not a stop of its own for Tab.
    assert "asked.focus({ preventScroll: true });" in render
    rule = re.search(r"\.round-question:focus-visible \{[^}]*\}", CSS).group(0)
    assert "outline: 2px solid var(--lamp)" in rule and "#" not in rule
