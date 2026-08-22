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


def test_cache_rows_are_namespaced_by_the_engine_build(srv):
    """TH-42: ENGINE_VERSION was a hand-bumped 2.

    Reproduced end to end in a scratch mirror: editing `#define MATE` fired the
    rebuild and gave a new engine, while the server went on serving the old
    values under an unchanged version key. It is derived now, from the compiled
    build id and a hash of server.py -- the engine decides the values, this file
    decides the payload shape and the frame they are expressed in.
    """
    import hashlib
    import pathlib

    import engine_c

    server = srv.module
    expect = (engine_c.lib.th_build_id() ^ int.from_bytes(
        hashlib.sha1(pathlib.Path(server.__file__).read_bytes()).digest()[:8],
        "little")) & 0x7FFFFFFFFFFFFFFF
    assert server.ENGINE_VERSION == expect

    srv("/api/analyze", tfen=MATE9, depth=10)
    with server.DB_LOCK:
        server.db.execute("UPDATE analysis SET version = version + 1")
        server.db.commit()
    code, a = srv("/api/analyze", tfen=MATE9, depth=10)
    assert a["cached"] is False, "a row from another engine version was served"


def sigma(tfen):
    """Colour mirror: flip ranks, swap colours, swap hands, flip side to move.

    Maps a legal position to a legal one whose value in White's frame is the
    negation of the original's, with the mover in an identical situation.
    """
    import tinyhouse as T

    p = T.Position.from_tfen(tfen)
    q = T.Position()
    for s in range(16):
        pc = p.board[s]
        if pc:
            r, f = s >> 2, s & 3
            q.board[(3 - r) * 4 + f] = T.piece(1 - T.pcolor(pc), T.ptype(pc), T.ppromoted(pc))
    q.hands = [list(p.hands[1]), list(p.hands[0])]
    q.stm = 1 - p.stm
    return q.tfen()


def test_value_and_snd_are_in_the_same_frame(srv):
    """TH-40: `value` was white-view and `snd` was mover-view.

    SND_LB and SND_UB are duals of the value they describe, so negating the
    value has to swap them. The colour-mirrored pair below returned -29991 and
    +29991, correctly negated, and both reported snd=1 -- a lower bound for
    White and an upper bound for Black, served under the same name.
    """
    code, a = srv("/api/analyze", tfen=MATE9, depth=10)
    code, b = srv("/api/analyze", tfen=sigma(MATE9), depth=10)
    assert a["value"] == -b["value"] != 0
    swap = ((b["snd"] & 1) << 1) | ((b["snd"] & 2) >> 1)
    assert a["snd"] == swap, (a["snd"], b["snd"])
    assert a["snd"] != b["snd"], "the flags did not move with the value"


def test_a_busy_engine_returns_503_instead_of_queueing(srv):
    """THB-11: an abandoned request pinned ENGINE_LOCK for its whole search.

    The handler runs to completion and only then dies on BrokenPipeError, so a
    trivial depth-2 request measured 11.36s behind one abandoned depth-14
    search, and 87.72s on an independent run. Only /api/analyze cache misses
    are affected; /api/position never touches the lock, which this also pins.
    """
    server = srv.module
    server.ENGINE_LOCK_TIMEOUT = 0.2
    try:
        assert server.ENGINE_LOCK.acquire()
        try:
            code, err = srv("/api/analyze", tfen=START, depth=8)
            assert code == 503 and "another analysis" in err["error"]
            code, info = srv("/api/position", tfen=START)      # never blocks
            assert code == 200
        finally:
            server.ENGINE_LOCK.release()
    finally:
        server.ENGINE_LOCK_TIMEOUT = 20.0

    code, a = srv("/api/analyze", tfen=START, depth=8)
    assert code == 200                                          # and recovers


def test_the_gui_cannot_ask_for_a_non_interactive_depth(srv):
    """The clamp is exercised at a cheap depth on purpose: running the real
    MAX_GUI_DEPTH here would put a 10s search in every suite run."""
    server = srv.module
    assert server.MAX_GUI_DEPTH == 16
    server.MAX_GUI_DEPTH = 4
    try:
        code, a = srv("/api/analyze", tfen=START, depth=22)
        assert code == 200 and a["depth"] == 4
    finally:
        server.MAX_GUI_DEPTH = 16
    page = (__import__("pathlib").Path(__file__).parent / "index.html").read_text()
    assert "[8,10,12,14,16]" in page


def test_an_internal_error_does_not_echo_a_filesystem_path(srv, monkeypatch, capfd):
    """TH-44: the blanket `except Exception` echoed str(e) into the body.

    Plenty of exceptions carry an absolute path -- a GET on a subdirectory of
    /pieces/ raises IsADirectoryError, whose message is the full path -- and
    the only mitigation was the 127.0.0.1 bind. Applies to every endpoint, so
    it is pinned by planting the exception rather than by needing a directory
    inside the repo.
    """
    secret = "/Users/somebody/private/checkout/Tinyhouse/pieces/sub"

    def boom(_tfen):
        raise IsADirectoryError(21, "Is a directory", secret)

    monkeypatch.setattr(srv.module, "position_info", boom)
    code, err = srv("/api/position", tfen=START)
    assert code == 500
    assert secret not in json.dumps(err)
    assert err["error"] == "internal error"
    assert secret in capfd.readouterr().err          # still logged locally


def test_a_missing_query_parameter_is_a_400(srv):
    code, err = srv("/api/position")
    assert code == 400 and "tfen" in err["error"]


def test_analyze_reports_a_best_move_at_every_reachable_depth(srv):
    """TH-43: root_search recovered the best move by probing the TT.

    Unproven depth-1 stores are skipped on purpose -- they are most of the
    write traffic and nearly worthless -- so at depth 1 the probe found nothing
    and the response carried best = null while listing six scored moves. The
    searching thread already knew the move; it just was not handing it back.
    Reachable since THB-10 put the floor at 1.
    """
    for d in (1, 2, 3):
        code, a = srv("/api/analyze", tfen=START, depth=d)
        assert code == 200 and a["best"] is not None, (d, a)
        assert a["best"] in srv("/api/position", tfen=START)[1]["moves"]


def test_the_gui_carries_its_two_client_side_guards():
    """index.html has no test harness, so these are presence checks backing
    browser-driven verification recorded in SCOREBOARD.md.

    THB-12: playMove refuses while a load is in flight. Verified in the browser
    by clicking a2a3 then d1c2 without awaiting -- with the guard removed the
    history records both moves and lands on a position in which a2a3 was never
    played.

    THB-13: the setup palette can create a promoted piece. Verified in the
    browser: selecting F~ and clicking c1 builds `fuwk/3p/P3/KWF~F[-] w`.
    """
    page = (__import__("pathlib").Path(__file__).parent / "index.html").read_text()
    assert "if (loading) return;" in page
    assert '"F~","U~","W~"' in page and '"f~","u~","w~"' in page


def test_each_root_move_carries_its_own_soundness(srv):
    """TH-35: th_root_moves discarded per-move soundness, and index.html
    hardcoded 0 for it, so every row read as unproven.

    The sign correction is the load-bearing part and it is asserted directly.
    The child value is negated on the way out, and SND_LB/SND_UB are duals of
    the value they describe, so the flags swap with it: from the start position
    d1c2 scores -29990 in White's frame and must carry SND_UB (2), an UPPER
    bound. A badge reading the raw child flag would print "lower bound".

    The obvious acceptance test -- "proven only when snd == 3" -- is
    insensitive to exactly this, because 3 is invariant under the swap.
    """
    code, a = srv("/api/analyze", tfen=START, depth=10)
    rows = {m["move"]: m for m in a["moves"]}
    assert rows["d1c2"]["value"] == -29990
    assert rows["d1c2"]["snd"] == 2, "the mate row must be an UPPER bound in White's frame"
    assert all(rows[m]["snd"] == 0 for m in rows if m != "d1c2")

    page = (__import__("pathlib").Path(__file__).parent / "index.html").read_text()
    assert "fmtVal(mv.value, mv.snd)" in page
