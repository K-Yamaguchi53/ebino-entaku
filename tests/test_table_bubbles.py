"""The round table's lamp cards (直し26-1): once the seats are at the table,
each seat that spoke shows its lamp card (the same words as on the map, cut
at BUBBLE_CHARS) with a tail pointing at its chair. They stay until
「地図にもどす」 or the next round. A seat with a card up has no name label.
They keep off one another, the table's top, the seats and chairs, the labels
and the frame; what has no room is left out, and its seat shows it when
pressed. The lamp cards on the whole map before the table stay as they were."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module

SCRIPT = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _inner_function(script, name):
    start = script.index(f"function {name}(")
    return script[start:script.index("\n  }\n", start) + 5]


def _consts():
    return SCRIPT[SCRIPT.index("  const NS ="):SCRIPT.index("  let map = null;")]


def _run(program):
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=60)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return json.loads(done.stdout.decode("utf-8"))


def test_the_table_opens_with_each_speakers_card_in_seat_order_and_the_map_cards_stay():
    table = _inner_function(SCRIPT, "openTable")
    assert "order.forEach((id, k) =>" in table
    assert "overlay.append(tableBubble(id, first[id], token.at, k), seatPress(id, token.at))" in table
    # The same words as the short card on the map: one place cuts them.
    bubble = _inner_function(SCRIPT, "bubble")
    assert 'div("voice", voiceOf(quote)), div("who", whoOf(seat))' in bubble
    assert "BUBBLE_FOR" in bubble  # The card on the whole map still goes.
    assert 'div("voice", voiceOf(quote)), div("who", whoOf(seatOf(seatId)))' in _inner_function(SCRIPT, "tableBubble")
    assert "BUBBLE_CHARS" in _inner_function(SCRIPT, "voiceOf")


def test_the_cards_stay_until_the_map_comes_back_or_the_next_round():
    # Moving the camera, a drag or a new size puts them again; it never takes them away.
    assert ".table-bubble" not in _inner_function(SCRIPT, "place")
    relayout = _inner_function(SCRIPT, "relayout")
    assert 'querySelectorAll(".map-bubble")) node.remove()' in relayout and "placeTableBubbles(" in relayout
    assert ".table-bubble" not in _inner_function(SCRIPT, "settleSoon")
    for name in ("clearRound", "closeTable"):
        assert ".table-bubble, .seat-press" in _inner_function(SCRIPT, name)
    assert "opened = null;" in _inner_function(SCRIPT, "clearTable")


def test_a_seat_with_its_card_up_has_no_name_label_and_one_without_takes_a_press():
    relayout = _inner_function(SCRIPT, "relayout")
    assert 'if (named.has(label.dataset.seat)) label.classList.add("unplaced")' in relayout
    assert "placeSeatPresses(planned);" in relayout
    press = _inner_function(SCRIPT, "seatPress")
    assert "node.tabIndex = 0;" in press and 'setAttribute("role", "button")' in press
    assert "pressable(node, () => {" in press and "opened = seatId;" in press
    assert "pointer-events: auto" in CSS[CSS.index(".seat-press {"):]
    assert ".seat-press:focus-visible { box-shadow: 0 0 0 2px var(--lamp); }" in CSS


def test_a_tail_crosses_no_label_put_before_and_the_labels_after_keep_off_it():
    place = _inner_function(SCRIPT, "placeTableBubbles")
    assert 'topStrips(tableTop.map(([x, y]) => toFrame(x, y))) : [], before)' in place
    assert "taken.push(box, ...(ends ? alongTail(ends) : []))" in place


def test_with_less_motion_the_cards_come_at_once():
    reduced = CSS[CSS.index("@media (prefers-reduced-motion: reduce)"):]
    assert ".table-bubble { animation: none !important; }" in reduced
    rules = CSS[CSS.index(".table-bubble {"):CSS.index(".split-tag {")]
    assert "#" not in rules and "var(--paper)" in rules and "var(--mincho)" in rules and "var(--gothic)" in rules


def test_the_planner_reads_only_what_it_is_given():
    plan = "".join(_inner_function(SCRIPT, name) for name in ("planTableBubbles", "tableBubbleSpot", "tailEnds", "crosses"))
    for outside in ("overlay", "dataset", "document", "vb", "style", "classList", "svg"):
        assert outside not in plan


_PLAN = """
%(consts)s
%(source)s
const frame = { w: 900, h: 480 };
// A table's top in the middle, two seats at its sides, one more at the back.
const top = [[330, 180, 240, 120]];
const seats = [[310, 240], [590, 240], [450, 150]];
const shapes = seats.map(([x, y]) => [x - 8, y - 8, 16, 16]);
const card = (px, py) => ({ w: 180, h: 70, px, py, gap: 30, r: 14, inView: true });
const items = seats.map(([x, y]) => card(x, y));
const spots = planTableBubbles(frame, items, [...top, ...shapes], [...top, ...shapes], 140);
// A frame with room for one card only.
const small = planTableBubbles({ w: 200, h: 260 }, [card(100, 40), card(100, 200)], [[90, 30, 20, 20], [90, 190, 20, 20]],
  [[90, 30, 20, 20], [90, 190, 20, 20]], 60);
const tails = spots.map((spot, k) => spot && tailEnds([spot[0], spot[1], 180, 70], ...seats[k], 14));
process.stdout.write(JSON.stringify({
  spots, tails, small,
  again: planTableBubbles(frame, items, [...top, ...shapes], [...top, ...shapes], 140),
  through: crosses([0, 0], [10, 10], [4, 4, 2, 2]), past: crosses([0, 0], [10, 0], [4, 4, 2, 2]),
  away: planTableBubbles(frame, [{ ...card(100, 100), inView: false }], [], [], 140),
}));
"""


@node
def test_the_cards_keep_off_the_table_the_seats_and_one_another_with_tails_to_their_own_seat():
    names = ("boxesMeet", "crosses", "tailEnds", "planTableBubbles", "tableBubbleSpot")
    out = _run(_PLAN % {"consts": _consts(), "source": "".join(_inner_function(SCRIPT, n) for n in names)})
    hit = lambda a, b: a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
    seats = [[310, 240], [590, 240], [450, 150]]
    fixed = [[330, 180, 240, 120]] + [[x - 8, y - 8, 16, 16] for x, y in seats]
    boxes = [[left, top, 180, 70] for left, top in out["spots"]]
    assert all(out["spots"])  # Room for all three.
    for k, box in enumerate(boxes):
        assert 4 <= box[0] and 4 <= box[1] and box[0] + 180 <= 896 and box[1] + 70 <= 476
        assert not any(hit(box, f) for f in fixed)
        assert not any(hit(box, other) for j, other in enumerate(boxes) if j != k)
        (fx, fy), (qx, qy) = out["tails"][k]
        # The tail starts by its own seat (r from it) and ends on its own card's side.
        assert abs(((fx - seats[k][0]) ** 2 + (fy - seats[k][1]) ** 2) ** 0.5 - 14) < 0.01
        assert box[0] <= qx <= box[0] + 180 and box[1] <= qy <= box[1] + 70
        assert ((qx - fx) ** 2 + (qy - fy) ** 2) ** 0.5 >= 14  # Long enough to see.
    assert out["again"] == out["spots"]  # The same frame, the same places.
    assert out["through"] is True and out["past"] is False
    # No room: the second card is left out, not put over the first.
    assert out["small"][0] and out["small"][1] is None
    assert out["away"] == [None]  # Its seat off screen: no card.
