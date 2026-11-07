"""直し54g (the teacher, 11/8: 日本語表現・読みやすい？): an article's words that
stop mid-sentence end at a sentence's end, and vertical text read with a
space after each character is joined. Every word here is invented."""

import random
from dataclasses import replace

import pytest
from fake_client import FakeClient

from ebino.gate import Gate, NameList
from ebino.ingest.utterance import mend_spacing
from ebino.one_tidy import end_whole
from ebino.session import Library, Session
from test_one_to_one import SEATS, UTTERANCES, _u


@pytest.mark.parametrize("text, want", [
    ("夜も同僚がいるからである。うまくいかない時は", "夜も同僚がいるからである。"),
    ("大切だと言っていた。この仕事で大事にしていることは", "大切だと言っていた。"),
    ("達成感がある。さらに、", "達成感がある。"),
    ("お客様に選ばれる。努力して育てた野菜が選ばれ、", "お客様に選ばれる。"),
    ("趣味は会話です。この方：町の出身で趣味は", "趣味は会話です。"),
])
def test_words_that_stop_mid_sentence_end_at_the_last_sentence(text, want):
    assert end_whole(text) == want


@pytest.mark.parametrize("text", [
    "何でもチャレンジしてください",               # A slogan, no 。 at all.
    "うまくいかない時は",                         # No sentence ends before it.
    "経歴は長い。\n・趣味\n・旅行",               # A list after the sentence.
    "楽しい職場です。ぜひ来てください",           # A whole sentence without 。.
    "働いて三年。続けてきたのは人と話すこと",     # Ends as こと: whole.
    "毎日楽しいです。",
    "「ありがとう」と言われた。",
    "",
])
def test_other_words_are_kept_as_they_are(text):
    assert end_whole(text) == text


@pytest.mark.parametrize("text, want", [
    ("自 分 を 変 え た か っ た。", "自分を変えたかった。"),
    ("好奇心！や ら な い 後 悔 よ り や っ た 後 悔 ！ ！", "好奇心！やらない後悔よりやった後悔！！"),
    ("N G ワ ー ド を 言 う", "NGワードを言う"),
    ("夜　に　銃　声　が　な　る。", "夜に銃声がなる。"),
])
def test_one_character_at_a_time_is_joined(text, want):
    assert mend_spacing(text) == want


@pytest.mark.parametrize("text", [
    "経歴　大学→ホテル→塾講師",                  # Spaces between words.
    "建築　設計　広告デザイン　カフェ",
    "表１　　　　　表２",
    "A B C",                                       # Too few to be vertical text.
])
def test_spaces_between_words_stay(text):
    assert mend_spacing(text) == text


def _session(monkeypatch, utterances):
    monkeypatch.setenv("EBINO_SPEAKER", "0")
    monkeypatch.setenv("EBINO_ASKER", "0")
    lib = Library.build(SEATS, utterances, {}, False, {})
    lib.ask_tables = {"pages": {}, "ranking": {}, "unread": []}
    return Session(lib, Gate(FakeClient([]), NameList.build(SEATS, {})), rng=random.Random(1))


def test_one_to_one_ends_an_article_piece_whose_words_go_on_in_a_piece_not_shown(monkeypatch):
    paragraph = "毎日が勉強です。うまくいかない時は「まず深呼吸」と話す。"
    lead = replace(_u("A01", "adult", "本文", "毎日が勉強です。うまくいかない時は", 1), paragraph=paragraph)
    said = replace(_u("A01", "adult", "本文", "まず深呼吸", 2, voice="spoken"), paragraph=paragraph)
    other = _u("A01", "adult", "本文", "町が好きです。休みの日は", 3)
    session = _session(monkeypatch, UTTERANCES + [lead, said, other])
    # Its 「」 shown right after it: kept whole.
    assert session.one_shown([lead, said])[1] == ["毎日が勉強です。うまくいかない時は", "まず深呼吸"]
    # Its 「」 left out (another kind, past the limit): ended at the sentence; the last one too.
    assert session.one_shown([lead, other])[1] == ["毎日が勉強です。", "町が好きです。"]
    assert session.one_shown([lead])[1] == ["毎日が勉強です。"]
    # What is recorded is not changed.
    assert lead.text == "毎日が勉強です。うまくいかない時は"
