"""直し54h (the teacher, 11/8: 直せるところは直して): web addresses, a reading
read as each kana twice, and the masks' words where they read oddly.
Every word here is invented."""

import pytest

from ebino.ingest.utterance import mend_reading


@pytest.mark.parametrize("text, want", [
    # Web addresses.
    ("寄付を募った。• ページはこちらから（https://example.jp/projects/123）",
     "寄付を募った。"),
    # The pointer is taken out alone, not the bullet before it.
    ("• 現在、進行中（２１名の支援）• ページはこちらから（https://example.jp/p/1）。返礼品もある！",
     "• 現在、進行中（２１名の支援）。返礼品もある！"),
    # An address ends at its .html: the date after it stays.
    ("ふれあい館https://example.jp/main/html/rd/p/000000001.000012345.html11月3日に行った。",
     "ふれあい館11月3日に行った。"),
    ("地図で調べた。000400060008000https://example.jp/cities/detail/city/", "地図で調べた。"),
    ("記事を読んだ！https://example.jp/main/html/rd/p/0 次に行った。", "記事を読んだ！ 次に行った。"),
    ("資料（https://example.jp/a）を見た。", "資料を見た。"),
    # A reading set over a word, each kana twice.
    ("町を再興（リリ    ババ   イイ    ババ   ルル   ）させよう！", "町を再興（リバイバル）させよう！"),
    # The masks' words.
    ("株式会社この職場は主に部品を作る。", "この会社は主に部品を作る。"),
    ("本社を置くこの職場（株）は、", "本社を置くこの会社は、"),
    ("九州（㈱この職場）は主に", "九州（この会社）は主に"),
    ("有限会社この職場を設立した。", "この会社を設立した。"),
    ("その絵をお客この方が買う。", "その絵をお客さんが買う。"),
    ("現在は奥この方と二人で営む。", "現在は奥さんと二人で営む。"),
    ("読み聞かせの様子（この方先生）", "読み聞かせの様子（この先生）"),
    ("この方は、「この職場」というカフェを営む。", "この方は、カフェを営む。"),
])
def test_what_reads_badly_is_mended(text, want):
    assert mend_reading(text) == want


@pytest.mark.parametrize("text", [
    "この方は、町で生まれた。",
    "この職場の社長は、",
    "「この職場」というのは、",          # Not before a noun.
    "「この職場」とは、地域の会社だ。",
    # A name run into the next word (この方農園) gets a break since 直し54i: test_once_54i.
    "ママと話した。",                    # Kana twice, but not a reading.
    "イイ ネ と言われた。",              # Fewer than three pairs.
    "（例）を見る。",
    "",
])
def test_other_words_are_kept(text):
    assert mend_reading(text) == text
