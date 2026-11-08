"""直し54m (the teacher, 11/8): 好きな教科・がんばりたい教科を聞いて, then that
subject's card from the teacher's table, and where it came up in today's
people's words (the model points, code checks word for word). Everything
here is invented."""

import json

import pytest
from fake_client import text_response

from ebino import app as app_module, hitokoto, subjects
from ebino.session import Refused
from test_hitokoto import Model, sitting, to_scale
from test_subjects import catalog

HITOKOTO_JS = (app_module.STATIC_DIR / "hitokoto.js").read_text(encoding="utf-8")
LIKED_LEAD = "あなたは、高校生が「好きな教科"


class LikedModel(Model):
    """The hitokoto fake, and the liked subject's request answered by `tie`
    (a dict, an Exception, or a function of the data sent)."""

    def __init__(self, tie=None, **kwargs):
        super().__init__(**kwargs)
        self.tie = tie
        self.tie_sent: list[dict] = []

    def __call__(self, request):
        system = request["system"][0]["text"]
        if system.startswith(LIKED_LEAD):
            data = json.loads(request["messages"][0]["content"])
            self.tie_sent.append(data)
            value = self.tie(data) if callable(self.tie) else self.tie
            if isinstance(value, Exception):
                raise value
            return text_response(value)
        return super().__call__(request)


def at_subject(tie=None, lab="quest"):
    model = LikedModel(tie)
    session, _, _, _ = sitting(model)
    session.library.subject_catalog = catalog()
    session.lab = lab
    to_scale(session)
    session.hitokoto_scale(10)
    session.hitokoto_forward("", skip=True)
    session.hitokoto_notice("no_answer")
    session.hitokoto_way("", skip=True)
    return session, model


# --- the teacher's table ---

def test_the_subjects_to_pick_are_this_students_each_once_in_table_order():
    names = subjects.subject_names(catalog(), "quest")
    rows = [c.row.subject for c in catalog().candidates("quest")]
    assert names == list(dict.fromkeys(rows)) and len(names) == len(set(names)) and names
    assert subjects.subject_names(catalog(manabu=False), "quest") == []
    assert subjects.subject_names(None, "quest") == []


def test_the_card_is_the_picked_subjects_row():
    name = subjects.subject_names(catalog(), "quest")[0]
    pick = subjects.choose_subject(catalog(), "quest", name, {"question": ""}, subjects.Counter())
    assert pick.status == subjects.SHOWN and pick.source == subjects.SOURCE_LIKED
    assert {c.row.subject for c in pick.order} == {name}
    assert subjects.choose_subject(catalog(), "quest", "架空の科目", {}, subjects.Counter()).status \
        == subjects.STATUS_NO_CANDIDATE
    assert subjects.choose_subject(catalog(manabu=False), "quest", name, {}, subjects.Counter()).status \
        == subjects.STATUS_NO_MANABU


# --- the sitting ---

def test_the_subject_picked_shows_its_card_and_the_words_it_came_up_in():
    def tie(data):
        return {"person": 1, "quote": data["people"][0]["text"][:8]}

    session, model = at_subject(tie)
    names = session.hitokoto_subject_names()["names"]
    assert names == subjects.subject_names(catalog(), "quest")
    result = session.hitokoto_liked(names[0])
    assert result["next"] == "try" and session.talk.stage == hitokoto.TRY
    assert result["subject"]["cards"][0]["subject"] == names[0]
    person = session.talk.people[0]
    assert result["tie"] == {"lead": f"{names[0]}は、今日の話のここに出てきた", "who": person.title,
                             "quote": person.text[:8]}
    # The model got the subject and the people's words by number: no seat, title or name.
    sent = model.tie_sent[0]
    assert sent["subject"] == names[0] and set(sent["people"][0]) == {"number", "text"}
    record = session.talk.record()
    assert record["liked"] == names[0] and record["liked_tie"]["seat_id"] == person.seat_id
    story = "".join(part["text"] for line in [hitokoto.story(session.talk)] for part in line)
    assert names[0] in story


@pytest.mark.parametrize("tie, reason", [
    ({"person": 0, "quote": ""}, hitokoto.STOP_LIKED_NONE),
    ({"person": 9, "quote": "休みは"}, hitokoto.STOP_LIKED_PERSON),
    ({"person": 1, "quote": "どこにもない言葉です"}, hitokoto.STOP_QUOTE_NOT_WRITTEN),
    (RuntimeError("down"), None),
])
def test_words_code_cannot_find_in_that_persons_words_show_no_line(tie, reason):
    session, _ = at_subject(tie)
    name = session.hitokoto_subject_names()["names"][0]
    result = session.hitokoto_liked(name)
    assert result["tie"] is None and result["subject"] is not None and result["next"] == "try"
    if reason:
        assert session.talk.liked_asked["reason"] == reason


def test_answer_none_goes_on_and_an_unknown_subject_is_refused():
    session, model = at_subject({"person": 0, "quote": ""})
    with pytest.raises(Refused):
        session.hitokoto_liked("架空の科目")
    assert session.hitokoto_liked(None, skip=True) == {"next": "try", "subject": None, "tie": None}
    assert session.talk.liked == "" and model.tie_sent == []


def test_with_no_table_the_screen_asks_as_before():
    session, _ = at_subject()
    session.library.subject_catalog = catalog(manabu=False)
    assert session.hitokoto_subject_names() == {"names": []}
    assert 'post("subject_names", {})' in HITOKOTO_JS
    assert "if (!names.length) return askSubjectBefore();" in HITOKOTO_JS
    assert hitokoto.words()["liked_q"]
