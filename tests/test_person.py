"""直し34-3: a seat as a person at one to one (static/person.js), drawn by
code. The same seat ID is always the same person; within a kind in seat ID
order, two next to each other never have the same clothes and head (with
the invented seats 103/45/10/1); a kind of twenty or fewer has no two the
same; two from outside differ. Nothing that says a sex, an age or a school
is drawn: no face, no long hair, no skirt, no name. Its colours come from
its kind's colour only."""

import json
import re
import shutil
import subprocess

import pytest

from ebino import app as app_module

STATIC = app_module.STATIC_DIR
PERSON = (STATIC / "person.js").read_text(encoding="utf-8")
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
COUNTS = {"adult": 103, "poster": 45, "cross": 10, "outsider_teacher": 1}
PREFIX = {"adult": "A", "poster": "P", "cross": "C", "outsider_teacher": "O"}


def _run(body):
    out = subprocess.run(["node", "-"], input=(PERSON + "\n" + body).encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    return json.loads(out.stdout.decode("utf-8"))


def _ids(kind, n):
    return sorted(f"{PREFIX[kind]}{k:03}" for k in range(n))


@node
def test_the_same_seat_is_the_same_person_every_time():
    got = _run("const a = EbinoPerson.looks('A012', 12), b = EbinoPerson.looks('A012', 12), c = EbinoPerson.looks('A013', 13);"
               "process.stdout.write(JSON.stringify([a, b, c]));")
    assert got[0] == got[1] and got[0] != got[2]


@node
def test_next_to_each_other_never_the_same_clothes_and_head_and_twenty_or_fewer_all_differ():
    seats = {kind: _ids(kind, n) for kind, n in COUNTS.items()}
    seats["outsider_teacher_two"] = _ids("outsider_teacher", 2)  # Only one in the sample: two here.
    got = _run(f"const seats = {json.dumps(seats)}; const out = {{}};"
               "for (const [kind, ids] of Object.entries(seats)) out[kind] = ids.map((id, k) => { "
               "const l = EbinoPerson.looks(id, k); return l.top + '/' + l.head; });"
               "process.stdout.write(JSON.stringify(out));")
    for kind, pairs in got.items():
        assert all(a != b for a, b in zip(pairs, pairs[1:])), kind
        if len(pairs) <= 20:
            assert len(set(pairs)) == len(pairs), kind
    assert got["outsider_teacher_two"][0] != got["outsider_teacher_two"][1]
    # Four clothes and five heads: twenty pairs in all.
    assert len(set(got["adult"])) == 20


def test_nothing_that_says_a_sex_an_age_or_a_school_and_only_its_kinds_colour():
    # The code, not its comments (which say what is not drawn).
    lowered = " ".join(line for line in PERSON.lower().splitlines() if not line.strip().startswith("//"))
    for drawn in ("eye", "mouth", "skirt", "uniform", "ponytail", "longhair", "textcontent", "<text", '"text"'):
        assert drawn not in lowered, drawn
    # Every colour from --kind (mixed with white or black), no other colour.
    colours = set(re.findall(r"#[0-9a-fA-F]{3,6}\b", PERSON))
    assert not colours
    assert 'const SKIN = "color-mix(in srgb, var(--kind) 45%, white)";' in PERSON
    assert "Math.random" not in PERSON  # Never by chance.


def test_at_one_to_one_it_stands_with_a_hand_up_and_the_ai_never_does():
    stood = MAP[MAP.index("function standUp("):]
    stood = stood[:stood.index("\n  }\n")]
    assert 'EbinoPerson.figure(seatOf(one.seatId).kind, one.seatId, placeAmong(one.seatId), "wave")' in stood
    # The AI's seat has no card at the table, so it never gets this far.
    assert "openOne(" in MAP and ".ai-question" not in stood
    opened = MAP[MAP.index("async function openOne("):]
    opened = opened[:opened.index("\n  }\n")]
    assert "motion ? CAMERA_FOR : 0" in opened and "if (token && motion)" in opened  # Reduced: at once.
    assert 'closeOne()' in MAP and 'event.key === "Escape" && one' in MAP


def test_the_person_whole_in_the_frame_and_the_ai_seat_steps_back():
    # A home at the drawing's top (the way out, a window): the camera may go
    # past the edge at one to one, so the head is never cut off.
    clamp = MAP[MAP.index("function clampView("):]
    clamp = clamp[:clamp.index("\n  }\n")]
    assert "if (one) return" in clamp
    # The AI's seat covered the feet and the words: it steps back meanwhile.
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    assert "body.one-open #ai-seat { visibility: hidden; }" in css
    assert 'document.body.classList.add("one-open")' in MAP and 'document.body.classList.remove("one-open")' in MAP
    # The words keep clear of the person's outline as it stands, hand up included.
    placed = MAP[MAP.index("function placeOne("):]
    placed = placed[:placed.index("\n  }\n")]
    assert "getBBox()" in placed
