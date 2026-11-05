"""直し43: one to one says a slide's page as the person would, not as the
slide shows it. Before it is shown, code tidies the page (one_tidy.py): the
title's line, a page number, a date and marks go; the PDF's breaks are
joined; each bullet is a sentence; nothing is added but 「。」. A page with
nothing left, or whose words tidied hold a name, is not shown. The words
recorded never change. Every page, seat and word here is invented."""

import json
import random
import re

import anthropic
import httpx2
import pytest
from conftest import make_seat
from fake_client import FakeClient, text_response

from ebino import app as app_module
from ebino import librarian, one_tidy, one_to_one, speaker
from ebino.gate import Gate, NameList
from ebino.ingest.utterance import Utterance
from ebino.librarian import Found
from ebino.records import Records
from ebino.session import Library, Session

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")

# Pages shaped as a slide's are read (ingest/slides_pdf.py): lines joined by "\n".
PAGES = {
    "p1": "行く前のこと\n高校のころは、町の外をほとんど知らなかった。\nだから一度は\n外に出てみようと思った\n3",
    "p2": "海外での生活\n・言葉がわからなくて、最初は困った\n・毎日、市場で野菜を買った\n2. 友だちができたのは半年後\n11/3（月）",
    "p3": "大切にしたいこと\n① 人の話を最後まで聞く\n② 迷ったら、まず手を動かす\n★★★",
    "p4": "これから\n- 4 -",
    "p5": "ありがとう",
    "p6": "帰ってきて\n〇〇さんに声をかけてもらって、\n町の店を手伝うようになった。",
    "p7": "ありがとう\nみんなに会えてうれしかった。\n大切にしたいこと\nまた話そう。",
    "p8": "大切にしたいこと",
}
TIDIED = {
    "p1": "高校のころは、町の外をほとんど知らなかった。だから一度は外に出てみようと思った。",
    "p2": "言葉がわからなくて、最初は困った。毎日、市場で野菜を買った。友だちができたのは半年後。",
    "p3": "人の話を最後まで聞く。迷ったら、まず手を動かす。",
    "p4": "",
    "p5": "ありがとう。",
    "p6": "〇〇さんに声をかけてもらって、町の店を手伝うようになった。",
    # A line with no sentence's end and the next one: one (the PDF's break or
    # not), but a heading after a sentence's end a line of its own (11/6).
    "p7": "ありがとうみんなに会えてうれしかった。\n大切にしたいこと。\nまた話そう。",
    "p8": "大切にしたいこと。",
}
AXES = {"p1": ["行く前"], "p2": ["向こうで"], "p6": ["帰ってきて"], "p3": ["これから"], "p4": ["これから"],
        "p5": ["これから"], "p7": [], "p8": []}
# A name only where the lines meet (the seat's 「谷口さん」 is on the name list).
NAMED = "お世話になった人\n町の谷\n口さんに教わった。"
LONG = "向こうでは毎朝早く起きて、市場で店の人と話しながら野菜の名前を覚えていった。"  # 38 characters.

SEATS = [make_seat(seat_id="C01", kind="cross", title="県外に出た人（架空）", company="", display_name="", district=""),
         make_seat(seat_id="C02", kind="cross", title="県外に出た人（架空2）", company="", display_name="", district=""),
         make_seat(seat_id="N01", kind="cross", title="県外に出た人（架空3）", company="", display_name="谷口さん", district=""),
         make_seat(seat_id="A01", kind="adult", title="理容師", company="", display_name=""),
         make_seat(seat_id="P01", kind="poster", title="探究の先輩（架空）", company="", display_name="", district="")]


def _u(seat, kind, section, text, voice="own"):
    return Utterance(id=f"{seat}-{section}", seat_id=seat, kind=kind, section=section, voice=voice,
                     text=text, paragraph=text)


UTTERANCES = ([_u("C01", "cross", page, text) for page, text in PAGES.items()]
              + [_u("C02", "cross", "p1", LONG * 4), _u("C02", "cross", "p2", LONG * 3),
                 _u("C02", "cross", "p3", "これからのこと\n" + "ずっと" * 90 + "続けたい。" + LONG)]
              + [_u("N01", "cross", "p1", NAMED), _u("N01", "cross", "p2", "向こうで\n毎日、川で泳いだ。")]
              + [_u("A01", "adult", "本文", "休みは決めて取る\n店は月曜に閉める。", voice="article"),
                 _u("P01", "poster", "目的", "川の色を\n確かめたかった")])


def sitting(monkeypatch, answers=(), speaker_on=False, tmp_path=None):
    monkeypatch.setenv("EBINO_SPEAKER", "1" if speaker_on else "0")
    lib = Library.build(SEATS, UTTERANCES, {})
    lib.ask_tables = {"pages": {"C01": AXES, "C02": {"p1": ["行く前"], "p2": ["行く前"], "p3": ["これから"]},
                                "N01": {"p1": ["帰ってきて"], "p2": ["向こうで", "帰ってきて"]}},
                      "ranking": {}}
    client = FakeClient(list(answers))
    session = Session(lib, Gate(client, NameList.build(SEATS, {})), rng=random.Random(1),
                      records=Records(tmp_path) if tmp_path else None)
    return session, client


def _shown(answer):
    return [piece["spoken"] or piece["text"] for piece in answer["pieces"]]


# --- the code that tidies ---

def test_every_invented_page_tidied():
    for page, text in PAGES.items():
        assert one_tidy.tidy_page(text).text == TIDIED[page], page


def test_a_page_number_a_date_and_marks_go_by_themselves():
    for line in ("3", "- 4 -", "p.3", "P3", "１２", "3 / 12", "No.5"):
        assert one_tidy.line_drop(line) == one_tidy.DROP_NUMBER, line
    for line in ("11/3（月）", "11月3日", "11月3日（金）", "11.3(水)"):
        assert one_tidy.line_drop(line) == one_tidy.DROP_DATE, line
    for line in ("★★★", "――――", "・・・", "◆"):
        assert one_tidy.line_drop(line) == one_tidy.DROP_MARKS, line
    for line in ("2. 友だちができたのは半年後", "3人で始めた", "11月から店に出た。", "ありがとう"):
        assert one_tidy.line_drop(line) == "", line


def test_the_title_is_the_first_line_only_short_with_no_sentences_end():
    assert one_tidy.is_title("行く前のこと") and one_tidy.is_title("海外での生活") and one_tidy.is_title("これから")
    for line in ("ありがとう", "外に出てみようと思った", "毎日が楽しい", "まず手を動かす", "いつ帰るのか",
                 "向こうで驚いたこと。", "なぜ？", "・言葉の壁", "一度は外に出て、町の外の働き方を見てみたかった"):
        assert not one_tidy.is_title(line), line
    # One a page, the first: a second line like a title stays (p7's
    # 「大切にしたいこと」), a heading on a line of its own (11/6).
    tidied = one_tidy.tidy_page("向こうで\n大切にしたいこと\n人の話を聞く。")
    assert tidied.text == "大切にしたいこと。\n人の話を聞く。" and tidied.reasons == (one_tidy.DROP_TITLE,)


def test_a_short_line_of_the_body_and_a_page_of_one_line_stay():
    assert one_tidy.tidy_page("ありがとう").text == "ありがとう。"
    assert one_tidy.tidy_page("大切にしたいこと").text == "大切にしたいこと。"  # One line: never a title.
    # 「ありがとう」 first ends as a sentence ends: not a title; 「大切にしたいこと」 second: never one.
    assert "ありがとう" in TIDIED["p7"] and "大切にしたいこと" in TIDIED["p7"]


def test_a_line_the_pdf_broke_is_joined_and_a_bullet_is_not():
    assert one_tidy.tidy_page("はじめに\nだから一度は\n外に出てみようと思った").text == "だから一度は外に出てみようと思った。"
    assert one_tidy.tidy_page("はじめに\n言葉の壁は\n・大きかった").text == "言葉の壁は。大きかった。"
    # A bullet broken by the PDF: its two lines one.
    assert one_tidy.tidy_page("はじめに\n・毎日、市場で\n野菜を買った").text == "毎日、市場で野菜を買った。"
    # Letters of the alphabet: the break was a space.
    assert one_tidy.tidy_page("はじめに\nThank\nyou と言った。").text == "Thank you と言った。"


def test_a_heading_inside_the_page_is_a_line_of_its_own():
    # The teacher, 11/6: 「不安だったこと」 run into the next line was hard to read.
    page = "旅のこと\n食べ物はおいしいかな？過ごせるかな？\n不安だったこと\n無事に帰れるかな？"
    tidied = one_tidy.tidy_page(page)
    assert tidied.text == "食べ物はおいしいかな？過ごせるかな？\n不安だったこと。\n無事に帰れるかな？"
    assert tidied.joined == "食べ物はおいしいかな？過ごせるかな？不安だったこと無事に帰れるかな？"
    # A line that goes on (〜は, 〜の, 〜で) is never a heading: joined as before.
    for left in ("だから一度は", "町の店の", "毎日、市場で"):
        tidied = one_tidy.tidy_page(f"はじめに\n楽しかった。\n{left}\n手伝った。")
        assert tidied.text == f"楽しかった。{left}手伝った。" and tidied.joined == ""
    # A bullet is never a heading, and a heading before a bullet stays as it was.
    assert one_tidy.tidy_page("はじめに\n・不安だったこと\n無事に帰れるかな？").text == "不安だったこと無事に帰れるかな？"


def test_a_name_parted_by_a_heading_is_still_caught():
    tidied = one_tidy.tidy_page(NAMED)
    assert tidied.text == "町の谷。\n口さんに教わった。" and tidied.joined == "町の谷口さんに教わった。"
    names = NameList.build(SEATS, {})
    assert not names.hits(tidied.text) and names.hits(tidied.joined)


def test_each_bullet_a_sentence_its_head_gone():
    for head in ("・", "●", "○", "■", "□", "◆", "◇", "－", "-", "＊", "*", "※", "1.", "1)", "１．", "（1）", "①", "a."):
        assert one_tidy.tidy_page(f"はじめに\n{head} 人の話を聞く\n{head}迷ったら手を動かす！").text \
            == "人の話を聞く。迷ったら手を動かす！", head
    # A number that is not a bullet's head stays.
    assert one_tidy.tidy_page("はじめに\n1.5倍に増えた").text == "1.5倍に増えた。"
    assert one_tidy.tidy_page("はじめに\n・声をかけてもらって、").text == "声をかけてもらって。"


def _letters(text):
    return re.sub(r"[\s。]", "", text)


def test_nothing_is_added_but_the_full_stop():
    # The 「。」 aside, the words tidied are the page's letters in order, some left out.
    for text in [*PAGES.values(), NAMED, LONG * 4, "はじめに\nThank\nyou と言った。"]:
        rest = iter(_letters(text))
        assert all(char in rest for char in _letters(one_tidy.tidy_page(text).text)), text


def test_a_page_with_its_title_only_is_empty_and_none_of_the_items():
    assert one_tidy.tidy_page(PAGES["p4"]) == one_tidy.Tidied("", 2, (one_tidy.DROP_NUMBER, one_tidy.DROP_TITLE,
                                                                       one_tidy.EMPTY))
    for marks in ("★★★", "3\n★"):
        assert one_tidy.tidy_page(marks).text == ""


# --- one to one ---

def test_the_bubble_has_no_title_number_date_or_break(monkeypatch):
    session, _ = sitting(monkeypatch)
    for item, pages in (("行く前", ["p1"]), ("向こうで", ["p2"]), ("帰ってきて", ["p6"])):
        answer = session.one_ask("C01", item)
        assert _shown(answer) == [TIDIED[page] for page in pages]
        for gone in ("行く前のこと", "海外での生活", "帰ってきて\n", "11/3", "\n", "・", "2."):
            assert all(gone not in text for text in _shown(answer)), (item, gone)


def test_the_title_only_page_is_not_in_the_bubble_and_the_short_page_is(monkeypatch):
    session, _ = sitting(monkeypatch)
    answer = session.one_ask("C01", "これから")
    assert _shown(answer) == [TIDIED["p3"], TIDIED["p5"]]  # p4, its title only, is not.
    assert [p["utterance_id"] for p in answer["pieces"]] == ["C01-p3", "C01-p5"]
    assert [r["utterance_id"] for r in session.one_tidied] == ["C01-p3", "C01-p4", "C01-p5"]
    assert session.one_tidied[1] == {"utterance_id": "C01-p4", "tidied": "", "dropped_lines": 2,
                                     "reasons": [one_tidy.DROP_NUMBER, one_tidy.DROP_TITLE, one_tidy.EMPTY]}


def test_an_item_whose_pages_have_nothing_left_is_not_offered(monkeypatch):
    session, _ = sitting(monkeypatch)
    session.library.ask_tables["pages"]["C01"] = {"p4": ["行く前"], "p1": ["向こうで"]}
    assert [item for item, _, _ in session.one_items("C01")] == ["向こうで"]


def test_a_page_whose_words_tidied_hold_a_name_is_never_shown(monkeypatch):
    assert NameList.build(SEATS, {}).hits("谷口") and not NameList.build(SEATS, {}).hits("谷\n")
    session, client = sitting(monkeypatch)
    assert [item for item, _, _ in session.one_items("N01")] == ["向こうで", "帰ってきて"]
    assert _shown(session.one_ask("N01", "帰ってきて")) == ["毎日、川で泳いだ。"]
    tidied = session.one_page(session._utterances["N01-p1"])
    assert tidied.text == "" and one_tidy.NAME in tidied.reasons
    # The speaker on: the page is not sent either, and stopped or past its
    # limit, the words shown are the tidied ones that passed, never the page.
    timed_out = anthropic.APITimeoutError(request=httpx2.Request("POST", "https://api.invalid/v1/messages"))
    for answers in ([timed_out], [text_response({"lines": [{"id": "N01-p2", "text": "谷口さんと泳いだ。"}]})]):
        session, client = sitting(monkeypatch, answers, speaker_on=True)
        answer = session.one_ask("N01", "帰ってきて")
        assert _shown(answer) == ["毎日、川で泳いだ。"] and "谷" not in client.all_sent()


def test_the_words_recorded_never_change_and_the_record_keeps_why(monkeypatch, tmp_path):
    session, _ = sitting(monkeypatch, tmp_path=tmp_path)
    session.one_ask("C01", "これから")
    session.one_ask("N01", "帰ってきて")
    for u in session.library.utterances:
        assert u.text == u.paragraph
        if u.seat_id == "C01":
            assert u.text == PAGES[u.section]
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    kept = {item["utterance_id"]: item for item in record["one_tidied"]}
    assert kept["C01-p3"] == {"utterance_id": "C01-p3", "tidied": TIDIED["p3"], "dropped_lines": 2,
                              "reasons": [one_tidy.DROP_MARKS, one_tidy.DROP_TITLE]}
    assert kept["C01-p5"] == {"utterance_id": "C01-p5", "tidied": "ありがとう。", "dropped_lines": 0, "reasons": []}
    # A page with a name: why, never its words.
    assert kept["N01-p1"] == {"utterance_id": "N01-p1", "tidied": "", "dropped_lines": 1,
                              "reasons": [one_tidy.DROP_TITLE, one_tidy.NAME]}
    assert "谷" not in json.dumps(record["one_tidied"], ensure_ascii=False)


def test_pages_far_past_the_limit_are_cut_at_a_sentences_end(monkeypatch):
    assert one_to_one.ONE_CUT_CHARS == 240 == one_to_one.ONE_CHARS * 3 // 2
    session, _ = sitting(monkeypatch)
    shown = _shown(session.one_ask("C02", "行く前"))
    # p1 is 152 characters, p2 114: 266 together, past 240; cut after a sentence.
    assert len(LONG) == 38
    assert shown[0] == LONG * 4 and shown[1] == LONG * 2 and sum(map(len, shown)) == 228
    assert session.one_tidied[-1]["reasons"] == [one_tidy.CUT]
    # Its first sentence past the limit by itself: that sentence whole, no more.
    shown = _shown(session.one_ask("C02", "これから"))
    assert shown == ["ずっと" * 90 + "続けたい。"]


def test_the_cut_keeps_whole_sentences():
    assert one_tidy.cut(["あい。うえ。", "おか。"], 10) == (["あい。うえ。", "おか。"], False)
    assert one_tidy.cut(["あい。うえ。", "おか。"], 5) == (["あい。"], True)
    assert one_tidy.cut(["あいうえおかき。く。"], 3) == (["あいうえおかき。"], True)
    assert one_tidy.sentences("「行く！」と言った。まだ") == ["「行く！」", "と言った。", "まだ"]


def test_an_article_and_a_poster_are_as_recorded(monkeypatch):
    session, _ = sitting(monkeypatch)
    assert _shown(session.one_ask("A01", "本文")) == ["休みは決めて取る\n店は月曜に閉める。"]
    assert _shown(session.one_ask("P01", "目的")) == ["川の色を\n確かめたかった"]
    assert session.one_tidied == []


def test_a_written_question_shows_the_page_tidied_and_skips_one_with_nothing(monkeypatch):
    session, _ = sitting(monkeypatch)
    monkeypatch.setattr(librarian, "find", lambda *a, **k: Found(["C01-p4", "C01-p1"], "picked"))
    found = session.one_free_question("C01", "向こうに行く前は？")
    assert found["found"] and _shown(found) == [TIDIED["p1"]]
    monkeypatch.setattr(librarian, "find", lambda *a, **k: Found(["C01-p4"], "picked"))
    assert session.one_free_question("C01", "これからは？")["found"] is False
    assert session.one_free["C01"] == [True, False]


def test_stopped_past_the_limit_or_turned_off_the_tidied_words_are_shown(monkeypatch):
    timed_out = anthropic.APITimeoutError(request=httpx2.Request("POST", "https://api.invalid/v1/messages"))
    bad = text_response({"lines": [{"id": "C01-p1", "text": "ぼくは高校のころ、東京の外を知らなかったんだ。"}]})
    for answers, on in (([timed_out], True), ([bad], True), ([], False)):
        session, _ = sitting(monkeypatch, answers, speaker_on=on)
        answer = session.one_ask("C01", "行く前")
        assert answer["pieces"][0]["spoken"] == "" and answer["pieces"][0]["text"] == TIDIED["p1"], (answers, on)
        assert "\n" not in answer["pieces"][0]["text"] and "行く前のこと" not in answer["pieces"][0]["text"]


# --- the screen ---

def test_the_bubble_parts_its_pieces_where_a_sentence_ends():
    says = MAP[MAP.index("  function says(pieces, source) {"):MAP.index("  function oneAnswer(")]
    assert 'voice.replaceChildren(...pieces.map((piece) => div("one-piece", piece.spoken || piece.text)));' in says
    assert '.join("")' not in says
    assert ".one-bubble .voice .one-piece { display: block; white-space: pre-line; }" in CSS


def test_one_tidy_is_code_only():
    source = open(one_tidy.__file__, encoding="utf-8").read()
    imports = [line for line in source.splitlines() if line.startswith(("import ", "from "))]
    assert imports == ["import re", "import unicodedata", "from dataclasses import dataclass"]
    assert speaker.TIMEOUT_SECONDS == 8.0 and speaker.MAX_GROWTH == 1.5  # Unchanged (直し43 leaves speaker.py).


# --- the counts for the real data (tools/count_one_tidy.py) ---

def _tool():
    import importlib.util
    path = app_module.STATIC_DIR.parent.parent / "tools" / "count_one_tidy.py"
    spec = importlib.util.spec_from_file_location("count_one_tidy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path.read_text(encoding="utf-8")


def test_the_counting_tool_says_numbers_only_and_asks_no_model(monkeypatch):
    tool, source = _tool()
    session, client = sitting(monkeypatch)
    rows = tool.count(session)
    assert rows == [
        {"席": "C01", "項目": "行く前", "ページ": 1, "表題": 1, "空": 0, "名前": 0},
        {"席": "C01", "項目": "向こうで", "ページ": 1, "表題": 1, "空": 0, "名前": 0},
        {"席": "C01", "項目": "帰ってきて", "ページ": 1, "表題": 1, "空": 0, "名前": 0},
        {"席": "C01", "項目": "これから", "ページ": 3, "表題": 2, "空": 1, "名前": 0},
        {"席": "C02", "項目": "行く前", "ページ": 2, "表題": 0, "空": 0, "名前": 0},
        {"席": "C02", "項目": "これから", "ページ": 1, "表題": 1, "空": 0, "名前": 0},
        {"席": "N01", "項目": "向こうで", "ページ": 1, "表題": 1, "空": 0, "名前": 0},
        {"席": "N01", "項目": "帰ってきて", "ページ": 2, "表題": 2, "空": 0, "名前": 1}]
    printed = tool.table(rows)
    assert printed.splitlines()[0] == "席\t項目\tページ\t表題\t空\t名前"
    assert printed.splitlines()[-1] == "計\t8\t12\t9\t1\t1"
    words = re.sub(r"[\s\d]", "", "".join(PAGES.values()) + NAMED)
    assert not any(len(chunk) > 1 and chunk in printed for chunk in re.findall(r"[^\s\d]{2,}", words)
                   if chunk not in {"行く前", "向こうで", "帰ってきて", "これから"})
    assert client.requests == []
    # .env is read in main() only, which no test calls; no file is written.
    assert source.count("load_env_file()") == 1 and "def main()" in source
    assert "write_text" not in source and "open(" not in source
    with pytest.raises(RuntimeError):
        tool.NoModel().messages


# --- 段2: the speaker is given the words tidied ---

def _says(**lines):
    return text_response({"lines": [{"id": key, "text": text} for key, text in lines.items()]})


def test_the_speaker_is_given_the_words_tidied_as_the_original(monkeypatch):
    session, client = sitting(monkeypatch, [_says()], speaker_on=True)
    session.one_ask("C01", "向こうで")
    sent = json.loads(client.requests[-1]["messages"][0]["content"])["quotes"]
    assert sent == [{"id": "C01-p2", "voice": "own", "text": TIDIED["p2"]}]
    assert "海外での生活" not in client.all_sent() and "11/3" not in client.all_sent()


def test_spoken_words_without_the_title_pass_and_are_kept_beside_the_words_tidied(monkeypatch, tmp_path):
    spoken = "言葉がわからなくて、最初は困ったんだ。毎日、市場で野菜を買ってたよ。友だちができたのは半年後だったな。"
    # Checked against the page as recorded, the title's 「海外」「生活」 would be words dropped.
    assert speaker.stop_reason(spoken, PAGES["p2"], PAGES["p2"], Gate(FakeClient([]), NameList.build(SEATS, {}))) \
        == speaker.STOP_DROPPED
    session, _ = sitting(monkeypatch, [_says(**{"C01-p2": spoken})], speaker_on=True, tmp_path=tmp_path)
    answer = session.one_ask("C01", "向こうで")
    assert answer["pieces"][0]["spoken"] == spoken and answer["pieces"][0]["text"] == TIDIED["p2"]
    record = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))
    assert record["one_spoken"] == [{"utterance_id": "C01-p2", "shown": "spoken", "original": TIDIED["p2"],
                                     "spoken": spoken, "reason": ""}]


def test_spoken_words_with_a_word_or_a_number_not_in_the_words_tidied_stop(monkeypatch):
    for words, reason in (("海外での生活では、言葉がわからなくて、最初は困った。毎日、市場で野菜を買った。友だちができたのは半年後。",
                           speaker.STOP_WORD),  # 「生活」: the title's, gone.
                          ("言葉がわからなくて、最初は困った。毎日、市場で野菜を買った。友だちができたのは3か月後。",
                           speaker.STOP_NUMBER),
                          ("言葉がわからなくて、最初は困った。毎日、野菜を買った。友だちができたのは半年後。",
                           speaker.STOP_DROPPED)):  # 「市場」 left out.
        session, _ = sitting(monkeypatch, [_says(**{"C01-p2": words})], speaker_on=True)
        answer = session.one_ask("C01", "向こうで")
        assert answer["pieces"][0]["spoken"] == "" and answer["pieces"][0]["text"] == TIDIED["p2"], words
        assert session.one_spoken[-1].reason == reason, words


def test_an_article_is_given_to_the_speaker_as_recorded(monkeypatch):
    session, client = sitting(monkeypatch, [_says()], speaker_on=True)
    session.one_ask("A01", "本文")
    sent = json.loads(client.requests[-1]["messages"][0]["content"])["quotes"]
    assert sent == [{"id": "A01-本文", "voice": "article", "text": "休みは決めて取る\n店は月曜に閉める。"}]


def test_the_round_tables_bubbles_are_given_to_the_speaker_as_before():
    from ebino import session as session_module
    source = open(session_module.__file__, encoding="utf-8").read()
    speak = source[source.index("    def _speak(self"):source.index("    def card_like(")]
    assert 'quotes = [{"id": q.utterance_id, "voice": q.voice, "text": q.text,' in speak
    assert "one_tidy" not in speak
