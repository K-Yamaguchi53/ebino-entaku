"""A picture of each seat's work at the round table (直し29-3): 探究をした先輩
a magnifier, 県外・海外に出た人 an aeroplane; 地域で働く大人 and 外から来た
大人・先生 by their title, the first row of texts/seat_icons.tsv (the
teacher's table) whose word is in it; none, the mark as before. The mark
stays as the picture's frame. Only at the table: the map's points and the
seat list are as before. Drawn in the code as lines, nothing from outside,
no words."""

import json
import re
import shutil
import subprocess

import pytest

from ebino import app as app_module
from ebino import texts

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _inner(name):
    start = MAP.index(f"function {name}(")
    return MAP[start:MAP.index("\n  }\n", start) + 5]


def _paths():
    start = MAP.index("const SEAT_ICON_PATHS = {")
    return MAP[start:MAP.index("\n  };\n", start) + 5]


def test_the_table_is_the_teachers_and_every_picture_in_it_is_drawn():
    rows = texts.seat_icons()
    assert rows[0] == ["医師", "medical"] and rows[-1] == ["動物", "animal"] and len(rows) == 77
    assert texts.screen_texts()["seat_icons"] == rows
    drawn = set(re.findall(r"^    (\w+): ", _paths(), re.M))
    assert {icon for _, icon in rows} <= drawn and {"poster", "cross"} <= drawn
    assert len(drawn) == 18


def test_a_table_naming_a_picture_with_no_drawing_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(texts, "TEXTS_DIR", tmp_path)
    (tmp_path / "seat_icons.tsv").write_text("言葉\t絵\n医師\tmedical\n犬\tdragon\n", encoding="utf-8")
    with pytest.raises(ValueError):
        texts.seat_icons()


_PICK = """
%(source)s
const table = %(table)s;
const pick = (kind, title) => seatIcon(kind, title, table);
process.stdout.write(JSON.stringify([
  pick("adult", "農協の貯金窓口"), pick("adult", "冷凍野菜工場"), pick("adult", "理容師"), pick("adult", "農家"),
  pick("outsider_teacher", "外から来た先生"), pick("adult", "架空の仕事10"), pick("outsider_teacher", "架空"),
  pick("poster", "探究の先輩（架空の川1を調べた）"), pick("cross", "県外・海外に出た人（架空2）"),
  pick("poster", "理容師"), pick("adult", ""),
]));
"""


@node
def test_the_first_row_whose_word_is_in_the_title_gives_the_picture():
    source = _paths() + _inner("seatIcon")
    program = _PICK % {"source": source, "table": json.dumps(texts.seat_icons(), ensure_ascii=False)}
    out = subprocess.run(["node", "-"], input=program.encode("utf-8"), capture_output=True, timeout=30)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    assert json.loads(out.stdout.decode("utf-8")) == [
        "town", "food", "beauty", "farm", "child",  # From the top row down: 貯金 before 農, 冷凍 before 工場.
        None, None,  # No word in the table: the mark as before.
        "poster", "cross", "poster", None]  # 先輩 and 県外・海外 by their kind alone.
    for outside in ("document", "style", "classList", "overlay", "app."):
        assert outside not in _inner("seatIcon")


def test_only_the_seats_at_the_table_get_a_picture_in_their_mark_as_lines():
    opened = MAP[MAP.index("async function openTable("):MAP.index("function tableBubble(")]
    assert "seatIcon(kind, seatOf(sitting.id).title, app.state.texts.seat_icons || [])" in opened
    assert 'node.classList.add("has-icon")' in opened and 'class: "icon", d: SEAT_ICON_PATHS[icon]' in opened
    assert opened.index("shape(kind)") < opened.index("seatIcon(")  # The mark stays, the picture's frame.
    assert "seatIcon(" not in _inner("drawPoint") and "SEAT_ICON" not in _inner("drawPoint")
    assert ".token .icon { fill: none; stroke: var(--lamp-bright); stroke-width: 1.3;" in CSS
    # Lines only: no words, no emoji, nothing from outside.
    paths = _paths()
    assert "http" not in paths and "<text" not in paths and not re.search(r"[^\x00-\x7f]", paths.split("{", 1)[1])
    # What it reads out stays the seat's name.
    assert '"aria-hidden": "true"' in opened
