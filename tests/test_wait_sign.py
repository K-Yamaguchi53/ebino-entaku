"""The sign in the middle of the map while the model is waited for (直し42):
a big short word and one small line from texts/wait_sign.tsv, shown only
for a wait the caller names and only once it passes 0.4 seconds; gone when
the answer comes or the request fails. 「集合中」 while the seats fly to the
round table, with motion on. Everything here is invented."""

import json
import re
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
APP = (STATIC / "app.js").read_text(encoding="utf-8")
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
HK = (STATIC / "hitokoto.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
WORD_BREAKS = (app_module.STATIC_DIR.parent.parent / "tools" / "check_word_breaks.js").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _top(source, name):
    start = source.index(f"function {name}(")
    return source[start:source.index("\n}\n", start) + 3]


def _inner(name):
    start = MAP.rindex("\n", 0, MAP.index(f"function {name}(")) + 1
    return MAP[start:MAP.index("\n  }\n", start) + 5]


# --- the words, from texts/ ---

def test_the_words_come_from_the_teachers_table_and_go_to_the_screen():
    signs = texts.screen_texts()["wait_sign"]
    assert set(signs) == set(texts.WAIT_SIGN_IDS)
    assert signs["ask"]["word"] == "取材中" and signs["gather"]["word"] == "集合中"
    assert signs["slow"] == {"word": "", "line": "いつもより時間がかかっています"}
    assert all(signs[k]["word"] and signs[k]["line"] for k in texts.WAIT_SIGN_IDS if k != "slow")
    # None of the words is written in the code: the screen takes them from texts/.
    for kind in texts.WAIT_SIGN_IDS:
        for words in filter(None, signs[kind].values()):
            for quoted in (f'"{words}"', f"'{words}'", f">{words}<", f"`{words}`"):
                assert quoted not in APP + MAP + HK + HTML


def _table(tmp_path, monkeypatch, lines):
    (tmp_path / "wait_sign.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setattr(texts, "TEXTS_DIR", tmp_path)


def test_a_row_missing_or_a_big_word_missing_is_an_error(tmp_path, monkeypatch):
    rows = (texts.TEXTS_DIR / "wait_sign.tsv").read_text(encoding="utf-8-sig").splitlines()
    _table(tmp_path, monkeypatch, rows)
    assert texts.wait_signs()["coach"]["word"] == "考え中"
    _table(tmp_path, monkeypatch, [r for r in rows if not r.startswith("coach\t")])
    with pytest.raises(ValueError):
        texts.wait_signs()
    _table(tmp_path, monkeypatch, [("ask\t\t" + r.split("\t")[2]) if r.startswith("ask\t") else r for r in rows])
    with pytest.raises(ValueError):
        texts.wait_signs()
    _table(tmp_path, monkeypatch, rows + ["other\t他\t他のこと"])
    with pytest.raises(ValueError):
        texts.wait_signs()


# --- which requests name a wait ---

WAITED = {
    '"/api/start", { lab }': "start",
    '"/api/ask", { question }': "ask",
    '"/api/coach_answer", { round: roundNo, role, answer, after_notice: state.needsShown }': "ask",
    '"/api/coach", { round: roundNo }': "coach",
    '"/api/ask_seat", { round: roundNo }': "ask_seat",
    '"/api/reflect/begin", { changed, now_question: nowQuestion }': "reflect",
    '"/api/subject", {}': "subject",
}


def test_the_caller_names_the_wait_and_quick_requests_name_none():
    for args, kind in WAITED.items():
        assert re.search(re.escape(f"call({args},") + r"\s*" + re.escape(f'{{ wait: "{kind}" }})'), APP), args
    # Every other call names no wait: quick, or one to one's own dots.
    calls = re.findall(r'call\("(/api/[a-z_/]+)"([^;]*?)\)\)?;', APP)
    assert calls
    waited = {re.match(r'"([^"]+)"', args).group(1) for args in WAITED}
    for path, rest in calls:
        if path not in waited:
            assert "wait:" not in rest, path
    for quick in ("/api/mark", "/api/card", "/api/paragraph", "/api/one/open", "/api/one/ask", "/api/one/free",
                  "/api/split", "/api/purposes"):
        assert quick not in waited
    # 帰る前に、ひとこと: the steps that wait on the model, through the same call.
    assert 'const WAITS = { parts: "listen", choose: "listen", answer: "listen", subject_note: "subject", light: "light", sheet: "sheet" };' in HK
    assert "return app.call(`/api/hitokoto/${step}`, body, { wait: WAITS[step] });" in HK
    used = set(re.findall(r'wait: "([a-z_]+)"', APP)) | set(re.findall(r'"(listen|subject|light)"', HK))
    assert used <= set(texts.WAIT_SIGN_IDS)


# --- when it shows (node, with a clock of its own) ---

_PROGRAM = r"""
let clock = 0, timers = [], nextId = 1;
global.setTimeout = (fn, ms) => { const id = nextId++; timers.push({ id, at: clock + ms, fn }); return id; };
global.clearTimeout = (id) => { timers = timers.filter((t) => t.id !== id); };
const advance = async (ms) => {
  const until = clock + ms;
  for (;;) {
    timers.sort((a, b) => a.at - b.at);
    const t = timers[0];
    if (!t || t.at > until) break;
    timers.shift();
    clock = t.at;
    t.fn();
    await Promise.resolve();
  }
  clock = until;
  await new Promise((r) => setImmediate(r));
};
const box = () => ({ hidden: true, textContent: "", dataset: {}, attrs: {},
  setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute(k) { delete this.attrs[k]; } });
const nodes = { "wait-sign": box(), "wait-word": box(), "wait-line": box(), map: box() };
const $ = (id) => nodes[id];
const page = { busy: false, one: true, step: "", stepAsked: 0, stepFails: false };
global.document = { querySelector: () => (page.busy ? {} : null) };
const oneScreen = () => page.one;
const state = { now: { reading: false }, texts: { wait_sign: %(signs)s } };
let answer = null;
global.fetch = (path) => {
  if (path === "/api/now_step") {  // 段2: the server's step, asked by itself.
    page.stepAsked += 1;
    if (page.stepFails) return Promise.reject(new Error("no answer"));
    return Promise.resolve({ ok: true, json: async () => ({ step: page.step }) });
  }
  return new Promise((resolve) => { answer = resolve; });
};
const reply = (ok) => answer({ ok, status: ok ? 200 : 500, json: async () => (ok ? { fine: 1 } : { error: "x" }) });
%(source)s
const sign = () => (nodes["wait-sign"].hidden ? null
  : { word: nodes["wait-word"].textContent, line: nodes["wait-line"].textContent, busy: nodes.map.attrs["aria-busy"] || "" });
(async () => {
  const seen = {};
  // A named wait: nothing before 0.4 s, the sign at 0.4 s, gone when it comes.
  let p = call("/api/ask", { question: "q" }, { wait: "ask" });
  await advance(399); seen.before = sign();
  await advance(1); seen.at = sign();
  await advance(15000 - 400 - 1); seen.notSlow = sign();
  await advance(1); seen.slow = sign();
  reply(true); await p; await advance(0); seen.back = sign(); seen.busyAfter = nodes.map.attrs["aria-busy"] || "";
  // Back within 0.4 s: never shown.
  p = call("/api/ask", { question: "q" }, { wait: "ask" });
  await advance(300); reply(true); await p; await advance(1000); seen.quick = sign();
  // No wait named: never shown.
  p = call("/api/mark", { round: 1 });
  await advance(1000); seen.unnamed = sign(); reply(true); await p;
  // A failure: shown, then gone, and the caller still hears of it.
  p = call("/api/ask", { question: "q" }, { wait: "ask" });
  await advance(500); seen.failing = sign();
  reply(false);
  try { await p; seen.threw = false; } catch (error) { seen.threw = error.message; }
  await advance(0); seen.failed = sign();
  // The seats gathering: 「集合中」, over any other wait; gone after.
  p = call("/api/coach", { round: 1 }, { wait: "coach" });
  await advance(500); seen.coachClear = sign();
  gathering(true); seen.gather = sign();
  gathering(false); page.busy = true; drawWait(); seen.coachBehindTable = sign();
  state.now.reading = true; page.busy = false; drawWait(); seen.coachWhileReading = sign();
  state.now.reading = false;
  reply(true); await p; await advance(0); seen.coachBack = sign();
  // The map not out: no sign.
  page.one = false;
  p = call("/api/ask", { question: "q" }, { wait: "ask" });
  await advance(500); seen.noMap = sign(); reply(true); await p;
  page.one = true;
  // The student's own wait shows over the table, the AI's aside does not.
  page.busy = true;
  p = call("/api/ask", { question: "q" }, { wait: "ask" });
  await advance(500); seen.askOverTable = sign(); reply(true); await p;
  page.busy = false;
  // 段2: the server's step, once it is in it; asked every 0.5 s while a question waits.
  page.step = ""; page.stepAsked = 0;
  p = call("/api/ask", { question: "q" }, { wait: "ask" });
  await advance(500); seen.stepNone = sign();
  page.step = "find"; await advance(500); seen.stepFind = sign();
  page.step = "moderate"; await advance(500); seen.stepModerate = sign();
  page.stepFails = true; await advance(1000); seen.stepFailed = sign();
  page.stepFails = false; page.step = "speak"; await advance(500); seen.stepSpeak = sign();
  page.step = "other"; await advance(500); seen.stepUnknown = sign();
  seen.askedWhile = page.stepAsked;
  reply(true); await p; await advance(0);
  const asked = page.stepAsked;
  await advance(3000); seen.askedAfter = page.stepAsked - asked; seen.stepBack = sign();
  // Only a question's wait asks the server's step.
  page.stepAsked = 0;
  p = call("/api/ask_seat", { round: 1 }, { wait: "ask_seat" });
  await advance(2000); seen.askSeatAsked = page.stepAsked; reply(true); await p;
  // A failed question stops asking too.
  p = call("/api/ask", { question: "q" }, { wait: "ask" });
  await advance(1000); reply(false); await p.catch(() => null); await advance(0);
  const failedAt = page.stepAsked;
  await advance(3000); seen.askedAfterFail = page.stepAsked - failedAt;
  process.stdout.write(JSON.stringify(seen));
})();
"""


def _source():
    start = APP.index("// wait (直し42)")
    return APP[start:APP.index("function sourceLine(")]


@node
def test_the_sign_shows_after_0_4_seconds_only_for_a_named_wait_and_goes_when_it_ends():
    signs = texts.wait_signs()
    program = _PROGRAM % {"signs": json.dumps(signs, ensure_ascii=False), "source": _source()}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    seen = json.loads(out.stdout.decode("utf-8"))
    ask = {"word": "取材中", "line": signs["ask"]["line"], "busy": "true"}
    assert seen["before"] is None
    assert seen["at"] == ask and seen["notSlow"] == ask
    assert seen["slow"] == dict(ask, line="いつもより時間がかかっています")  # The big word stays.
    assert seen["back"] is None and seen["busyAfter"] == ""
    assert seen["quick"] is None and seen["unnamed"] is None
    assert seen["failing"] == ask and seen["threw"] == "x" and seen["failed"] is None
    assert seen["coachClear"]["word"] == "考え中"
    assert seen["gather"] == {"word": "集合中", "line": signs["gather"]["line"], "busy": "true"}
    assert seen["coachBehindTable"] is None and seen["coachWhileReading"] is None
    assert seen["coachBack"] is None and seen["noMap"] is None
    assert seen["askOverTable"] == ask
    # 段2: the step the server is at, and only once it is in it.
    assert seen["stepNone"] == ask and seen["stepFind"] == ask  # find's words are ask's draft.
    assert seen["stepModerate"] == {"word": "考え中", "line": signs["moderate"]["line"], "busy": "true"}
    assert seen["stepFailed"] == seen["stepModerate"]  # Not heard: the words as they were.
    assert seen["stepSpeak"]["word"] == "整え中" and seen["stepUnknown"] == seen["stepSpeak"]
    assert 6 <= seen["askedWhile"] <= 11  # About every 0.5 s over 4.5 s (each after the last is heard).
    assert seen["askedAfter"] == 0 and seen["stepBack"] is None
    assert seen["askSeatAsked"] == 0 and seen["askedAfterFail"] == 0


def test_no_timer_of_its_own_ends_a_wait():
    # The two timers only show the sign and change its line; the request ends it.
    source = _source()
    # 段2's asking reschedules itself and is stopped with the wait.
    assert source.count("setTimeout(") == 4
    assert "if (!stopped) timer = setTimeout(next, WAIT_STEP_MS);" in source
    assert 'window.addEventListener("pagehide"' in source
    assert "const WAIT_SHOW_MS = 400, WAIT_SLOW_MS = 15000;" in source
    assert "AbortController" not in source and "abort" not in source
    assert "} finally {\n    if (waiting) waitEnd(waiting);\n  }" in _top(APP, "call")


def test_the_top_line_stays_and_the_sign_redraws_with_it():
    now = _top(APP, "setNow")
    # Set only when it changes (11/6: and then lit once, "fresh").
    assert "if (nowLine.textContent !== line.text) {\n    nowLine.textContent = line.text;" in now
    assert 'nowLine.classList.add("fresh");' in now
    assert "drawWait();" in now
    assert "setNow({ asking: true });" in _top(APP, "ask") and "setNow({ asking: true });" in _top(APP, "sendAnswer")


# --- 集合中: the seats flying to the table, motion on ---

def test_gathering_is_only_from_the_school_risen_to_the_seats_landed_with_motion():
    table = _inner("openTable")
    risen = table.index("await risen.done;")
    on = table.index("app.gathering(true);")
    landed = table.index("await Promise.all(landed)")
    assert risen < on < landed
    # Inside `if (motion) { ... }`: never with motion reduced or a table opened again.
    block = table[table.index("    if (motion) {\n      await risen.done;"):]
    assert block.index("app.gathering(true);") < block.index("\n    }\n")
    assert "const motion = !reduced() && !again;" in table
    assert ("const done = await Promise.all(landed).finally(() => { if (motion && app.gathering) "
            "app.gathering(false); });") in table
    # Not while the seats light at home (tableRound), and none left over by a new round.
    assert "gathering" not in _inner("tableRound")
    assert "if (app && app.gathering) app.gathering(false);" in _inner("clearRound")
    assert "gathering, foldAiSeat, pressSplit, splitLabel };" in APP  # Lent to the map.


def test_one_to_ones_dots_stay_where_they_are():
    assert 'const wait = div("one-asks one-wait");' in _inner("showWait")
    assert "gathering" not in _inner("showWait") and "drawWait" not in MAP


# --- the page and its look ---

def test_the_sign_is_in_the_maps_frame_under_the_bubbles_and_read_out_by_the_top_line_only():
    frame = HTML[HTML.index('<div id="map-frame"'):HTML.index('<div id="opening"')]
    assert frame.index('id="map-svg"') < frame.index('id="wait-sign"') < frame.index('id="map-overlay"')
    tag = re.search(r'<div id="wait-sign"[^>]*>', HTML).group(0)
    assert 'aria-hidden="true"' in tag and " hidden" in tag and "style=" not in tag
    assert 'aria-live="polite"' in HTML[HTML.index('id="now-line"') - 80:HTML.index('id="now-line"') + 80]
    assert '"aria-busy"' in _top(APP, "drawWait")


def test_its_look_is_in_the_css_never_pressed_and_never_glass():
    rule = re.search(r"^\.wait-sign \{[^}]*\}", CSS, re.M).group(0)
    assert "pointer-events: none;" in rule and "position: absolute;" in rule
    assert "background: var(--night-2);" in rule
    for glass in ("backdrop-filter", "blur(", "opacity"):
        assert glass not in rule
    assert "font-family: var(--mincho);" in re.search(r"\.wait-word \{[^}]*\}", CSS).group(0)
    assert "font-family: var(--gothic);" in re.search(r"\.wait-line \{[^}]*\}", CSS).group(0)
    assert ".map-frame:has(.opening:not([hidden])) .wait-sign { display: none; }" in CSS
    # 集合中 off the round table: at the top, at the foot when the AI's seat is at a top corner.
    assert '.wait-sign[data-kind="gather"] { top: var(--sp-5); translate: -50% 0; }' in CSS
    assert '.stage[data-ai-corner^="top"] .wait-sign[data-kind="gather"] { top: auto; bottom: var(--sp-5); }' in CSS
    assert "sign.dataset.kind = now.kind;" in _top(APP, "drawWait")
    # Placed by class only: no style set from code but custom properties.
    assert ".style." not in _source().replace("style.setProperty", "")


def test_its_movement_is_only_in_its_own_block_at_the_end_and_still_when_motion_is_reduced():
    last = CSS.rindex("@media (prefers-reduced-motion: no-preference) {")
    block = CSS[last:]
    assert ".wait-dots span { animation: one-wait 1.2s ease-in-out infinite; }" in block
    assert block.rstrip().endswith("}")
    before = CSS[:last]
    assert "animation" not in re.search(r"\.wait-dots span \{[^}]*\}", before).group(0)
    assert "wait-sign" not in before[before.index("@media (prefers-reduced-motion: reduce) {"):][:1200]
    assert "wait-" not in "".join(re.findall(r"@media \(prefers-reduced-motion: no-preference\) \{.*?\n\}", before, re.S))


def test_its_words_wrap_between_words():
    selectors = CSS[CSS.index(".now-line, .start-purpose, .inside"):CSS.index("word-break: auto-phrase;")]
    assert ".wait-sign {" in selectors
    assert '".wait-sign"' in WORD_BREAKS
