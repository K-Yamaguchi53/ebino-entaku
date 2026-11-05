"""Where things live, read from the environment, and the safety checks on them.

The records folder must be outside this repository and outside any synced
folder (SPEC 2-1, 14-22). When it is not set, or sits in the wrong place, the
app does not start recording: there is no default path to fall back to.
Errors carry reason codes only, never a path, since a path can hold a name.
"""

import os
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
DATA_ENV = "EBINO_DATA_DIR"
RECORDS_ENV = "EBINO_RECORDS_DIR"
ENV_FILE = REPO_DIR / ".env"

# Environment variables that point at synced folders (SPEC 14-22).
SYNC_ENVS = ("OneDrive", "OneDriveCommercial", "OneDriveConsumer")
# Path parts that mean a synced folder even without those variables.
SYNC_WORDS = ("onedrive", "dropbox", "google drive", "icloud")


class PlaceError(Exception):
    """Carries a reason code only."""


def _inside(path: Path, folder: Path) -> bool:
    return path == folder or folder in path.parents


def _resolve(raw: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


def check_records_dir(raw: str | None, environ=os.environ) -> Path:
    """The records folder, or PlaceError if recording must not start."""
    if not raw or not raw.strip():
        raise PlaceError("records_dir_not_set")
    path = _resolve(raw.strip())
    if _inside(path, REPO_DIR) or _inside(REPO_DIR, path):
        raise PlaceError("records_dir_in_repo")
    for name in SYNC_ENVS:
        synced = environ.get(name, "").strip()
        if synced and _inside(path, _resolve(synced)):
            raise PlaceError("records_dir_in_synced_folder")
    lowered = str(path).lower()
    if any(word in lowered for word in SYNC_WORDS):
        raise PlaceError("records_dir_in_synced_folder")
    return path


def records_dir(environ=os.environ) -> Path:
    return check_records_dir(environ.get(RECORDS_ENV), environ)


def data_dir(environ=os.environ) -> Path:
    raw = environ.get(DATA_ENV, "").strip()
    if not raw:
        raise PlaceError("data_dir_not_set")
    return _resolve(raw)


COACH_ENV = "EBINO_COACH"
SPEAKER_ENV = "EBINO_SPEAKER"
ASKER_ENV = "EBINO_ASKER"


def coach_on(environ=os.environ) -> bool:
    """コーチとオブザーバー's band is shown unless EBINO_COACH=0 (SPEC 5-1)."""
    return environ.get(COACH_ENV, "").strip() != "0"


def speaker_on(environ=os.environ) -> bool:
    """The bubbles as spoken words (直し31-7) unless EBINO_SPEAKER=0: then
    every bubble shows its original words, and no request is made for them."""
    return environ.get(SPEAKER_ENV, "").strip() != "0"


def asker_on(environ=os.environ) -> bool:
    """One to one's questions put to each person (直し36-3) unless
    EBINO_ASKER=0: then the teacher's questions, and no request is made."""
    return environ.get(ASKER_ENV, "").strip() != "0"


def load_env_file(path: Path = ENV_FILE, environ=os.environ) -> None:
    """Read KEY=value lines from .env. A variable already set wins.

    The key itself is never printed or logged."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if key and value and not environ.get(key):
            environ[key] = value
