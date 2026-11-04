"""コーチ and オブザーバー sit at the round table (直し29-1): two seats of
their own (a small flame, no seat's mark), off the seats and chairs (at the
ends of a split's dashed line where they are free), their questions in
moonlit cards that find room before the seats'. Pressed: 「答える」 (the same
one-line box as below the map; sent, the next round starts) and 「閉じる」.
/api/coach is called once a round, by app.js; the map uses what it got."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def _top(name):
    start = APP.index(f"function {name}(")
    return APP[start:APP.index("\n}\n", start) + 3]


def test_the_word_to_answer_is_the_teachers():
    assert texts.screen_texts()["bubble_answer"] == "答える"
    assert "app.state.texts.bubble_answer" in _inner("openAnswer")
    assert "state.texts.bubble_answer" in _top("answerEntry")
    assert '"答える"' not in MAP and '"答える"' not in APP


def test_the_map_uses_the_band_app_js_got_and_calls_nothing_itself():
    band = _top("loadBand")
    assert band.count('call("/api/coach"') == 1 and APP.count('"/api/coach"') == 1
    assert "if (!band.cards.length) return;" in band
    assert band.index("if (!band.cards.length) return;") < band.index("map.band(roundNo, band.cards)")
    assert "if (!band.answered) onMap((map) => map.band(roundNo, band.cards));" in band
    assert "\"/api/coach" not in MAP and "fetch(" not in MAP  # (A comment may name it.)
    # The band below stays as it was.
    assert 'el("section", { class: "ai-band" })' in band and "answerEntry(roundNo, card.role)" in band


def test_the_band_sits_once_the_table_is_open_for_its_round():
    opened = MAP[MAP.index("async function openTable("):MAP.index("function tableBubble(")]
    assert "if (band && band.round === result.round) seatBand();" in opened
    assert opened.index("seatBand();") < opened.index("relayout();")
    put = _inner("setBand")
    assert "tableRoundNo === roundNo" in put and "!tokens.some((token) => token.ai)" in put
    assert "tableAt = null;" in _inner("clearTable")


def test_their_seats_are_flames_their_cards_moonlit_and_first_to_find_room():
    seat = _inner("seatBand")
    assert 'class: "token ai-seat lit"' in seat and "AI_FLAME" in seat and "shape(" not in seat
    assert 'div("table-label ai", card.label)' in seat
    assert "bubble.dataset.rank = String(k - band.cards.length);" in seat  # Before the seats' (0 and up).
    assert "seatPress(id, at)" in seat  # No room: pressing the seat shows it.
    bubble = _inner("aiBubble")
    assert 'div("table-bubble ai unplaced")' in bubble
    assert 'div("badge", card.badge), div("voice", card.question), div("who", card.label)' in bubble
    assert ".table-bubble.ai { background: var(--moon-paper);" in CSS
    assert ".table-bubble.ai .tail { background: var(--moon-paper); }" in CSS
    assert "--moon-paper: #" in CSS[CSS.index(":root {"):CSS.index("}", CSS.index(":root {"))]


def test_pressed_they_offer_to_answer_in_the_same_box_as_below_and_to_close():
    assert "if (ai) return openAnswer(seatId, card, ai.ai);" in _inner("openChoices")
    answer = _inner("openAnswer")
    assert "app.answerForm(roundNo, ai.role)" in answer and "closeChoices(true)" in answer
    assert "app.state.texts.bubble_close" in answer
    assert "answerForm };" in APP
    form = _top("answerForm")
    assert '"/api/coach_answer"' in form and "bandAnswered(roundNo, role);" in form and "renderRound(round);" in form
    # One answer per band: the other's 「答える」 goes, wherever it was written.
    done = _top("bandAnswered")
    assert ':scope > button' in done and 'card.dataset.role === role' in done


_ANGLES = """
%(source)s
const apart = (a, b) => { const d = (((a - b) %% 360) + 360) %% 360; return Math.min(d, 360 - d); };
const seats = [0, 13, 167, 193, 77, 103, 257, 283];  // Both sides, the back, two empty chairs.
const crowded = aiAngles(seats, true);
const free = aiAngles([0, 180], true);  // The line's ends free.
const none = aiAngles([0, 26, 180], false);
const near = (out, taken) => Math.min(...out.flatMap((a) => taken.map((b) => apart(a, b))), apart(out[0], out[1]));
process.stdout.write(JSON.stringify({ crowded, free, none, crowdedNear: near(crowded, seats), noneNear: near(none, [0, 26, 180]) }));
"""


@node
def test_they_sit_off_every_seat_at_the_split_lines_ends_where_free():
    source = "const AI_APART = 24;\n" + _inner("aiAngles")
    out = subprocess.run(["node", "-"], input=(_ANGLES % {"source": source}).encode("utf-8"),
                         capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    got = json.loads(out.stdout.decode("utf-8"))
    assert got["free"] == [270, 90]  # The ends of the dashed line: on neither side.
    assert got["crowdedNear"] >= 24 and got["noneNear"] >= 24
    assert got["none"][0] == 225
    for outside in ("document", "style", "classList", "overlay"):
        assert outside not in _inner("aiAngles")
