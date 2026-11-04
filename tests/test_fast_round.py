"""直し31-6: from 「聞く」 to the first bubble in about ten seconds. The
moderator runs on Sonnet with effort medium (the teacher allowed it lowered),
the librarian makes at most two requests, the moderator is sent only the
seats that matter to the pieces, and on screen the table comes sooner, its
cards rising one by one 0.25 s apart (all at once with motion reduced).
Everything here is invented."""

import json

from conftest import make_seat
from ebino import app as app_module
from ebino import gate, librarian, moderator
from ebino.index import Entry
from test_session import ANSWERED, sitting

MAP = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
CSS = (app_module.STATIC_DIR / "style.css").read_text(encoding="utf-8")


def test_the_moderator_is_lighter_and_the_librarian_shorter():
    assert gate.MODELS["moderator"] == "claude-sonnet-5-5" and gate.EFFORT["moderator"] == "medium"
    assert librarian.MAX_REQUESTS == 2


def entry(uid, seat_id, topics):
    return Entry(uid, seat_id, "adult", "架空", "", "spoken", "本文", tuple(topics), "架空の言葉。")


def test_the_moderator_gets_the_pieces_seats_and_the_others_sharing_their_topics():
    seats = [make_seat(seat_id=f"S{n:02}", company="", display_name="") for n in range(20)]
    candidates = [entry("a", "S00", ["休み"]), entry("b", "S01", ["休み", "家族"])]
    entries = candidates + [entry("c", "S02", ["休み", "家族"]), entry("d", "S03", ["家族"]),
                            entry("e", "S04", ["米"])] + [entry(f"x{n}", f"S{n:02}", ["休み"]) for n in range(5, 20)]
    kept = [seat.seat_id for seat in moderator.related_seats(candidates, entries, seats)]
    assert kept[:2] == ["S00", "S01"] and "S04" not in kept  # Nothing shared: not sent.
    assert "S02" in kept and len(kept) == 2 + moderator.MAX_OTHER_SEATS


def test_a_round_sends_the_moderator_fewer_seats():
    session, client = sitting(ANSWERED)
    session.ask("休みの日って、みんな何してる？")
    sent = json.loads(client.requests[1]["messages"][0]["content"])
    assert {seat["seat_id"] for seat in sent["seats"]} <= {"S01", "S02", "S03", "P01"}
    assert {"S01", "S02"} <= {seat["seat_id"] for seat in sent["seats"]}


def test_the_table_comes_sooner_and_its_cards_rise_one_by_one():
    assert "const LIGHT_EVERY = 250;" in MAP
    assert "const CAMERA_FOR = 700, FLY_FOR = 700, FLY_GAP = 90," in MAP
    assert "animation-delay: calc(var(--k, 0) * 250ms);" in CSS
    reduced = CSS[CSS.index("@media (prefers-reduced-motion: reduce)"):]
    assert ".table-bubble { animation: none !important; }" in reduced  # All at once.
