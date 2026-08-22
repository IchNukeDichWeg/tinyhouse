"""Exact census of positions REACHABLE from the start, by ply.

scripts/state_count.py counts what the notation can express -- 1.77e13 -- which
is an upper bound and says nothing about what a game can reach. This walks the
game graph instead, so it is the number that actually prices a strong solve and
a df-pn search (TH-37).

Positions are deduplicated on the exact state (board, both hands, side to move),
packed into a 20-byte key. No hashing, so there is no collision tail and no
"probably": every count here is exact.

  scripts/census.py [max_ply]

The cost is the point, so it is reported. Python reaches ply 8 in seconds and
ply 9 in a couple of minutes; past that this needs to be a C program -- the
merge's C run reached ply 10 in 185s wall and 3.06 GB RSS at hashbits 27 with
16-byte keys, which is worth quoting WITH those parameters, since the same item
carried a "12 seconds, 1.8 GB" claim that did not reproduce.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import tinyhouse as T  # noqa: E402

# Plies 1 and 2 must equal perft 1 and 2, since nothing can transpose that
# early. Anything beyond is strictly below perft, and the gap is the point.
KNOWN = {1: 6, 2: 33, 3: 193, 4: 1220, 5: 7751, 6: 45979, 7: 291007,
         8: 1689902, 9: 9630829, 10: 49003553}


def key(pos):
    return bytes(pos.board) + bytes(pos.hands[0]) + bytes(pos.hands[1]) + bytes([pos.stm])


def census(max_ply):
    start = T.Position.start()
    frontier = {key(start): start.tfen()}
    seen = set(frontier)
    total = 1
    print(f"  {'ply':>3s} {'new':>12s} {'cumulative':>13s} {'growth':>7s} {'seconds':>8s}")
    print(f"  {0:>3d} {1:>12,} {1:>13,} {'-':>7s} {0.0:>8.1f}")
    prev = 1
    for ply in range(1, max_ply + 1):
        t0 = time.perf_counter()
        nxt = {}
        for tfen in frontier.values():
            pos = T.Position.from_tfen(tfen)
            for m in pos.legal_moves():
                pos.make(m)
                k = key(pos)
                if k not in seen:
                    seen.add(k)
                    nxt[k] = pos.tfen()
                pos.unmake()
        frontier = nxt
        total += len(frontier)
        flag = ""
        if ply in KNOWN:
            flag = "  OK" if len(frontier) == KNOWN[ply] else f"  MISMATCH (recorded {KNOWN[ply]:,})"
        print(f"  {ply:>3d} {len(frontier):>12,} {total:>13,} {len(frontier)/max(prev,1):>7.2f}"
              f" {time.perf_counter()-t0:>8.1f}{flag}", flush=True)
        prev = len(frontier)
        if not frontier:
            break
    return total


if __name__ == "__main__":
    max_ply = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    print(f"exact reachable census from {T.Position.start().tfen()}, to ply {max_ply}")
    total = census(max_ply)
    print(f"\n  cumulative distinct positions within {max_ply} plies: {total:,}")
    print("  compare: 17,669,515,462,968 syntactically expressible (scripts/state_count.py)")
