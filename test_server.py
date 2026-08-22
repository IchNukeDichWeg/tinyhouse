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


def test_analyze_depth_is_clamped_below_as_well_as_above(srv):
    """THB-10: server.py clamped with min(depth, 22) and no floor.

    Cold, depth=0 returned best None and every move 0 -- harmless-looking. But
    the root skips the TT cutoff (`ply > 0`), so the headline `value` stays 0
    while the per-move array is served straight out of the table: after a
    depth-14 request on the same position, depth=0 came back with a real best
    move and mate scores in `moves`, all labelled `"depth": 0`. The payload
    contradicted itself, and that self-contradiction was then frozen into the
    cache under a key that can never be recomputed honestly.
    """
    code, a = srv("/api/analyze", tfen=START, depth=0)
    assert code == 200 and a["depth"] >= 1
    code, b = srv("/api/analyze", tfen=START, depth=-5)
    assert code == 200 and b["depth"] >= 1

    # and no row with an impossible depth can reach the cache
    rows = srv.module.db.execute("SELECT count(*) FROM analysis WHERE depth < 1").fetchone()
    assert rows[0] == 0
