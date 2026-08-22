"""Tinyhouse GUI backend: stdlib http.server serving index.html plus JSON
analysis endpoints backed by the C engine, with a sqlite cache of results.
Run: python server.py [port]"""
import json
import sqlite3
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import engine_c as E
import tinyhouse as T

DIR = Path(__file__).parent
DB = DIR / "analysis.sqlite"
STATUS = DIR / "solve_status.json"

# Bump when the search changes in a way that can change stored values, so a
# stale cache from an older engine is never served as this engine's result.
ENGINE_VERSION = 2

TT_BITS = 24

# THB-09: only cache a result the engine PROVED. Rows are keyed on
# (tfen, depth, version), but th_solve probes a table earlier requests filled
# and cuts on a proven entry regardless of depth, so an unproven answer is a
# function of live TT state rather than of its key -- ask depth 14 and then
# depth 6 on the same server and the depth-6 row holds the depth-14 answer for
# 15 nodes, permanently. A proven value has no such problem: it is the true
# game value, so it cannot be contradicted by any later, deeper search.
# The cost, named rather than discovered later: unproven positions recompute on
# every request, so scripts/build_book.py only precomputes proven ones.
CACHE_ONLY_PROVEN = True

# ponytail: one global engine lock -- the C search uses global TT/path state;
# per-request engines if this ever serves more than one user
ENGINE_LOCK = threading.Lock()
DB_LOCK = threading.Lock()
db = None


def init(db_path=None, tt_bits=TT_BITS):
    """Allocate the engine table and open the cache.

    Deliberately not at import time. Importing this module used to allocate a
    256 MiB transposition table and open the repo's analysis.sqlite as a side
    effect, which is why nothing in the suite could touch the server at all.
    """
    global db
    E.lib.th_tt_init(tt_bits)
    db = sqlite3.connect(db_path or DB, check_same_thread=False)
    db.execute("CREATE TABLE IF NOT EXISTS analysis "
               "(tfen TEXT, depth INT, version INT, json TEXT, PRIMARY KEY(tfen, depth, version))")
    # THB-10 let depth<1 rows into older databases. Nothing can produce one
    # again, and a stored one would be served forever under a key no honest
    # search reaches.
    db.execute("DELETE FROM analysis WHERE depth < 1")
    db.commit()
    return db


# mirrors MATE_BOUND in tinyhouse.c: |v| above this is a mate score
T_MATE_BOUND = 29000


def white_view(v: int, stm: int) -> int:
    return v if stm == T.WHITE else -v


def analyze(tfen: str, depth: int) -> dict:
    with DB_LOCK:
        row = db.execute("SELECT json FROM analysis WHERE tfen=? AND depth=? AND version=?",
                         (tfen, depth, ENGINE_VERSION)).fetchone()
    if row:
        out = json.loads(row[0])
        # TH-41: nodes/time describe the computation that PRODUCED the row, not
        # this request. A proven row can carry a tiny node count (the search
        # that found it had a warm table), so rendering it as this request's
        # cost would read as "15 nodes proved a mate in 9". `cached` is the
        # flag that says so, and index.html drops the numbers when it is set.
        out["cached"] = True
        return out
    pos = T.Position.from_tfen(tfen)
    with ENGINE_LOCK:
        c = E.to_c(pos)
        bm = E.ffi.new("uint16_t *")
        snd = E.ffi.new("int *")
        n0 = E.lib.th_nodes()
        t0 = time.perf_counter()
        v = E.lib.th_solve(c, depth, bm, snd)
        mvs = E.ffi.new("uint16_t[128]")
        vals = E.ffi.new("int[128]")
        n = E.lib.th_root_moves(c, depth, mvs, vals)
        dt = time.perf_counter() - t0
        nodes = E.lib.th_nodes() - n0
    moves = sorted(
        ({"move": T.move_str(mvs[i]), "value": white_view(vals[i], pos.stm)} for i in range(n)),
        key=lambda x: -x["value"] if pos.stm == T.WHITE else x["value"])
    proven = abs(v) > T_MATE_BOUND or snd[0] == 3
    out = {"tfen": tfen, "depth": depth, "value": white_view(v, pos.stm), "snd": snd[0],
           "best": T.move_str(bm[0]) if bm[0] else None, "moves": moves,
           "proven": proven, "nodes": nodes, "time": round(dt, 3), "cached": False}
    if proven or not CACHE_ONLY_PROVEN:
        with DB_LOCK:
            db.execute("INSERT OR REPLACE INTO analysis VALUES (?,?,?,?)",
                       (tfen, depth, ENGINE_VERSION, json.dumps(out)))
            db.commit()
    return out


def position_info(tfen: str) -> dict:
    pos = T.Position.from_tfen(tfen)
    moves = {}
    for m in pos.legal_moves():
        pos.make(m)
        moves[T.move_str(m)] = pos.tfen()
        pos.unmake()
    return {"tfen": tfen, "moves": moves, "in_check": pos.in_check(pos.stm),
            "result": pos.result(), "stm": "wb"[pos.stm],
            "hands": {"w": pos.hands[0], "b": pos.hands[1]},
            "board": [(T.TYPE_CHARS[T.ptype(pc)], T.pcolor(pc), T.ppromoted(pc)) if pc else None
                      for pc in pos.board]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        try:
            if url.path == "/":
                body = (DIR / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif url.path.startswith("/pieces/"):
                f = (DIR / url.path.lstrip("/")).resolve()
                if f.parent != (DIR / "pieces").resolve() or not f.exists():
                    self.send_json({"error": "not found"}, 404)
                    return
                body = f.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Cache-Control", "max-age=3600")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif url.path == "/api/position":
                self.send_json(position_info(q["tfen"]))
            elif url.path == "/api/analyze":
                # THB-10: clamped BOTH ways. With no floor, depth=0 reached the
                # engine; the root skips the TT cutoff so the headline value
                # stayed 0 while the per-move array came straight out of the
                # table, producing a payload that contradicted itself and a
                # cache row under a key no honest search can ever reproduce.
                self.send_json(analyze(q["tfen"], max(1, min(int(q.get("depth", 12)), 22))))
            elif url.path == "/api/status":
                status = json.loads(STATUS.read_text()) if STATUS.exists() else {}
                self.send_json(status)
            else:
                self.send_json({"error": "not found"}, 404)
        except Exception as e:  # surface engine/parse errors to the UI
            self.send_json({"error": str(e)}, 400)


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8642
    init()
    print(f"http://127.0.0.1:{port}/")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
