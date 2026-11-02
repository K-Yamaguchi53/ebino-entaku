"""Where records may live (SPEC 2-1, 14-22). Paths here are temporary folders."""

import pytest

from ebino.config import REPO_DIR, PlaceError, check_records_dir, data_dir, load_env_file


def test_a_folder_outside_the_repo_and_sync_is_accepted(tmp_path):
    assert check_records_dir(str(tmp_path / "records"), environ={}) == (tmp_path / "records").resolve()


@pytest.mark.parametrize("raw", [None, "", "  "])
def test_no_folder_means_no_recording(raw):
    with pytest.raises(PlaceError, match="records_dir_not_set"):
        check_records_dir(raw, environ={})


@pytest.mark.parametrize("inside", ["", "records", "tests/records"])
def test_a_folder_in_the_repo_is_refused(inside):
    with pytest.raises(PlaceError, match="records_dir_in_repo"):
        check_records_dir(str(REPO_DIR / inside), environ={})


def test_a_folder_holding_the_repo_is_refused():
    with pytest.raises(PlaceError, match="records_dir_in_repo"):
        check_records_dir(str(REPO_DIR.parent), environ={})


@pytest.mark.parametrize("name", ["OneDrive", "OneDriveCommercial", "OneDriveConsumer"])
def test_a_folder_under_a_sync_variable_is_refused(tmp_path, name):
    synced = tmp_path / "学校の同期"
    with pytest.raises(PlaceError, match="records_dir_in_synced_folder"):
        check_records_dir(str(synced / "records"), environ={name: str(synced)})


@pytest.mark.parametrize("word", ["OneDrive - 学校", "Dropbox", "Google Drive", "iCloudDrive"])
def test_a_folder_named_like_a_sync_service_is_refused(tmp_path, word):
    with pytest.raises(PlaceError, match="records_dir_in_synced_folder"):
        check_records_dir(str(tmp_path / word / "records"), environ={})


def test_errors_never_carry_the_path(tmp_path):
    with pytest.raises(PlaceError) as error:
        check_records_dir(str(tmp_path / "Dropbox" / "山川"), environ={})
    assert "山川" not in str(error.value)


def test_data_dir_must_be_set():
    with pytest.raises(PlaceError, match="data_dir_not_set"):
        data_dir(environ={})


def test_env_file_fills_only_unset_variables(tmp_path):
    env = tmp_path / "example.env"
    env.write_text('# note\nA_KEY="from-file"\nB_KEY=from-file\nEMPTY=\n', encoding="utf-8")
    environ = {"B_KEY": "already"}
    load_env_file(env, environ)
    assert environ == {"A_KEY": "from-file", "B_KEY": "already"}


def test_a_missing_env_file_is_fine(tmp_path):
    environ = {}
    load_env_file(tmp_path / "none.env", environ)
    assert environ == {}
