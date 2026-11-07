"""直し48 段5 (the teacher, 11/7: one question's answer can be longer than
the screen): at one to one, an answer past about four lines (120
characters) stops at the end of a sentence with 「続きを読む」; pressed, the
rest opens in place, pressed again it shuts. The words are never changed:
what shows and what is folded are, together, the words as they came. The
button is a button (the keyboard reaches it) and says whether it is open
(aria-expanded). The short quotes in the table's bubbles stay as they are."""

import json
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

STATIC = app_module.STATIC_DIR
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

HARNESS = """
const node = (tag) => ({ tag, className: "", textContent: "", hidden: false, id: "", attrs: {}, kids: [], listeners: {},
  classList: { set: new Set(), toggle(c, on) { if (on) this.set.add(c); else this.set.delete(c); } },
  setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; },
  append(...k) { this.kids.push(...k); }, addEventListener(n, f) { this.listeners[n] = f; } });
const document = { createElement: node };
function div(cls, text) { const d = node("div"); d.className = cls; if (text !== undefined) d.textContent = text; return d; }
let placed = 0;
function placeOne() { placed += 1; }
const app = { state: { texts: { one_words: { read_more: "MORE", read_less: "LESS" } } } };
%(source)s
const all = (nodes) => nodes.filter((n) => n.tag === "div").map((n) => n.textContent + n.kids.map((k) => k.textContent).join("")).join("");
const shown = (nodes) => nodes.filter((n) => n.tag === "div" && !n.hidden)
  .map((n) => n.textContent + n.kids.filter((k) => !k.hidden).map((k) => k.textContent).join("")).join("");
const out = {};
for (const [name, pieces] of Object.entries(%(cases)s)) {
  const bubble = node("div");
  const nodes = foldPieces(pieces, bubble);
  const button = nodes.find((n) => n.tag === "button");
  const one = { all: all(nodes), shown: shown(nodes), button: Boolean(button) };
  if (button) {
    Object.assign(one, { label: button.textContent, expanded: button.getAttribute("aria-expanded"),
      controls: button.getAttribute("aria-controls"), type: button.type });
    button.listeners.click();
    Object.assign(one, { openShown: shown(nodes), openLabel: button.textContent, openExpanded: button.getAttribute("aria-expanded"),
      unfolded: bubble.classList.set.has("unfolded") });
    button.listeners.click();
    Object.assign(one, { shutShown: shown(nodes), shutExpanded: button.getAttribute("aria-expanded") });
  }
  out[name] = one;
}
out.placed = placed;
process.stdout.write(JSON.stringify(out));
"""

LONG = ("（架空）髪を切りながら、お客さんの話を聞くのが仕事の半分です。朝は八時に店を開けて、まず道具を一つずつ確かめます。"
        "はさみの具合は日によって違うので、手に持った感じで分かるようになるまで何年もかかりました。昼は近所のお年寄りが多くて、"
        "畑の話や孫の話をしながら、ゆっくり切ります。夕方は学校帰りの子が来るので、少し急ぎます。")
CASES = {
    "short": ["休みは決めて取ります。"],
    "long_one": [LONG],
    "long_pieces": [LONG[:40], LONG[40:90], LONG[90:]],  # Each a line of its own.
    "no_end": ["あ" * 200],  # No sentence end at all: not folded (never cut mid-word).
    "little_more": ["い" * 60 + "。" + "う" * 70 + "。"],  # Only a little past: as it is.
}


def _run():
    source = MAP[MAP.index("  const FOLD_CHARS = 120"):MAP.index("  let foldCount = 0;") + len("  let foldCount = 0;")]
    program = HARNESS % {"source": source, "cases": json.dumps(CASES, ensure_ascii=False)}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    return json.loads(out.stdout.decode("utf-8"))


@node
def test_the_words_are_never_changed_shown_and_folded_together_are_the_answer():
    got = _run()
    for name, pieces in CASES.items():
        assert got[name]["all"] == "".join(pieces), name
    assert not got["short"]["button"] and got["short"]["shown"] == CASES["short"][0]
    assert not got["no_end"]["button"] and not got["little_more"]["button"]


@node
def test_it_stops_at_a_sentence_end_near_four_lines():
    got = _run()
    for name in ("long_one", "long_pieces"):
        shown = got[name]["shown"]
        assert shown.endswith("。") and 60 <= len(shown) <= 120, (name, len(shown))
        assert LONG.startswith(shown)
    assert got["long_one"]["shown"] == got["long_pieces"]["shown"]


@node
def test_read_more_opens_in_place_and_shuts_again_saying_so():
    got = _run()["long_pieces"]
    assert got["type"] == "button" and got["label"] == "MORE" and got["expanded"] == "false" and got["controls"]
    assert got["openShown"] == "".join(CASES["long_pieces"]) and got["openLabel"] == "LESS"
    assert got["openExpanded"] == "true" and got["unfolded"]
    assert got["shutShown"] == got["shown"] and got["shutExpanded"] == "false"


def test_at_one_to_one_only_and_its_words_in_texts():
    words = texts.screen_texts()["one_words"]
    assert words["read_more"] == "続きを読む" and words["read_less"] == "閉じる"
    says = MAP[MAP.index("  function says(pieces"):MAP.index("  // The person's words by its head")]
    assert "voice.replaceChildren(...foldPieces(pieces.map((piece) => piece.spoken || piece.text), one.bubble, limit));" in says
    # About four lines of the bubble (the screen check: 120 characters were six lines at 768).
    assert "const limit = Math.min(FOLD_CHARS, 4 * Math.max(10, Math.floor((most - 32) / 18)));" in says
    # The table's bubbles: their short quote as before (cut at BUBBLE_CHARS, two lines).
    assert "const BUBBLE_CHARS = 36;" in MAP
    assert ".one-bubble .voice .one-rest[hidden] { display: none; }" in CSS
    assert ".one-bubble.unfolded { max-height: calc(100% - 16px); overflow: auto; }" in CSS
