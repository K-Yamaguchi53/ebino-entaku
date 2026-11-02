"""The moderator and one round: librarian -> moderator -> guard (SPEC 5-1, 6,
7-3, 14-51). Everything here is invented."""

import json

from fake_client import FakeClient, text_response, tool_response

from conftest import COMPANY, DISPLAY_NAME, make_seat
from ebino import moderator, roundtable
from ebino.gate import Gate, NameList
from ebino.guard import Guard
from ebino.index import build_index
from ebino.ingest.utterance import Utterance
from ebino.texts import MODEL_UNAVAILABLE, PLANTED_FAKE_QUOTE, load_text

SEATS = [
    make_seat(seat_id="S01"),  # 理容師, はるかぜ理容, 山川さん.
    make_seat(seat_id="S02", title="農家", company="架空農園", display_name="谷口さん", district="北地区"),
    make_seat(seat_id="S03", title="保育士", company="架空保育園", display_name="森川さん", district="南地区"),
]
PIECES = [
    ("a1", "S01", "休みは決めて取ります。月曜は必ず休みです。"),
    ("a2", "S01", "朝は七時に店を開けます。"),
    ("a3", "S01", "休みの日は川で釣りをします。"),
    ("b1", "S02", "畑は天気しだいなので、休みは空いたら取ります。"),
    ("c1", "S03", "子どもの声で元気が出ます。"),
]
UTTERANCES = [Utterance(id=i, seat_id=s, kind="adult", section="本文", voice="article", text=t, paragraph="")
              for i, s, t in PIECES]
ENTRIES = build_index(UTTERANCES, SEATS, {})
QUESTION = "休みの日って、みんな何してる？"


def names():
    return NameList.build(SEATS, {})


def librarian_finds(*ids):
    return text_response({"utterance_ids": list(ids)})


def moderator_says(quotes, splits=()):
    return text_response({
        "quotes": [{"utterance_id": i, "text": t} for i, t in quotes],
        "splits": [{"heading": h, "side_a": list(a), "side_b": list(b)} for h, a, b in splits],
    })


def run(answers, plant=False):
    client = FakeClient(answers)
    guard = Guard(UTTERANCES)
    result = roundtable.run(Gate(client, names()), ENTRIES, guard, QUESTION, plant=plant)
    return result, client, guard


SPLIT = ('ここで割れた：休みを"決めて取る"人と"空いたら取る"人', ["a1"], ["b1"])


def test_an_answered_round_shows_the_pieces_own_words_in_order_with_a_split():
    result, client, _ = run([
        librarian_finds("a1", "b1", "c1"),
        moderator_says([("b1", "畑は天気しだいなので、休みは空いたら取ります。"),
                        ("a1", "休みは決めて取ります。")], [SPLIT]),
    ])
    assert result.status == "answered"
    assert [q.utterance_id for q in result.quotes] == ["b1", "a1"]
    assert result.seat_order == ["S02", "S01"] and result.answered_seats == 2
    assert result.quotes[1].text == "休みは決めて取ります。"
    assert [(s.side_a, s.side_b) for s in result.splits] == [(("a1",), ("b1",))]
    assert (result.guard_passed, result.guard_stopped) == (2, 0)
    assert [r["model"] for r in client.requests] == ["claude-sonnet-5-5", "claude-opus-5-5"]


def test_the_moderator_gets_only_the_librarians_pieces_and_no_company_or_name():
    _, client, _ = run([librarian_finds("a1", "b1"), moderator_says([])])
    data = json.loads(client.requests[1]["messages"][0]["content"])
    assert data["question"] == QUESTION
    assert [p["utterance_id"] for p in data["pieces"]] == ["a1", "b1"]
    sent = client.all_sent()
    for word in (COMPANY, "はるかぜ", "架空農園", "架空保育園", DISPLAY_NAME, "山川", "谷口", "森川"):
        assert word not in sent


def test_the_instruction_and_the_data_are_kept_apart():
    request = moderator.request_for(QUESTION, ENTRIES[:1])
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert QUESTION not in request["system"][0]["text"]
    assert "a1" not in request["system"][0]["text"]


def test_a_quote_the_piece_does_not_hold_or_cut_mid_sentence_is_not_shown():
    result, _, guard = run([
        librarian_finds("a1", "a2", "b1"),
        moderator_says([("a1", "休みは決めて"),  # Cut inside a sentence.
                        ("a2", "朝は六時に店を開けます。"),  # Not what was said.
                        ("b1", "休みは空いたら取ります。")]),  # Starts mid-sentence.
    ])
    assert result.status == "silent" and result.quotes == []
    assert (result.guard_passed, result.guard_stopped) == (0, 3)
    assert guard.tally.reasons == {"not_sentence_bounded": 2, "not_in_source": 1}


def test_a_split_needs_shown_words_on_both_sides():
    result, _, _ = run([
        librarian_finds("a1", "b1"),
        moderator_says([("a1", "休みは決めて取ります。"), ("b1", "作り話です。")], [SPLIT]),
    ])
    assert [q.utterance_id for q in result.quotes] == ["a1"]
    assert result.splits == [] and result.splits_dropped == 1


def test_a_heading_with_a_name_is_dropped():
    result, _, _ = run([
        librarian_finds("a1", "b1"),
        moderator_says([("a1", "休みは決めて取ります。"),
                        ("b1", "畑は天気しだいなので、休みは空いたら取ります。")],
                       [("山川と谷口で割れた", ["a1"], ["b1"])]),
    ])
    assert result.splits == [] and result.splits_dropped == 1


def test_seats_and_quotes_per_seat_are_capped_and_the_seat_comes_from_the_piece():
    answer = {"quotes": [{"utterance_id": i, "text": "x"} for i in ("a1", "a2", "a3", "a1", "zz")],
              "splits": []}
    plan = moderator.clean(answer, ENTRIES)
    assert [q.utterance_id for q in plan.quotes] == ["a1", "a2"]  # Two per seat, zz unknown.


def test_no_pieces_found_is_silent_without_calling_the_moderator():
    result, client, _ = run([librarian_finds()])
    assert result.status == "silent" and result.answered_seats == 0
    assert len(client.requests) == 1
    assert result.message == ""  # Silence shows only the count, no words.


def test_a_refusal_shows_the_fixed_sentence_and_is_not_silence():
    result, _, _ = run([librarian_finds("a1"), text_response("", stop_reason="refusal")])
    assert result.status == "unavailable" and result.reason == "refusal"
    assert result.message == load_text(MODEL_UNAVAILABLE)
    assert result.quotes == []


def test_a_name_in_the_question_stops_the_round_before_any_request():
    client = FakeClient([librarian_finds("a1")])
    result = roundtable.run(Gate(client, names()), ENTRIES, Guard(UTTERANCES), "山川さんの休みは？")
    assert (result.status, result.reason) == ("unavailable", "name_in_request")
    assert client.requests == []


def test_the_fixed_sentence_is_neither_a_command_nor_an_evaluation():
    text = load_text(MODEL_UNAVAILABLE)
    assert text and "答えた席" not in text
    for word in ("しなさい", "してみたら", "べき", "よくできました", "すごい"):
        assert word not in text


def test_a_planted_fake_is_stopped_by_the_real_guard_and_kept_out_of_the_counts():
    result, _, guard = run([
        librarian_finds("a1"),
        moderator_says([("a1", "休みは決めて取ります。")]),
    ], plant=True)
    assert result.planted_stopped == [load_text(PLANTED_FAKE_QUOTE)] and result.planted_passed == 0
    assert (result.guard_passed, result.guard_stopped) == (1, 0)
    assert guard.tally.planted_stopped == 1 and guard.tally.stopped == 0


def test_the_librarian_tool_loop_runs_inside_a_round():
    result, client, _ = run([
        tool_response(("t1", "search", {"words": ["休み"], "kind": "", "district": ""})),
        librarian_finds("a1"),
        moderator_says([("a1", "月曜は必ず休みです。")]),
    ])
    assert result.status == "answered" and result.quotes[0].text == "月曜は必ず休みです。"
    assert len(client.requests) == 3
