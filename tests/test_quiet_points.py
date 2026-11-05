"""直し41 段3: the points show people, not grains; before the first question
one point now and then glows quietly (never with motion reduced, never after
a round); a point pressed sends out one small ring."""

import json
import re
import shutil
import subprocess

import pytest

from ebino import app as app_module

STATIC = app_module.STATIC_DIR
SCRIPT = (STATIC / "map.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _inner(name):
    start = SCRIPT.index(f"function {name}(")
    return SCRIPT[start:SCRIPT.index("\n  }\n", start) + 5]


def _const(name):
    return re.search(rf"const {name} = [^;]+;", SCRIPT).group(0)


# The glow run with a clock of its own: timers kept in a list and fired in
# order of time; rng from the test; points as objects with a classList.
RUN = r"""
%(consts)s
%(source)s
const order = %(rng)s;
let i = 0;
const rng = () => order[i++ %% order.length];
let now = 0, timers = [], made = 0;
const later = (f, ms) => { timers.push({ at: now + ms, f, id: ++made }); return made; };
const cancel = (id) => { timers = timers.filter((t) => t.id !== id); };
const points = Array.from({ length: 6 }, (_, n) => {
  const on = new Set();
  return { n, classList: { add: (c) => on.add(c), remove: (c) => on.delete(c), has: (c) => on.has(c) } };
});
const stop = quietGlow(() => points, { rng, later, cancel, reduce: () => %(reduce)s });
let most = 0, starts = [], timersMade = made;
const until = %(until)s;
while (timers.length) {
  timers.sort((a, b) => a.at - b.at);
  const t = timers.shift();
  if (t.at > until) break;
  now = t.at;
  const before = points.filter((p) => p.classList.has("quiet-glow")).length;
  t.f();
  const after = points.filter((p) => p.classList.has("quiet-glow")).length;
  if (after > before) starts.push(now);
  most = Math.max(most, after);
}
stop();
const leftOn = points.filter((p) => p.classList.has("quiet-glow")).length;
console.log(JSON.stringify({ most, starts, leftOn, timersMade, pending: timers.length }));
"""


def _run(reduce=False, rng=(0.1, 0.9, 0.5, 0.3, 0.7), until=60000):
    program = RUN % {"consts": "\n".join([_const("QUIET_FOR"), "const reduced = () => false;"]),
                     "source": _inner("quietGlow"), "rng": json.dumps(list(rng)),
                     "reduce": "true" if reduce else "false", "until": until}
    done = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return json.loads(done.stdout.decode("utf-8"))


@node
def test_the_quiet_glow_lights_one_or_two_points_at_a_time_at_random_gaps():
    one = _run()
    assert one["starts"] and 1 <= one["most"] <= 2
    gaps = [b - a for a, b in zip(one["starts"], one["starts"][1:])]
    assert min(gaps) >= 1400  # Never more than one start in 1.4 s: far under three a second.
    assert len(set(gaps)) > 1  # The gaps follow the rng given: not one beat.
    assert one["leftOn"] == 0  # Stopped: no point left glowing.
    other = _run(rng=(0.6, 0.2, 0.95, 0.05))
    assert other["starts"] != one["starts"]  # Another rng, other times: it is the rng's.


@node
def test_with_motion_reduced_the_quiet_glow_does_not_even_set_a_timer():
    reduced = _run(reduce=True)
    assert reduced["timersMade"] == 0 and reduced["starts"] == [] and reduced["most"] == 0


def test_the_quiet_glow_reads_reduced_motion_in_the_script_too_and_stops_for_good_at_a_round():
    assert 'window.matchMedia("(prefers-reduced-motion: reduce)")' in SCRIPT
    assert "reduce = reduced" in _inner("quietGlow") and "if (reduce()) return () => {};" in _inner("quietGlow")
    # A round stops it and it never starts again.
    round_ = _inner("round")
    assert round_.index("stopQuiet();") < round_.index("if (!map) return;")
    assert "quietOver = true;" in _inner("stopQuiet") and "if (quiet || quietOver) return;" in _inner("startQuiet")
    # It glows only points not met, not lit, not away, not a senior at the school.
    assert '.points .pt:not(.met):not(.lit):not(.away):not(.school-home)' in _inner("startQuiet")


def test_the_new_motions_are_only_with_motion_not_reduced():
    glow = re.search(r"@media \(prefers-reduced-motion: no-preference\) \{\s*\.pt\.quiet-glow \.halo \{ animation: quiet-glow", CSS)
    assert glow
    assert CSS.count("animation: quiet-glow") == 1  # Nowhere else.
    reduce = CSS[CSS.index("@media (prefers-reduced-motion: reduce) {"):]
    reduce = reduce[:reduce.index("\n}\n")]
    assert ".pt.quiet-glow .halo, .press-ring { animation: none !important; display: none; }" in reduce
    assert "if (reduced() || !node || !node.animate) return;" in _inner("pressRing")
    assert re.search(r"const PRESS_RING_FOR = (\d+);", SCRIPT).group(1) == "400"


def test_points_are_drawn_bigger_where_they_go_and_what_takes_a_press_do_not_change():
    # Not met: .84 of met (was .72); met and lit at 1; hover a little bigger in .15 s.
    assert re.search(r"\.pt \.shape \{[^}]*transform: scale\(\.84\)", CSS)
    assert re.search(r"\.pt\.hover \.shape, \.pt:focus-visible \.shape \{[^}]*transform: scale\(1\.15\); transition-duration: \.15s;", CSS)
    assert "const MIN_DRAWN_PX = 6.5;" in SCRIPT
    # Drawn only: the homes are placed with MIN_POINT_PX as before, the press square is HIT_PX.
    assert "const MIN_POINT_PX = 3;" in SCRIPT and "const HIT_PX = 22;" in SCRIPT
    assert "MIN_DRAWN_PX" not in _inner("homePlace") and "MIN_DRAWN_PX" not in _inner("pointScale")
    # Never over MAX_POINT_PX: the seniors' 4px from an adult's lit point holds (test_homes).
    assert "MAX_POINT_PX * perPx / POINT_R" in _inner("drawnScale")
    # The seniors at the school keep their own size.
    assert 'node.classList.contains("school-home") ? atSchool : drawn' in _inner("rescale")
