"""Deep null-window mate hunt from a position, for one color, with live
progress, resume, and multi-core lazy SMP.

  solve_hunt.py <color: 0=white 1=black> [--workers N] [--maxdepth D]
                [--tt BITS] [--tfen TFEN] [--seed S] [--state FILE] [--fresh]

A value > 29000 at depth d proves a forced win for that color; anything else
proves there is no forced win within d plies (total plies - there are no
search extensions, so the ply budget is exact).

RESUME: progress is checkpointed to --state (default solve_state/<hash>.json)
after every completed depth, and the transposition table is dumped alongside
it. Re-running the same command picks up at the first unproven depth and
reloads the table, so an interrupted run costs at most the depth it died in.
--fresh ignores any checkpoint. Ctrl-C is safe and leaves a usable checkpoint.

There is no honest overall ETA: the proof depth, if one exists, is unknown.
The ETA shown covers the current depth only, extrapolated from the measured
growth factor between the last two completed depths.

WORKERS: lazy SMP scaling here is DEPTH-DEPENDENT and only measured shallow.
At depth 18 on an Apple M2 Pro (10 cores, 3 repeats, fresh table per run) 1
and 2 threads tie within noise (median 27.8s vs 28.4s) and 3+ regresses
badly (52s, 50s) - helpers duplicate work and perturb move ordering in a
null-window proof search. Deeper searches plausibly scale better as the
shared table fills, but that is UNMEASURED: do not extrapolate depth 18 to
depth 24. Measure at your target depth with scripts/bench_workers.py before
committing a long run.
"""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import engine_c as E
import tinyhouse as T

ap = argparse.ArgumentParser()
ap.add_argument("color", type=int, choices=(0, 1), help="0 = White win hunt, 1 = Black")
ap.add_argument("--workers", type=int, default=2, help="lazy SMP threads; measure with scripts/bench_workers.py, scaling is depth-dependent")
ap.add_argument("--maxdepth", type=int, default=40)
ap.add_argument("--tt", type=int, default=26, help="log2 TT entries (26 = 1 GiB, 27 = 2 GiB)")
ap.add_argument("--tfen", default="fuwk/3p/P3/KWUF[-] w")
ap.add_argument("--seed", type=lambda x: int(x, 0), default=0,
                help="Zobrist seed; re-run a proof under a second seed to rule "
                     "out a 64-bit key collision having faked it")
ap.add_argument("--state", default=None, help="checkpoint path (default solve_state/<hash>.json)")
ap.add_argument("--force-tt", action="store_true", help="skip the memory sanity check on --tt")
ap.add_argument("--fresh", action="store_true", help="ignore any existing checkpoint")
args = ap.parse_args()

def check_tt_size(bits):
    """Bound the table against physical RAM BEFORE allocating.

    calloc cannot be trusted for this: macOS and default-configured Linux
    overcommit, so a wildly oversized request returns a valid pointer and the
    process then grows without bound as the search touches pages, taking the
    machine down with it. Overnight runs must not be able to do that.
    """
    want = (1 << bits) * 16
    total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    safe_bits = (total // 2 // 16).bit_length() - 1     # largest table <= half of RAM
    if want > total // 2 and not args.force_tt:
        sys.exit(f"--tt {bits} wants {want / 2**30:.1f} GiB, over half of this "
                 f"machine's {total / 2**30:.0f} GiB of RAM. The allocation would "
                 f"appear to succeed (this OS overcommits) and then swap the "
                 f"machine to death as the search touches pages.\n"
                 f"Largest safe value here is --tt {safe_bits} "
                 f"({(1 << safe_bits) * 16 / 2**30:.0f} GiB); --force-tt overrides.")
    free = free_bytes()
    print(f"table {want / 2**30:.2f} GiB of {total / 2**30:.0f} GiB RAM"
          + (f", ~{free / 2**30:.1f} GiB currently free" if free else ""), flush=True)
    if free and want > free * 0.8:
        print(f"  WARNING: the table is close to or above currently free memory. "
              f"Overnight this will swap and throughput will collapse. "
              f"Consider --tt {bits - 1} ({(1 << (bits-1)) * 16 / 2**30:.1f} GiB) "
              f"or closing other apps.", flush=True)


def free_bytes():
    """Free + inactive (reclaimable) memory, or 0 if it cannot be determined."""
    try:
        out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5).stdout
        page = int(out.split("page size of ")[1].split(" ")[0])
        vals = {}
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                vals[k.strip()] = v.strip().rstrip(".")
        return (int(vals["Pages free"]) + int(vals["Pages inactive"])) * page
    except Exception:
        return 0


# checkpoint identity: everything that changes what a depth result MEANS
ident = hashlib.sha1(
    f"{args.tfen}|{args.color}|{args.seed}|{args.tt}".encode()).hexdigest()[:12]
state_path = Path(args.state) if args.state else Path("solve_state") / f"{ident}.json"
tt_path = state_path.with_suffix(".tt")
state_path.parent.mkdir(parents=True, exist_ok=True)

if args.seed:
    E.lib.th_seed(args.seed)
check_tt_size(args.tt)
if E.lib.th_tt_init(args.tt) != 0:
    sys.exit(f"could not allocate a 2^{args.tt}-entry table "
             f"({(1 << args.tt) * 16 // 2**20} MiB). Use a smaller --tt.")

state = {"tfen": args.tfen, "color": args.color, "seed": args.seed, "tt_bits": args.tt,
         "proven_no_win_through": 0, "result": None, "depths": []}
if state_path.exists() and not args.fresh:
    loaded = json.loads(state_path.read_text())
    if all(loaded.get(k) == state[k] for k in ("tfen", "color", "seed", "tt_bits")):
        state = loaded
        rc = E.lib.th_tt_load(str(tt_path).encode())
        print(f"resumed from {state_path}: no win through depth "
              f"{state['proven_no_win_through']}, "
              + {0: "table reloaded", -1: "no table dump (re-searching)",
                 -2: "table dump mismatched (ignored)"}[rc])
    else:
        print(f"checkpoint {state_path} is for a different run; starting fresh")

pos = E.to_c(T.Position.from_tfen(args.tfen))
bm = E.ffi.new("uint16_t *")
name = "WHITE" if args.color == 0 else "BLACK"
tty = sys.stdout.isatty()


def save_state():
    state_path.write_text(json.dumps(state, indent=2))
    E.lib.th_tt_save(str(tt_path).encode())


def on_sigint(sig, frm):
    print("\ninterrupted; checkpoint is current, re-run the same command to resume")
    sys.exit(130)


signal.signal(signal.SIGINT, on_sigint)

print(f"hunting forced {name} win from {args.tfen}")
print(f"workers {args.workers}, tt 2^{args.tt} entries ({(1 << args.tt) * 16 // 2**20} MiB)"
      + (f", zobrist seed {args.seed:#x}" if args.seed else "")
      + f", state {state_path}", flush=True)

prev_nodes = state["depths"][-1]["nodes"] if state["depths"] else None
growth = 8.0
if len(state["depths"]) >= 2:
    growth = max(state["depths"][-1]["nodes"] / max(state["depths"][-2]["nodes"], 1), 2.0)


def fmt(n):
    for u, d in (("G", 1e9), ("M", 1e6), ("k", 1e3)):
        if n >= d:
            return f"{n/d:.2f}{u}"
    return str(int(n))


start_depth = max(6, state["proven_no_win_through"] + 2)
for d in range(start_depth, args.maxdepth + 1, 2):
    t0 = time.perf_counter()
    n0 = E.lib.th_nodes()
    est = prev_nodes * growth if prev_nodes else None
    done = threading.Event()
    result = {}

    def run():
        result["v"] = E.lib.th_mate_hunt_mt(pos, d, args.color, args.workers, bm)
        done.set()

    th = threading.Thread(target=run, daemon=True)
    th.start()
    while not done.wait(2.0 if tty else 20.0):
        n = E.lib.th_nodes() - n0
        dt = time.perf_counter() - t0
        nps = n / max(dt, 1e-9)
        line = f"  d{d}  {fmt(n)} nodes  {fmt(nps)}nps  {dt:6.0f}s"
        if est:
            line += (f"  ~{min(n/est,0.99)*100:2.0f}% of est {fmt(est)}"
                     f"  eta ~{max(est-n,0)/max(nps,1)/60:.0f}m")
        print("\r" + line + "  ", end="" if tty else "\n", flush=True)
    th.join()
    dt = time.perf_counter() - t0
    n = E.lib.th_nodes() - n0
    if prev_nodes:
        growth = max(n / max(prev_nodes, 1), 2.0)
    prev_nodes = n
    v = result["v"]
    if tty:
        print("\r" + " " * 110, end="\r")
    print(f"depth {d:2d}  value {v:6d}  best {T.move_str(bm[0]) if bm[0] else '-':6s}"
          f"  nodes {n:>15,}  {dt:8.1f}s  {fmt(n/max(dt,1e-9))}nps  growth x{growth:.1f}", flush=True)
    state["depths"].append({"depth": d, "value": v, "nodes": n, "seconds": round(dt, 1)})
    if v > 29000:
        state["result"] = {"proven": f"{name} forces a win", "plies": 30000 - v, "depth": d}
        save_state()
        print(f"PROVEN: {name} forces a win in {30000 - v} plies", flush=True)
        if not args.seed:
            print("  re-verify under a second Zobrist seed before trusting it:\n"
                  f"  python solve_hunt.py {args.color} --workers {args.workers} "
                  f"--tt {args.tt} --maxdepth {d} --seed 0xC0FFEE --fresh", flush=True)
        break
    state["proven_no_win_through"] = d
    save_state()
    print(f"  => no forced {name} win within {d} plies (proven, checkpointed)", flush=True)
