"""The choices a lamp card opens are tied to whoever was pressed (直し27-1):
whose card it is at their top, their tail pointing at that seat, the seat a
ring brighter while they are open, and they go against the side of the
person's own card, which stays in sight. Only when there is no room do the
other cards step behind; the table's top and chairs are never covered. A
「閉じる」 button closes them, its word the teacher's, in texts/."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def test_the_choices_say_whose_they_are_and_close_with_the_teachers_word():
    assert texts.screen_texts()["bubble_close"] == "閉じる"
    opened = _inner("openChoices")
    assert 'head.append(div("who", whoOf(seatOf(seatId))), close);' in opened
    assert "close.textContent = app.state.texts.bubble_close;" in opened
    assert 'close.addEventListener("click", () => closeChoices(true));' in opened
    assert "node.append(head, read," in opened
    assert 'token.node.classList.add("chosen")' in opened
    assert 'querySelectorAll(".token.chosen")) token.classList.remove("chosen")' in _inner("closeChoices")
    assert ".token.chosen .halo { stroke: var(--lamp-bright)" in CSS


def test_the_choices_get_a_tail_and_their_card_stays_in_sight():
    put = _inner("putChoices")
    assert "choicesPlan(frameWH, item, own, { w: width, h: height }, hard, crossed, others, spots, needTail)" in put
    assert "for (const [cardCrossed, crossed, needTail] of [[block, block, true], [block, top, true], [block, top, false]," in put
    assert '[block, top, "near"], [top, top, true], [top, top, false], [top, top, "near"]]' in put  # Never over the top.
    assert "spots = cardSpots(frameWH, item, own, hard, cardCrossed, reach);" in put  # The card's tail last of all.
    assert "if (plan.tail) drawTail(node, [...plan.spot, width, height], item);" in put
    assert "drawTail(card, [...plan.at, own[2], own[3]], item);" in put and "choices.moved = true;" in put
    # What they cover, and what the moved card covers, steps behind; never the card itself.
    assert "if (overlaps(node, other) || overlaps(card, other) || (apart && overlaps(paragraph, other)))" in put
    assert ".map-choices .tail {" in CSS


_PLAN = """
%(source)s
const frame = { w: 600, h: 400 };
// A seat at (300, 200); its card above it.
const card = { w: 160, h: 60, px: 300, py: 200, r: 10, gap: 26 };
const own = [220, 110, 160, 60];
const box = { w: 140, h: 80 };
const meets = (a, b) => boxesMeet(a, b);
const stay = choicesPlan(frame, card, own, box, [], [], [], []);
// Another card where they would go on the right: they go on the left.
const right = [[380, 100, 220, 100]];
const left = choicesPlan(frame, card, own, box, [], [], right, []);
// The seat's own box is hard: nothing may cover it.
const seatBox = [290, 190, 20, 20];
const hard = choicesPlan(frame, card, own, box, [seatBox], [], [], []);
// No room by the card where it is (under or over it they would come
// between it and its seat): it moves to a spot (cardSpots) that has room.
const top = [[0, 0, 100, 400], [500, 0, 100, 400]];
const spots = cardSpots(frame, card, own, [seatBox, ...top], [], 240);
const moved = choicesPlan(frame, card, own, box, [seatBox, ...top], [], [], spots);
// Covered whichever way: the least, and the card keeps where it is if that is least.
const soft = [[0, 0, 600, 400]];
const crowded = choicesPlan(frame, card, own, box, [seatBox], [], soft, []);
process.stdout.write(JSON.stringify({ stay, left, hard, moved, crowded,
  hardHit: hard && meets([...hard.spot, box.w, box.h], seatBox),
  movedHit: moved && [seatBox, ...top].some((b) => meets([...moved.spot, box.w, box.h], b) || meets([...moved.at, card.w, card.h], b)),
  ownHit: [stay, left, hard, moved].some((p) => meets([...p.spot, box.w, box.h], [...p.at, card.w, card.h])) }));
"""


@node
def test_the_choices_go_against_their_card_never_over_it_the_table_or_the_seat():
    source = "\n".join([MAP[MAP.index("  const TABLE_STEP"):MAP.index("  const DRAW_FOR")]] +
                       [_inner(name) for name in ("boxesMeet", "crosses", "tailEnds", "cardSpots", "choicesPlan")])
    out = subprocess.run(["node", "-"], input=(_PLAN % {"source": source}).encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    plans = json.loads(out.stdout.decode("utf-8"))
    stay = plans["stay"]
    assert stay["at"] == [220, 110] and stay["covered"] == 0  # The card stays where it was.
    # Not under it (they would come between it and its seat): on its right, 6px off, tops level.
    assert stay["spot"] == [386, 110]
    assert plans["left"]["at"] == [220, 110] and plans["left"]["spot"] == [74, 110] and plans["left"]["covered"] == 0
    assert not plans["ownHit"] and not plans["hardHit"] and not plans["movedHit"]
    assert plans["moved"]["at"] != [220, 110] and plans["moved"]["covered"] == 0
    assert plans["crowded"]["at"] == [220, 110] and plans["crowded"]["covered"] > 0
    for name in ("cardSpots", "choicesPlan"):
        for outside in ("overlay", "document", "style", "classList", "dataset"):
            assert outside not in _inner(name)


def test_the_paragraph_says_whose_it_is_and_shows_five_lines_where_there_is_room():
    opened = _inner("openChoices")
    # The name only; a bubble shown as spoken words adds its source's note (直し31-7).
    assert 'paragraph.append(div("whose", [seatOf(seatId).title, card.dataset.note].filter(Boolean).join("　")), text);' in opened
    assert "text.textContent = await app.paragraph(utteranceId);" in opened
    put = _inner("putChoices")
    # All of it first, then PARAGRAPH_LINES or more, only then fewer (it scrolls).
    assert "PARAGRAPH_STEPS.flatMap(" in put and "const PARAGRAPH_STEPS = [0, 8, PARAGRAPH_LINES, 4, 3, 2];" in MAP
    assert "putParagraphApart(paragraph, text, lineHeight, frameBox, [...hard, ...seatRoom(frameBox), boxIn(card, frameBox)], others)" in put
    assert "const PARAGRAPH_LINES = 5;" in MAP
    assert "widths.map((w) => [\"\", false, lines, w])" in put  # Wider, where that finds room.
    assert "text.style.maxHeight = lines ?" in put
    assert ".map-choices .paragraph .text { overflow: auto; }" in CSS
    assert "max-height: 7.6em" not in CSS and "max-height: 84px" not in CSS


def test_choices_with_no_tail_keep_off_the_pressed_seats_ring_and_the_paragraph_off_the_seats():
    put = _inner("putChoices")
    assert 'ring: halo ? halo.width / 2 + 2 : seat.r' in put
    plan = _inner("choicesPlan")
    assert 'if (!seen && needTail !== "near" && Math.hypot(' in plan and "< (card.ring || card.r)) continue;" in plan
    # Only as the last resorts may they touch the ring.
    assert '[block, top, "near"]' in put
    room = _inner("seatRoom")
    assert "SEAT_ROOM" in room and ".shape" in room


def test_where_no_card_spot_has_room_the_paragraph_still_goes_apart_not_over_the_table():
    # 1366x650, a seat by the table's edge with no card spot (直し27, the
    # screen check): the choices go by their card as before, and the
    # paragraph on paper of its own; in them only where that covers none
    # of hard and shows PARAGRAPH_LINES or more.
    put = _inner("putChoices")
    last = put[put.index("// No such spot: as before"):]
    assert "const inOwn = chosen.clear ? seen(chosen.way[2]) : -1;" in last
    assert "if (!paragraph.hidden && inOwn < PARAGRAPH_LINES) {" in last
    assert "const closedChosen = byOwn(closed);" in last
    assert last.index("putParagraphApart(") < last.index("if (!apart) place(chosen);")  # Laying again would undo its lines.
    assert "if (apart) for (const other of shown) if (overlaps(paragraph, other))" in last
