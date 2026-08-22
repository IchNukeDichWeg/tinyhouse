"""Find the best --workers for solve_hunt on THIS machine at THE DEPTH you
actually intend to run.

SMP scaling is depth-dependent: at shallow depths helpers mostly duplicate
work and perturb move ordering, while deeper searches give the shared
transposition table more chance to pay off. A number measured at depth 18
does not predict depth 24, so measure at your target depth before committing
a long run to a worker count.

  scripts/bench_workers.py --depth 20 --workers 1,2,4 --repeats 2
  scripts/bench_workers.py --depth 20 --tt-sweep 20,22,24,26 --repeats 2

TT SIZE (TH-39): the --tt default was never measured at the depth it is used
at. The nodes-to-depth curve flattens early -- past 2^20 at depth 16 -- but that
is the wrong reason to lower it, because what a bigger table buys at depth is
throughput, not fewer nodes: at depth 18 a 91.7%-full 2^22 table took 216.6s
against 100.3s for 2^24 on the same work. --tt-sweep reports nodes, occupancy
and time per size so the decision is made at the depth actually being run.

Each run uses a fresh transposition table AND clears the thread-local history
table, so runs cannot seed each other. That second half is not optional: the
history table used to carry over, and five repeats of an identical depth-13
hunt measured 757,431 / 839,298 / 845,107 / 1,345,672 / 795,066 in one process
against 757,431 five times in five separate processes. The damage lands
BETWEEN arms, not within them: this script loops worker counts in the outer
position, so the first worker count was the only arm that ever contained a
cold-history sample, and helper threads are always cold - the contamination was
asymmetric between the workers=1 and workers>1 arms, which is the exact
comparison this script exists to make.

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
ap.add_argument("--tt-sweep", default=None, help="comma-separated log2 sizes; sweeps --tt instead of --workers")
ap.add_argument("--tfen", default="fuwk/3p/P3/KWUF[-] w")
args = ap.parse_args()

bm = E.ffi.new("uint16_t *")
snd = E.ffi.new("int *")
pos = T.Position.from_tfen(args.tfen)

if args.tt_sweep:
    print(f"depth {args.depth}, color {args.color}, workers {args.workers.split(',')[0]}, "
          f"{args.repeats} repeats each")
    print("nodes are load-independent and are the honest column here; time is not,"
          " on a machine with anything else running\n")
    w = int(args.workers.split(",")[0])
    for bits in [int(b) for b in args.tt_sweep.split(",")]:
        times, nodes, fills = [], [], []
        for _ in range(args.repeats):
            if E.lib.th_tt_init(bits) != 0:
                sys.exit(f"could not allocate a 2^{bits}-entry table")
            E.lib.th_clear_history()
            n0 = E.lib.th_nodes()
            t0 = time.perf_counter()
            v = E.lib.th_mate_hunt_mt(E.to_c(pos), args.depth, args.color, w, bm, snd)
            times.append(time.perf_counter() - t0)
            nodes.append(E.lib.th_nodes() - n0)
            fills.append(E.lib.th_tt_fill() / (1 << bits))
        print(f"tt 2^{bits:<2d} ({(1 << bits) * 16 / 2**30:6.2f} GiB)  "
              f"median nodes {statistics.median(nodes):>15,.0f}  "
              f"occupancy {statistics.median(fills):6.1%}  "
              f"median {statistics.median(times):8.1f}s  value {v}")
    print("\nPick on time at YOUR depth: the node curve flattens long before the "
          "time curve does.")
    sys.exit(0)

counts = [int(w) for w in args.workers.split(",")]
print(f"depth {args.depth}, color {args.color}, tt 2^{args.tt}, {args.repeats} repeats each")
print("run this on an otherwise idle machine; medians are what count\n")
best = None
for w in counts:
    times, nodes = [], []
    for _ in range(args.repeats):
        if E.lib.th_tt_init(args.tt) != 0:   # fresh table: no cross-run seeding
            sys.exit(f"could not allocate a 2^{args.tt}-entry table; use a smaller --tt")
        E.lib.th_clear_history()             # ...and a cold history table (TH-19)
        c = E.to_c(pos)
        n0 = E.lib.th_nodes()
        t0 = time.perf_counter()
        v = E.lib.th_mate_hunt_mt(c, args.depth, args.color, w, bm, E.ffi.NULL)
        times.append(time.perf_counter() - t0)
        nodes.append(E.lib.th_nodes() - n0)
    med = statistics.median(times)
    spread = max(times) - min(times)
    # nodes in full, not rounded to meganodes: "{n/1e6:8.0f}M" printed "1M"
    # for everything from 500k to 1.5M, which is exactly the range these depths
    # land in, and nodes are the load-independent metric here.
    print(f"workers {w:2d}  median {med:7.1f}s  spread {spread:6.1f}s  "
          f"median nodes {statistics.median(nodes):>14,.0f}  value {v}")
    if best is None or med < best[1]:
        best = (w, med)
print(f"\nbest at depth {args.depth}: --workers {best[0]} ({best[1]:.1f}s median)")
print("re-measure if you move to a materially deeper target depth.")
