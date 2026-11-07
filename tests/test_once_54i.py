"""直し54i (the teacher, 11/8): a masked name with no break before the next
word, and ask_cut.tsv: words the teacher takes out of a seat's pieces.
Every word here is invented."""

from ebino import one_to_one
from ebino.ingest.utterance import Utterance, mend_reading

ROOT_TEST_NAME = "山田"


def _piece(seat, text, n=0, paragraph=None):
    return Utterance(f"{seat}-{n}", seat, "cross", f"p{n}", "own", text, paragraph or text)


def test_a_masked_name_on_a_name_tag_or_credit_line_goes():
    assert mend_reading("第三回寺子屋　ー協力者：この方農園　この方") == "第三回寺子屋　ー協力者：地元の農園"
    assert mend_reading("景色が好きこの方小学校四年 福岡") == "景色が好き、小学校四年 福岡"
    assert mend_reading("インタビューした人：この方場所：公民館") == "場所：公民館"
    assert mend_reading("この方　この方　この方茶道という文化") == "茶道という文化"
    assert mend_reading("話を聞いて企画協力者：この方鹿革ができるまで") == "話を聞いて鹿革ができるまで"
    assert mend_reading("この方協力者：町のファーム") == "協力者：町のファーム"


def test_this_person_as_a_sentence_subject_stays():
    for text in ("この方自身が語る。", "この方以外にいない。", "この方達と話した。", "この方は町の人。",
                 "この方の夢。", "この方。", "この方、", "代表：この方。", "この方：町の出身。",
                 "と語るこの方は、", "この方！ごきげんよう"):
        assert mend_reading(text) == text


def _cuts(tmp_path, body):
    (tmp_path / one_to_one.CUT_FILE).write_text("席\t消す言葉\n" + body, encoding="utf-8")
    return one_to_one.load_cuts(tmp_path)


def test_the_words_written_are_taken_out_of_that_seat_only(tmp_path):
    rows, problem = _cuts(tmp_path, "C01\tr e h t o f C First\nC01\tとこだ学で\n")
    assert problem == ""
    pieces = [_piece("C01", "楽しかった。\nrehtofC First Mosque\n初めての体験。", 1),
              _piece("C01", "for othersとこだ学で他の文化を知った！", 2),
              _piece("C02", "とこだ学で知った。", 3)]
    kept, problems = one_to_one.apply_cuts(pieces, rows)
    assert [p.text for p in kept] == ["楽しかった。\n Mosque\n初めての体験。",
                                      "for others他の文化を知った！", "とこだ学で知った。"]
    assert kept[0].paragraph == kept[0].text and problems == []
    assert pieces[0].text.startswith("楽しかった。\nrehtofC")  # What was ingested is not changed.


def test_spaces_line_breaks_and_widths_do_not_matter(tmp_path):
    rows, _ = _cuts(tmp_path, "C01\tABC 12\n")
    kept, problems = one_to_one.apply_cuts([_piece("C01", "前ＡＢ\nＣ１２後。", 1)], rows)
    assert kept[0].text == "前後。" and problems == []


def test_circled_digits_and_full_width_digits_are_found_as_typed_or_either_way(tmp_path):
    rows, _ = _cuts(tmp_path, "C01\tアクション④　日時：３月２日\nC01\t㈱町\n")
    kept, problems = one_to_one.apply_cuts([_piece("C01", "前。アクション④日時：3月2日。㈱町の話。", 1)], rows)
    assert kept[0].text == "前。。の話。" and problems == []


def test_a_piece_left_with_nothing_is_not_shown(tmp_path):
    rows, _ = _cuts(tmp_path, "C01\tマイストーリー共有。\n")
    kept, _ = one_to_one.apply_cuts([_piece("C01", "マイストーリー共有。", 1), _piece("C01", "残る。", 2)], rows)
    assert [p.text for p in kept] == ["残る。"]


def test_rows_that_take_out_nothing_are_said_without_their_words(tmp_path):
    rows, _ = _cuts(tmp_path, f"C01\t{ROOT_TEST_NAME}\nZ99\tなにか\n")
    _, problems = one_to_one.apply_cuts([_piece("C01", "町の話。", 1)], rows)
    assert problems == [f"{one_to_one.CUT_FILE} 2行目（C01）：この言葉が、この席の言葉に見つからない",
                        f"{one_to_one.CUT_FILE} 3行目（席ID?）：この言葉が、この席の言葉に見つからない"]
    assert all(ROOT_TEST_NAME not in line for line in problems)


def test_no_table_takes_out_nothing(tmp_path):
    assert one_to_one.load_cuts(tmp_path) == ([], "")
