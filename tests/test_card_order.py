"""At the round table, when the round has a split, the lamp cards that find
room are taken from both sides by turns (直し27-2): side_a, side_b, side_a,
… each side in seat_order; when a side has no one left, the other side's;
then the seats on neither side. Without a split, seat_order as before. Tab
still goes through the cards in seat_order."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_both_sides_by_turns_then_the_rest():
    program = _inner("cardOrder") + """
const order = ["s1", "s2", "s3", "s4", "s5", "s6", "s7"];
process.stdout.write(JSON.stringify({
  none: cardOrder(order, null),
  turns: cardOrder(order, [new Set(["s1", "s2"]), new Set(["s3", "s4"])]),
  short: cardOrder(order, [new Set(["s5"]), new Set(["s2", "s3", "s6"])]),
  both: cardOrder(order, [new Set(["s1", "s4"]), new Set(["s4", "s2"])]),
}));"""
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    out = json.loads(done.stdout.decode("utf-8"))
    assert out["none"] == ["s1", "s2", "s3", "s4", "s5", "s6", "s7"]
    assert out["turns"] == ["s1", "s3", "s2", "s4", "s5", "s6", "s7"]
    # One on side_a: then side_b's, in seat_order, then the rest.
    assert out["short"] == ["s5", "s2", "s3", "s6", "s1", "s4", "s7"]
    assert out["both"] == ["s1", "s2", "s4", "s3", "s5", "s6", "s7"]  # A seat on both sides counts on side_a.
    for outside in ("document", "overlay", "dataset"):
        assert outside not in _inner("cardOrder")


def test_the_table_puts_the_cards_in_that_order_and_tab_keeps_seat_order():
    opened = MAP[MAP.index("async function openTable("):MAP.index("function tableBubble(")]
    assert "const rank = cardOrder(order, sides);" in opened
    assert "card.dataset.rank = String(rank.indexOf(id));" in opened
    assert "order.forEach((id, k) => {" in opened  # The page (and Tab) in seat_order.
    place = _inner("placeTableBubbles")
    assert '.sort((x, y) => Number(x.dataset.rank) - Number(y.dataset.rank))' in place
    assert "sides: split ? [split.a, split.b] : null" in _inner("seating")
