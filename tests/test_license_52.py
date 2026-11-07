"""直し52 段0: the code is under the MIT License (LICENSE at the top of the repo)."""
import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_licence_is_mit_under_the_account_name():
    lines = (REPO / "LICENSE").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "MIT License"
    # Only the GitHub account name of the commits, never a person's own name.
    assert re.fullmatch(r"Copyright \(c\) (?:[0-9]{4} )?K-Yamaguchi53", lines[2])
    # The standard words, unchanged: the same as the MIT text bundled with rough.js.
    rough = (REPO / "ebino" / "static" / "rough.LICENSE.txt").read_text(encoding="utf-8").splitlines()
    assert lines[3:] == rough[rough.index("MIT License") + 3:]
    assert tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]["license"] == "MIT"
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "## ライセンス" in readme and "MIT License（`LICENSE`）" in readme
    # 11/7: no adult's answer came back during the period; the README does not say one did.
    assert "期間中に返った答え" not in readme
