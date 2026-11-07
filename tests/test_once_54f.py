"""直し54f (the teacher, 11/8: 「目年２社入」を今直して): a senior's message
signed 入社N年目 in vertical text, read backwards at its end. The shapes are
those found in the list; the words around them are invented."""

import json

import pytest

from ebino.index import load_utterances
from ebino.ingest.run import OUTPUT_DIR, OUTPUT_FILE
from ebino.ingest.utterance import Utterance, mend_tenure


@pytest.mark.parametrize("text, want", [
    # The whole label at the end.
    ("教えてもらえる、働きやすい職場です！目年２社入", "教えてもらえる、働きやすい職場です！"),
    ("一緒にやってみませんか。目年4社入", "一緒にやってみませんか。"),
    ("毎日が楽しいです。目年3社入", "毎日が楽しいです。"),
    # 目年 slipped into the message, 社入 left at the end.
    ("お礼を言って頂け目年るとうれしいです。４社入", "お礼を言って頂けるとうれしいです。"),
    # Only 目 slipped.
    ("その力を生かしてみま目せんか？年8社入", "その力を生かしてみませんか？"),
    # Spaces or line breaks between the characters.
    ("楽しい職場です。目 年\n２ 社 入\n", "楽しい職場です。"),
])
def test_the_backwards_label_is_left_out_and_what_it_slipped_taken_back(text, want):
    assert mend_tenure(text) == want


@pytest.mark.parametrize("text", [
    "去年、3社入ってきた取引先です。",          # 社入 inside a sentence.
    "春に5社入",                                  # Not after 。！？.
    "目標は一年目で決めました。",                # 目・年 in words, no label.
    "入社2年目です。",                            # Written the right way round.
    "",
])
def test_other_words_are_not_touched(text):
    assert mend_tenure(text) == text


def test_a_slipped_character_inside_a_word_stays():
    # The label lacks 目, but the only 目 is in 目標 (beside a kanji): kept.
    assert mend_tenure("目標をもって働けます。年2社入") == "目標をもって働けます。"


def test_everything_that_reads_the_pieces_reads_them_mended(tmp_path):
    rows = [Utterance("a-1", "B01", "article", "s", "senior", "やってみま目せんか？年8社入",
                      "やってみま目せんか？年8社入").to_dict(),
            Utterance("a-2", "B01", "article", "s", "senior", "そのまま。", "そのまま。").to_dict()]
    (tmp_path / OUTPUT_DIR).mkdir()
    (tmp_path / OUTPUT_DIR / OUTPUT_FILE).write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    first, second = load_utterances(tmp_path)
    assert (first.id, first.text, first.paragraph) == ("a-1", "やってみませんか？", "やってみませんか？")
    assert second.text == "そのまま。"
