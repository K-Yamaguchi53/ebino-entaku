"""Long purpose samples shown as their saved summary (the teacher's call on
11/3). Every poster, seat and summary here is invented."""

import json
from datetime import date

from conftest import DISPLAY_NAME, make_seat
from fake_client import FakeClient, text_response

from ebino import purpose_summary
from ebino.banned_words import BANNED_WORDS
from ebino.gate import Gate, NameList
from ebino.ingest.utterance import Utterance
from ebino.purpose import samples
from ebino.purpose_summary import SUMMARY_FILE, Saved, SummaryReport, load_saved, shown_samples, summarize
from ebino.saved_output import save_output
from ebino.session import Library, Session
from ebino.texts import SAMPLE_SUMMARIZED, SCREEN_TEXTS, load_text

SEATS = [
    make_seat(seat_id="S01"),  # An adult seat: its name is on the gate's list.
    make_seat(seat_id="P01", kind="poster", title="探究の先輩（川の水）", company="", display_name="先輩"),
    make_seat(seat_id="P02", kind="poster", title="探究の先輩（朝市）", company="", display_name="先輩"),
    make_seat(seat_id="P03", kind="poster", title="探究の先輩（祭り）", company="", display_name="先輩"),
]


def u(i, seat, text):
    return Utterance(id=i, seat_id=seat, kind="poster", section="目的", voice="own", text=text,
                     paragraph=text, heading="目的")


# 200 characters, with PDF debris: numbers in a row and a URL.
LONG = ("川の水が減っていると聞いて、まず上流と下流で水の量を比べることにした。"
        "1 2 3 4 5 6 7 8 9 10 http://example.invalid/kawa/2026/data "
        "なぜ水が減ったのかを確かめるために、雨の量と田んぼに引く水の量も調べた。"
        "そのうえで、町の人に川との付き合い方を聞き、これからの川をどう守るかを考えたい。")
LONG = (LONG * 2)[:200]
SHORT = "朝市に若い人が来ないのはなぜかを、売る人と買う人の両方から確かめたい。" + "店ごとに話を聞いて比べる。"
SHORT = SHORT[:80] if len(SHORT) > 80 else SHORT
LONG3 = ("祭りの日に商店街の人の流れがどう変わるのかを、" * 8)[:150]
UTTERANCES = [u("p1", "P01", LONG), u("p2", "P02", SHORT), u("p3", "P03", LONG3)]
SUMMARY = "川の水がなぜ減ったのかを、上流と下流の水の量や雨の量から確かめ、これからの川の守り方を考えたい。"


def names():
    return NameList.build(SEATS, {})


def found():
    return samples(UTTERANCES, SEATS)


def test_the_invented_samples_are_the_lengths_the_teacher_named():
    assert [len("".join(s.texts)) for s in found()] == [200, len(SHORT), 150]
    assert len(SHORT) <= 120


def view(saved):
    lib = Library.build(SEATS, UTTERANCES, {}, saved_summaries=saved)
    session = Session(lib, Gate(FakeClient([]), names()))
    return {sample.seat_id: session.purpose_view(sample) for sample in lib.purposes}


def test_a_long_sample_is_shown_as_its_saved_summary_with_the_mark():
    shown = view(Saved({"P01": SUMMARY}, {"P01": ["p1"]}))
    assert shown["P01"]["texts"] == [SUMMARY] and shown["P01"]["summarized"]
    assert shown["P02"]["texts"] == [SHORT] and not shown["P02"]["summarized"]  # As it is, no mark.
    assert "P03" not in shown  # Long, with no summary: not shown.


def test_with_no_summary_file_only_samples_of_120_or_fewer_are_shown(tmp_path):
    assert load_saved(tmp_path) == Saved()
    assert list(view(load_saved(tmp_path))) == ["P02"]


def test_a_summary_that_fails_the_check_is_not_shown():
    for summary in (
        "川の水がなぜ減ったのかを、頑張って確かめたい。",  # A banned word.
        f"{DISPLAY_NAME}は、川の水がなぜ減ったのかを確かめたい。",  # A name on the gate's list.
        "「川の水を守りたい」と考えて、なぜ減ったのかを確かめたい。",  # 「」 not holding the sample's words.
        "川の水を確かめたい。" * 13,  # Over 120 characters.
    ):
        assert "P01" not in view(Saved({"P01": summary}, {"P01": ["p1"]}))


def test_a_quote_in_a_summary_never_runs_across_a_line_break_or_into_the_next_piece():
    rows = "上流では水が足りていた→下流では田んぼが乾いた\n雨の少ない年→川の水も減った"
    long = rows + "\n" + "川の水の量を毎日はかり、雨の量と比べて、これからの守り方を考えたい。" * 3
    sample = samples([u("p1", "P01", long), u("p4", "P01", "町の人に聞いて考えた。")], SEATS)[0]
    assert purpose_summary.is_long(sample)
    for crossing in ("「田んぼが乾いた雨の少ない年」", "「考えたい。町の人に聞いて」"):
        assert purpose_summary.stopped(f"{crossing}から、川の水を確かめたい。", sample, names())
    for inside in ("「田んぼが乾いた」", "「雨の少ない年→川の水も減った」", "「町の人に聞いて考えた。」"):
        assert not purpose_summary.stopped(f"{inside}から、川の水を確かめたい。", sample, names())


def test_line_breaks_are_not_counted_toward_the_length():
    rows = "\n".join(["水"] * 61)  # 61 characters on 61 rows: 121 with the breaks.
    assert not purpose_summary.is_long(samples([u("p1", "P01", rows)], SEATS)[0])


def test_a_summary_made_from_other_pieces_is_not_shown():
    # The sample was ingested again and its pieces changed: the summary is stale.
    assert "P01" not in view(Saved({"P01": SUMMARY}, {"P01": ["p1-old"]}))


def test_the_mark_is_the_teachers_text_sent_to_the_screen():
    assert SAMPLE_SUMMARIZED in SCREEN_TEXTS
    assert load_text(SAMPLE_SUMMARIZED) == "長いので、短くまとめたもの"


def says(summary):
    return text_response({"summary": summary})


def test_the_command_sends_only_long_samples_missing_a_summary_and_counts_what_failed():
    client = FakeClient([says("祭りの日の、頑張る人を調べたい。")])  # P03: stopped by the check.
    gate = Gate(client, names())
    report = SummaryReport()
    kept = summarize(gate, found(), Saved({"P01": SUMMARY}, {"P01": ["p1"]}), report)
    assert len(client.requests) == 1  # P01 was made before; P02 is short.
    request = client.requests[0]
    assert request["model"] == "claude-sonnet-5-5"
    assert request["output_config"]["format"]["type"] == "json_schema"
    assert LONG3 in request["messages"][0]["content"] and SHORT not in json.dumps(request, ensure_ascii=False)
    assert kept == Saved({"P01": SUMMARY}, {"P01": ["p1"]})  # The stopped one is not saved.
    assert (report.samples, report.long, report.already, report.made) == (3, 2, 1, 0)
    assert dict(report.stopped) == {"banned_word": 1} and report.missing == ["P03"]
    printed = "\n".join(report.lines())
    assert "P03" in printed and "祭り" not in printed and "川" not in printed  # Counts, codes and IDs only.


WISH = "若い人にも、商店街で店を開く楽しさを知ってほしいと考えた。"
WISH_SAMPLE = ("商店街の空き店舗が増えている理由を、店の人と町の人の両方から確かめたい。" * 3, WISH)


def wish_sample():
    pieces = [u("w1", "P01", WISH_SAMPLE[0]), u("w2", "P01", WISH_SAMPLE[1])]
    return samples(pieces, SEATS)[0]


def test_the_request_asks_for_a_wish_in_quotes_from_one_line_with_the_banned_words():
    sample = wish_sample()
    assert purpose_summary.is_long(sample)
    request = purpose_summary.request_for(sample)
    system = request["system"][0]["text"]
    assert "見本の言葉のまま「」で引く" in system and "見本の1行の中の言葉だけ" in system
    assert "「」『』は使わない" not in system  # The old rule against any quote is gone.
    assert all(word in system for word in BANNED_WORDS)
    assert "{" not in system  # Every slot is filled.
    # The pieces go one to a line, so the model sees the lines a quote stays in.
    assert json.loads(request["messages"][0]["content"])["text"] == "\n".join(WISH_SAMPLE)


def test_a_wish_quoted_from_the_sample_passes_and_one_in_own_words_is_still_stopped():
    sample = wish_sample()
    quoted = "空き店舗が増えた理由を確かめ、「若い人にも、商店街で店を開く楽しさを知ってほしい」と考えた。"
    assert not purpose_summary.stopped(quoted, sample, names())
    own_words = "空き店舗が増えた理由を確かめ、若い人にも店を開く楽しさを知ってほしいと考えた。"
    assert purpose_summary.stopped(own_words, sample, names()) == "banned_word"
    # A 「」 must still hold the sample's words from one line: not changed, not across pieces.
    for wrong in ("「若い人にも、店を開く楽しさを知ってほしい」", "「両方から確かめたい。若い人にも」"):
        assert purpose_summary.stopped(f"空き店舗が増えた中で、{wrong}と考えた。", sample, names()) == "quote_not_in_record"


def test_the_command_makes_a_summary_and_a_failed_request_is_counted():
    client = FakeClient([says(SUMMARY)])  # P03 then finds the fake client empty.
    report = SummaryReport()
    kept = summarize(Gate(client, names()), found(), Saved(), report)
    assert kept.summaries == {"P01": SUMMARY} and kept.sources == {"P01": ["p1"]}
    assert report.made == 1 and sum(report.failures.values()) == 1 and report.missing == ["P03"]


def test_a_changed_sample_is_summarized_again():
    client = FakeClient([says(SUMMARY), says("祭りの日の商店街の人の流れを確かめたい。")])
    report = SummaryReport()
    kept = summarize(Gate(client, names()), found(), Saved({"P01": "古い要約。"}, {"P01": ["p1-old"]}), report)
    assert kept.summaries["P01"] == SUMMARY and report.already == 0 and report.made == 2


def test_the_file_keeps_model_date_and_seat_to_summary_for_the_teacher(tmp_path):
    (tmp_path / "ingested").mkdir()
    path = tmp_path / "ingested" / SUMMARY_FILE
    save_output(path, "claude-sonnet-5-5", {"P01": SUMMARY}, date(2026, 11, 3),
                extra={purpose_summary.SOURCES: {"P01": ["p1"]}})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["model"] == "claude-sonnet-5-5" and data["created"] == "2026-11-03"
    assert data["output"] == {"P01": SUMMARY}
    # The teacher corrects a summary by hand: the corrected one is shown.
    data["output"]["P01"] = "川の水がなぜ減ったのかを確かめたい。"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert view(load_saved(tmp_path))["P01"]["texts"] == ["川の水がなぜ減ったのかを確かめたい。"]


def test_the_screen_marks_a_summarized_sample():
    from ebino import app as app_module
    script = (app_module.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    purposes = script[script.index("function renderPurposes"):script.index("\n}\n", script.index("function renderPurposes"))]
    assert 'sample.summarized ? el("span", { class: "summarized", text: state.texts.sample_summarized }) : null' in purposes
