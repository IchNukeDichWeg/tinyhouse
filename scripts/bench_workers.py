"""Find the best --workers for solve_hunt on THIS machine at THE DEPTH you
actually intend to run.

SMP scaling is depth-dependent: at shallow depths helpers mostly duplicate
work and perturb move ordering, while deeper searches give the shared
transposition table more chance to pay off. A number measured at depth 18
does not predict depth 24, so measure at your target depth before committing
a long run to a worker count.

  scripts/bench_workers.py --depth 20 --workers 1,2,4 --repeats 2

Each run uses a fresh transposition table so runs cannot seed each other.
Cost warning: one run at depth d costs roughly what solve_hunt.py spends on
that depth, times len(workers) times repeats.
"""
import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import engine_c as E  # noqa: E402
import tinyhouse as T  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--depth", type=int, default=18)
ap.add_argument("--workers", default="1,2,4", help="comma-separated worker counts")
ap.add_argument("--repeats", type=int, default=3)
ap.add_argument("--color", type=int, default=0, choices=(0, 1))
ap.add_argument("--tt", type=int, default=24)
ap.add_argument("--tfen", default="fuwk/3p/P3/KWUF[-] w")
args = ap.parse_args()

bm = E.ffi.new("uint16_t *")
pos = T.Position.from_tfen(args.tfen)
counts = [int(w) for w in args.workers.split(",")]
print(f"depth {args.depth}, color {args.color}, tt 2^{args.tt}, {args.repeats} repeats each")
print("run this on an otherwise idle machine; medians are what count\n")
best = None
for w in counts:
    times, nodes = [], []
    for _ in range(args.repeats):
        E.lib.th_tt_init(args.tt)          # fresh table: no cross-run seeding
        c = E.to_c(pos)
        n0 = E.lib.th_nodes()
        t0 = time.perf_counter()
        v = E.lib.th_mate_hunt_mt(c, args.depth, args.color, w, bm)
        times.append(time.perf_counter() - t0)
        nodes.append(E.lib.th_nodes() - n0)
    med = statistics.median(times)
    spread = max(times) - min(times)
    print(f"workers {w:2d}  median {med:7.1f}s  spread {spread:6.1f}s  "
          f"median nodes {statistics.median(nodes)/1e6:8.0f}M  value {v}")
    if best is None or med < best[1]:
        best = (w, med)
print(f"\nbest at depth {args.depth}: --workers {best[0]} ({best[1]:.1f}s median)")
print("re-measure if you move to a materially deeper target depth.")
