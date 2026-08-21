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

E.lib.th_tt_init(24)
# ponytail: one global engine lock -- the C search uses global TT/path state;
# per-request engines if this ever serves more than one user
ENGINE_LOCK = threading.Lock()
db = sqlite3.connect(DB, check_same_thread=False)
db.execute("CREATE TABLE IF NOT EXISTS analysis "
           "(tfen TEXT, depth INT, version INT, json TEXT, PRIMARY KEY(tfen, depth, version))")
DB_LOCK = threading.Lock()


def white_view(v: int, stm: int) -> int:
    return v if stm == T.WHITE else -v


def analyze(tfen: str, depth: int) -> dict:
    with DB_LOCK:
        row = db.execute("SELECT json FROM analysis WHERE tfen=? AND depth=? AND version=?",
                         (tfen, depth, ENGINE_VERSION)).fetchone()
    if row:
        out = json.loads(row[0])
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
    out = {"tfen": tfen, "depth": depth, "value": white_view(v, pos.stm), "snd": snd[0],
           "best": T.move_str(bm[0]) if bm[0] else None, "moves": moves,
           "nodes": nodes, "time": round(dt, 3), "cached": False}
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
                self.send_json(analyze(q["tfen"], min(int(q.get("depth", 12)), 22)))
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
    print(f"http://127.0.0.1:{port}/")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
