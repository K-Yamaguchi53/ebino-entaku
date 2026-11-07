"""直し50 段3 (ヒビキ, 11/7: on the last sheet 司会（AI）のまとめ said two people
「同じ向き」 while 割れていたところ, just under it, had the same two parting):
code holds it back, the prompt (TIE) as it was. When the two picked stood on
the two sides of one of the day's splits and the model says "same", no
まとめ is shown (as with "none"); "differ" is shown; "same" for two who did
not part is shown. The record keeps why (no name). Everything is invented;
the model is a fake one."""

import json
from types import SimpleNamespace

from ebino import hitokoto, prompts
from test_sheet_more import TieModel, _sheet


def test_same_for_the_two_who_parted_on_the_split_shows_no_tie(tmp_path):
    session, model, sheet = _sheet(TieModel(tie={"kind": "same", "a": "1", "b": "2"}), tmp_path=tmp_path)
    # The two on the map are the split's two (割れていたところ is on the sheet).
    assert sheet["split"] and {sheet["split"]["a"], sheet["split"]["b"]} == {p["title"] for p in sheet["met"]}
    assert session.talk.parted == [[0, 1]]
    assert sheet["tie"] is None
    assert [kind for kind, _ in model.sent].count("tie") == 1
    # Asked again: not sent again, still none.
    assert session.hitokoto_sheet("")["tie"] is None
    assert [kind for kind, _ in model.sent].count("tie") == 1
    kept = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))["hitokoto"]
    assert kept["tie"] is None and kept["tie_asked"]["reason"] == hitokoto.SAME_ON_SPLIT


def test_same_either_way_round_is_held_back():
    _, _, sheet = _sheet(TieModel(tie={"kind": "same", "a": "2", "b": "1"}))
    assert sheet["tie"] is None


def test_differ_for_the_two_who_parted_is_shown():
    _, _, sheet = _sheet(TieModel(tie={"kind": "differ", "a": "2", "b": "1"}))
    assert sheet["split"]
    assert sheet["tie"]["kind"] == "differ"
    assert sheet["tie"]["a"] == sheet["met"][1] and sheet["tie"]["b"] == sheet["met"][0]


def test_same_for_two_not_on_a_split_is_shown():
    _, _, sheet = _sheet(TieModel(split=False, tie={"kind": "same", "a": "1", "b": "2"}))
    assert sheet["split"] is None
    assert sheet["tie"]["kind"] == "same"
    assert sheet["tie"]["a"] == sheet["met"][0] and sheet["tie"]["b"] == sheet["met"][1]


def _person(seat_id):
    return SimpleNamespace(seat_id=seat_id)


def _quote(uid, seat_id):
    return SimpleNamespace(utterance_id=uid, seat_id=seat_id)


def test_the_pairs_that_parted_are_read_from_every_split_of_the_day():
    # Three on the map; two rounds; S01 and S02 parted in the first, S03 sat on
    # S01's side in the second (with S02 on the other): S01–S03 did not part.
    rounds = [
        SimpleNamespace(quotes=[_quote("a1", "S01"), _quote("b1", "S02")],
                        splits=[SimpleNamespace(side_a=("a1",), side_b=("b1",))]),
        SimpleNamespace(quotes=[_quote("c1", "S03"), _quote("a2", "S01"), _quote("b2", "S02")],
                        splits=[SimpleNamespace(side_a=("c1", "a2"), side_b=("b2",))]),
    ]
    people = [_person("S01"), _person("S03"), _person("S02")]
    assert hitokoto.parted_pairs(SimpleNamespace(rounds=rounds), people) == [[0, 2], [1, 2]]
    # A seat not on the map, or a side's piece not quoted, makes no pair.
    assert hitokoto.parted_pairs(SimpleNamespace(rounds=rounds), [_person("S01"), _person("S09")]) == []
    unquoted = [SimpleNamespace(quotes=[_quote("a1", "S01")], splits=[SimpleNamespace(side_a=("a1",), side_b=("b1",))])]
    assert hitokoto.parted_pairs(SimpleNamespace(rounds=unquoted), people) == []


def test_the_tie_prompt_is_as_it_was():
    assert 'kind' in json.dumps(hitokoto.TIE_SCHEMA) and hitokoto.TIE_SCHEMA["properties"]["kind"]["enum"] == ["same", "differ", "none"]
    assert "文を書かない。" in prompts.TIE
