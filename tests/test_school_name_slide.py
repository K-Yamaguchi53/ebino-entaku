"""The school's name slides left or right off the seats' points, by as little
as it takes (直し26-4: on the whole picture at 1920 the name's right end
nearly touched the seat just right of it)."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module

SCRIPT = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")


def _inner_function(name):
    start = SCRIPT.index(f"function {name}(")
    return SCRIPT[start:SCRIPT.index("\n  }\n", start) + 5]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_name_slides_the_least_way_off_the_points():
    consts = SCRIPT[SCRIPT.index("  const NS ="):SCRIPT.index("  let map = null;")]
    program = "\n".join([consts, _inner_function("boxesMeet"), _inner_function("nameSlide"), """
const name = [100, 50, 80, 20];
process.stdout.write(JSON.stringify({
  clear: nameSlide(name, [[300, 50, 10, 10]]),
  right: nameSlide(name, [[175, 55, 12, 12]]),   // A point on its right end: slide left.
  left: nameSlide(name, [[95, 55, 12, 12]]),     // On its left end: slide right.
  both: nameSlide(name, [[95, 55, 12, 12], [175, 55, 12, 12]]),
  far: nameSlide(name, [[60, 40, 160, 40]]),     // Nothing within SLIDE_MOST frees it: it stays.
}));"""])
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    out = json.loads(done.stdout.decode("utf-8"))
    assert out["clear"] == 0
    assert out["right"] == -5  # Its right end at 175, just clear of the point.
    assert out["left"] == 7  # Its left end at 107, just clear.
    assert out["both"] == 0  # Points at both ends, too far to slide past: it stays.
    assert out["far"] == 0
    for outside in ("document", "svg", "overlay", "style"):
        assert outside not in _inner_function("nameSlide")
