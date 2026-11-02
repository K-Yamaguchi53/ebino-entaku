"""The moderator and one round: librarian -> moderator -> guard (SPEC 5-1, 6,
7-3, 14-51). Everything here is invented."""

import json

from fake_client import FakeClient, text_response, tool_response

from conftest import COMPANY, DISPLAY_NAME, make_seat
from ebino import editor, moderator, roundtable
from ebino.gate import Gate, NameList
from ebino.guard import Guard
from ebino.index import build_index
from ebino.ingest.utterance import Utterance
from ebino.texts import MODEL_UNAVAILABLE, NAME_IN_QUESTION, PLANTED_FAKE_QUOTE, load_text

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


def moderator_says(quotes, splits=(), silent=()):
    return text_response({
        "quotes": [{"utterance_id": i, "text": t} for i, t in quotes],
        "splits": [{"heading": h, "side_a": list(a), "side_b": list(b)} for h, a, b in splits],
        "silent_seat_ids": list(silent),
    })


def editor_says(ask=(), rephrase=""):
    return text_response({"ask_seat_ids": list(ask), "rephrase": rephrase})


def run(answers, plant=False, question=QUESTION):
    client = FakeClient(answers)
    guard = Guard(UTTERANCES)
    result = roundtable.run(Gate(client, names()), ENTRIES, SEATS, guard, question, plant=plant)
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


def test_no_company_or_name_reaches_the_moderator_or_the_editor():
    _, client, _ = run([librarian_finds("a1", "b1"), moderator_says([]), editor_says(["S02"])])
    assert [r["model"] for r in client.requests] == ["claude-sonnet-5-5", "claude-opus-5-5", "claude-sonnet-5-5"]
    data = json.loads(client.requests[1]["messages"][0]["content"])
    assert data["question"] == QUESTION
    assert [p["utterance_id"] for p in data["pieces"]] == ["a1", "b1"]
    assert data["seats"][1] == {"seat_id": "S02", "kind": "adult", "title": "農家", "district": "北地区"}
    sent = client.all_sent()
    for word in (COMPANY, "はるかぜ", "架空農園", "架空保育園", DISPLAY_NAME, "山川", "谷口", "森川", "2026"):
        assert word not in sent


def test_the_instruction_and_the_data_are_kept_apart():
    request = moderator.request_for(QUESTION, ENTRIES[:1], SEATS)
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
    result, client, _ = run([librarian_finds(), editor_says()])
    assert result.status == "silent" and result.answered_seats == 0
    assert [r["model"] for r in client.requests] == ["claude-sonnet-5-5", "claude-sonnet-5-5"]
    assert result.message == ""  # Silence shows only the count, no words.
    assert result.card.origin == "no_answer" and result.card.text == QUESTION


# --- silent seats and question cards (SPEC 5-1, 14-12, 14-13) ---

def test_related_seats_without_words_are_silent_and_answered_ones_are_not():
    result, _, _ = run([
        librarian_finds("a1", "b1"),
        moderator_says([("a1", "休みは決めて取ります。")], silent=["S03", "S01", "Z99"]),
    ])
    # S01 spoke, Z99 is not a seat, so only S03 shows 「まだ誰も聞いていない」.
    assert result.silent_seats == ["S03"]
    assert result.card is None  # A card is made by itself only when no seat answered.


def test_a_seat_whose_quote_the_guard_stopped_is_neither_answered_nor_silent():
    result, _, _ = run([
        librarian_finds("a1", "b1"),
        moderator_says([("a1", "休みは決めて取ります。"), ("b1", "作り話です。")], silent=["S02"]),
    ])
    assert result.seat_order == ["S01"] and result.silent_seats == []


def test_when_no_seat_answers_the_question_becomes_a_card_with_a_back():
    result, client, _ = run([
        librarian_finds("a1"),
        moderator_says([("a1", "作り話です。")], silent=["S03"]),
        editor_says(["S02", "S02", "Z99", "S03"], "休みの取り方を、どうやって決めてきましたか"),
    ], question="休みは何日？")
    assert result.status == "silent" and result.silent_seats == ["S03"]
    card = result.card
    assert (card.origin, card.text, card.seat_id) == ("no_answer", "休みは何日？", "")
    assert card.card_id.startswith("q-") and len(card.card_id) == 10
    assert card.back.ask_seat_ids == ("S02", "S03")
    assert card.back.rephrase == "休みの取り方を、どうやって決めてきましたか"
    assert card.front() == {"card_id": card.card_id, "origin": "no_answer", "text": "休みは何日？", "seat_id": ""}
    assert client.requests[2]["output_config"]["effort"] == "low"


def test_the_back_of_a_card_drops_a_rephrase_with_a_name_or_too_long():
    gate = Gate(FakeClient([editor_says([], "山川さんに休みを聞く"), editor_says([], "あ" * 81)]), names())
    assert editor.write_back(gate, "休みは？", SEATS).rephrase == ""
    assert editor.write_back(gate, "休みは？", SEATS).rephrase == ""


def test_a_card_is_still_made_when_the_editor_fails():
    result, _, _ = run([librarian_finds(), text_response("", stop_reason="refusal")])
    assert result.status == "silent"
    assert result.card.text == QUESTION and result.card.back == editor.Back(reason="refusal")


def test_a_student_writes_a_card_at_a_silent_seat():
    client = FakeClient([editor_says(["S03"])])
    card = editor.card_from_student(Gate(client, names()), "S03", "  子どもと話すとき、何に気をつけますか  ", SEATS)
    assert (card.origin, card.seat_id, card.text) == ("student", "S03", "子どもと話すとき、何に気をつけますか")
    assert editor.card_from_student(Gate(client, names()), "S03", "   ", SEATS) is None
    assert editor.card_from_student(Gate(client, names()), "Z99", "問い", SEATS) is None


def test_a_name_in_a_students_card_keeps_the_card_but_never_reaches_the_editor():
    client = FakeClient([editor_says()])
    card = editor.card_from_student(Gate(client, names()), "S03", "森川さんは休みに何をしますか", SEATS)
    assert card.text == "森川さんは休みに何をしますか"  # People read cards before they go out.
    assert card.back.reason == "name_in_request"
    assert client.requests == []


def test_a_refusal_shows_the_fixed_sentence_and_is_not_silence():
    result, _, _ = run([librarian_finds("a1"), text_response("", stop_reason="refusal")])
    assert result.status == "unavailable" and result.reason == "refusal"
    assert result.message == load_text(MODEL_UNAVAILABLE)
    assert result.quotes == []


def test_a_name_in_the_question_asks_again_without_calling_any_model():
    client = FakeClient([librarian_finds("a1"), editor_says()])
    gate = Gate(client, names())
    result = roundtable.run(gate, ENTRIES, SEATS, Guard(UTTERANCES), "谷口さんの休みは？")
    assert (result.status, result.reason) == ("ask_again", "name_in_question")
    assert result.message == load_text(NAME_IN_QUESTION)
    assert result.message != load_text(MODEL_UNAVAILABLE)
    assert client.requests == [] and (gate.sent, gate.stopped) == (0, 0)
    assert result.card is None  # No question card for this.
    # Which word hit is kept nowhere, and neither is the question.
    kept = json.dumps(vars(result), ensure_ascii=False, default=str)
    assert "谷口" not in kept and "山川" not in kept


def test_a_question_without_a_name_runs_as_before():
    result, client, _ = run([librarian_finds("a1"), moderator_says([("a1", "休みは決めて取ります。")])],
                            question="お店の休みはどう決めますか")
    assert result.status == "answered" and len(client.requests) == 2


def test_the_ask_again_sentence_names_no_word_and_does_not_say_wait():
    text = load_text(NAME_IN_QUESTION)
    assert text and "時間をおく" not in text and "答えた席" not in text


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
