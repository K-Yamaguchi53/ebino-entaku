"""直し36: one to one's questions with a fast model (asker, Haiku, low),
where the teacher allowed it, with a fake model. Everything here is
invented.

段1: at ingest, which axes each page of a seat with pages only answers.
Only the axes' names come back; the answer goes to the model's own table
(ask_pages_model.tsv) beside the teacher's, which is read first."""

import pytest
from conftest import make_seat
from fake_client import FakeClient, text_response

from ebino import asker, gate as gate_module, one_to_one
from ebino.gate import Gate, NameList
from ebino.ingest.utterance import Utterance

SEATS = [make_seat(seat_id="C01", kind="cross", title="県外に出た人（架空）", company="", display_name=""),
         make_seat(seat_id="C02", kind="cross", title="海外に出た人（架空）", company="", display_name=""),
         make_seat(seat_id="O01", kind="outsider_teacher", title="外から来た先生（架空）", company="",
                   display_name="", district=""),
         make_seat(seat_id="N01", kind="adult", title="名前の席（架空）", company="", display_name="山川さん")]


def _u(seat, section, text, n=0):
    return Utterance(id=f"{seat}-{section}-{n}", seat_id=seat, kind="x", section=section, voice="own",
                     text=text, paragraph=text)


UTTERANCES = [_u("C01", "p1", "町を出ようと決めたのは秋でした。"), _u("C01", "p2", "向こうでは毎日が驚きでした。"),
              _u("C01", "p3", "目次"),
              _u("C02", "p1", "帰ってきて、町の見え方が変わった。"),
              _u("O01", "p1", "えびのに来たのは、山が好きだったから。")]
KINDS = {"C01": "cross", "C02": "cross", "O01": "outsider_teacher"}


def sorted_as(**pages):
    return text_response({"pages": [{"page": page, "axes": axes} for page, axes in pages.items()]})


def a_gate(answers):
    client = FakeClient(answers)
    return Gate(client, NameList.build(SEATS, {})), client


def table(path):
    return path.read_text(encoding="utf-8").splitlines()


# --- 段1: the pages sorted into axes ---

def test_the_asker_is_haiku_low_and_waits_30_seconds_at_ingest():
    assert gate_module.MODELS["asker"] == "claude-haiku-5-5" and gate_module.EFFORT["asker"] == "low"
    assert asker.INGEST_TIMEOUT_SECONDS == 30.0


def test_one_request_a_seat_and_only_the_axes_names_are_kept(tmp_path):
    gate, client = a_gate([
        sorted_as(p1=["行く前"], p2=["向こうで", "好きな食べ物"], p3=[], p9=["これから"]),
        sorted_as(p1=["帰ってきて"]),
        sorted_as(p1=["来たわけ", "行く前"]),
    ])
    counts = one_to_one.write_tables(tmp_path, UTTERANCES, KINDS, gate)
    assert len(client.requests) == 3  # One a seat, all its pages in it.
    assert client.options == [{"timeout": 30.0, "max_retries": 0}] * 3
    assert client.requests[0]["model"] == "claude-haiku-5-5"
    assert table(tmp_path / "ask_pages_model.tsv") == [
        "席\tページ\t軸", "C01\tp1\t行く前", "C01\tp2\t向こうで", "C01\tp3\t-", "C02\tp1\t帰ってきて",
        "O01\tp1\t来たわけ"]  # 好きな食べ物, p9 and 行く前 for O01 (not its group's) are dropped.
    tables = one_to_one.load_tables(tmp_path)
    assert tables["pages"]["C01"] == {"p1": ["行く前"], "p2": ["向こうで"]}
    assert counts["model"]["page_seats_sorted"] == 3 and counts["model"]["pages_no_axis"] == 1
    assert counts["model"]["pages_by_axis"] == {"行く前": 1, "向こうで": 1, "帰ってきて": 1, "来たわけ": 1}
    # The outsider's own axes are asked with its own questions, the schema naming them only.
    sent = client.requests[2]
    assert "来たわけ" in sent["messages"][0]["content"] and "行く前" not in sent["messages"][0]["content"]
    enum = sent["output_config"]["format"]["schema"]["properties"]["pages"]["items"]["properties"]["axes"]["items"]
    assert enum["enum"] == list(one_to_one.OUTSIDER_AXES)
    # Counts only in what goes to the report: no seat, no words.
    assert "C01" not in str(counts) and "町" not in str(counts)


def test_a_seat_written_in_the_models_table_is_not_asked_again(tmp_path):
    gate, client = a_gate([sorted_as(p1=["行く前"], p2=[], p3=[]), sorted_as(p1=[]), sorted_as(p1=["来たわけ"])])
    one_to_one.write_tables(tmp_path, UTTERANCES, KINDS, gate)
    before = (tmp_path / "ask_pages_model.tsv").read_bytes()
    gate, client = a_gate([])
    counts = one_to_one.write_tables(tmp_path, UTTERANCES, KINDS, gate)
    assert client.requests == [] and counts["model"]["page_seats_already"] == 3
    assert (tmp_path / "ask_pages_model.tsv").read_bytes() == before
    # Made anew: the table deleted and the ingest run again.
    (tmp_path / "ask_pages_model.tsv").unlink()
    gate, client = a_gate([sorted_as(p1=[], p2=[], p3=[]), sorted_as(p1=[]), sorted_as(p1=[])])
    one_to_one.write_tables(tmp_path, UTTERANCES, KINDS, gate)
    assert len(client.requests) == 3


def test_a_seat_whose_rows_the_teacher_filled_is_not_asked(tmp_path):
    (tmp_path / "ask_pages.tsv").write_text("席\tページ\t軸\nC01\tp1\t行く前\nC01\tp2\t-\nC01\tp3\t-\n"
                                            "C02\tp1\t\nO01\tp1\t\n", encoding="utf-8")
    gate, client = a_gate([sorted_as(p1=["帰ってきて"]), sorted_as(p1=["来たわけ"])])
    counts = one_to_one.write_tables(tmp_path, UTTERANCES, KINDS, gate)
    assert len(client.requests) == 2 and "毎日が驚き" not in client.all_sent()
    assert counts["model"]["page_seats_by_the_teacher"] == 1


def test_a_request_that_fails_or_comes_back_late_leaves_the_seat_to_ask_again(tmp_path):
    gate, client = a_gate([TimeoutError("late"), sorted_as(p1=[]), sorted_as(p1=[])])
    counts = one_to_one.write_tables(tmp_path, UTTERANCES, KINDS, gate)
    assert counts["model"]["page_seats_not_sorted"] == {"api_error:TimeoutError": 1}
    assert not any(line.startswith("C01") for line in table(tmp_path / "ask_pages_model.tsv"))
    gate, client = a_gate([sorted_as(p1=[], p2=[], p3=[])])
    one_to_one.write_tables(tmp_path, UTTERANCES, KINDS, gate)
    assert len(client.requests) == 1 and "C01\tp1\t-" in table(tmp_path / "ask_pages_model.tsv")


def test_a_name_in_the_pages_stops_the_request_before_it_is_sent(tmp_path):
    named = UTTERANCES[:1] + [_u("C01", "p2", "山川さんと向こうで会った。")]
    gate, client = a_gate([sorted_as(p1=["行く前"], p2=["向こうで"])])
    counts = one_to_one.write_tables(tmp_path, named, KINDS, gate)
    assert client.requests == [] and counts["model"]["page_seats_not_sorted"] == {"name_in_request": 1}


def test_no_gate_no_model_table(tmp_path):
    counts = one_to_one.write_tables(tmp_path, UTTERANCES, KINDS)
    assert counts["model"] is None and not (tmp_path / "ask_pages_model.tsv").exists()


# --- the tables read: the teacher's first ---

def write(path, text):
    path.write_text(text, encoding="utf-8")


def test_the_teachers_table_comes_first_and_its_empty_rows_are_the_models(tmp_path):
    write(tmp_path / "ask_pages.tsv", "席\tページ\t軸\nC01\tp1\t向こうで\nC01\tp2\t\n")
    write(tmp_path / "ask_pages_model.tsv", "席\tページ\t軸\nC01\tp1\t行く前\nC01\tp2\t向こうで\nC02\tp1\t帰ってきて\n")
    write(tmp_path / "ask_ranking.tsv", "席\t質問\nA01\t先生の質問ですか？\nA02\t\n")
    write(tmp_path / "ask_ranking_model.tsv", "席\t質問\nA01\tモデルの質問ですか？\nA02\tモデルの質問2ですか？\n")
    tables = one_to_one.load_tables(tmp_path)
    assert tables["pages"] == {"C01": {"p1": ["向こうで"], "p2": ["向こうで"]}, "C02": {"p1": ["帰ってきて"]}}
    assert tables["ranking"] == {"A01": "先生の質問ですか？", "A02": "モデルの質問2ですか？"}
    assert tables["unread"] == []


def test_a_dash_in_the_teachers_table_shows_nothing_even_with_the_models(tmp_path):
    write(tmp_path / "ask_pages.tsv", "席\tページ\t軸\nC01\tp1\t-\n")
    write(tmp_path / "ask_pages_model.tsv", "席\tページ\t軸\nC01\tp1\t行く前\nC01\tp2\t-\n")
    write(tmp_path / "ask_ranking.tsv", "席\t質問\nA01\t-\n")
    write(tmp_path / "ask_ranking_model.tsv", "席\t質問\nA01\tモデルの質問ですか？\nA02\t-\n")
    tables = one_to_one.load_tables(tmp_path)
    assert tables["pages"] == {} and tables["ranking"] == {}  # The model's 「-」 shows nothing either.


@pytest.mark.parametrize("name", ["ask_pages.tsv", "ask_pages_model.tsv", "ask_ranking.tsv", "ask_ranking_model.tsv"])
def test_a_table_not_read_says_its_name_and_line_only(tmp_path, name):
    columns = "席\tページ\t軸" if "pages" in name else "席\t質問"
    write(tmp_path / name, f"{columns}\nC01\tp1\t行く前\t余り\n" if "pages" in name else f"{columns}\nA01\tある\t余り\n")
    tables = one_to_one.load_tables(tmp_path)
    assert tables["unread"] == [f"{name} line 2"]
    (tmp_path / name).write_bytes(columns.encode("utf-8") + b"\n" + b"\xff\xfe\n")
    assert one_to_one.load_tables(tmp_path)["unread"] == [f"{name} line 2"]
    (tmp_path / name).write_text("ほかの見出し\n", encoding="utf-8")
    assert one_to_one.load_tables(tmp_path)["unread"] == [f"{name} line 1"]


def test_the_teachers_table_not_read_shows_the_models_neither(tmp_path):
    write(tmp_path / "ask_ranking.tsv", "ほかの見出し\n")
    write(tmp_path / "ask_ranking_model.tsv", "席\t質問\nA01\tモデルの質問ですか？\n")
    assert one_to_one.load_tables(tmp_path)["ranking"] == {}  # Its 「-」 could not be kept.


def test_a_table_not_read_is_said_at_ingest_and_at_the_servers_start(tmp_path):
    from pathlib import Path
    root = Path(one_to_one.__file__).parent
    run = (root / "ingest" / "run.py").read_text(encoding="utf-8")
    assert 'f"one to one, a table not read: {problem}" for problem in t["unread"]' in run
    app = (root / "app.py").read_text(encoding="utf-8")
    assert 'for problem in library.ask_tables.get("unread", []):' in app
    write(tmp_path / "ask_pages_model.tsv", "席\tページ\t軸\nC01\n")
    gate, client = a_gate([])
    counts = one_to_one.write_tables(tmp_path, UTTERANCES, KINDS, gate)
    assert counts["unread"] == ["ask_pages_model.tsv line 2"]
    assert counts["model"]["not_written"] == ["ask_pages_model.tsv line 2"] and client.requests == []
    assert table(tmp_path / "ask_pages_model.tsv") == ["席\tページ\t軸", "C01"]  # Never written over.
