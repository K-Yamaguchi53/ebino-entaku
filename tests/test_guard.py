"""The quote guard (SPEC 6, 7-3, 11, 14-15, 14-25). Every text here is invented."""

import pytest

from ebino.guard import (
    STOP_EMPTY,
    STOP_NOT_IN_SOURCE,
    STOP_UNKNOWN_UTTERANCE,
    Guard,
    Quote,
    check,
    plant_fake,
)
from ebino.ingest.utterance import (
    VOICE_ANSWER,
    VOICE_ARTICLE,
    VOICE_OWN,
    VOICE_SPOKEN,
    Utterance,
    split_voice,
)
from ebino.texts import PLANTED_FAKE_QUOTE, load_text

SOURCE = "休みの日は、朝から川で釣りをします。夕方には店に戻って、明日の仕込みをします。"


def piece(id_, text, voice=VOICE_OWN, paragraph=None):
    return Utterance(
        id=id_, seat_id="S01", kind="adult", section="本文", voice=voice,
        text=text, paragraph=paragraph or text,
    )


# --- Passing: a part of the source, made alike the same way ---------------------


@pytest.mark.parametrize(
    "quote",
    [
        SOURCE,
        "休みの日は、朝から川で釣りをします。",
        "夕方には店に戻って",
        "川で釣り",
    ],
)
def test_a_part_of_the_source_passes_and_shows_the_source(quote):
    verdict = check(quote, SOURCE)
    assert verdict.passed
    assert verdict.shown == quote


def test_width_spaces_and_line_breaks_are_made_alike_and_the_original_is_shown():
    source = "ＡＩの授業で、\n地域の店を　調べた。ﾁｰﾑは５人。"
    verdict = check("AIの授業で、地域の店を調べた。チームは5人。", source)
    assert verdict.passed
    assert verdict.shown == source  # Full-width, line break and half-width kana kept.


def test_the_shown_part_is_cut_from_the_original_not_the_quote():
    source = "前置き。ｶﾞｲﾄﾞの仕事は、ＡＢＣ　から始まる。後書き。"
    verdict = check("ガイドの仕事は、ABCから始まる。", source)
    assert verdict.passed
    assert verdict.shown == "ｶﾞｲﾄﾞの仕事は、ＡＢＣ　から始まる。"


# --- Stopping: never in the source, one character off ----------------------------


@pytest.mark.parametrize(
    "quote",
    [
        "迷ったら、いちばん給料の高い道を選びなさい。",
        # A real sentence with an invented one mixed in, before or after.
        "休みの日は、朝から川で釣りをします。毎日が楽しいです。",
        "釣りが一番の趣味です。夕方には店に戻って、明日の仕込みをします。",
        # Two real sentences out of order.
        "夕方には店に戻って、明日の仕込みをします。休みの日は、朝から川で釣りをします。",
    ],
)
def test_a_sentence_not_in_the_source_is_stopped(quote):
    verdict = check(quote, SOURCE)
    assert not verdict.passed
    assert verdict.reason == STOP_NOT_IN_SOURCE
    assert verdict.shown == ""


SENTENCE = "休みの日は、朝から川で釣りをします。"


@pytest.mark.parametrize("position", range(len(SENTENCE)))
def test_changing_any_one_character_is_stopped(position):
    for replacement in ("＊", "あ"):
        if SENTENCE[position] == replacement:
            continue
        changed = SENTENCE[:position] + replacement + SENTENCE[position + 1 :]
        assert check(changed, SOURCE).reason == STOP_NOT_IN_SOURCE


@pytest.mark.parametrize(
    "quote",
    [
        "体みの日は、朝から川で釣りをします。",  # A kanji that looks alike.
        "休みの日は、朝から川で釣りをしました。",  # The ending.
        "休みの日は。朝から川で釣りをします。",  # A punctuation mark.
        "休みの日は、朝から川で魚釣りをします。",  # One character added.
        "休みの日は、朝から川で釣をします。",  # One character dropped inside.
        "休みの日は、朝から川で釣りをしますｰ",  # A half-width mark that is not in the source.
    ],
)
def test_one_character_off_is_stopped(quote):
    assert check(quote, SOURCE).reason == STOP_NOT_IN_SOURCE


@pytest.mark.parametrize("quote", ["", " ", "　\n"])
def test_an_empty_quote_is_stopped(quote):
    assert check(quote, SOURCE).reason == STOP_EMPTY


# --- The guard over ingested pieces -------------------------------------------------


def test_the_guard_shows_only_quotes_its_pieces_hold_and_counts_them():
    pieces = [piece("a-1", SOURCE), piece("a-2", "店は朝七時に開けます。")]
    guard = Guard(pieces)
    verdicts = guard.screen([
        Quote("a-1", "川で釣りをします。"),
        Quote("a-2", "店は朝七時に開けます。"),
        Quote("a-2", "店は朝八時に開けます。"),
        Quote("a-9", "店は朝七時に開けます。"),
    ])
    assert [v.passed for v in verdicts] == [True, True, False, False]
    assert [v.reason for v in verdicts[2:]] == [STOP_NOT_IN_SOURCE, STOP_UNKNOWN_UTTERANCE]
    assert [v.shown for v in guard.shown([Quote("a-1", "川で釣り")])] == ["川で釣り"]
    tally = guard.tally
    assert (tally.passed, tally.stopped) == (3, 2)
    assert tally.stopped_ids == ["a-2", "a-9"]
    assert tally.reasons == {STOP_NOT_IN_SOURCE: 1, STOP_UNKNOWN_UTTERANCE: 1}


def test_a_quote_naming_another_piece_is_stopped():
    guard = Guard([piece("a-1", SOURCE), piece("a-2", "店は朝七時に開けます。")])
    assert guard.screen([Quote("a-2", "川で釣りをします。")])[0].reason == STOP_NOT_IN_SOURCE


def test_article_text_cannot_come_out_as_words_said():
    paragraph = "先輩に「好きにやれ」と言われた。それから店を継いだ。"
    pieces = [
        piece(f"p-{index}", text, voice, paragraph)
        for index, (voice, text) in enumerate(split_voice(paragraph))
    ]
    said = next(p for p in pieces if p.voice == VOICE_SPOKEN)
    assert [p.voice for p in pieces] == [VOICE_ARTICLE, VOICE_SPOKEN, VOICE_ARTICLE]
    guard = Guard(pieces)
    assert guard.screen([Quote(said.id, "好きにやれ")])[0].passed
    # In the paragraph, but not in the piece the quote names.
    assert guard.screen([Quote(said.id, "それから店を継いだ。")])[0].reason == STOP_NOT_IN_SOURCE


def test_the_tally_never_holds_text():
    guard = Guard([piece("a-1", SOURCE)])
    guard.screen([Quote("a-1", "迷ったら、いちばん給料の高い道を選びなさい。")])
    printed = "\n".join(guard.tally.lines())
    assert "給料" not in printed and "釣り" not in printed
    assert "a-1" in printed


# --- Answers returned during the event are counted apart (SPEC 14-25) ------------


def test_answers_are_checked_but_counted_apart():
    answer = piece("ans-1", "人と話すのが好きで、この仕事を選びました。", VOICE_ANSWER)
    guard = Guard([piece("a-1", SOURCE), answer])
    verdicts = guard.screen([
        Quote("a-1", "川で釣りをします。"),
        Quote("ans-1", "人と話すのが好きで、この仕事を選びました。"),
        Quote("ans-1", "お金のために、この仕事を選びました。"),
    ])
    assert [v.passed for v in verdicts] == [True, True, False]  # Answers are still checked.
    tally = guard.tally
    assert (tally.passed, tally.stopped, tally.stopped_ids) == (1, 0, [])
    assert (tally.answers_passed, tally.answers_stopped) == (1, 1)


# --- A planted fake, as in the sample mode (SPEC 7-3, 12) ------------------------


def test_a_planted_fake_is_stopped_by_the_real_guard_and_kept_out_of_the_counts():
    guard = Guard([piece("a-1", SOURCE), piece("a-2", "店は朝七時に開けます。")])
    quotes = plant_fake(
        [Quote("a-1", "川で釣りをします。"), Quote("a-2", "店は朝七時に開けます。")],
        load_text(PLANTED_FAKE_QUOTE),
    )
    assert [q.planted for q in quotes] == [False, True, False]
    assert quotes[1].utterance_id == "a-1"  # Names a real piece, so only the words are false.
    verdicts = guard.screen(quotes)
    assert [v.passed for v in verdicts] == [True, False, True]
    assert verdicts[1].reason == STOP_NOT_IN_SOURCE
    tally = guard.tally
    assert (tally.passed, tally.stopped, tally.stopped_ids) == (2, 0, [])
    assert (tally.planted_passed, tally.planted_stopped) == (0, 1)


def test_nothing_is_planted_without_real_quotes_or_fake_words():
    assert plant_fake([], "作り話。") == []
    assert plant_fake([Quote("a-1", "川")], " ") == [Quote("a-1", "川")]
