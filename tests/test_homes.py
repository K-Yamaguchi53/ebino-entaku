"""直し33-3: each seat has its home, worked out from the seat table each time:
地域で働く大人 at their places on the map, 県外・海外に出た人 by a way out at the
map's edge, 探究をした先輩 at the school's windows (more than the windows: on
the ground), 外から来た大人・先生 and whoever has no room elsewhere on the
ground, one to a square. Each home has its name where it is (no boxes in
the map's corners). With the invented seats (adults 103, seniors 45, gone
out 10, from outside 1) no two seats overlap, on the five screens, with the
school's picture's windows or the plain yard's."""

import json
import random
import re
import shutil
import subprocess

import pytest
from conftest import make_seat
from test_relief import MAP, VIEWBOX, setup_of

from ebino import app as app_module
from ebino.relief import load_relief
from ebino.session import Library

STATIC = app_module.STATIC_DIR
SCRIPT = (STATIC / "map.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
ROOMS = {"1920x1080": (1676, 886), "1536x760": (1292, 565), "1366x650": (1122, 491),
         "1180x820": (936, 614), "768x1024": (736, 684)}


def _inner(name):
    start = SCRIPT.index(f"function {name}(")
    return SCRIPT[start:SCRIPT.index("\n  }\n", start) + 5]


def _consts(*names):
    return "\n".join(re.search(rf"const {name} = [^;]+;", SCRIPT).group(0) for name in names)


def _invented(counts=(103, 45, 10, 1)):
    rng = random.Random(5)
    places = list(MAP.places["えびの市"])
    adults, seniors, out, outside = counts
    seats = [make_seat(seat_id=f"A{n:03}", title=f"架空の仕事{n}", company="", display_name="",
                       district="えびの市大字" + rng.choice(places[:24])) for n in range(adults - 3)]
    seats += [make_seat(seat_id=f"A9{n}", title="隣の町の仕事", company="", display_name="", district=d)
              for n, d in enumerate(["小林市細野", "湧水町栗野", "伊佐市大口里"])]
    seats += [make_seat(seat_id=f"P{n:03}", kind="poster", title=f"架空の先輩{n}", company="", display_name="",
                        district="") for n in range(seniors)]
    seats += [make_seat(seat_id=f"C{n:02}", kind="cross", title=f"架空の外{n}", company="", display_name="",
                        district="") for n in range(out)]
    seats += [make_seat(seat_id=f"O{n:02}", kind="outsider_teacher", title=f"外から来た大人{n}", company="",
                        display_name="", district="") for n in range(outside)]
    return seats


PLACES = r"""
const setup = %(setup)s, rooms = %(rooms)s, picture = %(picture)s;
let yardPicture = picture;
const map = setup.map;
%(consts)s
%(source)s
const out = {};
for (const [name, [w, h]] of Object.entries(rooms)) {
  const base = reliefView(map.relief), model = yardModel();
  const laid = compose({ w, h }, base.W, base.H, model);
  const unit = laid.W / w, [ox, oy] = laid.map;
  const P = (...at) => { const [x, y] = base.proj(...at); return [x + ox, y + oy]; };
  const seats = setup.seats.filter((s) => s.x !== undefined).map((s) => ({ id: s.seat_id, kind: s.kind,
    at: s.outer ? null : P(s.x, s.y, 1.5) }));
  // A point's radius on screen at the whole drawing (pointScale and shape()).
  const r = Math.max(MIN_POINT_PX, POINT_R * base.S / unit);
  const homes = homesOf(seats, { mapBox: [ox, oy, base.W, base.H], yard: { ...laid.yard, model }, unit, r: r * unit });
  const spots = seats.map((s) => ({ id: s.id, kind: s.kind, onMap: Boolean(s.kind === "adult" && s.at),
    px: homes.spots[s.id].map((v) => v / unit) }));
  let overlaps = 0, outside = 0, least = Infinity;
  for (let i = 0; i < spots.length; i++) {
    const [x, y] = spots[i].px;
    if (x < r || y < r || x > w - r || y > h - r) outside += 1;
    for (let j = i + 1; j < spots.length; j++) {
      if (spots[i].onMap && spots[j].onMap) continue;  // Two places on the map: seat_map.py's.
      const d = Math.hypot(x - spots[j].px[0], y - spots[j].px[1]);
      least = Math.min(least, d);
      if (d < 2 * r) overlaps += 1;
    }
  }
  const box = (ids) => ids.map((id) => homes.spots[id]);
  const yardBox = [laid.yard.x, laid.yard.y, laid.yard.x + model.width * laid.yard.k, laid.yard.y + model.height * laid.yard.k];
  const inYard = (p) => p[0] >= yardBox[0] && p[0] <= yardBox[2] && p[1] >= yardBox[1] && p[1] <= yardBox[3];
  const inMap = (p) => p[0] >= ox && p[0] <= ox + base.W && p[1] >= oy && p[1] <= oy + base.H;
  out[name] = { counts: homes.counts, overlaps, outside, least: least / r, names: homes.names.map((n) => n.kind),
    crossInMap: box(spots.filter((s) => s.kind === "cross").map((s) => s.id)).every(inMap),
    seniorsInYard: box(spots.filter((s) => s.kind === "poster").map((s) => s.id)).every(inYard),
    outsideInYard: box(spots.filter((s) => s.kind === "outsider_teacher").map((s) => s.id)).every(inYard) };
}
process.stdout.write(JSON.stringify(out));
"""


def _homes(seats, picture=None):
    lib = Library.build(seats, [], {}, False, map_data=MAP, relief_data=load_relief(VIEWBOX))
    setup = setup_of(lib)
    names = ["reliefView", "yardModel", "compose", "homesOf", "groundSquares"]
    program = PLACES % {"setup": json.dumps(setup, ensure_ascii=False), "rooms": json.dumps(ROOMS),
                        "picture": json.dumps(picture),
                        "consts": _consts("MAP_SHARE", "YARD_SHARE", "MAP_SHARE_UP", "ROOM_GAP", "UPRIGHT_UNDER",
                                          "PLAIN_YARD", "HOME_STEP", "POINT_R", "MIN_POINT_PX"),
                        "source": "".join(_inner(name) for name in names)}
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=60)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return json.loads(done.stdout.decode("utf-8"))


# The school's picture as sprite_school.py drew it: two rows of 20 windows on
# the ring's roof, the ground's four corners (picture px; the numbers only
# need be like the picture's).
RING = [[round(700 + rr * __import__("math").cos(__import__("math").radians(8 + 164 * i / 19)), 1),
         round(330 - rr * 0.79 * __import__("math").sin(__import__("math").radians(8 + 164 * i / 19)), 1)]
        for rr in (215, 262) for i in range(20)]
PICTURE = {"image": "/school/school_yard.png", "width": 1413, "height": 737, "picture": True,
           "windows": [[x + 383, y + 30] for x, y in RING], "field": [[30, 8], [715, 18], [693, 728], [8, 716]]}


@node
@pytest.mark.parametrize("picture", [None, PICTURE], ids=["plain", "picture"])
def test_every_invented_seat_has_a_home_and_none_overlap_on_the_five_screens(picture):
    homes = _homes(_invented(), picture)
    assert set(homes) == set(ROOMS)
    for name, one in homes.items():
        counts = one["counts"]
        # 45 seniors, 40 windows: 5 on the ground, with the one from outside
        # and any adult whose place the map does not have.
        # At most one to a window (fewer where windows are too near together on screen).
        assert counts["gate"] == 10 and 30 <= counts["windows"] <= 40, name
        assert counts["map"] >= 100 and counts["ground"] == 1 + (45 - counts["windows"]) + (103 - counts["map"]), name
        assert counts["map"] + counts["gate"] + counts["windows"] + counts["ground"] == 159, name
        assert one["overlaps"] == 0 and one["outside"] == 0, (name, one["least"])
        assert one["crossInMap"] and one["seniorsInYard"] and one["outsideInYard"], name
        assert sorted(one["names"]) == ["adult", "cross", "outsider_teacher", "poster"], name


@node
def test_more_than_the_way_out_and_the_windows_hold_go_to_the_ground():
    homes = _homes(_invented((20, 70, 25, 3)))
    for name, one in homes.items():
        counts = one["counts"]
        assert counts["gate"] == 20 and counts["windows"] <= 40, name
        assert counts["ground"] == (70 - counts["windows"]) + (25 - 20) + 3 + (20 - counts["map"]), name
        assert one["overlaps"] == 0, (name, one["least"])


def test_the_homes_come_from_the_seat_table_each_time_and_the_corners_boxes_are_gone():
    drawn = _inner("draw")
    assert "const homes = homesOf(placed.map((seat) => ({ id: seat.seat_id, kind: seat.kind," in drawn
    assert "shelf" not in SCRIPT.lower()
    assert ".shelf-" not in CSS
    # Each home's name in the seat list's words for that kind, drawn where it is.
    assert "const words = app.state.kinds[kind];" in drawn and 'layer("home-names")' in drawn
    # The marks that stay go on a seat at its home as anywhere: the same point.
    refreshed = _inner("refresh")
    for mark in ('"met"', '"silent"', '"carded"'):
        assert f"node.classList.toggle({mark}" in refreshed
    # The words a card keeps off include the homes' names.
    assert ".home-names text" in _inner("fixedBoxes") and ".home-names text" in _inner("placeAskMarks")
