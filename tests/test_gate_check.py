"""Trying the gate on data, without a model. Every name here is invented."""

import json

from conftest import make_seat, write_seats
from ebino import gate_check


def setup(tmp_path, texts, gate_ok=None):
    write_seats(tmp_path / "seats.tsv", [
        make_seat(seat_id="S01", display_name="山川さん"),
        make_seat(seat_id="P01", kind="poster", company="", display_name="先輩"),
    ])
    (tmp_path / "masks.tsv").write_text("席ID\t種類\t値\nS01\t語\t谷口師匠\n", encoding="utf-8")
    if gate_ok is not None:
        (tmp_path / "gate_ok.tsv").write_text(gate_ok, encoding="utf-8")
    folder = tmp_path / "ingested"
    folder.mkdir()
    rows = [{"id": f"x-{i}", "seat_id": "P01", "text": t, "heading": ""} for i, t in enumerate(texts)]
    (folder / "utterances.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")


def run_main(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("EBINO_DATA_DIR", str(tmp_path))
    return gate_check.main(), capsys.readouterr().out


def test_no_hits(tmp_path, monkeypatch, capsys):
    setup(tmp_path, ["はるかぜ理容で働く先輩に聞いた。"])
    code, out = run_main(tmp_path, monkeypatch, capsys)
    assert code == 0
    assert "pieces with a hit: 0" in out
    assert out.startswith("***")


def test_hits_are_shown_by_kind_with_word_and_seat(tmp_path, monkeypatch, capsys):
    setup(tmp_path, ["山川の河原で調べた。", "谷口師匠に習った。", "山川で泳いだ。"])
    code, out = run_main(tmp_path, monkeypatch, capsys)
    assert code == 1
    assert "pieces with a hit: 3" in out
    assert "hit words by kind: {'display_name': 1, 'mask_word': 1}" in out
    assert "[display_name] 山川  pieces: 2  seats: P01" in out
    assert "[mask_word] 谷口師匠  pieces: 1  seats: P01" in out


def test_words_in_gate_ok_are_not_hits(tmp_path, monkeypatch, capsys):
    setup(tmp_path, ["山川の河原で調べた。"], gate_ok="山川\n")
    code, out = run_main(tmp_path, monkeypatch, capsys)
    assert code == 0


def test_main_needs_the_data_folder(monkeypatch):
    monkeypatch.delenv("EBINO_DATA_DIR", raising=False)
    assert gate_check.main() == 2
