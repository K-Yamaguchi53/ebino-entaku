"""直し52 段6 (ヒビキ, 51_sheet_reveal_t00〜t20 / 51_sheet_*):
- 外す comes with its line, not before it (the box, its line and its 外す
  rise at the same time).
- The student's words first: 今日の気づき, 次にやってみること, 今日、光ったところ
  (0.2 s apart), then the rest; still 2 seconds at most, a press or a key all
  at once, motion reduced all there (as 直し51 段6).
- On the screen those three boxes stand at the top under the title, so at
  1920×1080 they and their marker's lines are in the window from the start
  (no scrolling done for the student). Printed, the sheet as before (its
  order, one A4 page).
- ↓ in 自分の言葉の動き, the people's titles and the note at its foot: 14px
  on the screen, the paper's quiet ink (6.7:1); printed as before (12px).
(In a browser: at 0.4 s the first line and its 外す both rising; at 1920×1080
the three boxes' bottoms 419, 544, 683 px; the PDF one page in the old order.)"""

from ebino import app as app_module

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
REVEAL = HK[HK.index("  function reveal(box) {"):HK.index("  function setup() {")]
PRINTED = CSS[CSS.index("/* Printed: the one sheet alone"):CSS.index("@page { size: A4;")]


def test_the_students_words_first_each_with_its_drop():
    assert '[".hk-notice-box", ".hk-try-box", ".hk-light-box"]' in REVEAL
    assert 'part.style.setProperty("--hk-at", `${n * 200}ms`);' in REVEAL
    # The line rises with its box, its 外す (in the box, not timed apart) with them.
    assert 'for (const line of part.querySelectorAll(".hk-own-text")) line.style.setProperty("--hk-at", `${n * 200}ms`);' in REVEAL
    assert ".hk-drop" not in REVEAL
    assert "const rest = [...box.children].filter((part) => part !== title && !leads.includes(part));" in REVEAL
    assert "const timer = setTimeout(done, 2 * 1000);" in REVEAL


def test_on_the_screen_at_the_top_printed_as_before():
    screen = CSS[CSS.index("@media screen {\n  .hk-sheet { display: flex;"):]
    screen = screen[:screen.index("\n}\n")]
    assert ".hk-sheet > .hk-notice-box { order: -3; }" in screen
    assert ".hk-sheet > .hk-try-box { order: -2; }" in screen
    assert ".hk-sheet > .hk-light-box { order: -1; }" in screen
    assert "order" not in PRINTED and "display: flex" not in PRINTED[:PRINTED.index(".hk-qq")]
    # No scrolling done for the student.
    assert "scrollIntoView" not in REVEAL and "scrollTo" not in REVEAL


def test_the_small_words_on_the_sheet():
    assert ".hk-met-who { display: block; font-size: 14px; color: var(--paper-soft); }" in CSS
    assert 'content: "↓"; position: absolute; left: .2em; top: -.85em; font-size: 14px; color: var(--paper-soft); }' in CSS
    assert ".hk-print-note { margin: 18px 0 0; font-size: 14px; color: var(--paper-soft); }" in CSS
    assert ".hk-met-who, .hk-print-note, .hk-moves-list li + li::before { font-size: 12px; }" in PRINTED
