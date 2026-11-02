import json
from datetime import date

import pytest

from ebino.saved_output import SavedOutput, load_output, save_output

MODEL = "claude-example-model"  # A made-up name: the real one is whatever made the output.


def test_saved_output_round_trips_with_model_and_date(tmp_path):
    path = tmp_path / "host.json"
    save_output(path, MODEL, {"split": ["この方の言葉"]}, created=date(2026, 11, 5))
    saved = load_output(path)
    assert saved == SavedOutput(MODEL, date(2026, 11, 5), {"split": ["この方の言葉"]})


def test_caption_shows_model_and_date():
    saved = SavedOutput(MODEL, date(2026, 11, 5), {})
    assert saved.caption() == f"{MODEL}・2026-11-05 に作った出力"


def test_date_defaults_to_today(tmp_path):
    saved = save_output(tmp_path / "a.json", MODEL, [])
    assert saved.created == date.today()


def test_saving_without_a_model_name_is_refused(tmp_path):
    with pytest.raises(ValueError, match="model name"):
        save_output(tmp_path / "a.json", " ", [])


@pytest.mark.parametrize(
    "data, reason",
    [
        ({"created": "2026-11-05", "output": []}, "model name"),
        ({"model": "", "created": "2026-11-05", "output": []}, "model name"),
        ({"model": MODEL, "output": []}, "valid date"),
        ({"model": MODEL, "created": "11/5", "output": []}, "valid date"),
        ({"model": MODEL, "created": "2026-11-05"}, "no output"),
    ],
)
def test_output_without_model_or_date_is_not_replayed(tmp_path, data, reason):
    path = tmp_path / "a.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=reason):
        load_output(path)
