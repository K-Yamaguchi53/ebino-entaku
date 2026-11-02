"""The librarian's search and tool loop (SPEC 6, 14-52). Everything here is invented."""

import json

import pytest
from fake_client import FakeClient, text_response, tool_response

from conftest import COMPANY, DISPLAY_NAME, make_seat
from ebino import librarian
from ebino.gate import Gate, GateError, NameList
from ebino.index import build_index
from ebino.ingest.utterance import Utterance
from ebino.librarian import Shelf, find, word_hits

SEATS = [
    make_seat(seat_id="S01"),  # 理容師, はるかぜ理容, 山川さん, 架空地区.
    make_seat(seat_id="S02", title="農家", company="架空農園", display_name="谷口さん", district="北地区"),
    make_seat(seat_id="P01", kind="poster", title="探究の先輩（川の水を調べた）", company="",
              display_name="先輩", district=""),
]
PIECES = [
    ("a1", "S01", "休みの日は川で釣りをします。", ["休日", "釣り"]),
    ("a2", "S01", "朝は七時に店を開けます。", ["開店時間"]),
    ("b1", "S02", "週に一度は休みを決めて取ります。", ["休み方"]),
    ("b2", "S02", "畑は天気しだいです。", ["天気"]),
    ("p1", "P01", "川の水のにごりを調べた。", ["水質調査"]),
]


def entries(pieces=PIECES):
    utterances = [Utterance(id=i, seat_id=s, kind="adult", section="本文", voice="article", text=t, paragraph="")
                  for i, s, t, _ in pieces]
    return build_index(utterances, SEATS, {i: topics for i, _, _, topics in pieces})


def names():
    return NameList.build(SEATS, {})


def by_id(utterance_id):
    return next(e for e in entries() if e.utterance_id == utterance_id)


# --- searching by words is not an exact match (SPEC 14-52) ---

def test_a_word_inside_a_topic_hits():
    assert word_hits(by_id("b1"), "休み") == 2  # 休み ⊂ 休み方


def test_a_topic_inside_the_word_hits():
    assert word_hits(by_id("a1"), "釣り好き") == 2  # 釣り ⊂ 釣り好き


def test_a_word_only_in_the_text_hits_lower():
    assert word_hits(by_id("a2"), "七時") == 1


def test_a_word_that_meets_nothing_misses():
    assert word_hits(by_id("a2"), "給料") == 0
    assert word_hits(by_id("a2"), " ") == 0


def test_search_finds_through_topics_and_text_and_ranks_topic_hits_first():
    result = Shelf(entries()).search(["休み"])
    ids = [p["utterance_id"] for p in result["pieces"]]
    # b1: 休み ⊂ 休み方 (topic). a1: 休み in the text only (its topic is 休日).
    assert ids == ["b1", "a1"]
    assert result["hits"] == 2


def test_search_can_be_narrowed_by_kind_and_district():
    shelf = Shelf(entries())
    assert [p["utterance_id"] for p in shelf.search(["川"], kind="poster")["pieces"]] == ["p1"]
    assert [p["utterance_id"] for p in shelf.search(["休み"], district="北地区")["pieces"]] == ["b1"]


def test_list_and_read_seats():
    shelf = Shelf(entries())
    seats = shelf.list_seats(kind="adult")["seats"]
    assert [(s["seat_id"], s["pieces"]) for s in seats] == [("S01", 2), ("S02", 2)]
    assert [p["utterance_id"] for p in shelf.read_seat("S02")["pieces"]] == ["b1", "b2"]


def test_a_bad_tool_call_gives_an_error_result_not_an_exception():
    shelf = Shelf(entries())
    assert shelf.run("search", {}) == ({"error": "bad_arguments"}, True)
    assert shelf.run("delete_all", {}) == ({"error": "unknown_tool"}, True)


# --- the tool loop (SPEC 14-52) ---

def test_the_loop_runs_tools_and_returns_only_known_ids():
    client = FakeClient([
        tool_response(("t1", "search", {"words": ["休み"], "kind": "", "district": ""})),
        text_response({"utterance_ids": ["b1", "a1", "b1", "zz9"]}),
    ])
    found = find(Gate(client, names()), entries(), "休みの日って、みんな何してる？")
    assert found.utterance_ids == ["b1", "a1"]
    assert (found.ended, found.requests, dict(found.tool_calls)) == ("answered", 2, {"search": 1})
    second = client.requests[1]["messages"]
    assert second[1]["role"] == "assistant" and second[1]["content"][0]["type"] == "tool_use"
    result = second[2]["content"][0]
    assert result["type"] == "tool_result" and result["tool_use_id"] == "t1"
    assert "b1" in result["content"]


def test_the_request_uses_strict_tools_and_no_forced_choice_or_fallbacks():
    client = FakeClient([text_response({"utterance_ids": []})])
    find(Gate(client, names()), entries(), "問い")
    request = client.requests[0]
    assert request["model"] == "claude-sonnet-5-5"
    assert all(t["strict"] and t["input_schema"]["additionalProperties"] is False for t in request["tools"])
    assert "tool_choice" not in request and "fallbacks" not in request


def test_at_the_request_cap_the_pieces_found_so_far_are_handed_on():
    calls = iter(range(100))

    def keeps_searching(request):
        return tool_response((f"t{next(calls)}", "search", {"words": ["川"], "kind": "", "district": ""}))

    client = FakeClient(keeps_searching)
    found = find(Gate(client, names()), entries(), "川のこと")
    assert len(client.requests) == librarian.MAX_REQUESTS
    assert found.ended == "request_limit"
    assert found.utterance_ids == ["a1", "p1"]


def test_no_company_or_display_name_reaches_the_librarian_even_in_tool_results():
    client = FakeClient([
        tool_response(("t1", "list_seats", {"kind": "", "district": ""}),
                      ("t2", "read_seat", {"seat_id": "S01"}),
                      ("t3", "search", {"words": ["休み", "川"], "kind": "", "district": ""})),
        text_response({"utterance_ids": ["a1"]}),
    ])
    find(Gate(client, names()), entries(), "休みの日って、みんな何してる？")
    sent = client.all_sent()
    assert len(client.requests) == 2
    for word in (COMPANY, "はるかぜ", "架空農園", DISPLAY_NAME, "山川", "谷口"):
        assert word not in sent


def test_a_name_in_a_tool_result_stops_the_next_request():
    leaky = PIECES + [("a3", "S01", "谷口さんに習った。", ["修業"])]
    client = FakeClient([
        tool_response(("t1", "read_seat", {"seat_id": "S01"})),
        text_response({"utterance_ids": []}),
    ])
    with pytest.raises(GateError, match="name_in_request"):
        find(Gate(client, names()), entries(leaky), "問い")
    assert len(client.requests) == 1


def test_an_answer_that_is_not_an_object_is_unavailable():
    from ebino.gate import ModelUnavailable

    with pytest.raises(ModelUnavailable, match="bad_output"):
        find(Gate(FakeClient([text_response(["a1"])]), names()), entries(), "問い")
