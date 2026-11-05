"""直し40-0 (the teacher's answers to 38's report): on 帰る前に、ひとこと's
screen, the split's heading in 「」 as everywhere else (on screen only);
after 段4, the main button says 「光ったところを見る」; a question card
answered or a ladder card picked is not faded: the people's and the
student's words read as before (4.5:1 or more against their ground), done
shown by its edges and a small mark."""

import re

from ebino import app as app_module
from ebino import hitokoto

STATIC = app_module.STATIC_DIR
HK = (STATIC / "hitokoto.js").read_text(encoding="utf-8")
APP = (STATIC / "app.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")


def _inner(name):
    start = HK.index(f"function {name}(")
    return HK[start:HK.index("\n  }\n", start) + 5]


def test_the_maps_split_heading_goes_through_shown_quotes_on_screen_only():
    drawn = _inner("drawMap")
    assert 'el("span", "hk-split-heading", app.shownQuotes(view.split.heading))' in drawn
    assert "`${W.map_split}${app.shownQuotes(view.split.heading)}`" in drawn  # Read aloud the same.
    assert "view.split.heading)" not in drawn.replace("app.shownQuotes(view.split.heading)", "")
    assert "EbinoHitokoto.open({ call, state, setNow, sendFailed, showBackToStart, shownQuotes });" in APP


def test_after_the_last_step_the_main_button_goes_to_the_light_and_stop_here_stays_for_before():
    words = hitokoto.words()
    assert words["to_light"] == "光ったところを見る" and words["stop"] == "ここまでにする"
    end = _inner("atEnd")
    assert 'button("hk-primary", W.to_light, toLight)' in end and '$("hk-stop").hidden = true;' in end
    assert "hk-stop\").classList.add(\"hk-primary\")" not in HK
    # 「ここまでにする」: the quiet way out in 段2, as before.
    assert '$("hk-stop").addEventListener("click", toLight);' in HK
    assert '<p class="hk-exit"><button type="button" id="hk-stop" class="quiet"></button></p>' in (
        STATIC / "index.html").read_text(encoding="utf-8")


def test_a_card_answered_or_picked_is_not_faded_and_shows_done_by_its_edge_and_a_mark():
    lock = _inner("lock")
    assert 'box.classList.add("hk-done");' in lock and 'chosen.classList.add("hk-chosen");' in lock
    assert 'chosen.setAttribute("aria-pressed", "true");' in lock
    for picked in ("lock(box, quote);", "lock(box, pick);", "lock(box, chosen);"):
        assert picked in HK, picked
    assert "#hk-log .hk-done :is(button, input, select):disabled { opacity: 1; cursor: default; }" in CSS
    assert '#hk-log .hk-done .hk-chosen::before { content: "✓" / "";' in CSS
    assert "#hk-log .hk-done :is(.hk-quote, .hk-pick):not(.hk-chosen) { border-style: dashed; }" in CSS
    # A send that failed: the card can be answered again.
    assert 'box.classList.remove("hk-done");' in _inner("unlock")


def _colour(name):
    value = re.search(rf"--{name}: (#[0-9a-f]{{6}});", CSS).group(1)
    return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _contrast(a, b):
    def lum(rgb):
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_the_words_in_a_done_card_keep_four_and_a_half_to_one():
    # The people's words on paper (2択), the student's (picks, a line, the
    # blank, the seat picked), each on its own ground, not faded.
    pairs = {"hk-quote": ("paper-ink", "paper"), "hk-quote small": ("paper-soft", "paper"),
             "hk-pick": ("ink", "night-3"), "hk-force": ("soft", "night-3"), "input": ("paper-ink", "paper")}
    for what, (ink, ground) in pairs.items():
        assert _contrast(_colour(ink), _colour(ground)) >= 4.5, what
