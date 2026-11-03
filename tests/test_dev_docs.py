"""The development docs: the settings copy and docs/development.md (SPEC 10, 13).

The copy must say what the real settings deny, and neither docs file may hold
where things really are on the author's machine.
"""

import getpass
import json
import re
from pathlib import Path

import pytest

from ebino.gate import EFFORT, MODELS

DOCS = Path(__file__).resolve().parent.parent / "docs"
SETTINGS = DOCS / "claude-code-settings.example.json"
DEVELOPMENT = DOCS / "development.md"
DOC_FILES = (SETTINGS, DEVELOPMENT)

DATA = "<EBINO_DATA_DIR>"
RECORDS = "<EBINO_RECORDS_DIR>"
SYNC = "<学校の同期フォルダ>"
FOLDERS = (DATA, RECORDS, SYNC)
DRIVE_PATH = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")


def _settings() -> dict:
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def _deny() -> list[str]:
    return _settings()["permissions"]["deny"]


def test_the_settings_copy_reads_as_json():
    settings = _settings()
    assert settings["model"] == "opus"
    assert settings["effortLevel"] == "high"
    assert isinstance(_deny(), list)


@pytest.mark.parametrize("folder", FOLDERS)
def test_reading_each_folder_is_denied(folder):
    assert f"Read(//{folder}/**)" in _deny()


def test_reading_env_is_denied():
    deny = _deny()
    assert "Read(./.env)" in deny
    assert "Read(./.env.*)" in deny


def test_editing_the_sync_folder_is_denied():
    assert f"Edit(//{SYNC}/**)" in _deny()


@pytest.mark.parametrize("folder", [DATA, RECORDS])
def test_editing_the_data_and_records_folders_is_denied(folder):
    assert f"Edit(//{folder}/**)" in _deny()


@pytest.mark.parametrize("shell", ["Bash", "PowerShell"])
@pytest.mark.parametrize("folder", FOLDERS)
def test_commands_naming_each_folder_are_denied(shell, folder):
    assert f"{shell}(*{folder}*)" in _deny()


@pytest.mark.parametrize("shell", ["Bash", "PowerShell"])
def test_commands_naming_env_are_denied(shell):
    assert f"{shell}(*.env*)" in _deny()


def _user_names() -> set[str]:
    names = {getpass.getuser(), Path.home().name}
    return {name for name in names if len(name) >= 2}


@pytest.mark.parametrize("path", DOC_FILES, ids=lambda p: p.name)
def test_no_real_place_in_the_docs(path):
    text = path.read_text(encoding="utf-8")
    assert "onedrive" not in text.lower()
    assert not DRIVE_PATH.search(text)
    for name in _user_names():
        assert name.lower() not in text.lower()


def test_the_drive_path_check_catches_a_real_path():
    assert DRIVE_PATH.search("X:\\folder")
    assert DRIVE_PATH.search("d:/folder")
    assert not DRIVE_PATH.search("Read(./.env)")


@pytest.mark.parametrize("role", sorted(MODELS))
def test_development_lists_every_role_with_its_model(role):
    rows = [line for line in DEVELOPMENT.read_text(encoding="utf-8").splitlines() if f"（`{role}`）" in line]
    assert len(rows) == 1
    cells = [cell.strip() for cell in rows[0].strip("|").split("|")]
    assert cells[1] == MODELS[role]
    assert cells[2] == EFFORT[role]
