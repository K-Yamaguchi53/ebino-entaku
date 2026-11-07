"""直し48 段3 (the teacher, 11/7: 「まとめるときは、ここ」 went unseen): after
some asking (the same state as before), the sign by 「帰る前に、ひとこと」 is
large and in two lines, the second saying going on is fine too (so it is not
taken for the one right next step), and the button is lit: a slow ring once,
never blinking; with motion reduced, colour and size only."""

import re

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


def test_its_two_lines_are_in_texts():
    guide = texts.screen_texts()["guide"]
    assert guide["after"] == "まとめるときは、ここ"
    assert guide["after_more"] == "もっと話を聞きたい人は、吹き出しを押してみよう"
    assert guide["answer_ai"] == "コーチとオブザーバーの問いはここ。押して答えよう"


def test_large_two_lines_and_the_button_lit():
    assert 'after: { at: () => $("to-reflect"), more: "after_more", big: true },' in APP
    draw = _top("drawGuide")
    assert 'el("span", { class: "guide-main", text: words[spec.words || now] })' in draw
    assert 'el("span", { class: "guide-more", text: words[spec.more] })' in draw
    assert 'if (spec.big) guide.classList.add("big");' in draw
    assert 'if (glow && !$("first-look").open) glow.classList.add("guide-glow");' in draw
    assert ".guide.big { max-width: min(400px, calc(100vw - 16px)); padding: 12px 22px; font-size: 26px; }" in CSS
    assert ".guide-more { margin-top: 4px; font-size: 17px;" in CSS


def test_the_ring_is_slow_and_once_and_none_with_motion_reduced():
    lit = re.search(r"#to-reflect\.guide-glow \{[^}]*\}", CSS).group(0)
    assert "animation" not in lit and "transform: scale(1.06)" in lit  # Size, not the layout.
    block = CSS[CSS.index("@media (prefers-reduced-motion: no-preference) {\n  .guide.fresh"):]
    block = block[:block.index("\n}\n")]
    assert "#to-reflect.guide-glow { animation: guide-glow 2.6s ease-out 1; }" in block
    assert "infinite" not in CSS[CSS.index("@keyframes guide-glow"):CSS.index("@keyframes guide-glow") + 300]
