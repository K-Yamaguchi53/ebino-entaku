"""The kind of talk of each piece (SPEC 14-53 A as widened on 11/3).
Everything here is invented."""

import json

import pytest
from fake_client import FakeClient, text_response

from conftest import COMPANY, DISPLAY_NAME
from ebino import talk_kinds
from ebino.saved_output import load_output
from ebino.texts import CLOSING_KIND_LABELS, load_table
from test_tagger import piece, setup


def kinds_for(kind="refresh"):
    def answer(request):
        sent = json.loads(request["messages"][0]["content"])
        return text_response({"kinds": [{"id": p["id"], "kind": kind} for p in sent]})
    return answer


def test_the_teachers_table_has_the_kinds_in_order_and_none():
    kinds = talk_kinds.load_kinds()
    assert [k.kind_id for k in kinds] == [
        "to_students", "reason", "joy", "hardship", "refresh", "school_days", "values", "skills", "daily",
        "local", "future", "none"]
    assert [k.name for k in kinds][:2] == ["高校生へ", "きっかけ"] and kinds[-1].name == "なし"
    assert all(k.description for k in kinds)


def test_every_kind_but_none_has_a_line_for_the_screen_and_none_says_this_person():
    labels = {row["ID"]: row["見出し"] for row in load_table(CLOSING_KIND_LABELS, ("ID", "見出し"))}
    assert set(labels) == {k.kind_id for k in talk_kinds.load_kinds()} - {"none"}
    # Most pieces are an interviewer's article or a senior employee's words.
    assert not any("この人" in label for label in labels.values())


def test_pieces_get_one_kind_each_from_haiku_and_only_ids_go_back(tmp_path):
    folder = setup(tmp_path, [piece(i) for i in range(45)])
    client = FakeClient(kinds_for())
    report = talk_kinds.run(folder, client)
    assert (report.answered, report.unanswered, report.batches) == (45, 0, 2)
    saved = load_output(folder / "ingested" / "talk_kinds.json")
    assert saved.model == "claude-haiku-5-5" and saved.output["adult-000"] == "refresh"
    request = client.requests[0]
    assert request["model"] == "claude-haiku-5-5"
    # Structured output: an ID and a kind ID from the table, no words.
    item = request["output_config"]["format"]["schema"]["properties"]["kinds"]["items"]
    assert set(item["properties"]) == {"id", "kind"}
    assert item["properties"]["kind"]["enum"][-1] == "none"
    # The model is told the teacher's descriptions.
    system = request["system"][0]["text"]
    assert all(k.description in system for k in talk_kinds.load_kinds())
    assert set(json.loads(request["messages"][0]["content"])[0]) == {"id", "text"}


def test_a_piece_not_answered_or_answered_off_the_table_counts_as_none_and_is_asked_again(tmp_path):
    folder = setup(tmp_path, [piece(1), piece(2), piece(3)])

    def some(request):
        sent = json.loads(request["messages"][0]["content"])
        return text_response({"kinds": [{"id": sent[0]["id"], "kind": "joy"},
                                        {"id": sent[1]["id"], "kind": "made_up"}]})

    report = talk_kinds.run(folder, FakeClient(some))
    assert (report.answered, report.unanswered) == (1, 2)
    assert report.by_kind == {"joy": 1, "none": 2}
    saved = talk_kinds.load_saved(folder)
    kinds = talk_kinds.load_kinds()
    assert [talk_kinds.kind_of(saved, f"adult-{i:03}", kinds) for i in (1, 2, 3)] == ["joy", "none", "none"]
    client = FakeClient(kinds_for("daily"))
    again = talk_kinds.run(folder, client)
    assert (again.already, again.answered, again.unanswered) == (1, 2, 0)
    assert len(json.loads(client.requests[0]["messages"][0]["content"])) == 2


def test_a_failed_batch_is_counted_and_its_pieces_count_as_none(tmp_path):
    folder = setup(tmp_path, [piece(1)])
    report = talk_kinds.run(folder, FakeClient([text_response("", stop_reason="refusal")]))
    assert report.failures == {"refusal": 1} and report.unanswered == 1
    assert talk_kinds.kind_of(talk_kinds.load_saved(folder), "adult-001", talk_kinds.load_kinds()) == "none"


def test_kinds_of_pieces_no_longer_ingested_are_removed(tmp_path):
    folder = setup(tmp_path, [piece(1), piece(2)])
    talk_kinds.run(folder, FakeClient(kinds_for()))
    (folder / "ingested" / "utterances.json").write_text(
        json.dumps([piece(1).to_dict()], ensure_ascii=False), encoding="utf-8")
    report = talk_kinds.run(folder, FakeClient(kinds_for()))
    assert (report.dropped, report.already) == (1, 1)
    assert list(talk_kinds.load_saved(folder)) == ["adult-001"]


def test_no_company_or_display_name_reaches_the_model(tmp_path):
    folder = setup(tmp_path, [piece(1), piece(2, "P01", "川の水を調べた。")])
    client = FakeClient(kinds_for())
    talk_kinds.run(folder, client)
    sent = client.all_sent()
    assert COMPANY not in sent and "はるかぜ" not in sent and DISPLAY_NAME not in sent and "山川" not in sent


@pytest.mark.parametrize("bad, message", [
    ("ID\t名前\n", "columns"),
    ("ID\t名前\t説明\njoy\t楽しい\t説明\njoy\t楽しい\t説明\n", "twice"),
    ("ID\t名前\t説明\njoy\t楽しい\t説明\n", "no row for none"),
    ("ID\t名前\t説明\njoy\t楽しい\n", "line 2"),
])
def test_a_broken_table_is_refused_with_line_numbers_only(tmp_path, monkeypatch, bad, message):
    (tmp_path / "talk_kinds.tsv").write_text(bad, encoding="utf-8")
    monkeypatch.setattr("ebino.texts.TEXTS_DIR", tmp_path)
    with pytest.raises(ValueError, match=message):
        talk_kinds.load_kinds()
