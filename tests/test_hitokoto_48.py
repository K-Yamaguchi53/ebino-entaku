"""直し48 段7 (the teacher, 11/7, 帰る前に、ひとこと): on the map page a whole
sentence is pressed, not a phrase; beside the talk, today's trail, each step
opening what was heard then, as recorded; at 0 on the scale no question to
lower it; ⑤ (割れていた所を、本人に確かめる) only on a day with a split.
Every record and word here is invented; the model is a fake one."""

import pytest

from ebino import app as app_module
from ebino import harvest, hitokoto
from ebino.session import Refused
from test_hitokoto import Model, sitting, to_scale
from test_session import UTTERANCES

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")


def test_sentences_whole_word_for_word_never_inside_quotes():
    assert hitokoto.sentences("月曜は休み。火曜は畑！どうする？") == ["月曜は休み。", "火曜は畑！", "どうする？"]
    # Not inside 「」, and a 」 after the end kept with it.
    assert hitokoto.sentences("父は「休め。休め。」と言った。私は休んだ") == ["父は「休め。休め。」と言った。", "私は休んだ"]
    assert hitokoto.sentences("「休みは決めて取る。」それが私です。") == ["「休みは決めて取る。」", "それが私です。"]
    for u in UTTERANCES:
        assert "".join(hitokoto.sentences(u.text)).replace(" ", "") == u.text.strip().replace(" ", "")


def test_the_map_page_offers_each_whole_sentence_and_takes_one():
    session, _, _, view = sitting()
    for person in view["people"]:
        assert person["sentences"] == hitokoto.sentences(person["text"])
    session.hitokoto_parts()
    person = session.talk.people[0]
    sentence = hitokoto.sentences(person.text)[0]
    result = session.hitokoto_choose(0, sentence)
    assert result["part"] == sentence and session.talk.chosen_part == sentence


def test_a_part_of_a_sentence_that_was_not_lit_is_refused():
    session, _, _, _ = sitting()
    session.hitokoto_parts()
    with pytest.raises(Refused):
        session.hitokoto_choose(0, "天気しだい")


def test_the_screen_makes_each_sentence_a_button():
    cards = HK[HK.index("  function renderCards(parts) {"):HK.index("  function pick(index, part, node) {")]
    assert 'for (const sentence of person.sentences || [person.text]) {' in cards
    assert 'const kw = button("hk-kw hk-sentence", sentence, () => pick(index, sentence, kw));' in cards
    assert "words.indexOf(part)" not in cards


def test_the_trail_beside_the_talk_with_what_was_heard_as_recorded():
    session, _, _, view = sitting(opened=("a1",))
    trail = view["trail"]
    assert trail[0]["kind"] == "question" and trail[0]["head"] == "休みの日って、みんな何してる？"
    recorded = {u.id: u.text for u in UTTERANCES}
    heard = [item for item in trail if item["quote"]]
    for item in heard:
        assert any(item["quote"] in text or text in item["quote"] for text in recorded.values()), item
        assert item["who"]
    render = HK[HK.index("  function renderTrail(items) {"):HK.index("  // Each person's words, as recorded.")]
    assert 'head.setAttribute("aria-expanded", "false");' in render and "$(id).hidden = !open;" in render
    assert '$("hk-trail-fold").open = window.matchMedia("(min-width: 769px)").matches;' in render


@pytest.mark.parametrize("value, asked", [
    (0, None),  # 迷いなし: no question to lower it.
    (1, "scale_down"), (9, "scale_down"),
    (10, "scale_same"),
    (11, "scale_up"), (15, "scale_up"),
])
def test_the_scales_next_question_by_the_value(value, asked):
    session, _, _, _ = sitting()
    to_scale(session)
    result = session.hitokoto_scale(value)
    words = hitokoto.words()
    if asked is None:
        assert result == {"next": "way", "question": ""} and session.talk.stage == hitokoto.WAY
        assert not [a for a in session.talk.asked if a.step == "forward"]
    else:
        assert result == {"next": "forward", "question": words[asked]}
    assert 'if (result.next === "way") return askWay();' in HK


def test_five_only_on_a_day_with_a_split():
    with_split, _, _, _ = sitting(Model(split=True))
    without, _, _, _ = sitting(Model(split=False))
    assert 5 in harvest.uses_offered(with_split)
    assert 5 not in harvest.uses_offered(without)
    assert not any(r.splits for r in without.rounds)


def test_a_sentence_pressed_before_the_lit_parts_come_stays_pressed():
    # The screen check: the cards were whole-card buttons until the parts
    # came, and a press then was lost. Sentences from the first; kept.
    cards = HK[HK.index("  function renderCards(parts) {"):HK.index("  function pick(index, part, node) {")]
    assert "const keep = picked;" in cards and "if (node) return pick(keep.person, keep.part, node);" in cards
    assert "if (!(person.sentences && person.sentences.length)) {" in cards
    assert "if (part && sentence.includes(part)) kw.classList.add(\"hk-lit-part\");" in cards
