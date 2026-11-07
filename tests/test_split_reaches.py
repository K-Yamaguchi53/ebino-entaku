"""直し48 段8 (the teacher, 11/7: 「ここで割れた：」 has hardly been seen since
yesterday): from the model's answer to the screen, nothing in the code holds
back a split whose two sides were shown: the round sends its heading; the
map puts it under the map (and on the table where wide). What the code does drop, as it always did: a side whose
words did not reach the screen (a piece the moderator did not quote, or one
the guard stopped). Everything here is invented; the model is a fake one."""

from ebino import app as app_module
from ebino import moderator
from test_session import SPLIT, librarian_finds, moderator_says, sitting

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
QUOTES = [("a1", "休みは決めて取ります。"), ("a2", "月曜は必ず店を閉める。"), ("b1", "畑は天気しだいなので、休みは空いたら取ります。")]


def test_two_people_who_part_make_a_heading_that_reaches_the_screen():
    session, _ = sitting([librarian_finds("a1", "a2", "b1"), moderator_says(QUOTES, [SPLIT])])
    view = session.ask("休みの日って、みんな何してる？")
    assert [s["heading"] for s in view["splits"]] == [SPLIT[0]]
    assert view["splits"][0]["side_a"] == ["a1"] and view["splits"][0]["side_b"] == ["b1"]
    # The map shows it: under the map, and on the table where it is wide enough.
    assert 'if (split && overlay.clientWidth >= TAG_ON_MAP) $("map-heading").replaceChildren(splitButton(' in MAP
    assert "const TAG_ON_MAP = 600;" in MAP
    assert moderator.MAX_SPLITS == 3


def test_a_side_whose_words_were_not_quoted_is_dropped_as_before():
    # The moderator names a piece for a side that it did not quote: no words
    # of that side on screen, so no heading (SPEC 14-39). Likely why fewer
    # headings come now (fewer pieces since 直し31-6; see the report).
    unquoted = ('ここで割れた：休みを"決めて取る"人と"空いたら取る"人', ["a1"], ["b1"])
    session, _ = sitting([librarian_finds("a1", "a2", "b1"), moderator_says(QUOTES[:2], [unquoted])])
    view = session.ask("休みの日って、みんな何してる？")
    assert view["splits"] == []
    assert session.rounds[-1].splits_dropped == 1


def test_the_moderator_still_has_its_split_in_its_instruction_and_answer():
    from ebino.prompts import MODERATOR
    assert "考えが分かれているところにだけ、見出しを立てる（多くて3つ）" in MODERATOR
    assert "splits" in moderator.SCHEMA["properties"] and "splits" in moderator.SCHEMA["required"]
