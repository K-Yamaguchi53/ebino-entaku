"""直し36: one to one's questions with a fast model (asker, Haiku, low),
where the teacher allowed it, with a fake model. Everything here is
invented.

段1: at ingest, which axes each page of a seat with pages only answers.
Only the axes' names come back; the answer goes to the model's own table
(ask_pages_model.tsv) beside the teacher's, which is read first.
段2: at ingest, a seat's own question on its ranking, made by the model and
checked by code: only the ranking paragraph's words and numbers, no banned
word, no name, 40 characters at most, ending in 「？」.
段3: at one to one, the teacher's questions put to that person in one
request (3 seconds), checked by code as the ranking's, except that its
words may come from the teacher's question too, a banned word stops it only
when the teacher's question lacks it, and it is at most 1.5 times as long.
Any that fails, and all when the model is late or cannot be used, show the
teacher's question."""

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


# --- 段2: a seat's own question on its ranking ---

RANKING = "（架空）好きな景色ベスト3　1位 朝の霧　2位 秋の紅葉　3位 冬の星空"
RANKED = [Utterance(id="A01-r", seat_id="A01", kind="adult", section="ランキング", voice="article",
                    text=RANKING, paragraph=RANKING),
          Utterance(id="A02-r", seat_id="A02", kind="adult", section="ランキング", voice="article",
                    text="おすすめのパン　1位 あんぱん", paragraph="おすすめのパン　1位 あんぱん")]


def asks(question):
    return text_response({"question": question})


def ranking_check(question, paragraph=RANKING):
    gate, _ = a_gate([])
    return asker.check_ranking(question, paragraph, gate)


def test_a_ranking_question_made_from_the_paragraph_passes():
    assert ranking_check("好きな景色の1位が朝の霧なのは、どうしてですか？") == ""


def test_a_ranking_question_with_a_kanji_or_katakana_word_not_in_the_ranking_paragraph_is_not_used():
    assert ranking_check("好きな風景の1位が朝の霧なのは、どうしてですか？") == "word_not_in_original"
    assert ranking_check("朝の霧のポイントは、どこですか？") == "word_not_in_original"


def test_a_ranking_question_with_a_number_not_in_the_ranking_paragraph_is_not_used():
    assert ranking_check("好きな景色の4位は、何ですか？") == "number_not_in_original"


def test_a_ranking_question_with_a_banned_word_is_not_used_even_when_the_paragraph_has_it():
    assert ranking_check("おすすめのパンの1位は、どうしてあんぱんですか？", "おすすめのパン　1位 あんぱん") == "banned_word"


def test_a_ranking_question_with_a_name_is_not_used():
    assert ranking_check("山川さんの好きな景色の1位は、朝の霧ですか？", "山川さんの" + RANKING) == "name"


def test_a_ranking_question_over_40_characters_or_not_ending_in_a_question_mark_is_not_used():
    long = "好きな景色の1位が朝の霧で、2位が秋の紅葉で、3位が冬の星空なのは、どうしてなんですか？"
    assert len(long) > 40 and ranking_check(long) == "too_long"
    assert ranking_check("好きな景色の1位が朝の霧なのは、どうしてですか") == "no_question_mark"
    assert ranking_check("好きな景色の1位は？\n朝の霧ですか？") == "not_one_line"


def test_one_request_a_ranking_and_a_seat_that_failed_is_written_with_a_dash_and_not_asked_again(tmp_path):
    gate, client = a_gate([asks("好きな景色の1位が朝の霧なのは、どうしてですか？"),
                           asks("おすすめの1位は、あんぱんですか？")])
    counts = one_to_one.write_tables(tmp_path, RANKED, {"A01": "adult", "A02": "adult"}, gate)
    assert len(client.requests) == 2 and client.options == [{"timeout": 30.0, "max_retries": 0}] * 2
    assert table(tmp_path / "ask_ranking_model.tsv") == [
        "席\t質問", "A01\t好きな景色の1位が朝の霧なのは、どうしてですか？", "A02\t-"]
    assert counts["model"]["ranking_made"] == 1 and counts["model"]["ranking_not_made"] == {"banned_word": 1}
    assert one_to_one.load_tables(tmp_path)["ranking"] == {"A01": "好きな景色の1位が朝の霧なのは、どうしてですか？"}
    assert "朝の霧" not in str(counts)  # Counts only.
    gate, client = a_gate([])
    counts = one_to_one.write_tables(tmp_path, RANKED, {"A01": "adult", "A02": "adult"}, gate)
    assert client.requests == [] and counts["model"]["ranking_already"] == 2


def test_a_ranking_the_teacher_wrote_is_not_asked_and_a_late_answer_is_asked_again(tmp_path):
    write(tmp_path / "ask_ranking.tsv", "席\t質問\nA01\t先生の質問ですか？\nA02\t\n")
    gate, client = a_gate([TimeoutError("late")])
    counts = one_to_one.write_tables(tmp_path, RANKED, {"A01": "adult", "A02": "adult"}, gate)
    assert len(client.requests) == 1 and RANKING not in client.all_sent()
    assert counts["model"]["ranking_by_the_teacher"] == 1
    assert counts["model"]["ranking_not_asked"] == {"api_error:TimeoutError": 1}
    assert not (tmp_path / "ask_ranking_model.tsv").exists()


def test_the_ingest_report_says_the_ranking_counts():
    from pathlib import Path
    run = (Path(one_to_one.__file__).parent / "ingest" / "run.py").read_text(encoding="utf-8")
    assert "one to one, the model's ranking questions: made now {model['ranking_made']}" in run
    assert "not made by reason {model['ranking_not_made']}" in run


# --- 段3: the teacher's questions put to the person at one to one ---

import json  # noqa: E402
import random  # noqa: E402

import anthropic  # noqa: E402
import httpx2  # noqa: E402

from ebino.session import Library, Session  # noqa: E402

SKELETON = "毎日、どんな仕事をしているんですか？"
PARAGRAPH = "朝は5時からパンを焼きます。"


def rephrase_check(question, skeleton=SKELETON, paragraph=PARAGRAPH):
    gate, _ = a_gate([])
    return asker.check_rephrase(question, skeleton, paragraph, gate)


def test_a_question_put_to_the_person_from_the_teachers_words_and_the_paragraph_passes():
    assert rephrase_check("朝からパンを焼く毎日は、どんな仕事ですか？") == ""


def test_a_rephrased_question_may_keep_the_teachers_words_the_paragraph_lacks():
    assert "仕事" not in PARAGRAPH and rephrase_check("パンを焼く仕事は、どんな毎日ですか？") == ""


def test_a_rephrased_question_with_a_word_in_neither_the_teachers_question_nor_the_items_paragraph_is_not_shown():
    assert rephrase_check("朝からパンを焼く毎日は、どんな職人ですか？") == "word_not_in_original"
    assert rephrase_check("朝からパンを焼くレシピは、どんな仕事ですか？") == "word_not_in_original"


def test_a_rephrased_question_with_a_number_not_in_the_paragraph_is_not_shown():
    assert rephrase_check("朝6時からパンを焼く毎日は、どんな仕事ですか？") == "number_not_in_original"


def test_a_rephrased_question_longer_than_one_and_a_half_times_the_teachers_is_not_shown():
    long = "朝は5時からパンを焼く毎日は、どんな仕事をしているんですか？"
    assert len(long) > len(SKELETON) * 1.5 and rephrase_check(long) == "too_long"


def test_a_rephrased_question_with_a_name_is_not_shown():
    assert rephrase_check("山川さんの毎日は、どんな仕事ですか？", paragraph="山川さんは" + PARAGRAPH) == "name"


def test_a_banned_word_the_teachers_question_holds_does_not_stop_the_rephrased_one():
    skeleton = "どうして行こうと思ったの？"  # 行こう is a banned word (34).
    assert rephrase_check("どうして県外に行こうと思ったの？", skeleton, "県外の大学に進みました。") == ""


def test_a_banned_word_not_in_the_teachers_question_stops_the_rephrased_one():
    assert rephrase_check("パンを焼く毎日は、すごい仕事ですか？") == "banned_word"


def test_the_teachers_question_given_back_shows_the_teachers():
    assert rephrase_check(SKELETON) == "unchanged"


from test_one_to_one import SEATS as ONE_SEATS, UTTERANCES as ONE_UTTERANCES, Kept  # noqa: E402

PUT = {"プロフィール": "町で生まれて、店を継いだのはどうしてですか？", "仕事の内容": "髪を切って話を聞く毎日は、どんな仕事ですか？",
       "本文": "休みを決めて取る話を、もっと聞かせてくれますか？", "高校生に一言": "迷ったら、高校生に伝えたいことはありますか？"}


def put_to_the_person(request):
    sent = json.loads(request["messages"][0]["content"])
    return text_response({"lines": [{"id": q["id"], "question": PUT.get(q["id"], q["question"])}
                                    for q in sent["questions"]]})


def one_sitting(monkeypatch, answers):
    monkeypatch.setenv("EBINO_SPEAKER", "0")
    lib = Library.build(ONE_SEATS, ONE_UTTERANCES, {})
    lib.ask_tables = {"pages": {"C01": {"p1": ["行く前"], "p2": ["向こうで"]}},
                      "ranking": {"A01": "架空のランキングの質問ですか？"}}
    client, kept = FakeClient(answers), Kept()
    session = Session(lib, Gate(client, NameList.build(ONE_SEATS, {})), rng=random.Random(1), records=kept)
    return session, client, kept


def test_this_person_pressed_one_request_in_three_seconds_and_the_questions_put_to_the_person(monkeypatch):
    session, client, kept = one_sitting(monkeypatch, put_to_the_person)
    view = session.one_open("A01")
    assert len(client.requests) == 1 and client.options == [{"timeout": 3.0, "max_retries": 0}]
    assert client.requests[0]["model"] == "claude-haiku-5-5"
    sent = json.loads(client.requests[0]["messages"][0]["content"])
    # The questions offered now, each with its own paragraph.
    assert [q["id"] for q in sent["questions"]] == ["プロフィール", "仕事の内容", "本文"]
    assert sent["questions"][0]["paragraph"] == "町で生まれて、店を継ぎました。"
    assert [(q["question"], q["rephrased"]) for q in view["questions"]] == [
        (PUT["プロフィール"], True), (PUT["仕事の内容"], True), (PUT["本文"], True)]
    # After one asked: the ranking's own question comes after 本文, as the table has it, not put again.
    after = session.one_ask("A01", "プロフィール")
    assert [(q["question"], q["rephrased"]) for q in after["questions"]] == [
        (PUT["仕事の内容"], True), (PUT["本文"], True), ("架空のランキングの質問ですか？", False)]
    # One offered later is the teacher's, with no request, until pressed again.
    after = session.one_ask("A01", "仕事の内容")
    assert after["questions"][-1] == {"item": "高校生に一言", "question": "高校生に伝えたいことはありますか？",
                                      "rephrased": False}
    assert len(client.requests) == 1
    view = session.one_open("A01")
    assert len(client.requests) == 2 and view["questions"][-1]["question"] == PUT["高校生に一言"]
    assert [q["id"] for q in json.loads(client.requests[1]["messages"][0]["content"])["questions"]] == ["高校生に一言"]
    session.one_open("A01")
    assert len(client.requests) == 2  # Nothing left to put.
    # The record: which was shown and why, never the words.
    record = kept.sessions[-1]["one_rephrased"]
    assert {r["item"]: r["shown"] for r in record} == {item: "rephrased" for item in PUT}
    assert all(set(r) == {"seat_id", "item", "shown", "reason"} for r in record)
    assert "髪を切って" not in json.dumps(kept.sessions[-1]["one_rephrased"], ensure_ascii=False)


def test_one_that_fails_its_check_shows_the_teachers_and_the_others_do_not(monkeypatch):
    def answers(request):
        sent = json.loads(request["messages"][0]["content"])
        return text_response({"lines": [{"id": q["id"], "question": "すごい" + q["question"]} if q["id"] == "本文"
                                         else {"id": q["id"], "question": PUT[q["id"]]} for q in sent["questions"]]})
    session, client, kept = one_sitting(monkeypatch, answers)
    view = session.one_open("A01")
    shown = {q["item"]: (q["question"], q["rephrased"]) for q in view["questions"]}
    assert shown["本文"] == ("この仕事の話を、もっと聞かせてください。", False)
    assert shown["プロフィール"] == (PUT["プロフィール"], True)
    assert session.one_rephrased["A01"]["本文"].reason == "banned_word"


def test_past_three_seconds_every_question_is_the_teachers(monkeypatch):
    late = anthropic.APITimeoutError(request=httpx2.Request("POST", "https://api.invalid/v1/messages"))
    session, client, kept = one_sitting(monkeypatch, [late])
    view = session.one_open("A01")
    assert [q["rephrased"] for q in view["questions"]] == [False, False, False]
    assert view["questions"][0]["question"] == "どんな道を通って、今の仕事に就いたんですか？"
    assert {r["reason"] for r in kept.sessions[-1]["one_rephrased"]} == {"api_error:APITimeoutError"}


def test_the_model_not_usable_or_turned_off_every_question_is_the_teachers(monkeypatch):
    session, client, kept = one_sitting(monkeypatch, [text_response("not json")])
    assert not any(q["rephrased"] for q in session.one_open("A01")["questions"])
    monkeypatch.setenv("EBINO_ASKER", "0")
    session, client, kept = one_sitting(monkeypatch, [])
    assert not any(q["rephrased"] for q in session.one_open("A01")["questions"])
    assert client.requests == []


def test_no_name_is_sent_when_putting_the_questions(monkeypatch):
    session, client, kept = one_sitting(monkeypatch, put_to_the_person)
    session.one_open("P01")
    sent = client.all_sent()
    assert all(not seat.display_name or seat.display_name not in sent for seat in ONE_SEATS)


def test_it_is_asked_for_while_the_camera_flies_and_a_put_question_is_marked():
    from ebino import app as app_module
    source = (app_module.STATIC_DIR / "map.js").read_text(encoding="utf-8")
    opened = source[source.index("async function openOne("):]
    opened = opened[:opened.index("\n  }\n")]
    assert opened.index("mine.asks = app.oneOpen(seatId)") < opened.index("await moveTo(")
    assert 'if (rephrased) ask.dataset.rephrased = "1";' in source
