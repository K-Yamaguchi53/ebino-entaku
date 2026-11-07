"""直し48 段4 (the teacher, 11/7: 「これで本当に生徒はなるほど！となるか？
時間はかかってもいい」): today's sheet holds more, made from the record and
the student's own words: each person met with one sentence of their words as
recorded and their title; the student's words in turn; 司会（AI）のまとめ (the
model only picks two people and whether they go the same way or part; it
writes no words, and is sent no title or name); the split; the seat to meet.
「整理中」 while it is made. Every record and word here is invented."""

import json

from fake_client import text_response

from ebino import hitokoto, prompts, texts
from test_hitokoto import Model, sitting, to_end, to_scale
from test_session import UTTERANCES


class TieModel(Model):
    """The fake model, answering 司会（AI）のまとめ too."""

    def __init__(self, tie=None, **kwargs):
        super().__init__(**kwargs)
        self.tie = tie if tie is not None else {"kind": "differ", "a": "1", "b": "2"}

    def __call__(self, request):
        system = request["system"][0]["text"]
        if system.startswith(prompts.TIE.split("\n")[0]):
            data = json.loads(request["messages"][0]["content"])
            self.sent.append(("tie", data))
            if isinstance(self.tie, Exception):
                raise self.tie
            return text_response(self.tie)
        return super().__call__(request)


def _sheet(model=None, tmp_path=None, meet=True):
    session, model, _, _ = sitting(model or TieModel(), tmp_path=tmp_path)
    to_scale(session)
    to_end(session)
    if meet:
        session.talk.meet_seat, session.talk.meet_use = "S01", "2"
    session.hitokoto_light()
    return session, model, session.hitokoto_sheet("休みの決め方で、仕事はどう変わる？")


def test_each_person_met_with_one_sentence_of_their_own_words_as_recorded():
    _, _, sheet = _sheet()
    recorded = [u.text for u in UTTERANCES]
    assert sheet["met"], sheet
    for person in sheet["met"]:
        # Word for word a sentence of what was recorded (never rewritten), with the title.
        assert any(person["quote"] in text for text in recorded), person["quote"]
        assert person["title"] and "quote" in person and "said" in person
    # The lit part's sentence for the person whose part was lit.
    assert {"休みは空いたら取ります" in p["quote"] for p in sheet["met"]} == {True, False}


def test_the_sentence_with_the_part_word_for_word():
    text = "月曜は必ず店を閉める。休みは決めて取ります！それが続けるこつです。"
    assert hitokoto.sentence_with(text, "決めて取") == "休みは決めて取ります！"
    assert hitokoto.sentence_with(text, "") == "月曜は必ず店を閉める。"
    assert hitokoto.sentence_with(text, "ない言葉") == "月曜は必ず店を閉める。"


def test_the_students_words_in_turn_first_question_to_now():
    _, _, sheet = _sheet()
    moves = sheet["moves"]
    assert moves[0] == "休みの日って、みんな何してる？" and moves[-1] == "休みの決め方で、仕事はどう変わる？"
    assert "空いたら取るのがいいと思った" in moves
    assert len(moves) == len(set(moves))


def test_the_hosts_tie_two_people_and_how_they_go_no_words_of_its_own():
    _, model, sheet = _sheet()
    sent = [data for kind, data in model.sent if kind == "tie"]
    assert len(sent) == 1
    # Sent the sentences only: no title, no seat, no name.
    assert set(sent[0]) == {"people"} and all(set(p) == {"id", "text"} for p in sent[0]["people"])
    titles = [p["title"] for p in sheet["met"]]
    assert not any(title in json.dumps(sent, ensure_ascii=False) for title in titles)
    tie = sheet["tie"]
    assert tie["kind"] == "differ" and tie["a"] == sheet["met"][0] and tie["b"] == sheet["met"][1]
    # The words on screen for it are texts/, the model's are none.
    words = hitokoto.words()
    assert words["sheet_tie"] == "司会（AI）のまとめ"
    assert words["tie_same"] and words["tie_differ"]
    assert "文を書かない。" in prompts.TIE


def test_a_bad_or_missing_tie_shows_nothing_and_is_asked_once():
    for answer in ({"kind": "same", "a": "1", "b": "1"}, {"kind": "same", "a": "9", "b": "1"},
                   {"kind": "none", "a": "", "b": ""}, TimeoutError("slow")):
        session, model, sheet = _sheet(TieModel(tie=answer))
        assert sheet["tie"] is None
        session.hitokoto_sheet("")
        assert [kind for kind, _ in model.sent].count("tie") <= 1


def test_the_split_and_the_seat_to_meet():
    _, _, sheet = _sheet()
    assert sheet["split"]["heading"] and sheet["split"]["a"] != sheet["split"]["b"]
    from ebino import harvest
    from ebino.seat_label import seat_label
    from test_session import SEATS
    title = seat_label(next(s for s in SEATS if s.seat_id == "S01"), False).title
    assert sheet["meet"] == harvest.meet_line(title, 2)  # As the card says it (②).
    _, _, none = _sheet(meet=False)
    assert none["meet"] == ""


def test_the_record_keeps_which_two_and_no_words(tmp_path):
    session, _, _ = _sheet(tmp_path=tmp_path)
    kept = json.loads((tmp_path / "sessions" / f"{session.session_id}.json").read_text(encoding="utf-8"))["hitokoto"]
    assert kept["tie"]["kind"] == "differ" and set(kept["tie"]) == {"kind", "a", "b"}
    assert kept["tie_asked"]["reason"] == ""


def test_wait_sign_for_the_sheet():
    signs = texts.wait_signs()
    assert signs["sheet"] == {"word": "整理中", "line": "今日の話を、1枚にまとめています"}


def test_the_sheet_page_says_it_is_being_made_until_it_is():
    from ebino import app as app_module
    hk = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
    css = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
    to_sheet = hk[hk.index("  async function toSheet() {"):hk.index("  function setup() {")]
    # 「整理中」 and its line (texts/wait_sign.tsv) on the sheet's page first, the slow line after a while.
    assert 'waiting.append(el("p", "hk-making-word", signs.sheet.word), waitLine, dots);' in to_sheet
    assert to_sheet.index('show("sheet");') < to_sheet.index('await post("sheet"')
    assert "waitLine.textContent = signs.slow.line; }, 15000);" in to_sheet
    # Refused or failed: back to the page before, the message there.
    assert to_sheet.count('show("light");') == 2
    assert 'sheet: "sheet" };' in hk
    # Its dots move only where motion is not reduced.
    still = css[css.index(".hk-making-dots span {"):]
    assert "animation" not in still[:still.index("}")]


def test_the_sheet_prints_on_one_a4_page():
    from ebino import app as app_module
    css = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")
    # The screen check: its last line went onto a second page.
    assert "@page { size: A4; margin: 12mm; }" in css
    block = css[css.index("/* 直し48 段4: more on it, still one A4 sheet"):]
    block = block[:block.index("\n}\n")]
    assert ".hk-sheet { font-size: 13px; line-height: 1.55; }" in block and ".hk-qbox { min-height: 0;" in block
