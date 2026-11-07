"""直し51 段7 (49_notice_before: 「10 最初」 halfway, not under the knob at
10): the label's 「10」 under the knob's middle at 10 of 15 (the track less
half a knob each end). The words as they were (texts/hitokoto.tsv)."""

from ebino import app as app_module
from ebino import hitokoto

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")


def test_the_middle_label_is_at_ten_of_fifteen():
    assert ".hk-ticks { position: relative; }" in CSS
    assert ".hk-ticks span:nth-child(2) { position: absolute; left: calc(8px + (100% - 16px) * 10 / 15);" in CSS
    # The second of the three is 「10 最初」, the range 0 to 15 starting at 10.
    assert 'ticks.append(el("span", "", W.scale_low), el("span", "", W.scale_first), el("span", "", "15"));' in HK
    assert 'Object.assign(range, { type: "range", min: "0", max: "15", value: "10", step: "1" });' in HK
    assert hitokoto.words()["scale_first"] == "10 最初"
