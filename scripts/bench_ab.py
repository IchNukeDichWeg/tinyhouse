"""Paired A/B benchmark for the C search: node counts and CPU time, arm vs arm.

bench_workers.py answers "how many threads", which is a different question.
This one answers "did this change to tinyhouse.c pay", and it is built around
the three things that make that measurable here:

- **Fresh process per repeat.** The thread-local history table carries over
  between in-process searches and moves node counts by up to 78% on its own
  (TH-19). th_clear_history() fixes that within a process, and a fresh process
  removes the question entirely.
- **Interleaved A/B/A/B, never blocked AAA/BBB.** This machine throttles; a
  blocked run aliases thermal drift straight into the result.
- **First repeat discarded**, medians and spread reported. A delta smaller than
  the spread is NULL, not a win.

Node identity is reported separately from time, because a change claiming to be
node-identical has that identity as its acceptance test, and a node count is
load-independent where a time is not.

  scripts/bench_ab.py --lib base=/tmp/libbase.dylib --lib new=../libtinyhouse.dylib \
      --work "hunt|fuwk/3p/P3/KWUF[-] w|16|0" --repeats 4

Build an arm with:  cc -O2 -pthread -shared -DTH_BUILD_ID=1 -o /tmp/libX.dylib x.c
"""
import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import tinyhouse as T  # noqa: E402


def load(lib_path):
    """One dylib per process. Two builds of the same library cannot share a
    loader: the second dlopen hands back whatever was loaded first."""
    import cffi

    ffi = cffi.FFI()
    ffi.cdef((ROOT / "engine_c.py").read_text().split('ffi.cdef("""')[1].split('""")')[0])
    lib = ffi.dlopen(lib_path)
    lib.th_init()
    return ffi, lib


def to_c(ffi, pos):
    pos.validate()
    c = ffi.new("THPos *")
    for i, pc in enumerate(pos.board):
        c.board[i] = pc
    for col in (0, 1):
        for t in range(4):
            c.hands[col][t] = pos.hands[col][t]
    c.stm = pos.stm
    return c


def child(lib_path, mode, tfen, depth, color, tt_bits, workers):
    ffi, lib = load(lib_path)
    lib.th_tt_init(tt_bits)
    try:
        lib.th_clear_history()
    except AttributeError:
        # an arm built before TH-19. Harmless here, since every repeat is its
        # own process and the table starts cold anyway.
        pass
    c = to_c(ffi, T.Position.from_tfen(tfen))
    bm, snd = ffi.new("uint16_t *"), ffi.new("int *")
    t0 = time.process_time()
    if mode == "hunt":
        v = lib.th_mate_hunt_mt(c, depth, color, workers, bm, snd)
    elif mode == "solve":
        v = lib.th_solve_mt(c, depth, workers, bm, snd)
    elif mode == "perft":
        # th_perft does NOT feed the g_nodes counter (TH-31), and its return
        # value IS the leaf count, so use it directly rather than reporting 0.
        v = lib.th_perft(c, depth)
        return {"value": v, "nodes": v, "cpu": time.process_time() - t0, "best": None}
    else:
        sys.exit(f"unknown mode {mode!r}")
    # CPU time, not wall clock: it is the one that does not move when something
    # else on the machine wakes up.
    return {"value": v, "nodes": lib.th_nodes(), "cpu": time.process_time() - t0,
            "best": T.move_str(bm[0]) if bm[0] else None}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", action="append", required=True, metavar="NAME=PATH")
    ap.add_argument("--work", action="append", required=True,
                    metavar="MODE|TFEN|DEPTH|COLOR", help="mode is hunt, solve or perft")
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument("--tt", type=int, default=22)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--child", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args()

    if a.child:
        print(json.dumps(child(*json.loads(a.child))))
        sys.exit(0)

    arms = [x.split("=", 1) for x in a.lib]
    for w in a.work:
        mode, tfen, depth, color = w.split("|")
        print(f"\n=== {mode} d{depth} color{color}  {tfen}\n    tt 2^{a.tt}, "
              f"{a.workers} worker(s), {a.repeats} repeats (first discarded), interleaved ===")
        samples = {n: [] for n, _ in arms}
        seen = {n: set() for n, _ in arms}
        for r in range(a.repeats):
            for name, path in arms:              # A/B/A/B, not AAA/BBB
                arg = json.dumps([path, mode, tfen, int(depth), int(color), a.tt, a.workers])
                out = subprocess.run([sys.executable, __file__, "--lib", "x=x", "--work", "x|x|0|0",
                                      "--child", arg], capture_output=True, text=True)
                if out.returncode:
                    sys.exit(out.stderr)
                got = json.loads(out.stdout)
                seen[name].add((got["value"], got["nodes"], got["best"]))
                if r:
                    samples[name].append(got["cpu"])
        base = None
        for name, _ in arms:
            cpu = samples[name]
            med, spread = statistics.median(cpu), (max(cpu) - min(cpu)) / statistics.median(cpu) * 100
            nodes = {n for _, n, _ in seen[name]}
            rel = f"  x{base / med:.3f}" if base else "  (baseline)"
            base = base or med
            print(f"  {name:14s} value {sorted({v for v, _, _ in seen[name]})}  "
                  f"nodes {min(nodes):>13,}{'' if len(nodes) == 1 else ' VARIES'}  "
                  f"cpu {med:7.3f}s  spread {spread:4.1f}%{rel}")
        allnodes = set().union(*({n for _, n, _ in seen[k]} for k, _ in arms))
        print(f"  node identity across arms: {'YES' if len(allnodes) == 1 else 'NO ' + str(sorted(allnodes))}")
        if len(arms) == 2 and len(samples[arms[0][0]]) >= 2:
            a_med, b_med = (statistics.median(samples[n]) for n, _ in arms)
            worst = max((max(s) - min(s)) / statistics.median(s) * 100 for s in samples.values())
            delta = (a_med / b_med - 1) * 100
            print(f"  delta {delta:+.1f}%  worst spread {worst:.1f}%  -> "
                  f"{'NULL (delta is inside the spread)' if abs(delta) <= worst else 'signal'}")
