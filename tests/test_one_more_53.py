"""直し53 段2: at one to one, 「続きを読む」 under a long answer could not be
pressed (the teacher's screen). The map's overlay takes no presses
(pointer-events: none) and the person's bubble never took them back, so the
button under the folded words was reached only by the keyboard. The bubble
now takes presses itself; the fold and its button are as they were."""

import re

from ebino import app as app_module

SCRIPT = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")


def _rule(selector):
    return re.search(re.escape(selector) + r" \{[^}]*\}", CSS).group(0)


def test_the_overlay_still_takes_no_presses_but_the_bubble_does():
    assert "pointer-events: none" in _rule(".map-overlay")
    assert "pointer-events: auto" in _rule(".one-bubble")
    # Its questions and the coach's board took them already.
    assert "pointer-events: auto" in _rule(".one-asks")
    # Nothing turns the button itself off.
    assert "pointer-events" not in _rule(".one-more")


def test_the_button_opens_and_shuts_the_rest_as_before():
    start = SCRIPT.index("function foldPieces(")
    fold = SCRIPT[start:SCRIPT.index("\n  }\n", start)]
    assert 'toggle.type = "button";' in fold and 'toggle.className = "one-more";' in fold
    assert 'toggle.setAttribute("aria-expanded", String(open));' in fold
    assert "toggle.textContent = open ? words.read_less : words.read_more;" in fold
    assert "for (const node of rest) node.hidden = !open;" in fold
    # Opened, the bubble may scroll inside the frame (now with the wheel too).
    assert ".one-bubble.unfolded { max-height: calc(100% - 16px); overflow: auto; }" in CSS
