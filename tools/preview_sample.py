"""えびの円卓を、架空の見本だけで開く（APIキーなし・実データなし・モデルを呼ばない）。

    python tools/preview_sample.py            # http://127.0.0.1:8780/
    python tools/preview_sample.py --port 8781

席はリポジトリの架空の席表（samples/seats.tsv）、言葉はこのファイルの架空の数行、
地図と立体の絵はリポジトリの mapdata/ です。見られるのは、最初の画面・Lab を選んだ
あとの司会の説明・入っている言葉・地図と席まで。モデルを呼ばないので、問いを送ると
「いまは答えられない」ときの画面になります（円卓が答える場面は動画で）。

記録は取りません（記録のフォルダを渡さない）。待ち受けはこのPCの中（127.0.0.1）だけです。
"""

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ebino import coach, relief, seat_map  # noqa: E402
from ebino.app import App, make_server  # noqa: E402
from ebino.gate import Gate, NameList  # noqa: E402
from ebino.ingest.seats import load_seats  # noqa: E402
from ebino.ingest.utterance import Utterance  # noqa: E402
from ebino.session import Library  # noqa: E402

SAMPLES = REPO / "samples"
DEFAULT_PORT = 8780


def piece(i, seat, text, kind="adult", voice="article", section="本文", heading=""):
    return Utterance(id=i, seat_id=seat, kind=kind, section=section, voice=voice, text=text,
                     paragraph=text, heading=heading)


# 架空の言葉（実在の人の言葉ではない）。席は samples/seats.tsv。
PIECES = [
    piece("s1", "S01", "休みは決めて取ります。月曜は必ず店を閉めます。", voice="spoken"),
    piece("s2", "S01", "お客さんの話を聞くのも仕事のうちだと思っています。"),
    piece("f1", "S02", "畑は天気しだいなので、休みは空いたときに取ります。", voice="spoken"),
    piece("f2", "S02", "作ったものを直接届けると、食べた人の声が返ってきます。"),
    piece("d1", "D01", "図面どおりにいかないときに、どうするかを考えるのがおもしろい。", voice="spoken"),
    piece("p1", "P01", "川のにごりが何で決まるのかを知る。", kind="poster", section="目的", heading="目的"),
    piece("p2", "P01", "雨の次の日ほど、にごりが強かった。", kind="poster", section="結果", heading="結果"),
    piece("p3", "P02", "朝市に人が集まる時間を調べた。", kind="poster", section="手法", heading="手法"),
    piece("c1", "C01", "島では、知らない人にも先にあいさつをする。", kind="cross", voice="own"),
    piece("o1", "O01", "外から来ると、ここの夜の暗さに驚きます。", kind="outsider_teacher", voice="spoken"),
]


class NoModel:
    """The client the gate is given: it never reaches a model, so every
    request ends as the app's own 「答えられない」 (the gate catches it)."""

    def __init__(self):
        self.messages = self

    def with_options(self, **_options):
        return self

    def create(self, **_request):
        raise RuntimeError("見本モード：モデルは呼ばない")


def library() -> Library:
    seats = load_seats(SAMPLES / "seats.tsv")
    map_data = seat_map.load_map()
    relief_data = relief.load_relief((map_data.width, map_data.height)) if map_data else None
    coach_seats = coach.load_coach(SAMPLES, {seat.seat_id for seat in seats})
    # 肩書きだけ（会社名は出さない）。
    return Library.build(seats, PIECES, {}, False, coach_seats=coach_seats, map_data=map_data,
                         relief_data=relief_data)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python tools/preview_sample.py")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    lib = library()
    server = make_server(App(lib, Gate(NoModel(), NameList.build(lib.all_seats, {})), None), args.port)
    print(f"見本モード（架空の席 {len(lib.seats)}・モデルなし）")
    print(f"open http://127.0.0.1:{server.server_address[1]}/  (Ctrl+C で止める)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
