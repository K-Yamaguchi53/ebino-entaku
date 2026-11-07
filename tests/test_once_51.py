"""直し51 段2 (ヒビキ, 49_sheet_notice_try: the farmer's sentence three times,
the student's line three times, the first question three times): on the one
sheet, one person's words (one sentence) and the student's own lines are in
full once; again, they are pointed at by a title or a heading of the sheet,
never reworded nor cut. Every record and word here is invented; the model is
a fake one."""

import json

from ebino import app as app_module
from ebino import hitokoto
from test_hitokoto import LIGHT_OK, Model, sitting, to_end, to_scale
from test_session import UTTERANCES
from test_sheet_more import TieModel

HK = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
SHEET_JS = HK[HK.index("  async function toSheet() {"):HK.index("  function setup() {")]
WORDS = hitokoto.words()
WROTE = "空いたら取るのがいいと思った"


def in_full(sheet):
    """Each piece of words the screen sets in full on the sheet (as toSheet
    does), its 「」 off: the rest are pointers (texts/)."""
    out = [sheet["notice"], sheet["first_question"], sheet["now_question"]]
    out += [m["quote"] for m in sheet["met"]]
    out += [t for t, ref in zip(sheet["moves"], sheet["moves_ref"]) if not ref] if len(sheet["moves"]) > 1 else []
    if sheet["tie"] and not sheet["tie"].get("short"):
        out += [sheet["tie"]["a"]["quote"], sheet["tie"]["b"]["quote"]]
    for mark in sheet["marks"]:
        out += [mark["note"]] + ([] if mark.get("ref") else [mark["text"]])
    out += [p["text"].strip("「」") for p in sheet["story"] if p["strong"]]
    if sheet["light"] and not sheet["light"].get("ref"):
        out.append(sheet["light"]["quote"])
    out.append(sheet["next_step"])
    if sheet["next_try"]:
        out.append(sheet["next_try"]["text"])
    return [hitokoto.bare(t) for t in out if t]


def _sheet(model=None, light=None, next_try="later", notice="yes"):
    model = model or TieModel(light=light)
    session, _, _, _ = sitting(model)
    to_scale(session)
    session.hitokoto_scale(8)
    session.hitokoto_forward("先輩にもう一回聞く")
    session.hitokoto_notice(notice, "畑の人は雨の日も休みじゃないと知った")
    session.hitokoto_way("農業")
    session.hitokoto_subject("no")
    session.hitokoto_try(next_try, "雨の日の畑を見に行く")
    if next_try == "meet":
        session.hitokoto_meet("")
    session.hitokoto_light()
    return session, session.hitokoto_sheet("休みの決め方で、仕事はどう変わる？")


def _count(sheet, text):
    body = hitokoto.bare(text)
    return sum(1 for full in in_full(sheet) if body == full)


def test_each_persons_sentence_and_each_line_of_the_students_once_in_full():
    for light in (None, dict(LIGHT_OK, quote=WROTE)):
        for next_try in ("later", "try"):
            session, sheet = _sheet(light=light, next_try=next_try)
            full = in_full(sheet)
            assert len(full) == len(set(full)), full
            # Each person's sentence, word for word as recorded, is there once.
            for person in sheet["met"]:
                assert any(person["quote"] in u.text for u in UTTERANCES)
                assert _count(sheet, person["quote"]) == 1
            # The first question and the student's lines, once.
            assert _count(sheet, sheet["first_question"]) == 1
            for written in session.talk.written:
                if not hitokoto.has_avoid(written["text"]):
                    assert _count(sheet, written["text"]) == 1, written


def test_the_hosts_tie_is_its_line_and_the_two_titles():
    _, sheet = _sheet()
    tie = sheet["tie"]
    assert tie["short"] is True and tie["kind"] == "differ"
    assert 'tie.append(el("p", "hk-tie-who", `${sheet.tie.a.title}・${sheet.tie.b.title}`));' in SHEET_JS
    assert "if (sheet.tie.short) {" in SHEET_JS
    # The record keeps the tie as it was (kind and seats only).
    assert set(session_record_tie()) == {"kind", "a", "b"}


def session_record_tie():
    session, _ = _sheet()
    return session.talk.record()["tie"]


def test_the_story_points_at_the_words_above():
    _, sheet = _sheet()
    story = "".join(p["text"] for p in sheet["story"])
    farmer = sheet["met"][0]["title"]
    assert hitokoto.fill(WORDS["story_word_short"], who=farmer) in story
    assert WORDS["story_wrote_short"] in story and WORDS["story_way_short"] in story
    assert WROTE not in story and "農業" not in story
    # Not quoted elsewhere: in full in the story, as before.
    alone = "".join(p["text"] for p in hitokoto.story(_sheet()[0].talk))
    assert f"「{WROTE}」" in alone


def test_the_students_words_in_turn_point_at_the_questions_and_the_light():
    _, sheet = _sheet(light=dict(LIGHT_OK, quote=WROTE))
    moves, refs = sheet["moves"], sheet["moves_ref"]
    assert moves[0] == sheet["first_question"] and refs[0] == "first_label"
    assert moves[-1] == sheet["now_question"] and refs[-1] == "sheet_now"
    assert refs[moves.index(WROTE)] == "light_title"  # In full in the light's box below.
    assert sheet["light"] == {"quote": WROTE, "why": LIGHT_OK["why"]}
    assert refs[moves.index("先輩にもう一回聞く")] == "sheet_step" and sheet["next_step"] == "先輩にもう一回聞く"
    assert refs[moves.index("部活がない日は空いたら休む")] == ""
    assert 'if (ref) li.append(el("span", "hk-ref", W[ref]));' in SHEET_JS
    for key in ("first_label", "sheet_now", "light_title", "sheet_step"):
        assert WORDS[key]


def test_a_mark_on_the_first_question_points_at_it():
    session, _ = _sheet()
    session.talk.marks = [{"n": 1, "mark": "surprised", "note": "", "label": "はじめて知った・気づいた",
                           "text": session.talk.first_question}]
    sheet = hitokoto.sheet_view(session.talk)
    assert sheet["marks"][0]["ref"] == "first_label" and sheet["marks"][0]["text"] == session.talk.first_question
    assert 'mark.ref ? el("span", "hk-ref", W[mark.ref]) : mark.text' in SHEET_JS


def test_the_light_on_a_persons_sentence_above_says_whose():
    session, sheet = _sheet()
    talk = session.talk
    talk.light = hitokoto.Light(sheet["met"][0]["quote"], "chosen", 2, "why", "", "code", "", sheet["met"][0]["title"])
    lit = hitokoto.sheet_view(talk)["light"]
    assert lit["ref"] == "chosen" and lit["who"] == sheet["met"][0]["title"]
    assert 'fill(W.light_chosen_who, { who: sheet.light.who })' in SHEET_JS
    talk.light = hitokoto.Light(talk.first_question, "first", 1, "why", "", "code", "")
    assert hitokoto.sheet_view(talk)["light"]["ref"] == "first_label"


def test_nothing_is_reworded():
    # Pointers are texts/ words; every quote kept is the record's or the student's as written.
    _, sheet = _sheet(light=dict(LIGHT_OK, quote=WROTE))
    for person in sheet["met"]:
        assert any(person["quote"] in u.text for u in UTTERANCES)
    assert sheet["notice"] == "畑の人は雨の日も休みじゃないと知った"
    assert sheet["next_try"] is None  # まだ決めない.
    assert _sheet(next_try="try")[1]["next_try"]["text"] == "雨の日の畑を見に行く"
    for key in ("story_word_short", "story_wrote_short", "story_more_short", "story_way_short"):
        assert "{*" not in WORDS[key]  # No words of anyone's in them.


def test_with_only_pointers_there_is_no_list():
    session, _ = _sheet()
    talk = session.talk
    talk.written = []
    sheet = hitokoto.sheet_view(talk)
    assert sheet["moves"] == [] and sheet["moves_ref"] == []
    json.dumps(sheet, ensure_ascii=False)
