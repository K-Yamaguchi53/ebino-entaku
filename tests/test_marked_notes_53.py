"""直し53 段6 (the teacher: 「ふせんを貼った所」をもっと見やすく): on the sheet,
each marked step is a note of its own: its tag (はじめて知った・気づいた …) a
small heading on its line, then whom and which question in plain words, then
the student's own answer as the student's words are shown. The words are
the same as before (only parted); 14px or more on the screen; the print
stays one A4 page (the tag beside the words there)."""

import re

from ebino import app as app_module
from ebino import trail
from ebino.session import Session

JS = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")


def _parts(item):
    return Session._mark_parts(None, item)


def _text(item):
    return Session._mark_text(None, item)


ITEMS = [
    {"kind": trail.AI_ANSWER, "question": "休みの取り方で、いちばん気になったのはだれの話？", "choice": "", "answer": "決めて取るほうに近い"},
    {"kind": trail.ONE_COACH, "question": "その人は、なぜそうしたと思う？", "choice": "わからない", "answer": "店があるから"},
    {"kind": trail.OPENED, "who": "農家", "label": "気分転換・休みの日のこと"},
    {"kind": trail.ONE_ASK, "who": "理容師", "text": "休みはどう決めていますか？"},
    {"kind": trail.QUESTION, "text": "休みの日って、みんな何してる？"},
    {"kind": trail.CARD, "text": "店の休みは誰が決めますか？"},
    {"kind": trail.DIRECTION, "text": "近い人に聞く"},
]


def test_the_parts_are_the_same_words_as_before_only_parted():
    for item in ITEMS:
        parts = _parts(item)
        assert set(parts) == {"head", "own"}
        # Nothing added, nothing left out: joined, they are the line there was.
        assert "　".join(filter(None, [parts["head"], parts["own"]])) == _text(item), item


def test_whose_words_are_whose():
    ai, coach, opened, one, question, card, direction = (_parts(item) for item in ITEMS)
    assert ai == {"head": "休みの取り方で、いちばん気になったのはだれの話？", "own": "決めて取るほうに近い"}
    assert coach == {"head": "その人は、なぜそうしたと思う？", "own": "わからない　店があるから"}
    assert opened["own"] == "" and one["own"] == "" and direction["own"] == ""
    assert question == {"head": "", "own": "休みの日って、みんな何してる？"} and card["head"] == ""


def test_the_sheet_shows_tag_head_and_own_apart():
    start = JS.index("// 直し53 段6 (the teacher: もっと見やすく)")
    part = JS[start:JS.index('box.append(el("p", "hk-label", W.sheet_story));', start)]
    assert part.index('el("p", "hk-marked-tag", mark.label)') < part.index('"hk-marked-head", mark.head')
    assert part.index('"hk-marked-head", mark.head') < part.index('el("p", "hk-marked-own", `「${mark.own}」`)')
    assert 'el("p", "hk-marked-head", mark.text)' in part  # Kept marks with no parts: the line as it was.
    assert "hk-marked-line" not in JS


def test_sizes_on_the_screen_and_one_page_on_paper():
    rule = lambda sel: re.search(re.escape(sel) + r" \{[^}]*\}", CSS).group(0)
    assert "font-size: 14px;" in rule(".hk-marked-tag") and "font-weight: 700;" in rule(".hk-marked-tag")
    assert "font-size: 15px;" in rule(".hk-marked-head")
    own = rule(".hk-marked-own, .hk-marked-note")
    assert "font-size: 17px;" in own and "font-family: var(--mincho);" in own and "font-weight: 700;" in own
    assert ".hk-sheet .hk-marked-head .hk-ref { font-size: 14px; }" in CSS
    # No ground of its own (the grey the teacher saw was not the app's).
    assert "background" not in rule(".hk-marked-item")
    # On paper: the tag beside the words, so the sheet stays one page.
    assert "grid-template-columns: auto minmax(0, 1fr);" in CSS[CSS.index("/* A4 one page: the tag beside the words"):]
