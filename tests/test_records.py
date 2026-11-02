"""The records of each sitting (SPEC 2-1, 6, 14-51). Invented data; the
records folder is a temporary folder outside the repository."""

import json
import random
import re

from fake_client import FakeClient

from conftest import COMPANY, DISPLAY_NAME
from ebino import records as records_module
from ebino.app import App
from ebino.gate import Gate, NameList
from ebino.prompts import MODERATOR
from ebino.records import Records, summary
from ebino.session import Session
from test_session import ANSWERED, SEATS, editor_says, librarian_finds, library, moderator_says


def sitting(tmp_path, answers):
    client = FakeClient(list(answers))
    session = Session(library(), Gate(client, NameList.build(SEATS, {})), rng=random.Random(1),
                      records=Records(tmp_path))
    return session, client


def saved(tmp_path, session):
    return json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))


def test_a_sitting_is_kept_after_every_step(tmp_path):
    session, _ = sitting(tmp_path, ANSWERED + [editor_says(["S03"], "")])
    session.set_lab("quest")
    assert saved(tmp_path, session)["lab"] == "quest"
    session.ask("休みの日って、みんな何してる？")
    session.mark(1, "a1")
    session.press_split(1, 0)
    session.write_card("S03", "子どもと話すとき、何に気をつけますか")
    record = saved(tmp_path, session)
    [round_] = record["rounds"]
    assert round_["question"] == "休みの日って、みんな何してる？"
    assert round_["seats_lit"] == ["S01", "S02"] and round_["quotes_shown"] == ["a1", "a2", "b1"]
    assert (round_["guard_passed"], round_["guard_stopped"], round_["guard_stopped_seats"]) == (3, 0, 0)
    assert round_["splits"][0]["pressed"] is True and round_["silent_seats"] == ["S03"]
    assert record["marked_quotes"] == {"S01": "a1"} and record["met_seats"] == ["S01", "S02"]
    [card] = record["cards"]
    assert (card["origin"], card["seat_id"], card["back"]["ask_seat_ids"]) == ("student", "S03", ["S03"])


def test_a_record_has_a_random_id_a_date_and_seconds_but_no_clock_time_or_names(tmp_path):
    session, _ = sitting(tmp_path, ANSWERED)
    session.set_lab("not_said")
    session.ask("休みは？")
    record = saved(tmp_path, session)
    assert re.fullmatch(r"[0-9a-f]{8}", record["session_id"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["date"]) and isinstance(record["seconds_used"], int)
    text = json.dumps(record, ensure_ascii=False)
    assert not re.search(r"\d{2}:\d{2}", text)
    for word in (COMPANY, "はるかぜ", "架空農園", DISPLAY_NAME, "山川", "谷口"):
        assert word not in text


def test_quotes_the_guard_stopped_are_kept_as_counts_only(tmp_path):
    session, _ = sitting(tmp_path, [
        librarian_finds("a1", "a2", "b1"),
        # S01: one passes, one is stopped. S02: its only quote is stopped.
        moderator_says([("a1", "休みは決めて取ります。"), ("a2", "月曜は休む。"), ("b1", "作り話です。")]),
    ])
    session.ask("休みは？")
    round_ = saved(tmp_path, session)["rounds"][0]
    assert (round_["guard_stopped"], round_["guard_stopped_seats"]) == (2, 1)
    assert "作り話" not in json.dumps(round_, ensure_ascii=False)
    assert round_["quotes_shown"] == ["a1"]


def test_a_name_in_the_question_is_not_kept(tmp_path):
    session, _ = sitting(tmp_path, [])
    session.ask("谷口さんの休みは？")
    round_ = saved(tmp_path, session)["rounds"][0]
    assert (round_["question"], round_["status"], round_["reason"]) == ("", "ask_again", "name_in_question")
    assert "谷口" not in json.dumps(saved(tmp_path, session), ensure_ascii=False)


def test_the_moderator_prompt_is_kept_with_instruction_and_data_apart(tmp_path):
    client = FakeClient(list(ANSWERED))
    app = App(library(), Gate(client, NameList.build(SEATS, {})), Records(tmp_path), rng=random.Random(1))
    app.start({"lab": "action"})
    app.handle("/api/ask", {"question": "休みの日って、みんな何してる？"})
    folder = tmp_path / "prompts" / app.session.session_id
    assert sorted(p.name for p in folder.iterdir()) == ["01-moderator-data.json", "01-moderator-instruction.txt"]
    instruction = (folder / "01-moderator-instruction.txt").read_text(encoding="utf-8")
    data = (folder / "01-moderator-data.json").read_text(encoding="utf-8")
    assert MODERATOR.strip() in instruction and "silent_seat_ids" in instruction
    assert "休みの日って" not in instruction and "a1" not in instruction
    assert "休みの日って" in data and "a1" in data


def test_the_count_of_questions_no_seat_answered(tmp_path):
    sessions = [
        {"rounds": [{"status": "answered", "guard_passed": 2, "guard_stopped": 1},
                    {"status": "silent", "guard_passed": 0, "guard_stopped": 0}], "cards": [{}]},
        {"rounds": [{"status": "unavailable", "guard_passed": 0, "guard_stopped": 0},
                    {"status": "answered", "guard_passed": 1, "guard_stopped": 0}], "cards": []},
    ]
    lines = summary(sessions)
    assert "no seat answered: 1 of 3 answered or silent (33%)" in lines
    assert "guard passed / stopped: 3 / 1" in lines and "cards: 1" in lines


def test_the_summary_command_reads_the_records_folder(tmp_path, monkeypatch, capsys):
    session, _ = sitting(tmp_path, ANSWERED)
    session.ask("休みは？")
    monkeypatch.setattr(records_module, "load_env_file", lambda: None)
    monkeypatch.setenv("EBINO_RECORDS_DIR", str(tmp_path))
    assert records_module.main() == 0
    out = capsys.readouterr().out
    assert "sittings: 1" in out and "休み" not in out
