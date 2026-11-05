"""直し35-2: each seat has its home, worked out from the seat table each time,
on the map that fills the room with the school on it, put larger (直し37-1:
SCHOOL_SCALE times its real size):
地域で働く大人 at their places (with none, together where the map is free,
their points dotted); 県外・海外に出た人 at a way out on the map's edge (to
海外 by the south, else to 県外 by the north), beside the arrow going out;
外から来た大人・先生 at the way to 県外, beside the arrow coming in;
探究をした先輩 at the school's windows, then inside its track, then on its
ground. With the invented seats (adults 103, two with no place; seniors 45;
gone out 10, three abroad; from outside 1) no two seats seen overlap on the
five screens at the whole map (the seniors folded into their count), and
once the seniors come out at their windows, no two of them overlap there."""

import json
import math
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


def _invented(counts=(103, 45, 10, 1), abroad=3, no_place=2):
    rng = random.Random(5)
    places = list(MAP.places["えびの市"])
    adults, seniors, out, outside = counts
    seats = [make_seat(seat_id=f"A{n:03}", title=f"架空の仕事{n}", company="", display_name="",
                       district="" if n < no_place else "えびの市大字" + rng.choice(places[:24])) for n in range(adults - 3)]
    seats += [make_seat(seat_id=f"A9{n}", title="隣の町の仕事", company="", display_name="", district=d)
              for n, d in enumerate(["小林市細野", "湧水町栗野", "伊佐市大口里"])]
    seats += [make_seat(seat_id=f"P{n:03}", kind="poster", title=f"架空の先輩{n}", company="", display_name="",
                        district="") for n in range(seniors)]
    seats += [make_seat(seat_id=f"C{n:02}", kind="cross", title=f"架空の外{n}", company="", display_name="",
                        district="", crossing_to="海外" if n >= out - abroad else "県外") for n in range(out)]
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
  const laid = compose({ w, h }, base.W, base.H);
  const unit = laid.W / w, [ox, oy] = laid.map;
  const P = (...at) => { const [x, y] = base.proj(...at); return [x + ox, y + oy]; };
  const yard = { ...schoolOnMap(P(map.school.x, map.school.y, 0), model, base.S / M_PER_UNIT), model };
  const seats = setup.seats.filter((s) => s.x !== undefined).map((s) => ({ id: s.seat_id, kind: s.kind,
    abroad: Boolean(s.abroad), at: s.outer ? null : P(s.x, s.y, 1.5) }));
  // A point's radius on screen at the whole drawing (pointScale and shape()).
  const r = Math.min(Math.max(MIN_POINT_PX, POINT_R * base.S / unit), MAX_POINT_PX);
  const avoid = map.places.map((place) => P(place.x, place.y, 2));
  const homes = homesOf(seats, { mapBox: [ox, oy, base.W, base.H], yard, unit, r: r * unit, avoid,
    middle: P(...centroid(map.boundary), 0) });
  const px = (id) => homes.spots[id].map((v) => v / unit);
  // At the whole map: every seat seen (the seniors are folded into their count).
  const seen = seats.filter((s) => !homes.school.has(s.id)).map((s) => ({ ...s, px: px(s.id),
    onMap: Boolean(s.kind === "adult" && s.at) }));
  let overlaps = 0, outside = 0, least = Infinity;
  for (let i = 0; i < seen.length; i++) {
    const [x, y] = seen[i].px;
    if (x < r || y < r || x > w - r || y > h - r) outside += 1;
    for (let j = i + 1; j < seen.length; j++) {
      if (seen[i].onMap && seen[j].onMap) continue;  // Two places on the map: seat_map.py's.
      const d = Math.hypot(x - seen[j].px[0], y - seen[j].px[1]);
      least = Math.min(least, d);
      if (d < 2 * r) overlaps += 1;
    }
  }
  // Where the seniors come out: the windows a senior's width apart on screen.
  const zoom = unit * 2 * SCHOOL_R_PX / homes.seniorStep;
  const school = [...homes.school].map((id) => homes.spots[id].map((v) => v / unit * zoom));
  let schoolOverlaps = 0;
  for (let i = 0; i < school.length; i++) for (let j = i + 1; j < school.length; j++) {
    if (Math.hypot(school[i][0] - school[j][0], school[i][1] - school[j][1]) < 2 * SCHOOL_R_PX - 0.01) schoolOverlaps += 1;
  }
  // 直し37-1: no senior on an adult's place where the school lies under it.
  const places = seats.filter((s) => s.kind === "adult" && s.at).map((s) => s.at);
  const onAdults = [...homes.school].filter((id) => places.some((a) =>
    Math.hypot(a[0] - homes.spots[id][0], a[1] - homes.spots[id][1]) < homes.seniorStep * SCHOOL_CLEAR)).length;
  const inMap = (p) => p[0] >= ox && p[0] <= ox + base.W && p[1] >= oy && p[1] <= oy + base.H;
  const kindsAt = (test) => seats.filter((s) => !(s.kind === "adult" && s.at) && test(homes.spots[s.id]));
  const nearGate = (gate) => (p) => Math.hypot(p[0] - gate[0], p[1] - gate[1]) < 8 * HOME_STEP * unit;
  out[name] = { counts: homes.counts, overlaps, outside, least: least / r, schoolOverlaps, zoom, onAdults,
    names: homes.names.map((n) => n.kind).sort(), trackRoom: homes.trackRoom,
    allInMap: seats.every((s) => inMap(homes.spots[s.id])),
    north: kindsAt(nearGate(homes.gates.out)).map((s) => s.kind + (s.abroad ? "!" : "")).sort(),
    south: kindsAt(nearGate(homes.gates.abroad)).map((s) => s.kind + (s.abroad ? "!" : "")).sort(),
    noPlace: [...homes.noPlace].sort() };
}
process.stdout.write(JSON.stringify(out));
"""


def _homes(seats, picture=None):
    lib = Library.build(seats, [], {}, False, map_data=MAP, relief_data=load_relief(VIEWBOX))
    setup = setup_of(lib)
    names = ["centroid", "within", "reliefView", "yardModel", "compose", "schoolOnMap", "windowStep", "homesOf",
             "schoolSquares", "clearOf", "freeBlock", "trackOn"]
    program = PLACES % {"setup": json.dumps(setup, ensure_ascii=False), "rooms": json.dumps(ROOMS),
                        "picture": json.dumps(picture),
                        "consts": _consts("UPRIGHT_UNDER", "AI_BAND_UP", "SCHOOL_SCALE", "SCHOOL_CLEAR", "M_PER_UNIT", "PLAIN_YARD", "TRACK", "HOME_STEP",
                                          "POINT_R", "MIN_POINT_PX") + "\n" +
                                  "const PLAIN_PX_PER_M = 520 / 96.2, PLAIN_RING = [1020, 290];\n"
                                  "const SCHOOL_R_PX = 5, MAX_POINT_PX = 10;",
                        "source": "".join(_inner(name) for name in names)}
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=60)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return json.loads(done.stdout.decode("utf-8"))


# The school's picture as sprite_school.py drew it (直し35-1): two rows of 20
# windows on the ring's roof, the ground's four corners, the ring's middle and
# its scale (picture px; the numbers only need be like the picture's).
RING = [[round(700 + rr * __import__("math").cos(__import__("math").radians(8 + 164 * i / 19)), 1),
         round(330 - rr * 0.79 * __import__("math").sin(__import__("math").radians(8 + 164 * i / 19)), 1)]
        for rr in (215, 262) for i in range(20)]
PICTURE = {"image": "/school/school_yard.png", "width": 1413, "height": 782, "picture": True,
           "windows": [[x + 383, y + 30] for x, y in RING], "field": [[71, 40], [724, 53], [702, 730], [49, 716]],
           "ring": [1081, 368], "px_per_m": 6.79}


@node
@pytest.mark.parametrize("picture", [None, PICTURE], ids=["plain", "picture"])
def test_every_invented_seat_has_a_home_and_none_overlap_on_the_five_screens(picture):
    homes = _homes(_invented(), picture)
    assert set(homes) == set(ROOMS)
    for name, one in homes.items():
        counts = one["counts"]
        # Two with no district, and any whose district the map does not have.
        assert counts["map"] + counts["noPlace"] == 103 and counts["noPlace"] >= 2, name
        assert counts["out"] == 7 and counts["abroad"] == 3 and counts["in"] == 1, name
        # 45 seniors, 40 windows less those under an adult's place (直し37-1:
        # the school put larger lies under some; 2 here), the rest inside the track.
        assert counts["windows"] + counts["track"] == 45 and counts["field"] == 0, name
        assert 36 <= counts["windows"] <= 40, name
        assert one["overlaps"] == 0 and one["outside"] == 0, (name, one["least"])
        assert one["schoolOverlaps"] == 0, name
        assert one["onAdults"] == 0, name  # 直し37-1: a window or square under an adult's place passed over.
        assert one["allInMap"], name
        assert one["north"] == ["cross"] * 7 + ["outsider_teacher"], name  # Out to 県外, and in from outside.
        assert one["south"] == ["cross!"] * 3, name  # Out to 海外.
        assert {"A000", "A001"} <= set(one["noPlace"]), name
        assert one["names"] == ["adult", "cross", "cross", "outsider_teacher", "poster"], name
        assert one["trackRoom"] >= 5, name


@node
def test_more_than_the_windows_go_inside_the_track_then_round_it():
    homes = _homes(_invented((20, 70, 25, 3), abroad=10, no_place=6))
    for name, one in homes.items():
        counts = one["counts"]
        assert counts["out"] == 15 and counts["abroad"] == 10 and counts["in"] == 3 and counts["noPlace"] >= 6, name
        assert counts["windows"] == 40 and counts["track"] == min(30, one["trackRoom"]), name
        assert counts["track"] + counts["field"] == 30, name
        assert one["overlaps"] == 0 and one["schoolOverlaps"] == 0, (name, one["least"])


@node
def test_the_seniors_come_out_within_ten_times_and_three_to_six_presses_and_never_both_or_neither():
    # 直し37-1: with the school put larger, the zoom where they come out is
    # at most 10 (the relief keeps its shape) and 3 to 6 presses of ＋ (1.4
    # each) from the whole map, picture or plain, at the five sizes.
    for picture in (PICTURE, None):
        for name, one in _homes(_invented(), picture).items():
            zoom = one["zoom"]
            presses = math.ceil(math.log(zoom) / math.log(1.4) - 1e-9)
            assert zoom <= 10 and 3 <= presses <= 6, (name, picture is None, zoom, presses)
    fold = _inner("foldSchool")
    assert "const out = seniorsOut(perPx);" in fold and "label.hidden = out;" in fold
    assert 'frame.classList.toggle("seniors-out", out);' in fold
    assert "return view.seniorStep / perPx >= 2 * SCHOOL_R_PX;" in _inner("seniorsOut")
    assert ".map-frame:not(.seniors-out) .pt.school-home" in CSS
    # The nearest zoom is nearer than where they come out.
    assert "closest: Math.max(CLOSEST, seniorZoom * CLOSEST_MORE)" in _inner("draw")
    assert "view.W / view.closest" in _inner("clampView")


def test_the_homes_come_from_the_seat_table_each_time_and_the_corners_boxes_are_gone():
    drawn = _inner("draw")
    assert "const homes = homesOf(placed.map((seat) => ({ id: seat.seat_id, kind: seat.kind, abroad: Boolean(seat.abroad)," in drawn
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


def test_only_who_went_abroad_is_marked_so_and_nothing_more():
    seats = [make_seat(seat_id="C1", kind="cross", title="架空の外1", company="", display_name="", district="", crossing_to="海外"),
             make_seat(seat_id="C2", kind="cross", title="架空の外2", company="", display_name="", district="", crossing_to="県外"),
             make_seat(seat_id="C3", kind="cross", title="架空の外3", company="", display_name="", district="", crossing_to=""),
             make_seat(seat_id="A1", kind="adult", title="架空の仕事", company="", display_name="", district="",
                       crossing_to="海外")]
    views = {view["seat_id"]: view for view in Library.build(seats, [], {}, False).seat_list()}
    assert views["C1"]["abroad"] is True
    assert all("abroad" not in views[seat] for seat in ("C2", "C3", "A1"))
    assert "海外" not in json.dumps(views, ensure_ascii=False)  # A mark only, not the table's words.
