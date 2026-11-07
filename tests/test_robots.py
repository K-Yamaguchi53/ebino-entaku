"""直し47: コーチ（AI） and オブザーバー（AI） as small robots, in place of the
square 「AI」 mark, so the AI is not taken for the map's people. Drawn in one
place (static/robot.js) and put together at each place: the first look's
two cards, the AI's seat's questions, the coach's board at one to one.
Never a person (no face but the eyes, no name, no words), a picture only
(aria-hidden), the name with （AI） beside it as before. 司会（AI）'s mark
and the AI's seat's heading mark are as they were."""

import json
import re
import shutil
import subprocess

import pytest

from ebino import app as app_module

STATIC = app_module.STATIC_DIR
ROBOT = (STATIC / "robot.js").read_text(encoding="utf-8")
APP = (STATIC / "app.js").read_text(encoding="utf-8")
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

# A document enough for robot.js: elements that keep their name, attributes,
# children and text.
DOCUMENT = """
const fakeNode = (tag, ns) => ({ tag, ns, className: "", dataset: {}, attrs: {}, kids: [], textContent: "",
  setAttribute(k, v) { this.attrs[k] = v; }, append(...kids) { this.kids.push(...kids); } });
const document = { createElement: (tag) => fakeNode(tag, null), createElementNS: (ns, tag) => fakeNode(tag, ns) };
"""


def _run(body):
    program = DOCUMENT + ROBOT + "\n" + body
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    return json.loads(out.stdout.decode("utf-8"))


def _shape(robot):
    """The parts of a made robot's lines: [tag, attrs] each."""
    svg = robot["kids"][0]
    lines = svg["kids"][0]
    return [[part["tag"], part["attrs"]] for part in lines["kids"]]


def _rule(pattern):
    found = re.search(pattern, CSS)
    assert found, pattern
    return found.group(0)


def _top(source, name):
    start = source.index(f"function {name}(")
    return source[start:source.index("\n}\n", start) + 3]


def test_the_robots_are_drawn_in_one_place_only():
    assert app_module.STATIC_FILES["/robot.js"] == ("robot.js", "text/javascript; charset=utf-8")
    # Loaded before the scripts that put it together.
    assert HTML.index('<script src="/robot.js"></script>') < HTML.index('<script src="/map.js"></script>')
    assert HTML.index('<script src="/robot.js"></script>') < HTML.index('<script src="/app.js"></script>')
    # The drawing's own lines (the coach's mouth, the observer's lens) are in robot.js and nowhere else.
    for mark in ('"M35 47 Q42 51 49 47"', "cx: 42, cy: 38, r: 10"):
        assert ROBOT.count(mark) == 1, mark
        for other in STATIC.glob("*"):
            if other.is_file() and other.name != "robot.js" and other.suffix in (".js", ".html", ".css", ".svg"):
                assert mark not in other.read_text(encoding="utf-8"), (mark, other.name)
    # No picture file, no SVG written as text: made by code.
    assert "<svg" not in ROBOT and "innerHTML" not in ROBOT
    assert not list(STATIC.glob("robot*.svg")) and not list(STATIC.glob("robot*.png"))
    # Every place makes it there.
    assert APP.count("EbinoRobot.make(") == 4 and MAP.count("EbinoRobot.make(") == 2


@node
def test_the_coach_and_the_observer_are_different_robots():
    got = _run('process.stdout.write(JSON.stringify({ coach: EbinoRobot.make("coach"), '
               'observer: EbinoRobot.make("observer"), other: EbinoRobot.make("moderator"), roles: EbinoRobot.roles }));')
    assert got["roles"] == ["coach", "observer", "host"]
    assert got["other"] is None  # Any other: no robot.
    coach, observer = _shape(got["coach"]), _shape(got["observer"])
    assert coach != observer
    assert got["coach"]["dataset"]["robot"] == "coach" and got["observer"]["dataset"]["robot"] == "observer"
    filled = lambda shape: [a for t, a in shape if t == "circle" and a.get("fill") == "currentColor"]
    # コーチ: a round head (its corners as round as half its height), two eyes and the antenna's dot,
    # a mouth, a pointer (two lines from the body's side) besides the antenna.
    head = [a for t, a in coach if t == "rect"][0]
    assert float(head["rx"]) * 2 == float(head["height"])
    assert len(filled(coach)) == 3 and [t for t, _ in coach].count("path") == 1
    assert [t for t, _ in coach].count("line") == 3
    # オブザーバー: a square head, two antennas, one lens (a ring round a dot), no mouth.
    head = [a for t, a in observer if t == "rect"][0]
    assert float(head["rx"]) * 2 < float(head["height"])
    assert len(filled(observer)) == 1 and "path" not in [t for t, _ in observer]
    assert [t for t, _ in observer].count("line") == 2
    lens = [a for t, a in observer if t == "circle"]
    assert len(lens) == 2 and lens[0]["cx"] == lens[1]["cx"] and lens[0]["cy"] == lens[1]["cy"]
    # Lines only, in the place's colour: no colour of its own, nothing filled but the eyes.
    for shape in (coach, observer):
        for tag, attrs in shape:
            assert set(attrs.get("fill", "currentColor").split()) == {"currentColor"}
            assert "stroke" not in attrs and "style" not in attrs


@node
def test_it_is_a_picture_only_and_says_nothing():
    got = _run('process.stdout.write(JSON.stringify([EbinoRobot.make("coach"), EbinoRobot.make("observer", { tag: "AI" })]));')
    for robot in got:
        assert robot["tag"] == "span" and robot["className"] == "robot"
        assert robot["attrs"]["aria-hidden"] == "true"
        svg = robot["kids"][0]
        assert svg["ns"] == "http://www.w3.org/2000/svg" and svg["attrs"]["aria-hidden"] == "true"
        assert svg["attrs"]["focusable"] == "false"
    # No words of its own: 「AI」 on its body only when the place gives it (from texts), nothing else.
    assert len(got[0]["kids"][0]["kids"]) == 1
    words = got[1]["kids"][0]["kids"][1]
    assert words["tag"] == "text" and words["textContent"] == "AI"
    for word in ("title", "desc", "aria-label", "role=", "animate"):
        assert word not in ROBOT, word


def test_every_place_keeps_the_name_with_ai_beside_it():
    # はじめに: the robot, then the name (コーチ（AI） / オブザーバー（AI）) at the top of the card's words.
    roles = APP[APP.index("// コーチとオブザーバー (直し46)"):APP.index("renderInside(data.inside")]
    assert 'EbinoRobot.make(role.role, { tag: data.texts.ai_seat_mark })' in roles
    assert roles.index("EbinoRobot.make(role.role") < roles.index('class: "who", text: role.name')
    assert "ai-mark role-mark" not in roles
    # The AI's seat: each question's robot just before its name.
    seat = _top(APP, "renderAiSeat")
    assert ('el("span", { class: "who" }, EbinoRobot.make(card.role), el("span", { class: "who-name", text: card.label }))'
            in seat)
    # The coach's board: the coach's robot, then its name.
    board = MAP[MAP.index("async function askCoach("):MAP.index("const question = div(\"one-coach-question\"")]
    assert 'head.append(EbinoRobot.make("coach"), div("one-coach-name", view.label));' in board
    # 直し48 段2: while it comes, the robot already there with three dots in its bubble.
    assert 'board.append(EbinoRobot.make("coach"), div("one-coach-question", ""));' in board
    assert '"ai-mark"' not in board


@node
def test_at_the_ais_seat_each_question_has_its_roles_robot_by_its_name():
    harness = """
const made = {};
const part = (id) => made[id] || (made[id] = { id, textContent: "", hidden: true, children: [], attrs: {},
  classList: { toggle() {} }, setAttribute(k, v) { this.attrs[k] = v; },
  replaceChildren(...kids) { this.children = kids; }, append(kid) { this.children.push(kid); }, after() {} });
const $ = part;
function el(tag, attrs, ...kids) { return { tag, attrs, kids, classList: { add() {} }, addEventListener() {} }; }
function mapMoved() {}
function showAiPick() {}  // 直し53 段5: tests/test_ai_answer_53.py.
const phrased = (text) => text;
const state = { texts: {} };
""" + DOCUMENT + ROBOT + _top(APP, "renderAiSeat") + _top(APP, "foldAiSeat") + _top(APP, "openAiSeat") + """
renderAiSeat(1, { cards: [{ role: "coach", label: "コーチ（AI）", question: "Q1" },
  { role: "observer", label: "オブザーバー（AI）", question: "Q2" }], answered: null });
process.stdout.write(JSON.stringify({ faces: $("ai-seat-faces").children.map((k) => k.dataset.robot),
  cards: $("ai-seat-cards").children.map((b) => b.kids[0].kids.map((k) => k.dataset
    ? [k.dataset.robot, k.attrs["aria-hidden"]] : k.attrs.text)) }));
"""
    out = subprocess.run(["node", "-"], input=harness.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    assert got["cards"] == [[["coach", "true"], "コーチ（AI）"], [["observer", "true"], "オブザーバー（AI）"]]
    # 直し48 段2: no square mark nor heading; folded, the head is the two robots.
    assert got["faces"] == ["coach", "observer"]


@node
def test_the_host_is_a_third_robot_told_apart_by_its_shape():
    """直し48 段2: 司会（AI） as a robot too, drawn as the other two (lines,
    currentColor, the same width by its place): a wide head with rounded
    corners, one small dot on its top (no antenna stick), two short level
    lines for eyes, no mouth, a bow tie (two triangles) on the body's top, a
    microphone (a small ring on a short stick) in one hand. Never a person."""
    got = _run('process.stdout.write(JSON.stringify({ host: EbinoRobot.make("host"), coach: EbinoRobot.make("coach"), '
               'observer: EbinoRobot.make("observer") }));')
    host = _shape(got["host"])
    assert got["host"]["dataset"]["robot"] == "host" and got["host"]["attrs"]["aria-hidden"] == "true"
    assert host != _shape(got["coach"]) and host != _shape(got["observer"])
    head = [a for t, a in host if t == "rect"][0]
    assert float(head["width"]) > float(head["height"]) * 1.5  # Wide.
    assert 0 < float(head["rx"]) * 2 < float(head["height"])  # Rounded corners, not round.
    # One dot on top (filled, small, over the head), no stick up to it.
    dots = [a for t, a in host if t == "circle" and a.get("fill") == "currentColor"]
    assert len(dots) == 1 and float(dots[0]["r"]) <= 3 and float(dots[0]["cy"]) + float(dots[0]["r"]) <= float(head["y"])
    assert not [a for t, a in host if t == "line" and min(float(a["y1"]), float(a["y2"])) < float(head["y"])]
    # Eyes: two short level lines inside the head; no mouth (no path).
    eyes = [a for t, a in host if t == "line" and a["y1"] == a["y2"]
            and float(head["y"]) < float(a["y1"]) < float(head["y"]) + float(head["height"])]
    assert len(eyes) == 2 and all(float(a["x2"]) - float(a["x1"]) <= 10 for a in eyes)
    assert "path" not in [t for t, _ in host]
    # A bow tie: two triangles meeting at the body's top middle.
    ties = [a["points"].split() for t, a in host if t == "polygon"]
    assert len(ties) == 2 and all(len(points) == 3 for points in ties) and ties[0][0] == ties[1][0]
    # A microphone: a ring (not filled) outside the body, by a hand.
    rings = [a for t, a in host if t == "circle" and "fill" not in a]
    body = [a for t, a in host if t == "rect"][1]
    assert len(rings) == 1 and float(rings[0]["cx"]) < float(body["x"])
    for tag, attrs in host:
        assert set(attrs.get("fill", "currentColor").split()) == {"currentColor"}
        assert "stroke" not in attrs and "style" not in attrs


def test_the_hosts_mark_is_its_robot_and_the_seats_heading_is_gone():
    # 直し48: the first look's speaker, 司会（AI）, is its robot by its name.
    assert '<span id="host-mark" class="host-mark"' in HTML and 'class="ai-mark host-mark"' not in HTML
    assert '$("host-mark").replaceChildren(EbinoRobot.make("host"));' in APP
    assert ".host-head .host-mark .robot { --robot-line: 2.4px; width: 100%; height: 100%; }" in CSS
    assert 'id="ai-seat-mark"' not in HTML  # 直し48 段2: the seat's square mark gone too.


def test_its_look_lines_in_the_ais_blue_never_moving():
    rule = _rule(r"\n\.robot \{[^}]*\}")
    assert "color: var(--ai)" in rule
    lines = _rule(r"\.robot-lines \{[^}]*\}")
    assert "fill: none" in lines and "stroke: currentColor" in lines
    assert "vector-effect: non-scaling-stroke" in _rule(r"\.robot-lines > \* \{[^}]*\}")
    for found in re.finditer(r"[^}]*\.robot[^{]*\{[^}]*\}", CSS):
        assert "animation" not in found.group(0) and "transition" not in found.group(0), found.group(0)
    # Largest on the first look's cards (「AI」 on its body there: 48px and over).
    assert ".role-card .robot { --robot-line: 2.4px; width: 68px; height: 68px;" in CSS
    assert ".role-card .robot { --robot-line: 2px; width: 56px; height: 56px; }" in CSS
