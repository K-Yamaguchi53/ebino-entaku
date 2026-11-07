"""直し53 段4 (the teacher's screen): at the table an empty chair 「？」 sat
half over a gathered seat's mark. The chairs now go, nearest their own place
round the front of the table, where their press square is clear of every
gathered seat's mark and name and of the other chairs. The screen check
counts them ("chair over token N")."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ebino import app as app_module

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CHECK = (Path(__file__).resolve().parent.parent / "tools" / "check_one_screen.js").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def test_the_chairs_are_put_after_the_gathered_seats_and_the_press_stays_44px():
    open_table = _inner("openTable")
    assert open_table.index("const spots = onArc(gatherSpots(") < open_table.index("const chairsAt = chairSpots(")
    assert 'sitting.group === "front" ? chairsAt[sitting.id]' in open_table
    assert "const HIT_PX = 22;" in MAP  # The press square, as it was.
    assert "CHAIR_BOX = [-HIT_PX - 2, -HIT_PX - 2, HIT_PX + 2, HIT_PX + 2]" in MAP


def test_the_screen_check_counts_chairs_over_the_seats():
    assert "chair over token ${t.chair}" in CHECK
    assert '#map-svg .chair.ready circle' in CHECK and ".table-label:not(.empty):not(.unplaced)" in CHECK


PROGRAM = """
const HIT_PX = 22, SEAT_OUT = 48, TABLE_RX = 150, TABLE_RY = 110, TABLE_LIFT = 7;
const view = { unit: 1, W: 1600, H: 1000 };
%(source)s
const center = { x: 0, y: 0, level: 0, proj: (x, y) => [800 + x, 500 + y] };
// The front is 90 deg (south); gathered seats sit right where the chairs would.
const chairs = [70, 80, 90, 100, 110].map((angle, k) => ({ id: "c" + k, angle }));
const gathered = [onTable(center, 80, SEAT_OUT), onTable(center, 100, SEAT_OUT), onTable(center, 90, SEAT_OUT + 34)];
const at = chairSpots(chairs, gathered, center);
process.stdout.write(JSON.stringify({ at, gathered }));
"""


@node
def test_no_chair_box_meets_a_seat_or_another_chair():
    source = MAP[MAP.index("  const TOKEN_BOX = "):MAP.index("  function onTable(")] + _inner("onTable")
    done = subprocess.run(["node", "-"], input=(PROGRAM % {"source": source}).encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    got = json.loads(done.stdout)
    box = lambda at, l, t, r, b: (at[0] + l, at[1] + t, at[0] + r, at[1] + b)
    hit = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    seats = [box(at, -60, -28, 60, 46) for at in got["gathered"]]
    chairs = [box(at, -24, -24, 24, 24) for at in got["at"].values()]
    assert len(chairs) == 5
    assert not any(hit(c, s) for c in chairs for s in seats)
    assert not any(hit(a, b) for i, a in enumerate(chairs) for b in chairs[i + 1:])
    assert all(c[0] >= 8 and c[1] >= 8 and c[2] <= 1592 and c[3] <= 992 for c in chairs)
