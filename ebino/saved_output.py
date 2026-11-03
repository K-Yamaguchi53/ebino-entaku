"""Model outputs saved ahead of time for the sample mode to replay (SPEC 12).

Every saved output carries the model name and the date it was made, and the
sample-mode screen shows both in small print (SPEC 14-47), so nobody mistakes a
replay for a live answer. A file without them is refused rather than replayed.
"""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SavedOutput:
    model: str
    created: date
    output: Any

    def caption(self) -> str:
        """The small line on the sample-mode screen."""
        return f"{self.model}・{self.created.isoformat()} に作った出力"


def save_output(path: Path, model: str, output: Any, created: date | None = None,
                extra: dict | None = None) -> SavedOutput:
    """extra: more top-level keys written after output (never model,
    created or output), such as what each output was made from."""
    if not model.strip():
        raise ValueError("saved output needs a model name")
    saved = SavedOutput(model.strip(), created or date.today(), output)
    data = {"model": saved.model, "created": saved.created.isoformat(), "output": output}
    data |= {key: value for key, value in (extra or {}).items() if key not in data}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return saved


def load_output(path: Path) -> SavedOutput:
    data = json.loads(path.read_text(encoding="utf-8"))
    model = data.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("saved output has no model name")
    try:
        created = date.fromisoformat(data.get("created") or "")
    except (TypeError, ValueError):
        raise ValueError("saved output has no valid date") from None
    if "output" not in data:
        raise ValueError("saved output has no output")
    return SavedOutput(model, created, data["output"])
