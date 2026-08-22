"""Tinyhouse GUI backend: stdlib http.server serving index.html plus JSON
analysis endpoints backed by the C engine, with a sqlite cache of results.
Run: python server.py [port]"""
import hashlib
import json
import sqlite3
import threading
import time
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import engine_c as E
import tinyhouse as T

DIR = Path(__file__).parent
DB = DIR / "analysis.sqlite"
STATUS = DIR / "solve_status.json"

# Cache namespace, DERIVED rather than hand-bumped (TH-42). A stale cache from
# an older engine must never be served as this engine's result, and nobody
# remembers to bump a constant: editing `#define MATE` and letting the rebuild
# fire left the server serving the old values under an unchanged key. Both
# inputs matter -- the engine decides the values, this file decides the payload
# shape and the frames those values are expressed in.
# Cost, named rather than discovered: any edit to either file invalidates the
# whole cache. It is gitignored and rebuildable, and over-invalidating is the
# safe direction.
ENGINE_VERSION = (E.lib.th_build_id() ^ int.from_bytes(
    hashlib.sha1(Path(__file__).read_bytes()).digest()[:8], "little")) & 0x7FFFFFFFFFFFFFFF

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

# THB-11: an abandoned request used to hold the lock for as long as its search
# ran, because the handler runs to completion and only then dies on
# BrokenPipeError. Measured: a trivial depth-2 request went from a 0.13s idle
# baseline to 11.36s behind one abandoned depth-14 search, and 87.72s on an
# independent run. Only /api/analyze cache misses are affected -- /api/position,
# /api/status, / and /pieces/ never touch the lock, and cache hits return
# before it.
ENGINE_LOCK_TIMEOUT = 20.0

# ...and cap what the GUI can ask for at all. Measured cold on an M2 Pro, one
# /api/analyze call each (th_solve plus th_root_moves) from the start position:
# d14 1.10s / 3.7M nodes, d16 10.25s / 36.4M nodes, d18 98.77s / 397M nodes.
# 18 is not an interactive depth and 20/22 are the multi-hour bound runs;
# solve_hunt.py is the tool for those.
MAX_GUI_DEPTH = 16


class EngineBusy(Exception):
    """Another analysis holds the engine and did not finish in time."""
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


def white_view_snd(snd: int, stm: int) -> int:
    """TH-40: put the soundness flags in the same frame as the value.

    SND_LB and SND_UB are duals of the value they describe, so negating the
    value into White's frame has to swap them. Serving the raw mover-frame bits
    beside a white-view value made the payload mix frames: a colour-mirrored
    pair returned values -29991 and +29991 -- correctly negated -- and BOTH
    reported snd=1, which is a lower bound for White and an upper bound for
    Black. A badge reading the raw flag prints "lower bound" for an upper one.
    """
    if stm == T.WHITE:
        return snd
    return ((snd & 1) << 1) | ((snd & 2) >> 1)


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
    if not ENGINE_LOCK.acquire(timeout=ENGINE_LOCK_TIMEOUT):
        raise EngineBusy("another analysis is still running; try again in a moment")
    try:
        c = E.to_c(pos)
        bm = E.ffi.new("uint16_t *")
        snd = E.ffi.new("int *")
        n0 = E.lib.th_nodes()
        t0 = time.perf_counter()
        v = E.lib.th_solve(c, depth, bm, snd)
        mvs = E.ffi.new("uint16_t[128]")
        vals = E.ffi.new("int[128]")
        msnd = E.ffi.new("int[128]")
        n = E.lib.th_root_moves(c, depth, mvs, vals, msnd)
        dt = time.perf_counter() - t0
        nodes = E.lib.th_nodes() - n0
    finally:
        ENGINE_LOCK.release()
    # TH-35: each move carries its own soundness, in the same frame as its
    # value. th_root_moves already swapped the flags for the negation it does
    # internally; white_view_snd swaps again when the value is put in White's
    # frame, so the two always travel together.
    moves = sorted(
        ({"move": T.move_str(mvs[i]), "value": white_view(vals[i], pos.stm),
          "snd": white_view_snd(msnd[i], pos.stm)} for i in range(n)),
        key=lambda x: -x["value"] if pos.stm == T.WHITE else x["value"])
    proven = abs(v) > T_MATE_BOUND or snd[0] == 3
    out = {"tfen": tfen, "depth": depth, "value": white_view(v, pos.stm),
           "snd": white_view_snd(snd[0], pos.stm),
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
    moves, checks = {}, []
    for m in pos.legal_moves():
        pos.make(m)
        moves[T.move_str(m)] = pos.tfen()
        # TH-46: move_str never appends '+', and it cannot -- a move string
        # says nothing about the position it lands in. Reported as a separate
        # list rather than baked into the key, because the key is the move's
        # identity everywhere in the GUI.
        if pos.in_check(pos.stm):
            checks.append(T.move_str(m))
        pos.unmake()
    return {"tfen": tfen, "moves": moves, "checks": checks, "in_check": pos.in_check(pos.stm),
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
                # TH-47: the Content-Type below is hardcoded, and that is the
                # right call -- guessing would introduce a sniffing risk this
                # route does not otherwise have. What was missing is the
                # premise: require the .svg suffix, so the hardcoded type is
                # provably correct rather than incidentally correct.
                if (f.suffix != ".svg" or f.parent != (DIR / "pieces").resolve()
                        or not f.exists()):
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
                self.send_json(analyze(q["tfen"], max(1, min(int(q.get("depth", 12)), MAX_GUI_DEPTH))))
            elif url.path == "/api/status":
                status = json.loads(STATUS.read_text()) if STATUS.exists() else {}
                self.send_json(status)
            else:
                self.send_json({"error": "not found"}, 404)
        except EngineBusy as e:
            self.send_json({"error": str(e)}, 503)
        except ValueError as e:
            # our own validation: the message quotes the caller's own input
            self.send_json({"error": str(e)}, 400)
        except KeyError as e:
            self.send_json({"error": f"missing query parameter {e}"}, 400)
        except Exception:
            # TH-44: a blanket `str(e)` echoed whatever the exception carried,
            # and plenty carry an absolute filesystem path -- GET on a
            # subdirectory of /pieces/ raises IsADirectoryError, whose message
            # is the full path. Log it here, tell the client nothing. Applies
            # to every endpoint; the 127.0.0.1 bind was the only mitigation.
            traceback.print_exc()
            self.send_json({"error": "internal error"}, 500)


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8642
    init()
    print(f"http://127.0.0.1:{port}/")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
