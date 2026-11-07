"""直し52 段3 (ヒビキ, 48_ai_seat / 50_scene_autumn_button / 50_ai_seat_hint):
- At the meeting, the plain building (no picture of the school) is not
  lifted into it: its flat navy box lay over the table's lower half, the
  seats and their bubbles. The school is then its name only, dimmed as the
  other places' names; the map's school out of the meeting as it was; the
  picture of the school (when there is one) rises as before.
- 「吹き出しを1つ押してみよう」 keeps clear of the AI's seat's blue frame.
- 「コーチとオブザーバーの問いはここ。押して答えよう」, when it can only be
  put away from the frame, reaches it with a line of its colour and a dot.
The screen check counts the school over the ring, seats and bubbles ("school
over N") and the sign over the frame ("guide over ai N")."""

from pathlib import Path

from ebino import app as app_module

APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
CHECK = (Path(__file__).resolve().parent.parent / "tools" / "check_one_screen.js").read_text(encoding="utf-8")
RISE = MAP[MAP.index("  function riseSchool(center, motion) {"):MAP.index("  // The school back down to its place on the map")]


def test_the_plain_building_is_not_lifted_into_the_meeting():
    assert 'const plain = from.classList.contains("plain");' in RISE
    assert 'class: plain ? "risen-school plain" : "risen-school"' in RISE
    assert 'class: plain ? "risen-shadow plain" : "risen-shadow"' in RISE
    assert ".risen-school.plain, .risen-shadow.plain { display: none; }" in CSS
    # The school on the map, out of the meeting, as it was (lifted: unseen while the table is open).
    assert ".yard.lifted { visibility: hidden; }" in CSS
    assert 'from.classList.add("lifted");' in RISE


def test_the_sign_keeps_clear_of_the_ai_frame():
    table = APP[APP.index("  table: { at: () =>"):APP.index("  pressed: {")]
    assert 'clear: () => [...document.querySelectorAll("#ai-seat-cards .ai-question"), $("now-line"), $("ai-seat")],' in table


def test_far_from_the_frame_the_sign_reaches_it():
    draw = APP[APP.index("function drawGuide() {"):APP.index("function guideReach() {")]
    assert 'guideReach().hidden = true;' in draw
    assert draw.index('guideReach().hidden = true;') < draw.index("if (!words || !target || lit")
    assert 'const frame = target.closest && target.closest("#ai-seat");' in draw
    assert "return reachGuide(room, frame ? frame.getBoundingClientRect() : box);" in draw
    assert 'reach = el("div", { id: "guide-reach", class: "guide-reach", "aria-hidden": "true" });' in APP
    # The screen check's 差し戻し (768×1024: it ran through two cards' quotes): never over the
    # people's words nor the AI's questions; no clear way, no line.
    reach = APP[APP.index("function reachGuide(place, to) {"):APP.index("// The bubble at place { side, left, top, w, h }")]
    assert 'const keep = [...peopleVoices(), ...document.querySelectorAll("#ai-seat-cards .ai-question")]' in reach
    assert "if (crosses(sx, sy, ex, ey)) continue;" in reach
    assert reach.index("if (crosses(sx, sy, ex, ey)) continue;") < reach.index("reach.hidden = false;")
    assert ".guide-reach { position: fixed;" in CSS and "pointer-events: none;" in CSS[CSS.index(".guide-reach {"):]
    assert "@media print { .guide, .guide-reach, .first-look { display: none !important; } }" in CSS


def test_the_screen_check_counts_them():
    assert "bad.push(`guide over ai ${t.overAi}`);" in CHECK
    assert "bad.push(`school over ${t.school}`);" in CHECK
