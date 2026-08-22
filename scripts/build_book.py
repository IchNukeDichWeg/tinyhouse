"""Precompute analyses for all positions up to PLIES from the start into
analysis.sqlite (the GUI cache), at DEPTH. Rerun with a higher depth to
deepen the book. Usage: build_book.py [depth] [plies] [db]

Only PROVEN results are stored (server.CACHE_ONLY_PROVEN): an unproven value
depends on what the transposition table already held, so it is not a function
of its (tfen, depth) key and must not be frozen. At shallow depths most
positions near the start are unproven, so the book is small on purpose -- the
`kept` count below is the honest one, not the visited count.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import server  # noqa: E402  (reuses analyze() and the sqlite cache)
from tinyhouse import Position  # noqa: E402

DEPTH = int(sys.argv[1]) if len(sys.argv) > 1 else 14
PLIES = int(sys.argv[2]) if len(sys.argv) > 2 else 2
server.init(sys.argv[3] if len(sys.argv) > 3 else None)
seen = set()
done = 0
kept = 0


def rec(pos: Position, ply: int) -> None:
    global done, kept
    tfen = pos.tfen()
    if tfen in seen or pos.result() is not None:
        return
    seen.add(tfen)
    a = server.analyze(tfen, DEPTH)
    done += 1
    kept += a["proven"]
    print(f"{done:4d} ply{PLIES-ply} {tfen:34s} v={a['value']:6d} best={a['best']}"
          f"{'  (proven, stored)' if a['proven'] else ''}", flush=True)
    if ply == 0:
        return
    for m in pos.legal_moves():
        pos.make(m)
        rec(pos, ply - 1)
        pos.unmake()


rec(Position.start(), PLIES)
print(f"book: {kept} proven of {done} positions visited at depth {DEPTH}")
