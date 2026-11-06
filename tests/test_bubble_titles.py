"""直し45 段1: a small line over each bubble, the kind of talk of its piece,
in the teacher's words (closing_kind_labels.tsv), never a model's. Every
seat, piece and kind here is invented."""

import random
import shutil

import pytest
from fake_client import FakeClient

from ebino import app as app_module, texts
from ebino.gate import Gate, NameList
from ebino.session import Library, Session
from test_closing import ALL_SEATS, KINDS, PIECES, says
from test_one_to_one import SEATS as ONE_SEATS, UTTERANCES as ONE_UTTERANCES
from test_session import ANSWERED, UTTERANCES

STATIC = app_module.STATIC_DIR
MAP = (STATIC / "map.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
QUESTION = "休みの日って、みんな何してる？"


def sitting(answers, kinds):
    lib = Library.build(ALL_SEATS, UTTERANCES + PIECES, {}, False, kinds)
    return Session(lib, Gate(FakeClient(list(answers)), NameList.build(ALL_SEATS, {})), rng=random.Random(1))


def test_the_line_is_the_teachers_table_short_one_else_its_heading():
    labels = texts.kind_labels()
    rows = {row["ID"]: row for row in texts.load_table(texts.CLOSING_KIND_LABELS, texts.KIND_LABEL_COLUMNS,
                                                         may_be_empty=("短い見出し",))}
    for key, row in rows.items():
        assert labels[key]["heading"] == row["見出し"]
        assert labels[key]["short"] == (row["短い見出し"] or row["見出し"])
    assert "none" not in labels


def test_a_kind_with_no_row_stops_the_app(tmp_path, monkeypatch):
    for name in ("closing_kind_labels.tsv", "talk_kinds.tsv"):
        shutil.copy(texts.TEXTS_DIR / name, tmp_path / name)
    lines = (tmp_path / "closing_kind_labels.tsv").read_text(encoding="utf-8").splitlines()
    (tmp_path / "closing_kind_labels.tsv").write_text("\n".join(line for line in lines if not line.startswith("joy\t")),
                                                      encoding="utf-8")
    monkeypatch.setattr(texts, "TEXTS_DIR", tmp_path)
    with pytest.raises(ValueError):
        texts.kind_labels()


def test_a_bubble_at_the_table_gets_its_kinds_line_and_none_gets_none():
    session = sitting(ANSWERED, dict(KINDS, a1="reason", b1="none"))
    view = session.ask(QUESTION)
    lines = {q["utterance_id"]: q["kind_label"] for q in view["quotes"]}
    short = texts.kind_labels()["reason"]["short"]
    # a1: its kind's short line; b1: 「なし」; a2: never tagged.
    assert lines == {"a1": short, "a2": "", "b1": ""}


def test_the_last_word_and_the_bubble_say_one_kind_the_same_way():
    # The last word keeps its 見出し; the bubble its 短い見出し, else the same 見出し.
    session = sitting([*ANSWERED, says(("a9", "地元にも、面白い仕事はたくさんあります。"))],
                      dict(KINDS, a1="to_students"))
    view = session.ask(QUESTION)
    closing = session.close_round(1)
    labels = texts.kind_labels()
    word = closing["words"][0]
    assert word["kind"] == "to_students" and word["label"] == labels["to_students"]["heading"]
    bubble = next(q for q in view["quotes"] if q["utterance_id"] == "a1")
    assert bubble["kind_label"] == labels["to_students"]["short"]
    assert labels["to_students"]["short"] == labels["to_students"]["heading"]  # No short one: the same words.


def test_one_to_one_gets_the_line_of_its_first_piece_with_a_kind(monkeypatch):
    monkeypatch.setenv("EBINO_SPEAKER", "0")
    kinds = {ONE_UTTERANCES[4].id: "values", ONE_UTTERANCES[3].id: "none"}
    lib = Library.build(ONE_SEATS, ONE_UTTERANCES, {}, False, kinds)
    session = Session(lib, Gate(FakeClient([]), NameList.build(ONE_SEATS, {})), rng=random.Random(1))
    answer = session.one_ask("A01", "本文")
    assert answer["kind_label"] == texts.kind_labels()["values"]["short"]
    assert [p["kind_label"] for p in answer["pieces"]][-1] == texts.kind_labels()["values"]["short"]
    assert session.one_ask("A01", "プロフィール")["kind_label"] == ""


def test_the_screen_puts_the_line_first_small_and_never_wider_than_the_words():
    assert 'node.append(...kindOf(quote), div("voice", voiceOf(quote)), div("who", whoOf(seatOf(seatId))));' in MAP
    assert 'bubble.append(...kindOf({ kind_label: one.kind }), voice, div("who", whoOf(seatOf(one.seatId))));' in MAP
    assert "says(answer.pieces, answer.source, answer.kind_label);" in MAP
    rule = CSS[CSS.index(".map-bubble .kind, .table-bubble .kind, .one-bubble .kind {"):]
    rule = rule[:rule.index("}")]
    # A long line never widens its bubble at 768: it wraps between words.
    assert "width: 0; min-width: 100%;" in rule and "font-size: 13px;" in rule and "color: var(--paper-soft);" in rule
    assert "font-size: 15px" in CSS[CSS.index(".table-bubble .voice {"):][:120]  # The words stay larger.
    words = CSS[CSS.index(".now-line, .start-purpose, .inside"):]
    assert ".table-bubble" in words[:words.index("}")] and ".one-bubble" in words[:words.index("}")]
