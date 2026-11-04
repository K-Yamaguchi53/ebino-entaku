"""直し31-7: the round's bubbles as if the person were talking, checked by
code before they are shown; the original kept beside them and always
readable. Everything here is invented."""

import json
import random

import anthropic
import httpx2
import pytest
from fake_client import FakeClient, text_response

from ebino import app as app_module
from ebino import gate, speaker
from ebino.gate import Gate, NameList
from ebino.records import Records
from ebino.session import Session
from test_session import ANSWERED, SEATS, library

APP = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
QUESTION = "休みの日って、みんな何してる？"
PARAGRAPH = "この方は「休みは決めて取ります。」と話す。"


@pytest.fixture(autouse=True)
def speaker_on(monkeypatch):
    monkeypatch.setenv("EBINO_SPEAKER", "1")


def test_ebino_speaker_0_turns_it_off(monkeypatch):
    monkeypatch.setenv("EBINO_SPEAKER", "0")
    session, client = sitting(ANSWERED)
    view = session.ask(QUESTION)
    assert len(client.requests) == 2 and all(q["spoken"] == "" for q in view["quotes"])


def says(**lines):
    return text_response({"lines": [{"id": key, "text": text} for key, text in lines.items()]})


def sitting(answers, tmp_path=None):
    client = FakeClient(list(answers))
    session = Session(library(), Gate(client, NameList.build(SEATS, {})), rng=random.Random(1),
                      records=Records(tmp_path) if tmp_path else None)
    return session, client


def names_gate():
    return Gate(FakeClient([]), NameList.build(SEATS, {}))


# --- the code's checks ---

ORIGINAL = "休みは決めて取ります。決めておかないと、ずっと店に立ってしまうので。"


def check(spoken, original=ORIGINAL, paragraph=PARAGRAPH):
    return speaker.stop_reason(spoken, original, paragraph, names_gate())


def test_endings_and_the_first_person_pass():
    assert check("休みは決めて取るんだ。決めておかないと、ずっと店に立っちゃうからね。") == ""
    assert check("ぼくは、休みは決めて取るんだよね。決めておかないと、ずっと店に立っちゃうから。") == ""


def test_a_number_not_in_the_paragraph_keeps_the_original():
    assert check("休みは月に2回、決めて取るんだ。") == speaker.STOP_NUMBER
    assert check("休みは三回決めて取るんだ。") == speaker.STOP_NUMBER


def test_a_kanji_or_katakana_word_not_in_the_paragraph_keeps_the_original():
    assert check("休日は決めて取るんだ。") == speaker.STOP_WORD  # 休日: not in the paragraph.
    assert check("休みはスケジュールで決めるんだ。") == speaker.STOP_WORD
    assert check("自分で、休みは決めて取るんだ。") == ""  # A spoken word from texts/spoken_allowed.txt.
    # Only as a whole word: inside a longer run of kanji it is checked as that run.
    assert check("大事故で、休みは決めて取るんだ。") == speaker.STOP_WORD
    assert check("一番星を見て、休みは決めて取るんだ。") in (speaker.STOP_WORD, speaker.STOP_NUMBER)


def test_too_long_or_a_name_keeps_the_original():
    assert check("休みは決めて取るんだ。決めて取るんだよ。本当に決めて取るんだ。決めておかないと、ずっと店に立っちゃうんだよね。")         == speaker.STOP_LONG
    assert check("山川は、休みは決めて取る。") == speaker.STOP_NAME


# --- a round ---

SPOKEN = says(a1="休みは決めて取るんだ。", a2="月曜は必ず店を閉めるんだよね。", b1="畑は天気しだいなので、休みは空いたら取るんだ。")


def test_the_bubbles_go_in_one_request_with_their_limit_and_come_back_spoken(tmp_path):
    session, client = sitting(ANSWERED + [SPOKEN], tmp_path)
    view = session.ask(QUESTION)
    request = client.requests[-1]
    assert request["model"] == "claude-haiku-5-5" and request["output_config"]["effort"] == "low"
    assert gate.MODELS["speaker"] == "claude-haiku-5-5" and gate.EFFORT["speaker"] == "low"
    assert client.options[-1] == {"timeout": 8.0, "max_retries": 0}
    assert len(client.requests) == 3  # librarian, moderator, one for all the bubbles.
    shown = {q["utterance_id"]: q for q in view["quotes"]}
    assert shown["a1"]["spoken"] == "休みは決めて取るんだ。" and shown["a1"]["text"] == "休みは決めて取ります。"
    # The record keeps both, which was shown, and why the original was kept.
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    kept = {item["utterance_id"]: item for item in record["spoken"]}
    assert kept["a1"] == {"utterance_id": "a1", "shown": "spoken", "original": "休みは決めて取ります。",
                          "spoken": "休みは決めて取るんだ。", "reason": "", "round": 1}


def test_a_bubble_that_fails_a_check_keeps_its_original_and_the_others_do_not():
    bad = says(a1="休日は決めて取るんだ。", a2="月曜は必ず店を閉めるんだよね。", b1="畑は天気しだいなので、休みは空いたら取るんだ。")
    session, _ = sitting(ANSWERED + [bad])
    shown = {q["utterance_id"]: q for q in session.ask(QUESTION)["quotes"]}
    assert shown["a1"]["spoken"] == "" and shown["a2"]["spoken"]
    assert session.rounds[0].spoken["a1"].reason == speaker.STOP_WORD


def test_past_the_limit_every_bubble_keeps_its_original():
    timed_out = anthropic.APITimeoutError(request=httpx2.Request("POST", "https://api.invalid/v1/messages"))
    session, _ = sitting(ANSWERED + [timed_out])
    view = session.ask(QUESTION)
    assert view["status"] == "answered" and all(q["spoken"] == "" for q in view["quotes"])
    assert {s.reason for s in session.rounds[0].spoken.values()} == {"api_error:APITimeoutError"}


def test_no_name_is_sent_and_a_name_in_the_words_stops_the_request():
    session, client = sitting(ANSWERED + [SPOKEN])
    session.ask(QUESTION)
    sent = json.dumps(client.requests[-1], ensure_ascii=False)
    for seat in SEATS:
        assert not seat.company or seat.company not in sent
        assert "山川" not in sent and "谷口" not in sent
    # A piece that names someone never leaves: the gate stops it, the originals stay.
    named = speaker.speak(names_gate(), [{"id": "x", "voice": "spoken", "text": "山川さんに聞いた。", "paragraph": ""}])
    assert named[0].spoken == "" and named[0].reason == "name_in_request"


def test_the_screen_shows_spoken_words_marked_and_the_note_with_the_original():
    assert "const text = quote.spoken || quote.text;" in MAP and "spokenMark(node, quote);" in MAP
    assert "quote.said && !quote.spoken" in MAP  # No 「」 round spoken words.
    render = APP[APP.index("function renderQuote("):]
    render = render[:render.index("\n}\n")]
    assert "state.texts.spoken_mark" in render and "{ ...quote.source, note: \"\" }" in render
    assert ": null," not in render  # node.append would write a null out as "null".
    assert "quote.spoken && quote.source.note" in render  # The note goes with the paragraph.
    assert "state.texts.spoken_note" in APP and "state.spokenNoted" in APP
