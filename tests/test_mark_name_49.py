"""直し49 段3: the trail's mark 「いちばんおどろいた」 reads 「はじめて知った・気づいた」.
Its ID stays surprised (the records written before read the same), and the
marks' order (TRAIL_MARK_FIRST) stays. Every place the mark's words reach
(the marks to press, the sheet, the record's label) takes them from
texts/trail_marks.tsv, so all read the new words. Every record and word here
is invented; the model is a fake one."""

import json

from ebino import app as app_module
from ebino import hitokoto, texts
from test_hitokoto import to_end, to_scale

NEW = "はじめて知った・気づいた"
OLD = "いちばんおどろいた"
ROOT = app_module.STATIC_DIR.parent.parent


def test_the_mark_reads_the_new_words_and_keeps_its_id_and_order():
    marks = texts.id_table(texts.TRAIL_MARKS, texts.TRAIL_MARK_IDS)
    assert marks["surprised"] == NEW
    assert texts.TRAIL_MARK_IDS == ("surprised", "deeper", "more")
    assert texts.TRAIL_MARK_FIRST == ("more", "deeper", "surprised")


def test_the_screen_and_the_sheet_get_the_new_words():
    assert hitokoto.screen_words()["marks"]["surprised"] == NEW
    # A fresh sitting with a step marked surprised: its label on the sheet.
    session, _, _, _ = _marked()
    to_scale(session)
    to_end(session)
    session.hitokoto_light()
    sheet = session.hitokoto_sheet("")
    assert [m["label"] for m in sheet["marks"]] == [NEW]
    assert OLD not in json.dumps(sheet, ensure_ascii=False)


def test_the_record_keeps_the_id_surprised(tmp_path):
    session, _, _, _ = _marked(tmp_path)
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert [m["mark"] for m in record["hitokoto"]["marks"]] == ["surprised"]


def test_the_old_words_are_nowhere_the_screen_reads():
    for path in [*(ROOT / "texts").glob("*"), *(ROOT / "ebino" / "static").glob("*.js"),
                 ROOT / "ebino" / "static" / "index.html"]:
        if path.is_file():
            assert OLD not in path.read_text(encoding="utf-8"), path.name


def _marked(tmp_path=None):
    """A sitting whose trail's first step (the question) is marked surprised."""
    import random

    from ebino.gate import Gate, NameList
    from ebino.records import Records
    from ebino.session import Session
    from fake_client import FakeClient
    from test_hitokoto import QUESTION, Model
    from test_session import SEATS, library

    model = Model()
    session = Session(library(), Gate(FakeClient(model), NameList.build(SEATS, {})), rng=random.Random(1),
                      records=Records(tmp_path) if tmp_path else None)
    session.ask(QUESTION)
    session.mark(1, "b1")
    session.hitokoto_begin(["a1"], [{"n": 1, "mark": "surprised", "note": ""}])
    return session, model, None, None
