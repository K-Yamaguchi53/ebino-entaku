"""Poster purposes as sample questions (SPEC 5-1, 8, 14-42, 14-44). Invented posters."""

import random

from conftest import make_seat
from ebino.ingest.utterance import Utterance
from ebino.purpose import PurposeShelf, samples

SEATS = [
    make_seat(seat_id="S01"),
    make_seat(seat_id="P01", kind="poster", title="探究の先輩（川の水を調べた）", company="", display_name="先輩"),
    make_seat(seat_id="P02", kind="poster", title="探究の先輩（商店街の祭り）", company="", display_name="先輩"),
    make_seat(seat_id="P03", kind="poster", title="探究の先輩（朝ごはん）", company="", display_name="先輩"),
]


def u(i, seat, section, heading, text, kind="poster"):
    return Utterance(id=i, seat_id=seat, kind=kind, section=section, voice="poster", text=text,
                     paragraph=text, heading=heading)


UTTERANCES = [
    u("s1", "S01", "本文", "", "川で釣りをします。", kind="adult"),
    u("p1a", "P01", "背景と課題", "背景", "川がにごる日がある。"),
    u("p1b", "P01", "目的", "研究仮説", "雨のあとに川がにごるのではないか。"),
    u("p1c", "P01", "目的", "目的", "川のにごりは何で決まるのかを知る。"),
    u("p1d", "P01", "目的", "目的", "自分たちで測れる方法を探す。"),
    u("p2a", "P02", "目的", "探究仮説", "祭りがあると商店街に人が来るのではないか。"),
    u("p3a", "P03", "結果", "結果", "朝ごはんを食べる人が多かった。"),
]


def test_a_posters_purpose_section_wins_over_its_hypothesis_and_keeps_its_order():
    found = {s.seat_id: s for s in samples(UTTERANCES, SEATS)}
    assert found["P01"].utterance_ids == ("p1c", "p1d")
    assert found["P01"].texts == ("川のにごりは何で決まるのかを知る。", "自分たちで測れる方法を探す。")


def test_a_hypothesis_is_the_purpose_when_there_is_no_purpose_heading():
    found = {s.seat_id: s for s in samples(UTTERANCES, SEATS)}
    assert found["P02"].texts == ("祭りがあると商店街に人が来るのではないか。",)


def test_only_posters_with_a_purpose_give_samples():
    assert [s.seat_id for s in samples(UTTERANCES, SEATS)] == ["P01", "P02"]


def test_the_shelf_hands_out_each_sample_once_before_any_comes_back():
    found = samples(UTTERANCES, SEATS) * 2  # Four samples.
    shelf = PurposeShelf(found, random.Random(1))
    first, second = shelf.next(3), shelf.next(3)
    assert len(first) == 3 and len(second) == 3
    assert sorted(map(id, first + second[:1])) == sorted(map(id, found))
    assert PurposeShelf([], random.Random(1)).next() == []
