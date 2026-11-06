"""見本モード (tools/preview_sample.py, the teacher, 11/6: no live link; the
judges may open the same screens on their own PC): the fictional seat table
in the repo, a few fictional lines, no key, no model, no records."""

import importlib.util
import json
import threading
from pathlib import Path

from ebino.app import App, make_server
from ebino.gate import Gate, NameList

from test_app import request

TOOL = Path(__file__).resolve().parent.parent / "tools" / "preview_sample.py"


def tool():
    spec = importlib.util.spec_from_file_location("preview_sample", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def app_of(sample):
    lib = sample.library()
    return lib, App(lib, Gate(sample.NoModel(), NameList.build(lib.all_seats, {})), None)


def test_it_opens_the_fictional_seats_on_the_map_by_their_titles_alone():
    sample = tool()
    lib, app = app_of(sample)
    setup = app.setup()
    assert setup["map"] is not None and len(setup["seats"]) == 7
    # 肩書きだけ: no company and no person's name on the screen.
    shown = json.dumps(setup["seats"], ensure_ascii=False)
    assert "有限会社" not in shown and "さん" not in shown
    assert setup["ai_roles"]
    assert {piece.seat_id for piece in sample.PIECES} <= {seat.seat_id for seat in lib.all_seats}


def test_a_question_without_a_model_gives_the_apps_own_line_and_the_server_goes_on():
    server = make_server(app_of(tool())[1], 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        assert request(server, "POST", "/api/start", {"lab": "quest"})[0] == 200
        status, view = request(server, "POST", "/api/ask", {"question": "休みは？"})
        assert status == 200 and view["status"] == "unavailable" and view["answered_seats"] == 0
        assert view["message"]  # The same line as when the model is down.
        assert request(server, "GET", "/api/setup")[0] == 200
    finally:
        server.shutdown()
        server.server_close()


def test_it_reads_no_key_and_no_real_data():
    source = TOOL.read_text(encoding="utf-8")
    for word in ("ANTHROPIC_API_KEY", "load_env_file", "EBINO_DATA_DIR", "data_dir(", "Records(", "import anthropic"):
        assert word not in source
