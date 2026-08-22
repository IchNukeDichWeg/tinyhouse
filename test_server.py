"""GUI backend tests.

Nothing used to exercise server.py at all, because importing it allocated a
256 MiB transposition table and opened the repo's analysis.sqlite as an
import-time side effect. server.init() now does that, so a test can point it at
a scratch database and drive the real handler over a real socket.
"""
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

import pytest


@pytest.fixture
def srv(tmp_path):
    """The real handler on an ephemeral port, with its own cache database."""
    import server

    server.init(tmp_path / "cache.sqlite", tt_bits=18)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def get(path, **params):
        url = f"http://127.0.0.1:{httpd.server_address[1]}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    get.module = server
    yield get
    httpd.shutdown()


START = "fuwk/3p/P3/KWUF[-] w"


def test_position_and_analyze_round_trip(srv):
    code, info = srv("/api/position", tfen=START)
    assert code == 200
    assert sorted(info["moves"]) == ["a1b2", "a2a3", "b1b2", "c1b3", "c1d3", "d1c2"]
    assert info["stm"] == "w" and info["in_check"] is False and info["result"] is None

    code, a = srv("/api/analyze", tfen=START, depth=8)
    assert code == 200
    assert a["depth"] == 8 and a["cached"] is False and a["nodes"] > 0
    assert len(a["moves"]) == 6
    code, again = srv("/api/analyze", tfen=START, depth=8)
    assert again["cached"] is True and again["value"] == a["value"]


def test_a_malformed_tfen_is_a_400(srv):
    code, err = srv("/api/position", tfen="not a tfen")
    assert code == 400 and "error" in err
