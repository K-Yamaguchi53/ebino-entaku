"""直し31-3: the harvest card's ③ is never left empty, and is shown as a card
tied by a line to the student's question. Everything here is invented."""

import json
import random
from collections import Counter
from pathlib import Path

import pytest
from fake_client import FakeClient

from ebino import subjects
from ebino.gate import Gate, NameList
from ebino.records import Records
from ebino.session import Library, Refused, Session
from ebino.texts import HARVEST_SUBJECT_CHOOSE, HARVEST_SUBJECT_LINK, load_text
from test_reflection import reflection_says
from test_session import ANSWERED, SEATS, UTTERANCES
from test_subjects import FIRST, ROWS, catalog, says

STATIC = Path(__file__).resolve().parent.parent / "ebino" / "static"
NO_CLUE = "休みの日は何をする？"  # Holds none of the table's clue words.


def sitting(*answers, now_question=NO_CLUE, tmp_path=None):
    lib = Library.build(SEATS, UTTERANCES, {}, False, subject_catalog=catalog())
    client = FakeClient(list(ANSWERED))
    session = Session(lib, Gate(client, NameList.build(SEATS, {})), rng=random.Random(1),
                      records=Records(tmp_path) if tmp_path else None)
    session.lab = "quest"
    session.ask(FIRST)
    client._answers.append(reflection_says())
    session.reflect_begin("a_little", now_question)
    session.reflect_answer("わからない")
    session.reflect_finish("none", "", "", "", "")
    client._answers.extend(answers)
    return session


@pytest.mark.parametrize("answer", [says("なし"), RuntimeError("down"), says("札9", 1)])
def test_with_nothing_fitting_two_are_shown_to_pick_from_never_none(answer):
    view = sitting(answer).subject()["subject"]
    assert view is not None and view["choose"] is True and len(view["cards"]) == 2
    assert view["link"] == load_text(HARVEST_SUBJECT_CHOOSE) and view["more"] is False
    # Of two 札 when there are; each with its own ひとこと, no reason from a model.
    fuda = {row.subject: row.fuda for row in ROWS}
    assert len({fuda[card["subject"]] for card in view["cards"]}) == 2
    assert all(card["note"] in {row.note for row in ROWS} for card in view["cards"])


def test_nashi_with_a_clue_word_shows_one_card_tied_to_the_question():
    session = sitting(says("なし"), now_question="地域の昔を知りたい")
    view = session.subject()["subject"]
    assert view["choose"] is False and len(view["cards"]) == 1
    assert view["question"] == "地域の昔を知りたい" and view["link"] == load_text(HARVEST_SUBJECT_LINK)
    card = view["cards"][0]
    assert set(card) == {"when", "subject", "heading", "note", "line"} and card["when"] and card["subject"]


def test_the_card_ties_to_the_question_rewritten_when_there_is_one():
    session = sitting(says("なし"), now_question="地域の昔を知りたい")
    session.reflection.rewrite = "町の昔は、どこに残っている？"
    assert session.subject()["subject"]["question"] == "町の昔は、どこに残っている？"


def test_the_one_picked_is_shown_alone_then_its_fuda_goes_round_and_both_are_kept(tmp_path):
    session = sitting(says("なし"), tmp_path=tmp_path)
    two = session.subject()["subject"]["cards"]
    view = session.subject_choose(1)["subject"]
    assert view["choose"] is False and [c["subject"] for c in view["cards"]] == [two[1]["subject"]]
    assert view["link"] == load_text(HARVEST_SUBJECT_LINK)
    with pytest.raises(Refused):
        session.subject_choose(0)  # Once.
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    kept = record["reflection"]["harvest_subject"]
    keys = {row.subject: row.key for row in ROWS}
    assert kept["status"] == subjects.STATUS_CHOOSE and kept["source"] == subjects.SOURCE_STUDENT
    assert kept["model_said"] == "なし" and kept["chosen"] == keys[two[1]["subject"]]
    assert kept["offered"] == [keys[two[0]["subject"]], keys[two[1]["subject"]]]
    if view["more"]:
        assert session.subject_more()["subject"]["cards"][0]["subject"] != two[1]["subject"]


def test_neither_picked_leaves_both_on_the_card_and_is_kept(tmp_path):
    session = sitting(RuntimeError("down"), tmp_path=tmp_path)
    session.subject()
    view = session.subject_choose("none")["subject"]
    assert len(view["cards"]) == 2 and view["choose"] is False and view["more"] is False
    assert view["link"] == load_text(HARVEST_SUBJECT_LINK)  # No longer asks to pick.
    with pytest.raises(Refused):
        session.subject_more()
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert record["reflection"]["harvest_subject"]["chosen"] == subjects.CHOSE_NONE


@pytest.mark.parametrize("choice", [2, -1, True, "0", None])
def test_a_choice_not_offered_is_refused(choice):
    session = sitting(says("なし"))
    session.subject()
    with pytest.raises(Refused):
        session.subject_choose(choice)


def test_there_is_nothing_to_pick_when_the_card_was_shown_by_the_model():
    session = sitting(says("札3", 13, 14), now_question="地域の昔を知りたい")
    session.subject()
    with pytest.raises(Refused):
        session.subject_choose(0)


def test_both_offered_are_counted_as_shown():
    session = sitting(says("なし"))
    session.subject()
    assert sum(session._subject_counts.values()) == 2


def test_two_to_choose_takes_the_fewest_shown_and_one_of_another_fuda():
    candidates = catalog().candidates("quest")
    first, second = subjects.two_to_choose(candidates, Counter({candidates[0].row.key: 3}))
    assert first is candidates[1] and second.row.fuda != first.row.fuda


def test_the_screen_shows_question_line_and_card_and_the_choice_buttons():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    app = (STATIC / "app.js").read_text(encoding="utf-8")
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    assert 'id="harvest-subject-tie"' in html and 'id="harvest-subject-none"' in html
    show = app[app.index("function showSubject"):app.index("async function chooseSubject")]
    assert show.index('class: "subject-question"') < show.index('class: "subject-tie-line"') < show.index("cards);")
    assert "state.texts.harvest_subject_pick" in show and 'call("/api/subject_choose", { choice })' in app
    assert '$("harvest-subject-none").addEventListener("click", () => chooseSubject("none"));' in app
    assert ".subject-tie { display: grid;" in css and ".subject-tie-line {" in css
