"""The round-table screen: a small local web server (SPEC 5-1, 14-51).

    python -m ebino.app [--port 8765] [--plant]

Standard library only, plain HTML and JS, listening on 127.0.0.1 alone. The
map (seat_map.py) sits over the seat list, which stays; without the map file
the screen is the seat list alone. The app reads EBINO_DATA_DIR and
the key from .env, and does not start unless EBINO_RECORDS_DIR is set to a
safe place (SPEC 2-1): there is no default place to fall back to. Each
sitting and each prompt sent to the moderator is kept there (records.py).

Nothing the student types is printed or logged here. The console shows the
method, path and status of each request only.

Each connection gets its own thread, so a browser's spare connection that
sends nothing (or a page waiting on the moderator) cannot hold up the next
request, and an idle connection is closed after CONNECTION_TIMEOUT seconds.
The app is used by one student at a time: every request that touches the
sitting goes through one lock, one after another.
"""

import argparse
import json
import os
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import inside, relief
from .config import PlaceError, data_dir, load_env_file, records_dir
from .gate import Gate, load_names
from .records import Records
from .school_picture import SchoolPicture, folder_from_env
from .reflection import CHANGED_CHOICES
from .seat_label import KIND_LABELS, show_private_labels
from .session import LAB_CHOICES, Library, Refused, Session
from .texts import screen_texts

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/map.js": ("map.js", "text/javascript; charset=utf-8"),
    # A seat as a person at one to one (直し34-3), drawn by code.
    "/person.js": ("person.js", "text/javascript; charset=utf-8"),
    # Hand-drawn lines on the map (MIT), bundled: nothing is loaded from outside.
    "/rough.js": ("rough.js", "text/javascript; charset=utf-8"),
    "/rough.LICENSE.txt": ("rough.LICENSE.txt", "text/plain; charset=utf-8"),
    # The title's characters only, cut out of Shippori Mincho B1 (OFL, its
    # text beside it in title.OFL.txt).
    "/title.woff": ("title.woff", "font/woff"),
}
# Served from mapdata/, made once by the tools (relief.py). A missing file is 404.
MAP_FILES = {
    relief.IMAGE_PATH: (relief.RELIEF_DIR / relief.IMAGE, "image/webp"),
}
MAX_BODY = 16 * 1024
# Seconds a connection may sit without sending or taking bytes. Waiting for
# the model is not counted: that happens after the request is read.
CONNECTION_TIMEOUT = 20


class App:
    """Holds the library, the gate and the one sitting in progress."""

    def __init__(self, library: Library, gate: Gate, records: Records | None = None,
                 plant: bool = False, rng=None, school: SchoolPicture | None = None):
        self.library = library
        # The school's 3D picture, from outside the repo (school_picture.py);
        # None or without pictures: its line mark.
        self.school = school
        self.gate = gate
        self.records = records
        self.plant = plant
        self.rng = rng
        self.session: Session | None = None
        # The sitting is touched by one request at a time. setup() reads only
        # what never changes, so it does not wait here.
        self.lock = threading.Lock()
        if records is not None:
            gate.on_send = self._on_send

    def _on_send(self, role: str, request: dict) -> None:
        if self.session is not None:
            self.records.save_prompt(self.session.session_id, role, request)

    def setup(self) -> dict:
        view = self.library.map_view()  # None: no map, the seat list alone.
        if view is not None:
            view["school_picture"] = self.school.view if self.school else None
        return {
            "texts": screen_texts(),
            "kinds": KIND_LABELS,
            "labs": LAB_CHOICES,
            "changed_choices": CHANGED_CHOICES,
            "seats": self.library.seat_list(),
            "map": view,
            # Whose words are in the app, as counts from the seat table (直し31-5).
            "inside": inside.view(self.library.seats),
        }

    def start(self, body: dict) -> dict:
        session = Session(self.library, self.gate, plant=self.plant, rng=self.rng, records=self.records)
        session.set_lab(body.get("lab", ""))  # Saves the first record.
        self.session = session
        return {"purposes": session.next_purposes()}

    def handle(self, path: str, body: dict) -> dict:
        with self.lock:
            return self._handle(path, body)

    def _handle(self, path: str, body: dict) -> dict:
        if path == "/api/start":
            return self.start(body)
        session = self.session
        if session is None:
            raise Refused("no_session")
        if path == "/api/ask":
            return session.ask(body.get("question", ""))
        if path == "/api/closing":
            return session.close_round(body.get("round"))
        if path == "/api/coach":
            return session.coach_band(body.get("round"))
        if path == "/api/coach_answer":
            return session.coach_answer(body.get("round"), body.get("role", ""), body.get("answer", ""),
                                        after_notice=body.get("after_notice") is True)
        # One to one (直し34-4): the questions now, a question picked, a question written.
        if path == "/api/one/open":
            return session.one_view(body.get("seat_id"))
        if path == "/api/one/ask":
            return session.one_ask(body.get("seat_id"), body.get("item"))
        if path == "/api/one/thanks":
            return session.one_thanks(body.get("seat_id"))
        if path == "/api/one/free":
            return session.one_free_question(body.get("seat_id"), body.get("question", ""))
        if path == "/api/ask_card":
            return session.ask_card(body.get("round"))
        if path == "/api/ask_seat":
            return session.ask_the_seat(body.get("round"))
        if path == "/api/more":
            return session.hear_more(body.get("utterance_id", ""))
        if path == "/api/more_card":
            return session.more_card(body.get("utterance_id", ""))
        if path == "/api/card":
            return session.write_card(body.get("seat_id", ""), body.get("text", ""))
        if path == "/api/mark":
            return {"marks": session.mark(body.get("round"), body.get("utterance_id", ""))}
        if path == "/api/split":
            return {"heading": session.press_split(body.get("round"), body.get("index"))}
        if path == "/api/purposes":
            return {"purposes": session.next_purposes()}
        if path == "/api/paragraph":
            return session.paragraph(body.get("utterance_id", ""))
        if path == "/api/reflect/begin":
            return session.reflect_begin(body.get("changed", ""), body.get("now_question", ""))
        if path == "/api/reflect/answer":
            return session.reflect_answer(body.get("answer", ""), body.get("declined") is True)
        if path == "/api/reflect/finish":
            return session.reflect_finish(body.get("chosen", ""), body.get("own_move", ""),
                                          body.get("rewrite", ""), body.get("meet_seat", ""),
                                          body.get("meet_reason", ""))
        if path == "/api/harvest":
            return session.harvest(body.get("use", ""))
        if path == "/api/subject":
            return session.subject()
        if path == "/api/subject_more":
            return session.subject_more()
        if path == "/api/subject_choose":
            return session.subject_choose(body.get("choice"))
        raise Refused("unknown_path")


def make_handler(app: App, port: int, timeout: float = CONNECTION_TIMEOUT):
    allowed_hosts = {f"{HOST}:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # Path only: never a query or a body.
            pass

        def log_request(self, code="-", size="-"):
            print(f"{self.command} {urlsplit(self.path).path} {getattr(code, 'value', code)}")

        def _send(self, status: int, data: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, status: int, value) -> None:
            self._send(status, json.dumps(value, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

        def _host_ok(self) -> bool:
            # Another site's page cannot reach this server through a name
            # that points at 127.0.0.1.
            return self.headers.get("Host", "") in allowed_hosts

        def do_GET(self):
            if not self._host_ok():
                return self._json(HTTPStatus.FORBIDDEN, {"error": "bad_host"})
            path = urlsplit(self.path).path
            if path == "/api/setup":
                return self._json(HTTPStatus.OK, app.setup())
            if path in STATIC_FILES:
                name, content_type = STATIC_FILES[path]
                return self._send(HTTPStatus.OK, (STATIC_DIR / name).read_bytes(), content_type)
            if path in MAP_FILES:
                file, content_type = MAP_FILES[path]
                try:
                    return self._send(HTTPStatus.OK, file.read_bytes(), content_type)
                except OSError:
                    pass  # No picture: the screen keeps the flat map.
            # The school's two pictures, from their folder only; anything else is 404.
            picture = app.school.file(path) if app.school else None
            if picture is not None:
                return self._send(HTTPStatus.OK, picture, "image/png")
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if not 0 <= length <= MAX_BODY:
                self.close_connection = True
                return self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "too_large"})
            # Read the body before any answer: closing a socket with bytes
            # left unread resets it, and the browser would see no answer.
            raw = self.rfile.read(length)
            if not self._host_ok():
                return self._json(HTTPStatus.FORBIDDEN, {"error": "bad_host"})
            # A form on another site cannot send JSON without asking first.
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                return self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "json_only"})
            try:
                body = json.loads(raw or b"{}")
            except ValueError:
                return self._json(HTTPStatus.BAD_REQUEST, {"error": "bad_json"})
            if not isinstance(body, dict):
                return self._json(HTTPStatus.BAD_REQUEST, {"error": "bad_json"})
            try:
                result = app.handle(urlsplit(self.path).path, body)
            except Refused as error:
                status = HTTPStatus.CONFLICT if str(error) == "no_session" else HTTPStatus.BAD_REQUEST
                return self._json(status, {"error": str(error)})
            self._json(HTTPStatus.OK, result)

    Handler.timeout = timeout  # Socket timeout for each connection.
    return Handler


def make_server(app: App, port: int = DEFAULT_PORT, timeout: float = CONNECTION_TIMEOUT) -> ThreadingHTTPServer:
    """Port 0 picks a free port (tests); the handler learns the real one."""
    server = ThreadingHTTPServer((HOST, port), BaseHTTPRequestHandler)
    server.daemon_threads = True  # Ctrl+C does not wait for an open connection.
    server.RequestHandlerClass = make_handler(app, server.server_address[1], timeout)
    return server


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ebino.app")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--plant", action="store_true", help="mix in the planted fake quote (SPEC 7-3)")
    args = parser.parse_args(argv)
    load_env_file()
    try:
        folder = data_dir()
        records = Records(records_dir())  # Checked before anything starts (SPEC 2-1).
    except PlaceError as error:
        print(error, file=sys.stderr)
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set (put it in .env)", file=sys.stderr)
        return 2
    import anthropic

    try:
        library = Library.load(folder, show_private_labels())
    except FileNotFoundError:
        print("ingested pieces not found: run python -m ebino.ingest.run first", file=sys.stderr)
        return 2
    except ValueError as error:  # A table's file name and line number only.
        print(error, file=sys.stderr)
        return 2
    # Every seat's names, those kept off the map (coach.tsv) too.
    gate = Gate(anthropic.Anthropic(), load_names(folder, library.all_seats))
    school = SchoolPicture(folder_from_env())
    server = make_server(App(library, gate, records, plant=args.plant, school=school), args.port)
    print(f"seats {len(library.seats)}  pieces {len(library.entries)}  purpose samples {len(library.purposes)}")
    print(f"coach band {'on' if library.coach_on else 'off'}  coach pieces {len(library.coach_sources)}  "
          f"seats off the map {len(library.all_seats) - len(library.seats)}")
    print(library.map_report())  # 「地図なし」 when the map file is missing or broken.
    if library.placement is not None:
        print(library.relief_report())  # No picture: the flat map.
        print(school.report())  # No picture of the school: its line mark.
    print(library.subject_catalog.report())  # The harvest card's ③: counts only.
    print(f"open http://{HOST}:{server.server_address[1]}/  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
