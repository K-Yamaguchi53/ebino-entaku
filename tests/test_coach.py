"""コーチとオブザーバー (SPEC 5-1, 14-60). Every seat, piece, question and
answer here is invented."""

import json
import random
from pathlib import Path

import anthropic
import httpx2
import pytest
from fake_client import FakeClient, text_response

from conftest import COMPANY, DISPLAY_NAME
from ebino import coach, harvest, reflection, texts
from ebino.banned_words import BANNED_WORDS
from ebino.gate import Gate, NameList
from ebino.ingest.seats import load_seats
from ebino.records import Records, summary
from ebino.session import Library, Refused, Session, _sheet_heading
from ebino.texts import AI_QUESTION_BADGE, COACH_LABEL, OBSERVER_LABEL, load_lines, load_text
from test_session import ANSWERED, SEATS, UTTERANCES, editor_says, librarian_finds, moderator_says

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
QUESTION = "休みの日って、みんな何してる？"
GOOD_COACH = "「休みは決めて取ります。」と話す人がいたけれど、あなたはいつ休みを決める？"
GOOD_OBSERVER = "休みを決めて取る働き方は、誰の役に立っているのだろう？"
# S03 (保育士, 森川さん) is the coach's seat, kept off the map.
COACH_SEATS = {"S03": False}


def coach_says(**cards):
    return text_response(cards)


def sitting(answers, coach_seats=COACH_SEATS, coach_on=True, tmp_path=None):
    client = FakeClient(list(answers))
    lib = Library.build(SEATS, UTTERANCES, {}, coach_seats=coach_seats, coach_on=coach_on)
    session = Session(lib, Gate(client, NameList.build(SEATS, {})), rng=random.Random(1),
                      records=Records(tmp_path) if tmp_path else None)
    return session, client


def round_one(cards, coach_seats=COACH_SEATS, tmp_path=None, more=()):
    session, client = sitting(ANSWERED + [coach_says(**cards)] + list(more), coach_seats, tmp_path=tmp_path)
    session.ask(QUESTION)
    return session, client


def sent(client, index=-1) -> str:
    return json.dumps(client.requests[index], ensure_ascii=False)


# --- the code's check: what never reaches the screen ---

@pytest.mark.parametrize("text, reason", [
    ("「休みは月に二回です。」と聞いて、あなたはどう考える？", "quote_not_in_record"),
    ("休みは決めて取るほうが楽だと思わない？", "lure_form"),
    ("休みは自分で決めるものじゃない？", "lure_form"),
    ("休みは大事だよね？", "lure_form"),
    ("休みは決めて取る、それとも空いたら取る？", "lure_form"),
    ("休みのことを、もう一度聞いてみませんか？", "lure_form"),
    ("次は、休みの取り方を聞こうよね？", "banned_word"),
    ("休みの取り方を、席の人に確かめてみたら？", "banned_word"),
    ("あなたに向いている休み方は、どれだと考える？", "banned_word"),
    ("休みを決める理由を、あなたはどう考えるか。", "not_one_question"),
    ("休みは大事。あなたは、なぜそう考える？", "not_one_question"),
    ("休みが2日あったら、あなたは何をする？", "number"),
    ("あ" * 60 + "？", "too_long"),  # 61 characters.
    ("森川さんは休みに何をしていると思う？", "name"),
])
def test_a_question_the_check_stops(text, reason):
    session, _ = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER})
    assert coach.stop_reason(text, coach.Record(session, 1), session.gate) == reason


@pytest.mark.parametrize("text", [
    GOOD_COACH, GOOD_OBSERVER,
    "あ" * 59 + "？",  # 60 characters.
    "「理容師」の席の言葉で、あなたが一番気になったのはどこ？",
    "「休みは決めて取ります。」と、「畑は天気しだいなので、休みは空いたら取ります。」は、どこが違う？",
])
def test_a_question_the_check_lets_through(text):
    session, _ = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER})
    reason = coach.stop_reason(text, coach.Record(session, 1), session.gate)
    assert reason == ("too_long" if len(text) > coach.MAX_CHARS else "")


def test_both_cards_pass_and_come_in_the_fixed_order_with_their_lines():
    session, client = round_one({"observer": GOOD_OBSERVER, "coach": GOOD_COACH})
    view = session.coach_band(1)
    assert [card["role"] for card in view["cards"]] == ["coach", "observer"]
    # 直し46: the short name on every card (what each does is on the host's page).
    assert view["cards"][0] == {"role": "coach", "label": "コーチ（AI）",
                                "badge": load_text(AI_QUESTION_BADGE), "question": GOOD_COACH}
    assert view["cards"][1]["label"] == "オブザーバー（AI）"
    assert load_text(COACH_LABEL).startswith("コーチ") and load_text(OBSERVER_LABEL).startswith("オブザーバー")
    assert "｜" not in view["cards"][0]["label"] + view["cards"][1]["label"]
    assert view["answered"] == ""
    assert session.coach_band(1) == view and len(client.requests) == 3  # Asked once.


def test_one_card_stopped_shows_the_other_only_and_counts_the_stop(tmp_path):
    session, _ = round_one({"coach": "休みは決めて取るほうがいいよね？", "observer": GOOD_OBSERVER},
                           tmp_path=tmp_path)
    view = session.coach_band(1)
    assert [card["question"] for card in view["cards"]] == [GOOD_OBSERVER]
    band = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8")
                      )["rounds"][0]["band"]
    assert band["shown"] == [{"role": "observer", "text": GOOD_OBSERVER}]
    assert band["stopped"] == {"banned_word": 1} and band["answered"] == ""
    assert "ほうがいい" not in json.dumps(band, ensure_ascii=False)  # Stopped words are never kept.


def test_both_cards_stopped_means_no_band():
    session, _ = round_one({"coach": "休みは大事だよね？", "observer": "あ" * 61 + "？"})
    view = session.coach_band(1)
    assert view["cards"] == []
    assert session.rounds[0].band.status == coach.STATUS_STOPPED
    assert session.rounds[0].band.stopped == {"lure_form": 1, "too_long": 1}


def test_no_model_means_no_band():
    session, _ = sitting(ANSWERED + [RuntimeError("down")])
    session.ask(QUESTION)
    assert session.coach_band(1)["cards"] == []
    assert session.rounds[0].band.status == coach.STATUS_UNAVAILABLE


def timed_out() -> Exception:
    """What the SDK raises when the wait runs out (no request text in it)."""
    return anthropic.APITimeoutError(request=httpx2.Request("POST", "https://api.invalid/v1/messages"))


def test_a_band_past_the_wait_limit_is_not_shown_and_the_next_question_is_answered(tmp_path):
    session, client = sitting(ANSWERED + [timed_out()] + ANSWERED, tmp_path=tmp_path)
    session.ask(QUESTION)
    assert session.coach_band(1)["cards"] == []
    band = session.rounds[0].band
    assert band.status == coach.STATUS_UNAVAILABLE and band.reason == "api_error:APITimeoutError"
    view = session.ask("休みを決めるのは、自分？")
    assert view["status"] == "answered" and view["round"] == 2
    # The band's call has its wait limit, with no retry; so does every call
    # the screen waits on (直し31-1).
    assert client.options[2] == {"timeout": 30.0, "max_retries": 0}
    assert all(option.get("max_retries") == 0 for option in client.options)
    kept = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8")
                      )["rounds"][0]["band"]
    assert kept["status"] == coach.STATUS_UNAVAILABLE and kept["shown"] == [] and kept["stopped"] == {}


def test_a_silent_round_has_a_band_too():
    session, _ = sitting([librarian_finds(), editor_says(), coach_says(coach=GOOD_OBSERVER, observer=GOOD_OBSERVER)])
    session.ask("やってみて合わなかった人は？")
    assert len(session.coach_band(1)["cards"]) == 2


def test_a_round_that_asked_again_has_no_band():
    session, _ = sitting([])
    session.ask("谷口さんの休みは？")
    with pytest.raises(Refused):
        session.coach_band(1)


def test_ebino_coach_0_turns_the_band_off(monkeypatch):
    monkeypatch.setenv("EBINO_COACH", "0")
    session, client = sitting(ANSWERED, coach_on=None)
    session.ask(QUESTION)
    assert session.coach_band(1) == {"round": 1, "cards": [], "answered": ""}
    assert len(client.requests) == 2  # The round only: no model was asked for a band.


def test_the_band_is_on_unless_ebino_coach_is_0(monkeypatch):
    monkeypatch.delenv("EBINO_COACH", raising=False)
    assert Library.build(SEATS, UTTERANCES, {}).coach_on is True
    monkeypatch.setenv("EBINO_COACH", "1")
    assert Library.build(SEATS, UTTERANCES, {}).coach_on is True


# --- coach.tsv: the coach's source, and seats kept off the map ---

def test_a_seat_kept_off_the_map_is_on_neither_the_map_nor_the_moderators_list():
    session, client = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER})
    assert "S03" not in [seat["seat_id"] for seat in session.library.seat_list()]
    assert all(entry.seat_id != "S03" for entry in session.library.entries)
    moderator_data = json.loads(client.requests[1]["messages"][0]["content"])
    assert "S03" not in [seat["seat_id"] for seat in moderator_data["seats"]]
    assert "保育士" not in json.dumps(client.requests[:2], ensure_ascii=False)
    # Its pieces are the coach's source only.
    session.coach_band(1)
    assert json.loads(client.requests[2]["messages"][0]["content"])["coach_sources"] == ["子どもの声で元気が出ます。"]


def test_a_seat_shown_on_the_map_stays_a_seat_and_is_the_coachs_source_too():
    session, client = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER}, coach_seats={"S03": True})
    assert "S03" in [seat["seat_id"] for seat in session.library.seat_list()]
    # A seat the moderator may name (it is sent when its pieces share a topic; 直し31-6).
    assert "S03" in [seat.seat_id for seat in session.library.seats]
    session.coach_band(1)
    assert json.loads(client.requests[2]["messages"][0]["content"])["coach_sources"] == ["子どもの声で元気が出ます。"]


def test_without_coach_tsv_only_the_coach_card_is_left_out():
    session, client = round_one({"observer": GOOD_OBSERVER}, coach_seats={})
    view = session.coach_band(1)
    assert [card["role"] for card in view["cards"]] == ["observer"]
    request = client.requests[2]
    assert list(request["output_config"]["format"]["schema"]["properties"]) == ["observer"]
    assert "coach_sources" not in json.loads(request["messages"][0]["content"])


def test_coach_tsv_is_read_from_the_data_folder(tmp_path):
    assert coach.load_coach(tmp_path, {"S01"}) == {}  # No file.
    (tmp_path / "coach.tsv").write_text("席ID\t地図に出す\n", encoding="utf-8")
    assert coach.load_coach(tmp_path, {"S01"}) == {}  # No rows: no coach card.
    (tmp_path / "coach.tsv").write_text("席ID\t地図に出す\nS01\t0\n", encoding="utf-8")
    assert coach.load_coach(tmp_path, {"S01"}) == {"S01": False}
    for bad in ("S09\t1", "S01\t2"):
        (tmp_path / "coach.tsv").write_text(f"席ID\t地図に出す\n{bad}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="line 2"):
            coach.load_coach(tmp_path, {"S01"})


def test_the_sample_coach_tsv_has_the_same_shape():
    seats = load_seats(SAMPLES / "seats.tsv")
    found = coach.load_coach(SAMPLES, {seat.seat_id for seat in seats})
    assert set(found.values()) == {True, False}


def test_the_name_list_still_holds_a_seat_kept_off_the_map():
    lib = Library.build(SEATS, UTTERANCES, {}, coach_seats=COACH_SEATS, coach_on=True)
    assert "S03" in [seat.seat_id for seat in lib.all_seats]
    assert NameList.build(lib.all_seats, {}).hits("森川さんの話")


# --- what the model is sent ---

def test_the_model_gets_the_record_and_the_coachs_pieces_but_no_name_company_lab_or_subjects():
    session, client = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER})
    session.set_lab("creation")
    session.coach_band(1)
    request = sent(client)
    data = json.loads(client.requests[-1]["messages"][0]["content"])
    assert data["rounds"][0]["question"] == QUESTION
    assert data["rounds"][0]["quotes"][0] == {"seat": "理容師", "text": "休みは決めて取ります。"}
    for word in (COMPANY, "はるかぜ", "架空農園", "架空保育園", DISPLAY_NAME, "山川", "谷口", "森川",
                 "creation", "Creation", "生活文化科", "学ぶ人", "Lab"):
        assert word not in request
    assert client.requests[-1]["model"] == "claude-opus-5-5"


def test_the_instruction_part_names_no_question_of_the_record():
    session, client = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER})
    session.coach_band(1)
    system = client.requests[-1]["system"][0]["text"]
    assert QUESTION not in system and "畑は天気しだい" not in system
    assert load_text("observer_view").splitlines()[0] in system


def test_the_instruction_part_lists_every_banned_word():
    session, client = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER})
    session.coach_band(1)
    system = client.requests[-1]["system"][0]["text"]
    assert "・".join(BANNED_WORDS) in system
    assert all(word in system for word in BANNED_WORDS) and "{banned}" not in system


def round_two_band(second_cards, first_cards=None):
    """Round 1 with its band, then a typed round 2 and its band."""
    first_cards = first_cards or {"coach": "休みは決めて取るほうがいいよね？", "observer": GOOD_OBSERVER}
    session, client = round_one(first_cards, more=ANSWERED + [coach_says(**second_cards)])
    session.coach_band(1)
    session.ask("休みを決めるのは、自分？")
    view = session.coach_band(2)
    return session, client, view


def test_the_second_band_is_sent_the_questions_shown_before_but_not_the_stopped_one():
    session, client, _ = round_two_band({"coach": GOOD_COACH, "observer": GOOD_OBSERVER})
    first = json.loads(client.requests[2]["messages"][0]["content"])
    second = json.loads(client.requests[-1]["messages"][0]["content"])
    assert first["asked_before"] == []
    assert second["asked_before"] == [{"role": "observer", "text": GOOD_OBSERVER}]
    assert "ほうがいい" not in client.requests[-1]["messages"][0]["content"]  # The stopped card.
    assert [r["round"] for r in second["rounds"]] == [1, 2]


def test_the_questions_shown_before_go_in_the_order_they_were_shown():
    session, client, _ = round_two_band({"coach": GOOD_COACH, "observer": GOOD_OBSERVER},
                                        first_cards={"coach": GOOD_COACH, "observer": GOOD_OBSERVER})
    assert json.loads(client.requests[-1]["messages"][0]["content"])["asked_before"] == [
        {"role": "coach", "text": GOOD_COACH}, {"role": "observer", "text": GOOD_OBSERVER}]


def test_a_question_quoting_an_earlier_ai_question_is_not_shown():
    quoting = "「誰の役に立っているのだろう」と聞かれて、あなたが思い出すのは何？"
    session, _, view = round_two_band({"coach": GOOD_COACH, "observer": quoting})
    assert [card["question"] for card in view["cards"]] == [GOOD_COACH]
    assert session.rounds[1].band.stopped == {"quote_not_in_record": 1}


# --- answering ---

def answered_round_two(tmp_path=None, answers=ANSWERED):
    session, client = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER}, tmp_path=tmp_path,
                                more=answers)
    session.coach_band(1)
    view = session.coach_answer(1, "observer", "店を開ける人の役に立っていると思う")
    return session, client, view


def test_an_answer_starts_the_next_round_with_the_question_and_the_answer():
    session, client, view = answered_round_two()
    assert view["round"] == 2 and view["question"] == "店を開ける人の役に立っていると思う"
    assert view["ai_question"] == {"role": "observer", "label": "オブザーバー（AI）", "text": GOOD_OBSERVER}
    librarian = client.requests[3]["messages"][0]["content"]
    assert librarian == f"AIの問い：{GOOD_OBSERVER}\n生徒の答え：店を開ける人の役に立っていると思う"
    moderator = json.loads(client.requests[4]["messages"][0]["content"])
    assert moderator["ai_question"] == GOOD_OBSERVER
    assert moderator["question"] == "店を開ける人の役に立っていると思う"
    assert session.band_view(1)["answered"] == "observer"


def test_a_silent_answer_round_makes_no_question_card():
    session, client, view = answered_round_two(answers=[librarian_finds()])
    assert view["status"] == "silent" and view["answered_seats"] == 0 and view["card"] is None
    assert session.cards == [] and len(client.requests) == 4  # No editor was asked.


def test_a_silent_answer_round_after_the_moderator_makes_no_card_either():
    session, _, view = answered_round_two(answers=[librarian_finds("a1"), moderator_says([])])
    assert view["status"] == "silent" and view["card"] is None and session.cards == []


def test_one_answer_per_band_on_a_card_that_was_shown():
    session, client, _ = answered_round_two()
    with pytest.raises(Refused):
        session.coach_answer(1, "coach", "もう一度")
    other, _ = round_one({"observer": GOOD_OBSERVER}, coach_seats={})
    other.coach_band(1)
    with pytest.raises(Refused):
        other.coach_answer(1, "coach", "答え")  # Not shown.
    with pytest.raises(Refused):
        other.coach_answer(1, "observer", "   ")


def test_a_name_in_the_answer_asks_again_and_calls_no_model():
    session, client = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER})
    session.coach_band(1)
    before = len(client.requests)
    view = session.coach_answer(1, "coach", "谷口さんみたいに決める")
    assert view["status"] == "ask_again" and len(client.requests) == before
    assert session.band_view(1)["answered"] == "" and len(session.rounds) == 1


def test_the_record_keeps_the_questions_the_card_answered_and_the_answer(tmp_path):
    session, _, _ = answered_round_two(tmp_path=tmp_path)
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    first, second = record["rounds"]
    assert first["band"] == {"status": "shown", "reason": "", "asked_roles": ["coach", "observer"],
                             "shown": [{"role": "coach", "text": GOOD_COACH},
                                       {"role": "observer", "text": GOOD_OBSERVER}],
                             "stopped": {}, "answered": "observer", "answer": "店を開ける人の役に立っていると思う"}
    assert second["ai_question"] == {"role": "observer", "text": GOOD_OBSERVER}
    assert second["band"] is None
    assert "ai questions shown / stopped: 2 / 0  answered: 1" in summary([record])


def test_what_was_sent_for_the_band_is_kept_in_two_parts(tmp_path):
    session, client = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER})
    session.coach_band(1)
    Records(tmp_path).save_prompt("x1", "coach", client.requests[-1])
    assert sorted(p.name for p in (tmp_path / "prompts" / "x1").iterdir()) == [
        "01-coach-data.json", "01-coach-instruction.txt"]


def test_an_answer_round_is_not_a_move_on_the_harvest_card():
    session, _, _ = answered_round_two(answers=[librarian_finds()])
    session.reflection = reflection.Reflection("same", "休みは？")
    codes = [move.code for move in harvest.found_moves(session, _sheet_heading)]
    assert "silent_question" not in codes and "asked_after_silence" not in codes


def test_the_reflection_reads_the_answer_as_the_students_but_not_the_ai_question():
    session, _, _ = answered_round_two()
    record = reflection.Record(session)
    answer = record.by_id()["A1"]
    assert answer.kind == "answer" and answer.for_model["asked"] == GOOD_OBSERVER
    assert record.holds("店を開ける人の役に立っている")
    assert not record.holds("誰の役に立っているのだろう")


def _abstract_line(system):
    """The words of the band's line on hard words (直し46: from the table)."""
    head = "次のような、むずかしい言葉を使わない："
    assert system.count(head) == 1
    return system.split(head, 1)[1].split("。", 1)[0].split("・")


def test_the_band_instruction_names_the_abstract_words_of_the_table_and_no_other():
    session, client = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER})
    session.coach_band(1)
    system = client.requests[-1]["system"][0]["text"]
    assert _abstract_line(system) == load_lines(texts.AI_ABSTRACT_WORDS)
    assert "{abstract}" not in system


def test_the_band_instruction_follows_the_table_when_it_changes(monkeypatch):
    real = coach.load_lines
    monkeypatch.setattr(coach, "load_lines", lambda name: ["架空語ア", "架空語イ"]
                        if name == texts.AI_ABSTRACT_WORDS else real(name))
    session, client = round_one({"coach": GOOD_COACH, "observer": GOOD_OBSERVER})
    session.coach_band(1)
    system = client.requests[-1]["system"][0]["text"]
    assert _abstract_line(system) == ["架空語ア", "架空語イ"]
    assert "価値観" not in system and "自己実現" not in system
