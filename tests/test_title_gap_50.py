"""直し50 段4 (ヒビキ: on 整理中, 48_sheet_wait_1366x650, the title
「えびの円卓」 touched the band under it): on 帰る前に、ひとこと the title alone
goes a little higher. position: relative moves its picture only, so nothing
else on the page moves (the band, the heading, the sign stay where they were)."""

from ebino import app as app_module

CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
RULE = "body:has(#hitokoto:not([hidden])) .masthead h1 { position: relative; top: -6px; }"


def test_the_title_goes_up_on_the_hitokoto_page_only():
    assert CSS.count(RULE) == 1
    # Not on the entrance, the table or the old reflection.
    assert CSS.count(".masthead h1 { position: relative") == 1
    # Its size and its margin as before (the band and all under it do not move).
    assert "body:has(#start[hidden]) .masthead h1 { font-size: 36px; letter-spacing: .12em; margin-bottom: 4px; }" in CSS
