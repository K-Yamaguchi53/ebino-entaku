"""直し54n (the teacher, 11/8): an opening as the page opens, made after the
teacher's own opening for their class newsletter (a 3D paper plane, a cut on
the beat to a flat one, the title a character a beat). Here the plane flies
over Ebino's relief as the seasons go round (spring, autumn, night), lands in
the lamp's light, and 「えびの円卓」 comes a beat a character, then goes to its
place on the first screen. Nothing sent or kept; with motion reduced, none;
a click, Enter, Esc or the space bar skips it (a click, not a press, so the
Lab button under it is never pressed); its words are the teacher's
(texts/launch_line.txt, a draft; opening_skip.txt).
(The screen check, in a browser: it starts under a second in, spring to
autumn to night to the cut at 3.5 seconds, the title in its place at about
9; a click over a Lab button skips it and presses none; Enter the same;
motion reduced: none.)"""

import re

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
LAUNCH = (STATIC / "launch.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
APP = (STATIC / "app.js").read_text(encoding="utf-8")
# The script without its comments (they speak of the server and the title in words).
CODE = re.sub(r"^\s*//.*$|\s+//\s.*$", "", LAUNCH, flags=re.M)


def test_it_is_served_and_starts_in_the_head_before_the_first_screen():
    assert app_module.STATIC_FILES["/launch.js"] == ("launch.js", "text/javascript; charset=utf-8")
    head = HTML[:HTML.index("</head>")]
    assert '<script src="/launch.js"></script>' in head
    body = HTML[HTML.index("<body>"):]
    assert body.index('<div id="launch" class="launch" aria-hidden="true"></div>') < body.index('<header class="masthead">')
    # The class goes on before the first paint; the overlay and the hidden title only with it.
    assert 'root.classList.add("launch-on");' in LAUNCH
    assert ".launch { display: none; }" in CSS
    assert "html.launch-on .launch { display: block; position: fixed; inset: 0; z-index: 1000;" in CSS
    assert "html.launch-on .masthead h1 { visibility: hidden; }" in CSS


def test_motion_reduced_means_none_at_all():
    still = LAUNCH.index('const still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;')
    assert LAUNCH.index("if (still) return;") < LAUNCH.index('root.classList.add("launch-on");')
    assert still < LAUNCH.index("if (still) return;")


def test_nothing_sent_or_kept_only_the_maps_pictures_read():
    for word in ("fetch(", "XMLHttpRequest", "sendBeacon", "Storage", "indexedDB", "cookie", "/api/"):
        assert word not in CODE, word
    assert sorted(re.findall(r'"(/[a-z_]+\.webp)"', CODE)) == ["/relief.webp", "/relief_autumn.webp", "/relief_spring.webp"]
    assert "Audio" not in LAUNCH and "<audio" not in HTML  # No sound.


def test_a_click_not_a_press_skips_it_and_the_keys_too():
    assert 'box.addEventListener("click", skip);' in LAUNCH
    assert "pointerdown" not in LAUNCH and "mousedown" not in LAUNCH
    keys = LAUNCH[LAUNCH.index("function onKey(event) {"):LAUNCH.index("function onResize()")]
    assert 'event.key === "Enter" || event.key === "Escape" || event.key === " "' in keys
    assert "event.preventDefault();" in keys and "event.stopPropagation();" in keys
    assert 'document.addEventListener("keydown", onKey, true);' in LAUNCH
    # Over: the overlay gone, the class off, the title the page's own again.
    over = LAUNCH[LAUNCH.index("  function finish() {"):LAUNCH.index("  function step(now) {")]
    assert 'root.classList.remove("launch-on");' in over and "box.remove();" in over


def test_the_seasons_go_round_and_the_town_lights_come_at_night():
    render = LAUNCH[LAUNCH.index("  function render(T, out) {"):LAUNCH.index("  // Where the title goes")]
    assert "parts.autumn.style.opacity = aut;" in render and "parts.night.style.opacity = nig;" in render
    assert "const aut = ioS(p(T, 0.9, 0.7)), nig = ioS(p(T, 1.85, 0.7));" in render  # Autumn, then night.
    assert "t.node.style.opacity = nig * " in render  # No light before night.
    assert "const B = 0.46, CUT = 3.5," in LAUNCH


def test_a_picture_not_read_leaves_out_the_flight_and_it_waits_only_while_seen():
    assert "const LOAD_MS = 4000;" in LAUNCH
    assert "if (!flight) began = performance.now() - CUT * 1000;" in LAUNCH
    assert "document.hidden" in LAUNCH and '"visibilitychange"' in LAUNCH
    assert ".launch:not(.launch-going) > * { visibility: hidden; }" in CSS


def test_its_title_is_the_pages_and_its_words_the_teachers():
    assert 'const h1 = document.querySelector(".masthead h1");' in LAUNCH
    assert texts.load_text(texts.LAUNCH_LINE) == "町の大人と、ひとつの卓をかこむ"  # A draft for the teacher.
    assert texts.screen_texts()["launch_line"] and texts.screen_texts()["opening_skip"] == "とばす"
    assert "if (window.EbinoLaunch) EbinoLaunch.words({ line: data.texts.launch_line, skip: data.texts.opening_skip });" in APP
    # No word of the screen written in the script itself.
    for literal in re.findall(r'"([^"\n]{2,})"', CODE):  # One character: the font's probe, never shown.
        assert not re.search(r"[ぁ-んァ-ン一-龥]", literal), literal


def test_no_flashing_and_the_title_lands_where_the_page_has_it():
    assert "flash" not in LAUNCH.lower() and "infinite" not in CSS[CSS.index("/* 直し54n: the opening as the page opens"):]
    assert "return { scale: size / fs, dx: to.left + to.width / 2 - cx, dy: to.top + to.height / 2 - cy };" in LAUNCH
