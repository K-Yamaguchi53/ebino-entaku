"""The map and the seats' points (SPEC 4, 5-1, 14-7, 14-65). An invented map:
a round basin, invented place names, invented seats."""

import json
import math
import random
import re

import pytest
from conftest import make_seat
from fake_client import FakeClient

from ebino import app as app_module
from ebino import seat_map
from ebino.app import App
from ebino.gate import Gate, NameList
from ebino.seat_map import POINT_GAP, MapData, find_place, load_map, parse_map, place_seats
from ebino.session import Library
from test_session import UTTERANCES

HOME = "えびの市"
CENTER = (500.0, 400.0)
RADIUS = 250.0
RING = [[round(CENTER[0] + RADIUS * math.cos(k * math.pi / 30), 1),
         round(CENTER[1] + RADIUS * math.sin(k * math.pi / 30), 1)] for k in range(60)]
RAW = {
    "source": "© OpenStreetMap contributors",
    "license": "ODbL 1.0",
    "fetched": "2026-11-04",
    "home": HOME,
    "viewbox": [0, 0, 1000, 800],
    "boundary": RING,
    "river": [[[200, 300], [500, 420], [800, 500]]],
    "places": {
        HOME: {
            "架空原": [450, 380, "village"],
            "字架空台": [560, 330, "neighbourhood"],
            "架空丘": [520, 500, "hamlet"],
            "架空町": [400, 300, "town"],
        },
        "小林市": {"架空野": [950, 400, "suburb"]},
        "湧水町": {"架空坂": [500, 790, "village"]},
    },
    "school": [470, 420],
}


def raw(**changes):
    value = json.loads(json.dumps(RAW))
    value.update(changes)
    return value


@pytest.fixture
def data() -> MapData:
    return parse_map(raw())


def seats(*specs):
    return [make_seat(seat_id=seat_id, kind=kind, district=district, title=f"肩書き{seat_id}")
            for seat_id, kind, district in specs]


def apart(points):
    points = list(points)
    return min(math.hypot(a.x - b.x, a.y - b.y) for i, a in enumerate(points) for b in points[i + 1:])


def rim_distance(point):
    return math.hypot(point.x - CENTER[0], point.y - CENTER[1])


# --- finding the place ---

def test_the_city_name_and_oaza_are_taken_off_then_the_name_must_match(data):
    assert find_place("えびの市架空原", data) == (HOME, "架空原")
    assert find_place("えびの市大字架空原", data) == (HOME, "架空原")
    assert find_place("えびの市大字架空原北", data) is None  # Not exact: not found.
    assert find_place("架空原", data) is None  # No municipality at the head.
    assert find_place("えびの市", data) is None


def test_aza_is_put_on_or_taken_off_and_no_further(data):
    assert find_place("えびの市架空台", data) == (HOME, "字架空台")
    assert find_place("えびの市大字字架空台", data) == (HOME, "字架空台")
    assert find_place("えびの市字架空丘", data) == (HOME, "架空丘")
    assert find_place("えびの市小字架空丘", data) is None


def test_a_place_in_the_next_town_is_found_in_that_town(data):
    assert find_place("小林市架空野", data) == ("小林市", "架空野")
    assert find_place("小林市架空原", data) is None


# --- placing ---

def test_a_seat_in_the_city_sits_at_its_place(data):
    placement = place_seats(data, seats(("S01", "adult", "えびの市大字架空原")))
    point = placement.points["S01"]
    assert (point.x, point.y, point.outer) == (450, 380, False)
    assert placement.not_found == 0


def test_a_seat_in_another_town_sits_just_beyond_the_rim_in_its_direction(data):
    placement = place_seats(data, seats(("S01", "adult", "小林市架空野"), ("S02", "adult", "湧水町架空坂")))
    east, south = placement.points["S01"], placement.points["S02"]
    assert not east.outer and not south.outer
    for point in (east, south):
        assert RADIUS < rim_distance(point) < RADIUS + 3 * POINT_GAP
    assert east.x > CENTER[0] + RADIUS and abs(east.y - CENTER[1]) < POINT_GAP
    assert south.y > CENTER[1] + RADIUS and abs(south.x - CENTER[0]) < POINT_GAP


def test_an_empty_district_and_a_place_not_found_go_on_the_shelves_off_the_basin(data):
    placement = place_seats(data, seats(("S01", "adult", "えびの市大字どこにもない"),
                                        ("P01", "poster", ""), ("S02", "adult", "架空市架空原")))
    assert placement.not_found == 2  # The empty one is not counted as not found.
    for seat_id in ("S01", "P01", "S02"):
        point = placement.points[seat_id]
        assert point.outer
        assert rim_distance(point) > RADIUS + seat_map.SHELF_CLEARANCE  # Off the basin.
        assert 0 <= point.x <= 1000 and 0 <= point.y <= 800
    assert placement.outer == 3
    # A place not found stays on its kind's shelf: one shelf for the adults.
    assert [shelf.kind for shelf in placement.shelves] == ["adult", "poster"]


def test_each_kind_has_one_shelf_with_its_seats_in_a_block(data):
    specs = [(f"P{n:02}", "poster", "") for n in range(6)] + [(f"C{n:02}", "cross", "") for n in range(4)]
    specs += [(f"O{n:02}", "outsider_teacher", "") for n in range(3)]
    placement = place_seats(data, seats(*reversed(specs)))
    assert [shelf.kind for shelf in placement.shelves] == ["poster", "cross", "outsider_teacher"]
    for shelf in placement.shelves:
        mine = [p for seat_id, p in placement.points.items() if seat_id[0] == shelf.kind[0].upper()]
        assert all(within(p, shelf.box) for p in mine)
        assert not any(within(p, shelf.box) for seat_id, p in placement.points.items()
                       if seat_id[0] != shelf.kind[0].upper())
        # A grid, POINT_GAP apart, in seat ID order row by row.
        first, second = mine[0], mine[1]
        assert (second.x - first.x, second.y - first.y) == (POINT_GAP, 0)


def within(point, box):
    x0, y0, x1, y1 = box
    return x0 <= point.x <= x1 and y0 <= point.y <= y1


def apart_boxes(a, b, gap=0.0):
    return a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1]


def _many_seats():
    """About 170 invented seats, much like the real ones: most in the city,
    a few in the next towns, many posters and some others with no place."""
    rng = random.Random(11)
    places = ["えびの市大字架空原", "えびの市架空台", "えびの市架空丘", "えびの市架空町", "小林市架空野"]
    specs = [(f"A{n:03}", "adult", rng.choice(places)) for n in range(95)]
    specs += [(f"A9{n:02}", "adult", "") for n in range(6)]
    specs += [(f"A8{n:02}", "adult", "えびの市大字どこにもない") for n in range(2)]
    specs += [(f"P{n:03}", "poster", "") for n in range(52)]
    specs += [(f"C{n:02}", "cross", "") for n in range(12)]
    specs += [(f"O{n:02}", "outsider_teacher", "") for n in range(3)]
    return specs


def test_with_about_170_seats_the_shelves_keep_off_each_other_and_the_basin_and_come_out_the_same(data):
    specs = _many_seats()
    assert len(specs) == 170
    first = place_seats(data, seats(*specs))
    shuffled = seats(*specs)
    random.Random(4).shuffle(shuffled)
    second = place_seats(data, shuffled)
    assert first.points == second.points and first.shelves == second.shelves  # The same every time.
    assert len(first.points) == 170
    assert apart(first.points.values()) >= POINT_GAP - 1e-6
    shelves = first.shelves
    assert [shelf.kind for shelf in shelves] == ["adult", "poster", "cross", "outsider_teacher"]
    for i, a in enumerate(shelves):
        for b in shelves[i + 1:]:
            assert apart_boxes(a.box, b.box, seat_map.SHELF_GAP)
    shelf_points = [p for p in first.points.values() if p.outer]
    assert len(shelf_points) == 6 + 2 + 52 + 12 + 3
    river = data.river[0]
    for shelf in shelves:
        x0, y0, x1, y1 = shelf.box
        corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
        assert x0 >= seat_map.SHELF_EDGE and y0 >= seat_map.SHELF_EDGE  # Inside the screen.
        assert x1 <= 1000 - seat_map.SHELF_EDGE and y1 <= 800 - seat_map.SHELF_EDGE
        assert not any(seat_map.inside(c, data.boundary) for c in corners)  # Off the basin.
        assert seat_map.distance_to_ring(((x0 + x1) / 2, (y0 + y1) / 2), data.boundary) > 0
        assert not within(seat_map.SeatPoint(*data.school, False), shelf.box)  # Not on the school.
        for place in seat_map.place_names(data):
            assert not within(seat_map.SeatPoint(place["x"], place["y"], False), shelf.box)
        assert all(distance_to_line(c, river) > seat_map.RIVER_CLEARANCE for c in corners)
        for p in (p for p in first.points.values() if not p.outer):
            assert not within(p, shelf.box)  # No point on the basin side comes onto a shelf.
    for p in shelf_points:
        assert not seat_map.inside((p.x, p.y), data.boundary)
        assert rim_distance(p) > RADIUS + seat_map.SHELF_CLEARANCE
        assert distance_to_line((p.x, p.y), river) > seat_map.RIVER_CLEARANCE


def distance_to_line(point, line):
    return min(seat_map.distance_to_ring(point, (a, b)) for a, b in zip(line, line[1:]))


def test_with_no_room_for_a_block_the_seats_still_never_overlap():
    # A basin that fills the screen: no block fits; the seats still get points.
    full = raw(viewbox=[0, 0, 300, 260], boundary=[[5, 5], [295, 5], [295, 255], [5, 255]],
               river=[], school=None, places={HOME: {"架空原": [150, 130, "village"]}})
    placement = place_seats(parse_map(full), seats(*[(f"P{n:02}", "poster", "") for n in range(12)]))
    assert len(placement.points) == 12 and placement.shelves == []
    assert apart(placement.points.values()) >= POINT_GAP - 1e-6


def test_the_shelf_names_are_the_seat_lists_headings_from_the_same_place(data):
    library, _ = _library(data)
    setup = App(library, Gate(FakeClient([]), NameList.build(library.seats, {}))).setup()
    shelves = setup["map"]["shelves"]
    assert [shelf["kind"] for shelf in shelves] == ["poster"]
    assert set(shelves[0]) == {"kind", "box", "label"}  # The words are not here twice ...
    assert shelves[0]["kind"] in setup["kinds"]  # ... the screen takes them from setup's kinds.
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    # Each home's name (直し33-3), in setup's kinds' words.
    assert "const words = app.state.kinds[kind];" in script


def test_the_place_names_are_drawn_over_the_points_and_outlined():
    script = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    assert script.index('layer("points")') < script.index('layer("place-names")')
    css = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
    rule = re.search(r"\.place-names text \{([^}]*)\}", css).group(1)
    assert "paint-order: stroke" in rule and "fill: var(--soft)" in rule


def test_many_seats_at_one_place_never_overlap_and_come_out_the_same_every_time(data):
    specs = [(f"S{n:03}", "adult", "えびの市大字架空原") for n in range(40)]
    specs += [(f"T{n:03}", "adult", "えびの市架空台") for n in range(15)]  # A place nearby.
    specs += [(f"K{n:03}", "adult", "小林市架空野") for n in range(10)]
    specs += [(f"P{n:03}", "poster", "") for n in range(60)]
    first = place_seats(data, seats(*specs))
    shuffled = seats(*specs)
    random.Random(3).shuffle(shuffled)
    second = place_seats(data, shuffled)
    assert first.points == second.points
    assert len(first.points) == len(specs)
    assert apart(first.points.values()) >= POINT_GAP - 1e-6
    # Spread round the place, not scattered over the basin.
    near = [p for seat_id, p in first.points.items() if seat_id.startswith("S")]
    assert max(math.hypot(p.x - 450, p.y - 380) for p in near) < 6 * POINT_GAP


def test_a_seat_kept_off_the_map_by_coach_tsv_has_no_point():
    table = seats(("S01", "adult", "えびの市架空原"), ("O02", "outsider_teacher", ""))
    library = Library.build(table, [], {}, coach_seats={"O02": False}, map_data=parse_map(raw()))
    assert set(library.placement.points) == {"S01"}
    assert [seat["seat_id"] for seat in library.seat_list()] == ["S01"]


def test_the_crossing_line_is_there_only_when_a_seat_is_its_end(data):
    plain = seats(("S01", "adult", "えびの市架空原"), ("C01", "cross", ""))
    assert place_seats(data, plain).crossing is None
    marked = plain[:1] + [make_seat(seat_id="C01", kind="cross", district="", is_crossing_target=True)]
    placement = place_seats(data, marked)
    line = placement.crossing
    assert line["seat_id"] == "C01"
    end = placement.points["C01"]
    assert line["to"] == [end.x, end.y]
    x, y = line["from"]
    assert x in (0, 1000) or y in (0, 800)  # From the screen's edge: outside the basin.


# --- the start-up line ---

def test_the_start_up_line_has_counts_only(data):
    table = seats(("S01", "adult", "えびの市大字架空原"), ("S02", "adult", "えびの市大字ない所"),
                  ("P01", "poster", ""))
    library = Library.build(table, [], {}, map_data=data)
    line = library.map_report()
    assert line == "地図　点 3・外周 2・地名が見つからない 1"
    for word in ("架空原", "ない所", "S01", "S02", "P01"):
        assert word not in line


def test_no_map_says_so_in_one_line():
    assert Library.build(seats(("S01", "adult", "えびの市架空原")), [], {}).map_report() == "地図なし"


# --- no map, or a broken one ---

@pytest.mark.parametrize("content", [None, "", "{not json", "[]", json.dumps({"viewbox": [0, 0, 1, 1]}),
                                     json.dumps(raw(boundary=[[1, 2]])), json.dumps(raw(source=""))])
def test_a_missing_or_broken_map_file_gives_no_map_and_the_seat_list_stays(tmp_path, content):
    path = tmp_path / "map.json"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    assert load_map(path) is None
    library = Library.build(seats(("S01", "adult", "えびの市架空原")), [], {}, map_data=load_map(path))
    the_app = App(library, Gate(FakeClient([]), NameList.build(library.seats, {})))
    setup = the_app.setup()
    assert setup["map"] is None
    assert [seat["seat_id"] for seat in setup["seats"]] == ["S01"]
    assert "x" not in setup["seats"][0]


def test_library_load_starts_with_a_broken_map_file(tmp_path, monkeypatch):
    broken = tmp_path / "map.json"
    broken.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr(seat_map, "MAP_FILE", broken)
    assert seat_map.load_map() is None


# --- what setup sends ---

def _library(data, show_private=True):
    table = [make_seat(seat_id="S01", district="えびの市大字架空原"),
             make_seat(seat_id="S02", title="農家", company="架空農園", display_name="谷口さん",
                       district="小林市架空野"),
             make_seat(seat_id="P01", kind="poster", title="探究の先輩（川の水を調べた）", company="",
                       display_name="先輩", district="")]
    return Library.build(table, UTTERANCES, {}, show_private, map_data=data), table


def test_setup_gives_each_seat_its_point_and_the_drawing(data):
    library, _ = _library(data)
    setup = App(library, Gate(FakeClient([]), NameList.build(library.seats, {}))).setup()
    by_id = {seat["seat_id"]: seat for seat in setup["seats"]}
    assert by_id["S01"]["outer"] is False and by_id["P01"]["outer"] is True
    assert all({"x", "y", "outer"} <= set(seat) for seat in setup["seats"])
    drawing = setup["map"]
    assert drawing["viewbox"] == [0, 0, 1000, 800]
    assert len(drawing["boundary"]) == 60 and drawing["river"]
    assert drawing["source"] == "© OpenStreetMap contributors"
    assert 1 <= len(drawing["places"]) <= 8
    assert {"name", "x", "y"} == set(drawing["places"][0])


def test_the_map_parts_hold_no_company_or_display_name(data):
    library, table = _library(data)
    drawing = json.dumps(library.map_view(), ensure_ascii=False)
    points = json.dumps({s: vars(p) for s, p in library.placement.points.items()}, ensure_ascii=False)
    for seat in table:
        for word in (seat.company, seat.display_name):
            if word:
                assert word not in drawing and word not in points
    # The labels stay where they were: the seat list, from seat_label.
    assert {seat["detail"] for seat in library.seat_list()} >= {"はるかぜ理容　山川さん"}


def test_the_place_names_drawn_are_a_few_big_ones_in_the_city(data):
    names = [place["name"] for place in seat_map.place_names(data)]
    assert names[0] == "架空町"  # town first.
    assert "架空野" not in names and "架空坂" not in names  # Other towns' places.
    assert "字架空台" not in names and "架空丘" not in names  # Small kinds.


# --- the school's landmark ---

def test_the_school_label_comes_from_texts_and_no_file_or_an_empty_one_means_no_landmark(data, tmp_path,
                                                                                       monkeypatch):
    library, _ = _library(data)
    seat_count = len(library.seat_list())
    assert library.map_view()["school"] == {"x": 470, "y": 420, "label": "飯野高校"}  # texts/school_label.txt
    monkeypatch.setattr("ebino.texts.TEXTS_DIR", tmp_path)
    assert library.map_view()["school"] is None  # No file.
    (tmp_path / "school_label.txt").write_text(" \n", encoding="utf-8")
    assert library.map_view()["school"] is None  # Empty.
    (tmp_path / "school_label.txt").write_text("学校\n", encoding="utf-8")
    assert library.map_view()["school"]["label"] == "学校"
    # Not a seat: not in the seat list, not counted.
    assert len(library.seat_list()) == seat_count
    assert library.map_report().startswith(f"地図　点 {seat_count}・")


def test_no_school_in_the_map_file_means_no_landmark():
    library, _ = _library(parse_map(raw(school=None)))
    assert library.map_view()["school"] is None


# --- the map file in the repo ---

def test_the_map_file_in_the_repo_reads_and_carries_its_source_and_license():
    text = seat_map.MAP_FILE.read_text(encoding="utf-8")
    assert "© OpenStreetMap contributors" in text
    assert "ODbL 1.0" in text
    data = load_map()
    assert data is not None and data.home == HOME
    assert 3 <= len(data.boundary) <= 200
    assert data.river and data.places.get(HOME)
    assert data.school is not None
    # Place names are kept without 大字.
    assert not any(name.startswith("大字") for table in data.places.values() for name in table)


def test_the_map_file_holds_no_seat_table_words():
    text = seat_map.MAP_FILE.read_text(encoding="utf-8")
    for word in ("会社名", "表示名", "はるかぜ理容", "山川さん"):
        assert word not in text


# --- the static files ---

STATIC_SERVED = [name for name, _ in app_module.STATIC_FILES.values()]
# The SVG namespace is a name, not a place anything is loaded from.
NAMESPACES = ("http://www.w3.org/2000/svg",)
URL = re.compile(r"(?:https?:)?//[A-Za-z0-9.-]+\.[A-Za-z]{2,}[^\s\"')]*")


def test_rough_js_and_its_license_are_served(tmp_path):
    assert "rough.js" in STATIC_SERVED and "rough.LICENSE.txt" in STATIC_SERVED
    license_text = (app_module.STATIC_DIR / "rough.LICENSE.txt").read_text(encoding="utf-8")
    assert "MIT License" in license_text and "4.6.6" in license_text
    html = (app_module.STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert '<script src="/rough.js"></script>' in html


def test_the_static_files_load_nothing_from_outside():
    texts = [name for name, kind in app_module.STATIC_FILES.values()
             if kind.startswith(("text/", "application/", "image/svg+xml"))]  # 直し41: the tab's picture is text.
    # The fonts: binary, nothing to load.
    assert set(STATIC_SERVED) - set(texts) == {"title.woff", "fonts/BIZUDPMincho-Regular.woff2",
                                               "fonts/BIZUDPMincho-Bold.woff2", "fonts/BIZUDPGothic-Regular.woff2",
                                               "fonts/BIZUDPGothic-Bold.woff2"}
    assert "favicon.svg" in texts
    # The pictures from mapdata/ are files, not pages: nothing in them loads anything.
    assert {kind for _, kind in app_module.MAP_FILES.values()} == {"image/webp"}
    for name in texts:
        text = (app_module.STATIC_DIR / name).read_text(encoding="utf-8")
        found = [url for url in URL.findall(text) if not url.startswith(NAMESPACES)]
        assert not found, (name, found[:3])
        assert "@import" not in text and "fonts.googleapis" not in text


def test_the_policy_still_allows_self_only():
    source = (app_module.Path(app_module.__file__)).read_text(encoding="utf-8")
    assert '"Content-Security-Policy", "default-src \'self\'"' in source


def test_the_sample_seats_sit_on_the_real_map():
    from pathlib import Path

    from ebino import coach
    from ebino.ingest.seats import load_seats

    samples = Path(__file__).resolve().parent.parent / "samples"
    table = load_seats(samples / "seats.tsv")
    shown = coach.load_coach(samples, {seat.seat_id for seat in table})
    library = Library.build(table, [], {}, coach_seats=shown, map_data=load_map())
    points = library.placement.points
    districts = {seat.district for seat in table if seat.district}
    assert len(districts) >= 2 and all(find_place(d, library.map_data) for d in districts)
    assert library.placement.not_found == 0
    assert "O02" not in points  # 地図に出す 0 in the sample coach.tsv.
    on_map = sorted(s for s, p in points.items() if not p.outer)
    assert on_map == ["D01", "S01", "S02"]
    assert library.placement.outer == len(points) - 3
