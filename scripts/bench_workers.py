"""Find the best --workers for solve_hunt on THIS machine at THE DEPTH you
actually intend to run. Built for a fresh box (rented or otherwise) as much as
for a laptop: run it once before committing a long hunt to a worker count.

SMP scaling is depth-dependent: at shallow depths helpers mostly duplicate
work and perturb move ordering, while deeper searches give the shared
transposition table more chance to pay off. A number measured at depth 18
does not predict depth 24, so measure at your target depth before committing
a long run to a worker count.

  scripts/bench_workers.py --depth 20 --workers 1,2,4,6,8 --repeats 3
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

WARMUP: one untimed rep per arm is run and thrown away before the timed ones.
Measured here (M2 Pro, cold process, 2 workers, depth 16, 5 successive reps in
one process): 1.488s / 1.392s / 1.968s / 1.532s / 1.450s -- no clear first-rep
penalty on THIS machine, because th_tt_init frees and reallocates the table on
EVERY rep, so first-touch cost recurs each time rather than concentrating in
rep 1. The spread (1.39-1.97s) is bigger than any first-rep effect would be.
The warmup is kept anyway for a case that machine did not test: a genuinely
COLD one, a rented box seconds after boot, where the CPU governor has not
reached its sustained clock and the allocator has not yet warmed its free
lists at all. That mechanism is real and well known; it just was not the
dominant noise source in the process above. Cheap insurance, not a proven fix
here -- said plainly rather than dressed up as measured.

IDLE CHECK: refuses to start if solve_hunt.py, server.py or another
bench_workers.py is already running (this project has hit exactly that before:
a benchmark competing with a live hunt read 715 knps against a clean ~4 Mnps),
or if the 1-minute load average already exceeds half the machine's cores.
--force skips both checks.

Cost warning: one run at depth d costs roughly what solve_hunt.py spends on
that depth, times len(workers) times (repeats + 1) -- the +1 is the warmup.
"""
import argparse
import os
import statistics
import subprocess
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
ap.add_argument("--force", action="store_true", help="skip the idle-machine check")
args = ap.parse_args()


def idle_check():
    if args.force:
        return
    try:
        out = subprocess.run(["pgrep", "-fl", "solve_hunt.py|server.py|bench_workers.py"],
                             capture_output=True, text=True, timeout=5).stdout
    except Exception:
        out = ""
    others = [line for line in out.splitlines() if str(os.getpid()) not in line.split()[0]]
    if others:
        sys.exit("another solve_hunt.py, server.py or bench_workers.py is running "
                 "-- it will compete for cores and the numbers below will be wrong:\n  "
                 + "\n  ".join(others) + "\nstop it first, or pass --force to proceed anyway")
    try:
        load1 = os.getloadavg()[0]
        cores = os.cpu_count() or 1
        if load1 > cores * 0.5:
            sys.exit(f"1-minute load average is {load1:.1f} on a {cores}-core machine "
                     f"-- something else is using it. Close other apps, or pass --force.")
    except (OSError, AttributeError):
        pass    # no getloadavg on this platform; the pgrep check still ran


idle_check()

bm = E.ffi.new("uint16_t *")
snd = E.ffi.new("int *")
pos = T.Position.from_tfen(args.tfen)


def one_hunt(bits, workers):
    if E.lib.th_tt_init(bits) != 0:
        sys.exit(f"could not allocate a 2^{bits}-entry table; use a smaller size")
    E.lib.th_clear_history()               # a cold history table too (TH-19)
    n0 = E.lib.th_nodes()
    t0 = time.perf_counter()
    v = E.lib.th_mate_hunt_mt(E.to_c(pos), args.depth, args.color, workers, bm, snd)
    return time.perf_counter() - t0, E.lib.th_nodes() - n0, v


if args.tt_sweep:
    print(f"depth {args.depth}, color {args.color}, workers {args.workers.split(',')[0]}, "
          f"{args.repeats} repeats each (+1 warmup, discarded)")
    print("nodes are load-independent and are the honest column here; time is not,"
          " on a machine with anything else running\n")
    w = int(args.workers.split(",")[0])
    for bits in [int(b) for b in args.tt_sweep.split(",")]:
        one_hunt(bits, w)                  # warmup, discarded
        times, nodes, fills = [], [], []
        for _ in range(args.repeats):
            dt, n, v = one_hunt(bits, w)
            times.append(dt); nodes.append(n)
            fills.append(E.lib.th_tt_fill() / (1 << bits))
        print(f"tt 2^{bits:<2d} ({(1 << bits) * 16 / 2**30:6.2f} GiB)  "
              f"median nodes {statistics.median(nodes):>15,.0f}  "
              f"occupancy {statistics.median(fills):6.1%}  "
              f"median {statistics.median(times):8.1f}s  value {v}")
    print("\nPick on time at YOUR depth: the node curve flattens long before the "
          "time curve does.")
    sys.exit(0)

counts = [int(w) for w in args.workers.split(",")]
print(f"depth {args.depth}, color {args.color}, tt 2^{args.tt}, "
      f"{args.repeats} repeats each (+1 warmup, discarded), arms INTERLEAVED")
print("machine checked idle; medians are what count\n")

# Arms are interleaved -- one rep of every worker count, then the next rep --
# rather than finishing one arm before starting the next. A sweep at a real
# depth runs for many minutes, and anything that drifts over that window
# (thermal throttling, another process starting, Spotlight waking up) would
# otherwise land entirely on whichever arms happened to run during it. This is
# the same discipline bench_ab.py uses; without it the outer-loop order is
# itself a variable.
for w in counts:
    one_hunt(args.tt, w)                   # warmup per arm, discarded
times = {w: [] for w in counts}
nodes = {w: [] for w in counts}
value = None
for rep in range(args.repeats):
    for w in counts:
        dt, n, v = one_hunt(args.tt, w)
        times[w].append(dt); nodes[w].append(n)
        value = v
    print(f"  rep {rep + 1}/{args.repeats}: "
          + "  ".join(f"{w}w {times[w][-1]:.1f}s" for w in counts), flush=True)

print()
best = None
base = statistics.median(times[counts[0]])
for w in counts:
    med = statistics.median(times[w])
    spread = (max(times[w]) - min(times[w])) / med * 100 if med else 0
    # nodes in full, not rounded to meganodes: "{n/1e6:8.0f}M" printed "1M"
    # for everything from 500k to 1.5M, which is exactly the range these depths
    # land in, and nodes are the load-independent metric here.
    print(f"workers {w:2d}  median {med:7.1f}s  spread {spread:4.1f}%  "
          f"speedup x{base / med:5.2f}  median nodes {statistics.median(nodes[w]):>14,.0f}")
    if best is None or med < best[1]:
        best = (w, med)
print(f"\nbest at depth {args.depth}: --workers {best[0]} ({best[1]:.1f}s median, "
      f"x{base / best[1]:.2f} over {counts[0]} worker(s)); value {value}")
print("re-measure if you move to a materially deeper target depth.")
