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
    # 直し54o: its music is made in the page as it plays; no file, nothing fetched for it.
    assert "<audio" not in HTML and "new Audio(" not in LAUNCH
    for ext in (".mp3", ".wav", ".ogg", ".m4a"):
        assert ext not in CODE, ext


def test_a_click_not_a_press_skips_it_and_the_keys_too():
    assert 'box.addEventListener("click", onClick);' in LAUNCH
    assert "function onClick() { if (asked) skip(); else begin(); }" in LAUNCH
    assert "pointerdown" not in LAUNCH and "mousedown" not in LAUNCH
    keys = LAUNCH[LAUNCH.index("function onKey(event) {"):LAUNCH.index("function onResize()")]
    assert 'event.key === "Enter" || event.key === "Escape" || event.key === " "' in keys
    assert "if (asked) skip();" in keys and 'else if (event.key === "Escape") finish();' in keys and "else begin();" in keys
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
    assert "const from = flight ? 0 : CUT;  // No pictures: from the cut." in LAUNCH
    assert "if (t < from - 0.02) return;  // Started at the cut: nothing of the flight." in LAUNCH
    assert "document.hidden" in LAUNCH and '"visibilitychange"' in LAUNCH
    assert ".launch:not(.launch-going) > * { visibility: hidden; }" in CSS


def test_its_title_is_the_pages_and_its_words_the_teachers():
    assert 'const h1 = document.querySelector(".masthead h1");' in LAUNCH
    assert texts.load_text(texts.LAUNCH_LINE) == "町の大人と、ひとつの卓をかこむ"  # A draft for the teacher.
    assert texts.screen_texts()["launch_line"] and texts.screen_texts()["opening_skip"] == "とばす"
    assert "if (window.EbinoLaunch) EbinoLaunch.words({ line: data.texts.launch_line, skip: data.texts.opening_skip, start: data.texts.launch_start, sound: data.texts.launch_sound });" in APP
    assert texts.load_text(texts.LAUNCH_START) == "クリックで はじまる" and texts.load_text(texts.LAUNCH_SOUND) == "音が出ます"
    assert texts.screen_texts()["launch_start"] and texts.screen_texts()["launch_sound"]
    # No word of the screen written in the script itself.
    for literal in re.findall(r'"([^"\n]{2,})"', CODE):  # One character: the font's probe, never shown.
        assert not re.search(r"[ぁ-んァ-ン一-龥]", literal), literal


def test_no_flashing_and_the_title_lands_where_the_page_has_it():
    assert "flash" not in LAUNCH.lower() and "infinite" not in CSS[CSS.index("/* 直し54n: the opening as the page opens"):]
    assert "return { scale: size / fs, dx: to.left + to.width / 2 - cx, dy: to.top + to.height / 2 - cy };" in LAUNCH


def test_54o_it_waits_for_a_click_and_its_music_starts_only_in_it():
    """直し54o (the teacher, 11/8): music with it. A page not yet touched may not
    sound, so it waits on the night's colour (「クリックで はじまる」「音が出ます」);
    the click (Enter, space) starts it and its music, made in the page on the
    same beats; once it plays a click ends it and the music fades with it.
    (The screen check: the words shown and nothing moving until the click; a
    click starts the flight and an AudioContext running; a second click ends
    it, nothing pressed under it.)"""
    # Shown only when read, and only until the click.
    go = LAUNCH[LAUNCH.index("  function go() {"):LAUNCH.index("  // The app gives the words")]
    assert 'if (asked) play();  // Clicked while it was still reading.' in go
    assert 'else box.classList.add("launch-waiting");' in go
    assert "requestAnimationFrame" not in go  # Nothing moves before the click.
    begin = LAUNCH[LAUNCH.index("  function begin() {"):LAUNCH.index("  function play() {")]
    assert 'box.classList.remove("launch-waiting");' in begin
    # The sound made only in the click or key (where a page may start one), once.
    assert CODE.count("hearing()") == 2 and "audio = hearing();" in begin
    assert "new Ctx()" in LAUNCH and "ctx.resume();" in LAUNCH
    # On the same beats as the picture, from the same start.
    play = LAUNCH[LAUNCH.index("  function play() {"):LAUNCH.index("  function onClick()")]
    assert "began = performance.now() + LEAD * 1000 - from * 1000;" in play and "music = score(audio, from);" in play
    sc = LAUNCH[LAUNCH.index("  function score(ctx, from) {"):LAUNCH.index("  function hush(length) {")]
    for at in ("thump(CUT, 0.8);", "thump(beat(3 + i), 0.32); pluck(n, beat(3 + i), 0.15);", "thump(beat(8), 0.4);", "air(beat(2), 0.8,"):
        assert at in sc, at
    # A skip fades it; the end lets the last chord die away before it is closed.
    skip = LAUNCH[LAUNCH.index("  function skip() {"):LAUNCH.index("  // Waiting: the click")]
    assert "hush(SKIP_OUT + 0.3);" in skip
    over = LAUNCH[LAUNCH.index("  function finish() {"):LAUNCH.index("  function step(now) {")]
    assert "ctx.close()" in over
    # Its look: hidden until read, then the words; never moving on and on.
    block = CSS[CSS.index("/* 直し54o: before it plays"):]
    assert ".launch.launch-waiting > .launch-gate { visibility: visible; opacity: 1; }" in block
    assert "infinite" not in block and "animation" not in block
