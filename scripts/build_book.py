"""Precompute analyses for all positions up to PLIES from the start into
analysis.sqlite (the GUI cache), at DEPTH. Rerun with a higher depth to
deepen the book. Usage: build_book.py [depth] [plies]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import server  # noqa: E402  (reuses analyze() and the sqlite cache)
from tinyhouse import Position  # noqa: E402

DEPTH = int(sys.argv[1]) if len(sys.argv) > 1 else 14
PLIES = int(sys.argv[2]) if len(sys.argv) > 2 else 2
seen = set()
done = 0


def rec(pos: Position, ply: int) -> None:
    global done
    tfen = pos.tfen()
    if tfen in seen or pos.result() is not None:
        return
    seen.add(tfen)
    a = server.analyze(tfen, DEPTH)
    done += 1
    print(f"{done:4d} ply{PLIES-ply} {tfen:34s} v={a['value']:6d} best={a['best']}", flush=True)
    if ply == 0:
        return
    for m in pos.legal_moves():
        pos.make(m)
        rec(pos, ply - 1)
        pos.unmake()


rec(Position.start(), PLIES)
print(f"book: {done} positions at depth {DEPTH}")
