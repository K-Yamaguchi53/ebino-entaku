"""直し51 段5 (ヒビキ, 49_sheet_notice_try: the student's own lines as large
and plain as the people's and the host's, no lead; the labels small and
pale): the student's own words (今日の気づき, 次にやってみること's line, the
light when it is theirs) lead, a step larger and bold, in the faces there
are (no new one); the people's words, the host's and the trail a step
quieter, their words as they are; the labels read: 13px or more on screen,
8pt or more on paper, 4.5:1 or more. Still one A4 sheet (the screen check)."""

import re

from ebino import app as app_module

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
SHEET_JS = HK[HK.index("  async function toSheet() {"):HK.index("  function setup() {")]
PRINTED = CSS[CSS.index("/* Printed: the one sheet alone"):CSS.index("@page { size: A4;")]
ROOT = CSS[CSS.index(":root {"):CSS.index("}", CSS.index(":root {"))]
VARS = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", ROOT))


def _contrast(fore, back):
    def lum(hex_):
        rgb = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
        return .2126 * lin[0] + .7152 * lin[1] + .0722 * lin[2]
    a, b = sorted((lum(VARS[fore]), lum(VARS[back])), reverse=True)
    return (a + .05) / (b + .05)


def test_the_students_own_lines_lead():
    assert SHEET_JS.count('classList.add("hk-own-text")') == 2  # 今日の気づき and 次にやってみること.
    # The light: the student's own words lead; a person's (who) do not.
    assert 'el("p", sheet.light.who ? "hk-lit" : "hk-lit hk-own-text", `「${sheet.light.quote}」`)' in SHEET_JS
    assert ".hk-sheet .hk-own-text { font-size: 21px; font-weight: 700;" in CSS
    assert ".hk-sheet :is(.hk-met-quote, .hk-moves-list, .hk-story) { font-size: 15px; }" in CSS


def test_the_others_a_step_quieter_and_still_read():
    assert "color: var(--paper-quiet); }" in CSS
    for back in ("paper-light", "paper"):
        assert _contrast("paper-quiet", back) >= 4.5
        assert _contrast("paper-soft", back) >= 4.5  # The labels.
        assert _contrast("paper-ink", back) > _contrast("paper-quiet", back)  # Still a step.


def test_the_labels_read_on_screen_and_on_paper():
    assert ".hk-sheet .hk-label { font-size: 14px; font-weight: 700;" in CSS
    size = re.search(r"\.hk-sheet \.hk-label \{ font-size: (\d+)px; \}", PRINTED)
    assert size and int(size.group(1)) * .75 >= 8  # px to pt.
    assert ".hk-sheet .hk-own-text { font-size: 16px;" in PRINTED


def test_no_new_face():
    faces = re.findall(r'font-family: "([^"]+)"', CSS)
    assert set(faces) == {"Ebino Title", "Ebino Mincho", "Ebino Gothic"}
