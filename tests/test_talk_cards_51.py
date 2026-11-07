"""直し51 段4 (ヒビキ, 49_try_choices: grey cards alike, muddy on the night, a
school questionnaire; the question to answer not standing out): 先生の問い on
the night's own blue; the question waiting for its answer (at the foot) a
step lighter, its edge the lamp's and its words a step larger, never
blinking; one answered, skipped or picked past a step smaller and sunk, its
✓ read. The label 先生の問い stays. Only the look: the questions, their
order, their words and the record as before. Each colour of words on its
ground 4.5:1 or more, measured here from style.css's own values."""

import re

from ebino import app as app_module

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
ROOT = CSS[CSS.index(":root {"):CSS.index("}", CSS.index(":root {"))]
VARS = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", ROOT))


def _lum(hex_):
    rgb = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
    return .2126 * lin[0] + .7152 * lin[1] + .0722 * lin[2]


def contrast(fore, back):
    a, b = sorted((_lum(VARS[fore]), _lum(VARS[back])), reverse=True)
    return (a + .05) / (b + .05)


def _inner(name):
    start = HK.index(f"  function {name}(")
    return HK[start:HK.index("\n  }\n", start)]


def test_the_question_waiting_is_the_last_one_asked_and_one_only():
    wait = _inner("waitOn")
    assert 'old.classList.remove("hk-now");' in wait and 'old.classList.add("hk-past");' in wait
    assert 'if (card) card.classList.add("hk-now");' in wait
    # Every card said marks it: a question waits; the student's card answers it.
    assert 'if (cls !== "waiting") waitOn(who === "me" ? null : card);' in _inner("say")
    assert "waitOn(null);" in _inner("atEnd")


def test_the_cards_on_the_nights_blue_not_grey():
    assert ".hk-card.teacher { align-self: flex-start; background: var(--night-2); border: 1px solid var(--moon-faint); }" in CSS
    assert "background: var(--lamp-faint); border: 1px solid var(--lamp-soft); }" not in CSS.split(".hk-card.teacher {")[1][:120]
    assert ".hk-card.teacher .hk-who { color: var(--lamp); }" in CSS  # 先生の問い stays.


def test_waiting_lit_a_step_and_larger_past_smaller_and_sunk():
    assert ".hk-card.teacher.hk-now { background: var(--night-3); border-color: var(--lamp);" in CSS
    assert ".hk-card.hk-now > .hk-q { font-size: 20px; }" in CSS
    assert ".hk-card .hk-q { margin: 0; font-size: 17px; }" in CSS
    assert ".hk-card.hk-past > .hk-q { font-size: 15px; color: var(--soft); }" in CSS
    assert ".hk-card.teacher.hk-past { background: var(--night); border-color: var(--moon-faint); }" in CSS
    # The ✓ of the one picked, as before.
    assert '#hk-log .hk-done .hk-chosen::before { content: "✓" / "";' in CSS


def test_no_blinking_nor_motion_added():
    rules = CSS[CSS.index("/* 直し51 段4: the question waiting"):CSS.index(".hk-card.hk-past .hk-meet select")]
    assert "animation" not in rules and "transition" not in rules


def test_each_word_on_its_ground_reads():
    pairs = [
        ("ink", "night-3"), ("lamp", "night-3"),  # Waiting: the question and 先生の問い.
        ("ink", "night-2"), ("lamp", "night-2"),
        ("soft", "night"), ("lamp", "night"),  # Past: its question, its label.
        ("ink", "night-3"),  # The answers to pick (on night-3), past or not.
        ("soft", "ai-deep"), ("ai", "ai-deep"), ("ai-ink", "ai-deep"),
    ]
    for fore, back in pairs:
        assert contrast(fore, back) >= 4.5, (fore, back, round(contrast(fore, back), 2))


def test_the_record_and_the_words_untouched():
    # Only classes: no word set, no post.
    wait = _inner("waitOn")
    assert "post(" not in wait and "textContent" not in wait
