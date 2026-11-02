"""The local web server for the screen (SPEC 5-1, 14-51). Invented data,
a fake model client, and a real server on 127.0.0.1 with a free port."""

import http.client
import json
import random
import socket
import threading

import pytest
from fake_client import FakeClient

from ebino import app as app_module
from ebino.app import App, make_server
from ebino.gate import Gate, NameList
from test_session import ANSWERED, SEATS, library


@pytest.fixture
def server():
    client = FakeClient(list(ANSWERED))
    the_app = App(library(), Gate(client, NameList.build(SEATS, {})), rng=random.Random(1))
    server = make_server(the_app, 0, timeout=1)
    server.the_app = the_app
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, client
    server.shutdown()
    server.server_close()


def request(server, method, path, body=None, headers=None, timeout=5):
    port = server.server_address[1]
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    sent = {"Host": f"127.0.0.1:{port}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        sent["Content-Type"] = "application/json"
    sent.update(headers or {})
    connection.request(method, path, body=data, headers=sent)
    response = connection.getresponse()
    raw = response.read()
    connection.close()
    kind = response.getheader("Content-Type", "")
    return response.status, json.loads(raw) if kind.startswith("application/json") else raw


def test_it_listens_on_127_0_0_1_only(server):
    srv, _ = server
    assert srv.server_address[0] == "127.0.0.1"


def test_the_page_and_its_two_files_are_served_and_nothing_else(server):
    srv, _ = server
    for path in ("/", "/app.js", "/style.css"):
        status, _ = request(srv, "GET", path)
        assert status == 200
    for path in ("/../ebino/app.py", "/static/app.js", "/.env", "/api/nothing"):
        assert request(srv, "GET", path)[0] == 404


def test_setup_gives_texts_kinds_and_seat_labels(server):
    srv, _ = server
    status, data = request(srv, "GET", "/api/setup")
    assert status == 200
    assert len(data["texts"]["start_notice"]) == 7
    assert data["texts"]["work_questions"] and "{n}" in data["texts"]["answered_count"]
    assert data["seats"][0] == {"seat_id": "S01", "kind": "adult", "title": "理容師", "detail": ""}


def test_a_whole_round_over_http(server):
    srv, client = server
    assert request(srv, "POST", "/api/ask", {"question": "休みは？"}) == (409, {"error": "no_session"})
    status, started = request(srv, "POST", "/api/start", {"lab": "quest"})
    assert status == 200 and started["purposes"][0]["seat_id"] == "P01"
    status, view = request(srv, "POST", "/api/ask", {"question": "休みは？"})
    assert status == 200 and view["status"] == "answered" and len(client.requests) == 2
    assert request(srv, "POST", "/api/mark", {"round": 1, "utterance_id": "a1"})[1] == {"marks": {"S01": "a1"}}
    assert request(srv, "POST", "/api/split", {"round": 1, "index": 0})[1]["heading"].startswith("ここで割れた")
    assert request(srv, "POST", "/api/paragraph", {"utterance_id": "c1"}) == (400, {"error": "not_shown"})


def test_the_reflection_sheet_over_http(server):
    srv, client = server
    from test_reflection import reflection_says
    client._answers.append(reflection_says())
    request(srv, "POST", "/api/start", {"lab": "creation"})
    # The moves quote 「休みの日」, so the question must hold those words.
    request(srv, "POST", "/api/ask", {"question": "休みの日って、みんな何してる？"})
    status, data = request(srv, "GET", "/api/setup")
    assert data["changed_choices"] == {"changed": "変わった", "a_little": "少し", "same": "変わらない"}
    status, begun = request(srv, "POST", "/api/reflect/begin", {"changed": "same", "now_question": "休みの決め方"})
    assert status == 200 and begun["status"] == "ok"
    status, answered = request(srv, "POST", "/api/reflect/answer", {"declined": True})
    assert [m["direction"] for m in answered["moves"]] == ["left_split", "silent_seat", "question_shift"]
    status, sheet = request(srv, "POST", "/api/reflect/finish",
                            {"chosen": "silent_seat", "meet_seat": "S03", "meet_reason": ""})
    assert status == 200 and sheet["move"]["label"] == "黙った席" and sheet["meet"]["title"] == "保育士"


def test_a_connection_that_sends_nothing_does_not_hold_up_the_screen(server):
    # Browsers open spare connections and may send nothing on them.
    srv, _ = server
    idle = socket.create_connection(srv.server_address, timeout=5)
    try:
        status, data = request(srv, "GET", "/api/setup", timeout=0.8)
        assert status == 200 and data["seats"]
    finally:
        idle.close()


def test_an_idle_connection_is_closed_after_the_timeout(server):
    srv, _ = server
    idle = socket.create_connection(srv.server_address, timeout=5)
    try:
        assert idle.recv(1) == b""  # The server closed it (timeout=1 here).
    finally:
        idle.close()


def test_the_sitting_is_touched_by_one_request_at_a_time(server):
    srv, _ = server
    done = []
    with srv.the_app.lock:  # As if a model call were still running.
        worker = threading.Thread(
            target=lambda: done.append(request(srv, "POST", "/api/start", {"lab": "quest"})))
        worker.start()
        worker.join(0.5)
        assert not done  # The second request waits its turn ...
        assert request(srv, "GET", "/api/setup", timeout=0.8)[0] == 200  # ... the page does not.
    worker.join(5)
    assert done and done[0][0] == 200


def test_the_waiting_words_come_from_texts(server):
    srv, _ = server
    texts = request(srv, "GET", "/api/setup")[1]["texts"]
    assert texts["waiting_ask"] and texts["waiting_reflection"] and "{error}" in texts["send_failed"]


def test_a_bad_lab_choice_does_not_start(server):
    srv, _ = server
    assert request(srv, "POST", "/api/start", {"lab": "x"}) == (400, {"error": "unknown_lab_choice"})


def test_another_host_name_is_refused(server):
    srv, _ = server
    status, data = request(srv, "GET", "/api/setup", headers={"Host": "evil.example:80"})
    assert (status, data) == (403, {"error": "bad_host"})


def test_posts_must_be_json(server):
    srv, _ = server
    port = srv.server_address[1]
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request("POST", "/api/start", body="lab=quest",
                       headers={"Host": f"127.0.0.1:{port}", "Content-Type": "application/x-www-form-urlencoded"})
    assert connection.getresponse().status == 415
    connection.close()


def test_the_console_shows_the_path_but_never_the_question(server, capsys):
    srv, _ = server
    request(srv, "POST", "/api/start", {"lab": "not_said"})
    request(srv, "POST", "/api/ask", {"question": "休みはひみつの問い？"})
    out = capsys.readouterr().out
    assert "POST /api/ask 200" in out and "ひみつ" not in out


def test_the_app_does_not_start_without_a_safe_records_folder(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(app_module, "load_env_file", lambda: None)
    monkeypatch.setenv("EBINO_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("EBINO_RECORDS_DIR", raising=False)
    assert app_module.main([]) == 2
    assert "records_dir_not_set" in capsys.readouterr().err
