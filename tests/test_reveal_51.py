"""直し51 段6 (the teacher, 11/7: 「1枚ができる」瞬間): the first time the sheet
comes up, its parts rise one after another (hk-rise's kind), then the
student's two lines, one then the other, each with a marker's line drawn once
under it, left to right. In 2 seconds at most; once only (the sheet opened
again: just there); a press or a key: all at once. Motion reduced: all there,
the lines drawn. Never blinking, never the whole screen. Printed: all there,
the marker's line not printed. A line not written or taken off: not waited
for. (The screen check measures it in a browser: 0 s with motion reduced,
2 s with motion, opened again.)"""

import re

from ebino import app as app_module

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
REVEAL = HK[HK.index("  function reveal(box) {"):HK.index("  function setup() {")]
PRINTED = CSS[CSS.index("/* Printed: the one sheet alone"):CSS.index("@page { size: A4;")]


def test_once_only_and_not_with_motion_reduced():
    assert "let revealed = false;" in HK
    assert "if (revealed || still()) {" in REVEAL
    assert REVEAL.index("revealed = true;") < REVEAL.index('box.classList.add("hk-reveal");')
    sheet = HK[HK.index("  async function toSheet() {"):HK.index("  function setup() {")]
    assert sheet.index('show("sheet");\n    reveal(box);') > sheet.index('box.append(el("p", "hk-print-note", W.print_note));')


def test_within_two_seconds_and_a_press_shows_it_all():
    # Parts at most 1 s apart in all, the two lines 0.2 s apart after, each
    # mark 0.25 s after its line and 0.45 s long: 1 + 0.2 + 0.25 + 0.45 = 1.9 s.
    assert "Math.min(90, Math.floor(1000 / Math.max(parts.length, 1)))" in REVEAL
    assert "const after = Math.min(parts.length * step, 1000);" in REVEAL
    assert "`${after + n * 200}ms`" in REVEAL
    assert "animation-delay: calc(var(--hk-at, 0ms) + 250ms); }" in CSS
    assert "@keyframes hk-mark { from { background-size: 0% 100%; } to { background-size: 100% 100%; } }" in CSS
    assert ".hk-sheet.hk-reveal .hk-own-text { animation: hk-rise .3s ease-out both;" in CSS
    assert "const timer = setTimeout(done, 2 * 1000);" in REVEAL
    assert 'document.addEventListener("pointerdown", done, true);' in REVEAL
    assert 'document.addEventListener("keydown", done, true);' in REVEAL
    assert 'box.classList.remove("hk-reveal");' in REVEAL


def test_only_the_two_lines_get_the_mark_and_not_one_taken_off():
    assert 'box.querySelectorAll(".hk-notice-text, .hk-try-text")].filter((line) => !line.hidden)' in REVEAL
    assert 'const mark = el("span", "hk-own-mark", line.textContent);' in REVEAL  # The words as they were.


def test_motion_only_when_not_reduced_never_blinking():
    block = CSS[CSS.index("/* 直し51 段6: the sheet coming up once"):CSS.index("@keyframes hk-mark")]
    moving = block[block.index("@media (prefers-reduced-motion: no-preference) {"):]
    assert "infinite" not in moving and "alternate" not in moving
    # Outside the media rule, the line is there drawn (motion reduced, done, pressed).
    still_rule = block[:block.index("@media")]
    assert "no-repeat 0 0 / 100% 100%" in still_rule
    # The sheet's parts only, not the page.
    assert not re.search(r"(body|html|#hitokoto)[^{]*\{[^}]*hk-rise", block)


def test_printed_all_there_no_mark():
    assert ".hk-sheet.hk-reveal > *, .hk-sheet.hk-reveal .hk-own-text, .hk-own-mark { animation: none !important; }" in PRINTED
    assert ".hk-own-mark { background: none; }" in PRINTED
