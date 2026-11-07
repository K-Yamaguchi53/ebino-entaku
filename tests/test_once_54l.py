"""直し54l (the teacher, 11/8, on screen): a bubble that mixed the person's
talk with the writer's words about them; a bubble pressed shown on the marks
by its kind only; 「よくわからない」 lit as 「自分の言葉で分けて言えている」;
the sheet's line that only pointed at 今日、光ったところ. Everything here is
invented."""

import random

from fake_client import FakeClient

from ebino import app as app_module, hitokoto, speaker
from ebino.gate import Gate, NameList
from ebino.ingest.utterance import Utterance, mend_reading
from ebino.session import ARTICLE_TITLE, TRAIL_WORDS, Library, Session
from test_session import ANSWERED, SEATS, UTTERANCES
from test_speaker import names_gate

HITOKOTO_JS = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")


# --- one voice in a bubble ---

def test_a_sentence_ending_on_the_masked_name_ends_on_its_verb():
    assert mend_reading("工場見学をきっかけに、この職場に就職したこの方。当初は事務員ではなかった。") \
        == "工場見学をきっかけに、この職場に就職した。当初は事務員ではなかった。"
    assert mend_reading("町で店を開いたこの方！") == "町で店を開いた！"
    for text in ("この方。", "代表：この方。", "と語るこの方は、", "この方の夢。"):
        assert mend_reading(text) == text


def test_spoken_words_that_still_talk_about_the_person_or_the_interview_are_stopped():
    original = "「責任のある立場として」この方はインタビューの中で何度もそう口にした。"
    assert speaker.stop_reason("「責任のある立場として」って、わたしはインタビューの中で何度もそう言ってたんだよね。",
                               original, original, names_gate()) == speaker.STOP_NARRATOR
    assert speaker.stop_reason("「責任のある立場として」この方は何度もそう言ってたんだ。",
                               original, original, names_gate()) == speaker.STOP_NARRATOR


def test_one_piece_stopped_puts_the_whole_bubble_in_its_original_words():
    talk = speaker.Spoken("a", "決めて取る。", "決めて取るんだ。")
    stopped = speaker.Spoken("b", "この方は笑う。", "", speaker.STOP_NARRATOR)
    assert speaker.one_voice([talk]) == [talk]
    out = speaker.one_voice([talk, stopped])
    assert [r.spoken for r in out] == ["", ""]
    assert [r.reason for r in out] == [speaker.STOP_OTHER, speaker.STOP_NARRATOR]
    assert out[0].original == "決めて取る。"


def _session(answers=()):
    lib = Library.build(SEATS, UTTERANCES, {}, False)
    return Session(lib, Gate(FakeClient(list(answers)), NameList.build(SEATS, {})), rng=random.Random(1))


def test_an_articles_title_is_not_in_the_bubble_when_the_item_has_other_words():
    seat = SEATS[0].seat_id if hasattr(SEATS[0], "seat_id") else "a"
    title = Utterance("t1", seat, "article", ARTICLE_TITLE, "about", "事務の力で頑張りを利益に", "事務の力で頑張りを利益に")
    body = Utterance("t2", seat, "article", "本文", "about", "工場見学をきっかけに就職した。", "工場見学をきっかけに就職した。")
    session = _session()
    shown, said, _, _ = session.one_shown([title, body])
    assert [u.id for u in shown] == ["t2"] and said == ["工場見学をきっかけに就職した。"]
    shown, _, _, _ = session.one_shown([title])  # Nothing else: the title as before.
    assert [u.id for u in shown] == ["t1"]


# --- the marks: a bubble pressed, by its words ---

def test_a_bubble_pressed_comes_on_the_trail_with_the_words_it_showed():
    session = _session([*ANSWERED, *ANSWERED])
    session.ask("休みの日って、みんな何してる？")
    session.bubble_opened(1, "a1")
    item = session.trail_view()["items"][1]
    result = session.rounds[0]
    quote = next(q for q in result.quotes if q.utterance_id == "a1")
    spoken = result.spoken.get("a1")
    words = (spoken.spoken if spoken and spoken.spoken else quote.text).replace("\n", "")
    assert item["kind"] == "opened" and item["text"]
    assert item["text"] == (words if len(words) <= TRAIL_WORDS else words[:TRAIL_WORDS] + "…")
    assert "item.text || item.label" in HITOKOTO_JS


def test_the_sheets_line_shows_its_words_and_the_heading_beside_them():
    assert 'const li = el("li", "", text);' in HITOKOTO_JS
    assert 'el("li", "", ref ? null : text)' not in HITOKOTO_JS


# --- the light: never 「わからない」 ---

def test_words_that_say_nothing():
    for text in ("よくわからない", "わからない。", "まだ分からないです", "特にない", "なし", "？", "わかんない笑", ""):
        assert hitokoto.says_nothing(text), text
    for text in ("わからないことが分かった", "何をしたいかが増えた", "農業", "知らない仕事が多い"):
        assert not hitokoto.says_nothing(text), text


def test_code_never_lights_a_dont_know():
    question = "休みの日って、みんな何してる？"
    talk = hitokoto.Hitokoto(question)
    talk.scale, talk.forward = 13, "よくわからない"
    talk.written = [{"step": "forward", "text": talk.forward}]
    light = hitokoto.code_light(talk, "test")
    assert light.quote != "よくわからない"
    assert (light.quote, light.force, light.source) == (question, 1, "first")
    assert hitokoto.light_words(talk) == []
