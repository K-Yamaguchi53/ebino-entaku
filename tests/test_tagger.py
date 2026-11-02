"""Topic tags and the index (SPEC 6, 14-3, 14-39). Everything here is invented."""

import json

from fake_client import FakeClient, text_response

from conftest import COMPANY, DISPLAY_NAME, make_seat, write_seats
from ebino import tagger
from ebino.gate import Gate, NameList
from ebino.index import build_index, load_topics, load_utterances
from ebino.ingest.utterance import Utterance
from ebino.saved_output import load_output

SEATS = [
    make_seat(seat_id="S01"),  # 理容師, company はるかぜ理容, display name 山川さん.
    make_seat(seat_id="P01", kind="poster", title="探究の先輩（川の水を調べた）", company="",
              display_name="先輩", district=""),
]


def piece(i, seat="S01", text=None):
    return Utterance(id=f"adult-{i:03}", seat_id=seat, kind="adult", section="本文",
                     voice="article", text=text or f"この方は朝{i}時に店を開ける。", paragraph="")


def setup(tmp_path, pieces):
    write_seats(tmp_path / "seats.tsv", SEATS)
    folder = tmp_path / "ingested"
    folder.mkdir()
    (folder / "utterances.json").write_text(
        json.dumps([p.to_dict() for p in pieces], ensure_ascii=False), encoding="utf-8")
    return tmp_path


def tags_for(request):
    sent = json.loads(request["messages"][0]["content"])
    return text_response({"tags": [{"id": p["id"], "topics": ["朝", "店"]} for p in sent]})


def test_pieces_are_tagged_in_batches_and_saved_with_the_model(tmp_path):
    folder = setup(tmp_path, [piece(i) for i in range(45)])
    client = FakeClient(tags_for)
    report = tagger.run(folder, client)
    assert (report.tagged, report.untagged, report.batches) == (45, 0, 2)
    saved = load_output(folder / "ingested" / "topics.json")
    assert saved.model == "claude-haiku-5-5"
    assert saved.output["adult-000"] == ["朝", "店"]
    assert all(r["model"] == "claude-haiku-5-5" for r in client.requests)


def test_a_second_run_only_fills_gaps(tmp_path):
    folder = setup(tmp_path, [piece(i) for i in range(3)])
    tagger.run(folder, FakeClient(tags_for))
    client = FakeClient(tags_for)
    report = tagger.run(folder, client)
    assert (report.already, report.tagged, report.batches) == (3, 0, 0)
    assert client.requests == []


def test_empty_answers_are_counted_apart_and_not_sent_again(tmp_path):
    # SPEC 14-52: tagged / answered with no topics / not answered yet.
    folder = setup(tmp_path, [piece(1), piece(2), piece(3)])

    def some_empty(request):
        sent = json.loads(request["messages"][0]["content"])
        return text_response({"tags": [
            {"id": sent[0]["id"], "topics": ["朝"]},
            {"id": sent[1]["id"], "topics": []},
            {"id": sent[2]["id"], "topics": ["とても長い話題の名前ですね"]},  # Trimmed to none.
        ]})

    report = tagger.run(folder, FakeClient(some_empty))
    assert (report.tagged, report.empty, report.untagged) == (1, 2, 0)
    assert (report.with_topics, report.empty_total) == (1, 2)
    assert "answered now with topics: 1" in report.lines()
    assert "answered now with no topics: 2" in report.lines()

    client = FakeClient(tags_for)
    again = tagger.run(folder, client)
    assert client.requests == []
    assert (again.already, again.tagged, again.empty) == (3, 0, 0)
    assert (again.with_topics, again.empty_total, again.untagged) == (1, 2, 0)


def test_no_company_or_display_name_reaches_the_tagger(tmp_path):
    folder = setup(tmp_path, [piece(1), piece(2, "P01", "川の水を調べた。")])
    client = FakeClient(tags_for)
    tagger.run(folder, client)
    sent = client.all_sent()
    assert COMPANY not in sent and "はるかぜ" not in sent
    assert DISPLAY_NAME not in sent and "山川" not in sent


def test_a_batch_with_a_name_is_stopped_and_counted(tmp_path):
    folder = setup(tmp_path, [piece(1, text="山川さんは店に立つ。")])
    client = FakeClient(tags_for)
    report = tagger.run(folder, client)
    assert report.failures == {"name_in_request": 1}
    assert report.untagged == 1
    assert client.requests == []


def test_a_refused_batch_is_counted_and_left_for_next_time(tmp_path):
    folder = setup(tmp_path, [piece(1)])
    report = tagger.run(folder, FakeClient([text_response("", stop_reason="refusal")]))
    assert report.failures == {"refusal": 1}
    assert load_topics(folder) == {}


def test_topics_are_trimmed_and_unknown_ids_ignored(tmp_path):
    answer = {"tags": [
        {"id": "adult-001", "topics": ["朝", "朝", "", "とても長い話題の名前ですね", "店", "髪", "顔"]},
        {"id": "adult-999", "topics": ["作り話"]},
    ]}
    topics = tagger.tag_pieces(
        Gate(FakeClient([text_response(answer)]), NameList()), [piece(1)], {}, tagger.TagReport()
    )
    assert topics == {"adult-001": ["朝", "店", "髪"]}


def test_index_has_seat_place_and_topics_but_no_company_name_or_year(tmp_path):
    folder = setup(tmp_path, [piece(1), piece(2, "Z99")])
    tagger.run(folder, FakeClient(tags_for))
    entries = build_index(load_utterances(folder), SEATS, load_topics(folder))
    assert [e.utterance_id for e in entries] == ["adult-001"]  # Z99 is not in the table.
    entry = entries[0].for_model()
    assert entry["title"] == "理容師" and entry["district"] == "架空地区"
    assert entry["topics"] == ["朝", "店"]
    flat = json.dumps(entry, ensure_ascii=False)
    assert "はるかぜ" not in flat and "山川" not in flat and "2026" not in flat
