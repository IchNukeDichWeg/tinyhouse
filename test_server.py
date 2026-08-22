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
MATE9 = "fuwk/3p/P1F1/KWU1[-] b"        # Black mates in 9


def test_position_and_analyze_round_trip(srv):
    code, info = srv("/api/position", tfen=START)
    assert code == 200
    assert sorted(info["moves"]) == ["a1b2", "a2a3", "b1b2", "c1b3", "c1d3", "d1c2"]
    assert info["stm"] == "w" and info["in_check"] is False and info["result"] is None

    code, a = srv("/api/analyze", tfen=START, depth=8)
    assert code == 200
    assert a["depth"] == 8 and a["cached"] is False and a["nodes"] > 0
    assert len(a["moves"]) == 6

    # Cache hits are asserted on a PROVEN position: since THB-09 only proven
    # results are stored, because an unproven one is a function of live TT
    # state rather than of its (tfen, depth) key.
    code, p = srv("/api/analyze", tfen=MATE9, depth=10)
    assert code == 200 and p["proven"] is True and p["cached"] is False
    code, again = srv("/api/analyze", tfen=MATE9, depth=10)
    assert again["cached"] is True and again["value"] == p["value"]


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



def test_an_unproven_analysis_is_not_frozen_into_the_cache(srv):
    """THB-09: rows were keyed on (tfen, depth, version) but the value is a
    function of live TT state.

    th_solve probes a table earlier requests filled, and the cutoff fires on a
    proven entry regardless of depth. Asking depth 14 first and then depth 6 on
    the same server returned the depth-14 answer for 15 nodes -- and stored it
    permanently under the depth-6 key, so an honest cold depth-6 request could
    never be served for that key again. The value itself is a genuine proof;
    what must not be frozen is a result that depends on what preceded it.
    """
    srv("/api/analyze", tfen=MATE9, depth=14)
    code, shallow = srv("/api/analyze", tfen=MATE9, depth=6)
    assert code == 200

    rows = srv.module.db.execute(
        "SELECT depth FROM analysis WHERE tfen=? ORDER BY depth", (MATE9,)).fetchall()
    depths = [r[0] for r in rows]
    if shallow["value"] < -29000:
        # served the deep proof: true, depth-independent, fine to keep
        assert 6 in depths
    else:
        # answered honestly at depth 6 and therefore unproven: must not be kept
        assert 6 not in depths, "an unproven, history-dependent row was cached"


def test_an_unproven_shallow_analysis_is_never_cached(srv):
    """The general rule, independent of ordering: a result that is neither a
    mate score nor snd == 3 is not the game value, so it must recompute."""
    code, a = srv("/api/analyze", tfen=START, depth=6)
    assert code == 200 and abs(a["value"]) < 29000 and a["snd"] != 3
    row = srv.module.db.execute(
        "SELECT count(*) FROM analysis WHERE tfen=? AND depth=6", (START,)).fetchone()
    assert row[0] == 0
    code, again = srv("/api/analyze", tfen=START, depth=6)
    assert again["cached"] is False


def test_build_book_runs(tmp_path, monkeypatch):
    """scripts/build_book.py is the only other caller of server.analyze, and it
    reaches it by import. Nothing covered it, so moving the engine and cache
    setup out of import broke it silently.
    """
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).parent
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
    r = subprocess.run([sys.executable, str(root / "scripts" / "build_book.py"),
                        "6", "0", str(tmp_path / "book.sqlite")],
                       cwd=tmp_path, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert "positions visited at depth 6" in r.stdout


def test_a_cache_hit_is_marked_and_its_provenance_is_not_this_request(srv):
    """TH-41: a hit replays the producing computation's nodes and time.

    Load-bearing only in combination with THB-09, which is fixed, so what is
    left is the label. A proven row can carry a tiny node count -- the search
    that found it had a warm table -- and showing that as this request's cost
    reads as "15 nodes proved a mate in 9". The response marks it; index.html
    prints "from cache" instead of the numbers.
    """
    code, first = srv("/api/analyze", tfen=MATE9, depth=10)
    assert first["cached"] is False
    code, hit = srv("/api/analyze", tfen=MATE9, depth=10)
    assert hit["cached"] is True
    assert hit["depth"] == first["depth"] == 10
    assert hit["nodes"] == first["nodes"] and hit["time"] == first["time"]

    page = (__import__("pathlib").Path(__file__).parent / "index.html").read_text()
    assert "from cache" in page
    assert "nodes · ${a.time}s` + (a.cached" not in page
