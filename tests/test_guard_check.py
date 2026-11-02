"""The batch guard check the teacher runs. Every text here is invented."""

import json

from ebino import guard_check
from ebino.ingest.utterance import VOICE_ANSWER, VOICE_ARTICLE, VOICE_OWN, VOICE_SPOKEN

PARAGRAPH = "先輩に「好きにやれ」と言われた。それから店を継いだ。"


def row(id_, text, voice=VOICE_OWN, paragraph=None):
    return {
        "id": id_, "seat_id": "S01", "kind": "adult", "section": "本文", "voice": voice,
        "text": text, "paragraph": paragraph if paragraph is not None else text,
        "heading": "", "source_note": "",
    }


def write_rows(tmp_path, rows):
    folder = tmp_path / "ingested"
    folder.mkdir()
    (folder / "utterances.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")


GOOD = [
    row("adult-1", "先輩に", VOICE_ARTICLE, PARAGRAPH),
    row("adult-2", "好きにやれ", VOICE_SPOKEN, PARAGRAPH),
    row("adult-3", "と言われた。それから店を継いだ。", VOICE_ARTICLE, PARAGRAPH),
    row("poster-1", "ＡＩで地域の店を\n調べた。"),
    row("ans-1", "人と話すのが好きで選びました。", VOICE_ANSWER),
]


def run_main(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("EBINO_DATA_DIR", str(tmp_path))
    code = guard_check.main()
    return code, capsys.readouterr()


def test_clean_pieces_all_pass(tmp_path, monkeypatch, capsys):
    write_rows(tmp_path, GOOD)
    code, out = run_main(tmp_path, monkeypatch, capsys)
    assert code == 0
    assert "pieces checked: 5" in out.out
    assert "piece inside its paragraph, passed / stopped: 5 / 0" in out.out
    assert "guard passed / stopped: 4 / 0" in out.out
    assert "answers returned during the event, passed / stopped (counted apart): 1 / 0" in out.out
    assert "shown text differs from the piece: 0" in out.out


def test_a_piece_not_in_its_paragraph_is_counted_by_id(tmp_path, monkeypatch, capsys):
    rows = [*GOOD, row("adult-9", "好きにやろう", VOICE_SPOKEN, PARAGRAPH)]
    write_rows(tmp_path, rows)
    code, out = run_main(tmp_path, monkeypatch, capsys)
    assert code == 1
    assert "piece inside its paragraph, passed / stopped: 5 / 1" in out.out
    assert "piece inside its paragraph, stopped utterance ids: ['adult-9']" in out.out


def test_one_id_for_two_texts_is_caught(tmp_path, monkeypatch, capsys):
    rows = [*GOOD, row("poster-1", "別の文。")]
    write_rows(tmp_path, rows)
    code, out = run_main(tmp_path, monkeypatch, capsys)
    assert code == 1
    assert "guard passed / stopped: 4 / 1" in out.out
    assert "guard stopped utterance ids: ['poster-1']" in out.out


def test_output_has_counts_and_ids_but_no_text(tmp_path, monkeypatch, capsys):
    rows = [*GOOD, row("adult-9", "好きにやろう", VOICE_SPOKEN, PARAGRAPH)]
    write_rows(tmp_path, rows)
    _, out = run_main(tmp_path, monkeypatch, capsys)
    printed = out.out + out.err
    for r in rows:
        assert r["text"] not in printed
    assert "先輩" not in printed and "店" not in printed


def test_main_needs_the_data_folder(monkeypatch):
    monkeypatch.delenv("EBINO_DATA_DIR", raising=False)
    assert guard_check.main() == 2


def test_main_asks_for_the_ingest_first(tmp_path, monkeypatch, capsys):
    code, out = run_main(tmp_path, monkeypatch, capsys)
    assert code == 2
    assert "python -m ebino.ingest.run" in out.err


def test_a_broken_row_is_named_by_error_type_only(tmp_path, monkeypatch, capsys):
    write_rows(tmp_path, [{"id": "x", "text": "壊れた行の本文"}])
    code, out = run_main(tmp_path, monkeypatch, capsys)
    assert code == 2
    assert "壊れた行" not in out.out + out.err
