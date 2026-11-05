"""直し35-1: the ground with no picture gets the school model's track: five
lane lines (four lanes), inside the field, and a straight across its middle."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _part(start, end="\n  }\n"):
    part = MAP[MAP.index(start):]
    return part[:part.index(end) + len(end)]


@node
def test_five_lane_lines_inside_the_field_and_a_straight_across_the_middle():
    track = MAP[MAP.index("  const TRACK = "):]
    track = track[:track.index(";\n") + 2]
    code = track + _part("  function trackOn(") + (
        "const field = [[40, 150], [560, 150], [560, 720], [40, 720]];"
        "process.stdout.write(JSON.stringify(trackOn(field)));")
    out = subprocess.run(["node", "-"], input=code.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    assert len(got["lanes"]) == 5
    for ring in got["lanes"]:
        assert all(40 < x < 560 and 150 < y < 720 for x, y in ring)
    (x0, y0), (x1, y1) = got["middle"]
    assert y0 == y1 and abs((x0 + x1) / 2 - 300) < 0.2  # Across the middle, east to west.
    # The outer lane wider than the inner one.
    width = lambda ring: max(x for x, _ in ring) - min(x for x, _ in ring)
    assert width(got["lanes"][-1]) > width(got["lanes"][0])
