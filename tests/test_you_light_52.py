"""直し52 段2 (the teacher, 11/7): 今日のあなた. On today's map of 帰る前に、
ひとこと, last, after today's people: one small light where the school is in
the sketch, its ring going out once, and beside it, small, 「今日のあなた」
(texts/hitokoto.tsv, a draft for the teacher). No name, no question. Nothing
is sent or kept: not the record, not the server, not the browser's storage;
the page alone (opened again, it is gone). The counts are as they were.
Motion reduced: lit from the first, no ring. Never on the sheet or its print.
(The screen check measures it in a browser: one light, its words only, no
request while it lights, nothing stored, lit at once with motion reduced.)"""

import re

from ebino import app as app_module
from ebino import hitokoto

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
YOU = HK[HK.index("  function youLight(map) {"):HK.index("  // 直し48 段7: today's trail beside the talk")]
DRAW = HK[HK.index("  function drawMap() {"):HK.index("  // 直し52 段2 (the teacher, 11/7): last, after today's people")]


def test_its_words_are_the_teachers_and_only_those():
    assert hitokoto.words()["map_you"] == "今日のあなた"
    assert "label.textContent = W.map_you;" in YOU
    # No name, no question, no title: nothing of the student or of the day.
    for word in ("view.", "first_question", "question", "title", "app.state"):
        assert word not in YOU, word


def test_one_light_last_on_todays_map_the_counts_as_they_were():
    assert DRAW.index("box.append(map);\n    youLight(map);") > DRAW.index("view.people.forEach(")
    assert YOU.count('map.append(g);') == 1 and YOU.count('svg("g", {') == 1
    # The counts as they were: the same words, the same numbers (today's you not one of them).
    assert 'counts.textContent = fill(W.map_counts, view.counts);' in DRAW
    assert hitokoto.words()["map_counts"] == "話を聞いた{people}人・印をつけた言葉 {marks}つ・残した質問カード {cards}枚"


def test_nothing_sent_or_kept_the_ways_out_counted():
    for word in ("post(", "fetch(", "call(", "Storage", "indexedDB", "sendBeacon", "cookie"):
        assert word not in YOU, word
    # The ways this page sends anything, as before 直し52: the trail read, and eleven steps.
    assert re.findall(r'fetch\("([^"]+)"', HK) == ["/api/trail"]
    assert sorted(re.findall(r'post\("([a-z_]+)"', HK)) == sorted(
        ["answer", "begin", "choose", "drop", "light", "meet", "parts", "scale", "sheet", "subject", "use"])
    assert "localStorage" not in HK and "sessionStorage" not in HK
    # Nothing of it in the record's words either: the server never hears of it.
    assert "map_you" not in (app_module.STATIC_DIR.parent / "hitokoto.py").read_text(encoding="utf-8").split("TEXT_IDS = (")[0]


def test_once_motion_reduced_lit_never_blinking_never_printed():
    assert "let youShown = false;" in HK
    assert 'svg("g", { class: youShown ? "hk-you" : "hk-you hk-you-new" });' in YOU
    block = CSS[CSS.index("/* 直し52 段2: 今日のあなた"):CSS.index("@keyframes hk-you-ring")]
    moving = block[block.index("@media (prefers-reduced-motion: no-preference) {"):]
    assert "infinite" not in moving and "alternate" not in moving
    assert "hk-you-ring 1.6s cubic-bezier(.2, .6, .3, 1) .9s 1 forwards;" in moving
    # Outside the media rule: lit (no opacity 0 on the light), the ring not there.
    still = block[:block.index("@media")]
    assert ".hk-you-ring { fill: none;" in still and "opacity: 0;" in still[still.index(".hk-you-ring"):]
    assert "opacity" not in still[still.index(".hk-you-dot"):still.index(".hk-you-ring")]
    # Today's map is never on the sheet: its print shows the sheet alone.
    printed = CSS[CSS.index("body:has(#hk-sheet:not([hidden])) :is("):]
    assert "#hk-map" in printed[:printed.index("{")]
    assert "hk-you" not in HK[HK.index("  async function toSheet() {"):]
