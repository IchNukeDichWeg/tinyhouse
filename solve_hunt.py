"""Deep null-window mate hunt from a position, for one color, with live
progress, resume, and multi-core lazy SMP.

  solve_hunt.py <color: 0=white 1=black> [--workers N] [--maxdepth D]
                [--tt BITS] [--tfen TFEN] [--seed S] [--state FILE] [--fresh]

A value > 29000 at depth d proves a forced win for that color, at exactly the
distance it reports; anything else proves there is no forced win within d
plies (total plies). Two things make the budget exact, not one: the search has
no extensions, AND a TT cutoff carrying a mate deeper than the depth remaining
at that node is refused (TT_BUDGET_GUARD in tinyhouse.c). Without that guard
the claim was simply false - a cold depth-12 hunt reported "mate in 15".

RESUME: progress is checkpointed to --state (default solve_state/<hash>.json)
after every completed depth, and the transposition table is dumped alongside
it. Re-running the same command picks up at the first unproven depth and
reloads the table, so an interrupted run costs at most the depth it died in.
--fresh ignores any checkpoint. Ctrl-C is safe and leaves a usable checkpoint.

There is no honest overall ETA: the proof depth, if one exists, is unknown.
The ETA shown covers the current depth only. It comes from MEASURED_NODES --
the node counts of completed passes -- rescaled to whatever this run is
actually costing, and falls back to the growth factor between the last two
depths only where no measurement exists.

WORKERS: defaults to 1, because lazy SMP is nondeterministic - helpers
perturb move ordering, so the same depth run twice gives different node counts
(820 and 807 on one shallow depth). The proofs do not depend on the thread
count; the reproducibility of the recorded node counts does.
Scaling here is DEPTH-DEPENDENT, and the direction REVERSES between depth 18
and depth 20. Apple M2 Pro, 10 cores, fresh table and cleared history per run:

  depth 18 (3 repeats, medians): 1w 27.8s · 2w 28.4s · 3w 51.7s · 4w 49.7s
  depth 20 (1 sample per arm):   1w 164.6s · 2w 88.5s · 4w 87.5s
                                 6w 66.1s · 8w 88.8s

So at 18 anything past 2 threads regresses hard, and at 20 six threads are
2.49x faster than one. Helpers duplicate work either way - the depth-20
six-thread run costs 1.42G nodes against 682M for one thread - but past depth
18 the wall clock wins anyway, presumably because the shared table stops being
mostly empty. Depth 20 predicting depth 26 is still an extrapolation; measure
at your own target depth with scripts/bench_workers.py before a long run.

The PROOFS do not depend on the thread count (test_solver.py pins that workers
1, 2 and 4 reach the same proof). The reproducibility of the node counts does,
which is why the default is 1.
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

# Grow the table when occupancy crosses this, checked between depths (the SMP
# helpers are joined there, so the rehash runs single-threaded). Growth is +2
# bits per step, capped at --tt. Measured motivation: an oversized table costs
# real time at shallow depths (d16 ran 2.21s at 2^20 against 2.61s at 2^27),
# and a right-sized start also means --tt is a CAP rather than an upfront
# multi-GiB allocation.
TT_GROW_AT = 0.80


def gib(b):
    """Sizes span 16 MiB to 32 GiB, so a fixed GiB format prints "0.0 GiB" for
    a table that is very much not zero."""
    return f"{b / 2**30:.2f} GiB" if b >= 2**30 else f"{b / 2**20:.0f} MiB"

ap = argparse.ArgumentParser()
ap.add_argument("color", type=int, choices=(0, 1), help="0 = White win hunt, 1 = Black")
# Default 1, not 2 (TH-05). Lazy SMP is NONDETERMINISTIC by construction --
# helpers perturb move ordering -- so a multi-worker run cannot reproduce its
# own node count, let alone anyone else's: two runs of the same shallow depth
# gave 820 and 807 nodes. One and two workers tie within noise at depth 18
# (median 27.8s vs 28.4s), so determinism costs nothing measured. The PROOFS
# never depended on this; only the node counts do.
ap.add_argument("--workers", type=int, default=1, help="lazy SMP threads; >1 makes node counts nondeterministic. Measure with scripts/bench_workers.py, scaling is depth-dependent")
ap.add_argument("--maxdepth", type=int, default=40)
ap.add_argument("--tt", type=int, default=26, help="log2 TT entries CAP (26 = 1 GiB, 27 = 2 GiB); the table starts at --tt-start and grows toward this")
ap.add_argument("--tt-start", type=int, default=20,
                help="log2 of the initial table; it grows when occupancy crosses TT_GROW_AT")
ap.add_argument("--tfen", default="fuwk/3p/P3/KWUF[-] w")
ap.add_argument("--seed", type=lambda x: int(x, 0), default=0,
                help="Zobrist seed; re-run a proof under a second seed to rule "
                     "out a 64-bit key collision having faked it")
ap.add_argument("--state", default=None, help="checkpoint path (default solve_state/<hash>.json)")
ap.add_argument("--force-tt", action="store_true", help="skip the memory sanity check on --tt")
ap.add_argument("--fresh", action="store_true", help="ignore any existing checkpoint")
ap.add_argument("--no-tt-dump", action="store_true",
                help="record proven depths but never write the table dump. The dump is "
                     "the SAME SIZE as the table, written once per completed depth, so a "
                     "2^31 run writes 32 GiB each time. Resuming then re-searches the "
                     "current depth from an empty table, which is the right trade for "
                     "tests and short runs.")
ap.add_argument("--tt-growth", choices=("jump", "step"), default="jump",
                help="with >1 worker, whether the first growth goes straight to --tt "
                     "(jump, default) or sizes to the projection (step). See maybe_grow_tt.")
args = ap.parse_args()

def gib(n):
    """Bytes as a human size. GiB rounds to nothing below a gigabyte, and these
    messages are read when someone is deciding whether a run will fit."""
    return f"{n / 2**30:.1f} GiB" if n >= 2**30 else f"{n / 2**20:.0f} MiB"


# TH-44: a jump-mode run ends at --tt regardless, so growing INTO it is pure
# loss. Growth costs target+held at peak (2^30 -> 2^31 peaks at 48 GiB against
# the 32 GiB the table actually needs), it can be refused when the same size
# would have been fine up front, and a refusal then STRANDS the run at whatever
# intermediate it stepped down to -- a Black hunt reached 2^30 that way and
# could never afford 2^31 afterwards. Allocating the cap before anything is
# held costs 32 GiB flat, the floor.
#
# What it gives up is TH-39's finding that an oversized table costs time at
# shallow depths (d16 ran 2.21s at 2^20 against 2.61s at 2^27). Depths 6-16
# together are under a second of a multi-hour run, so that is ~0.2s against a
# failure mode that cost a whole depth-28 attempt. Only for jump mode: stepping
# is the measured choice at one worker and it sizes to the projection anyway.
def start_bits_for(args):
    if args.workers > 1 and args.tt_growth == "jump" and args.tt_start < args.tt:
        cap = (1 << args.tt) * 16
        # Starting at the cap must clear the SAME memory bar growing into it
        # does, or this trades a refusal for an allocation that swaps the
        # machine -- and --force-tt bypasses check_tt_size, so nothing else
        # stops a 256 GiB request here. When it does not fit, fall back to
        # --tt-start and let maybe_grow_tt step down as it always did.
        free = free_bytes()
        if free and cap > free * 0.9:
            return args.tt_start, (f"cannot start at the 2^{args.tt} cap: it needs "
                                   f"{gib(cap)} against ~{gib(free)} free. Starting at "
                                   f"2^{args.tt_start} and growing instead, which may "
                                   f"end below the cap")
        return args.tt, (f"starting at the 2^{args.tt} cap ({gib(cap)}): jump mode ends "
                         f"there regardless, and growing into it later would peak at "
                         f"{gib(cap + cap // 2)} and can be refused outright")
    return args.tt_start, None


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
_start_bits, _why = start_bits_for(args)
if _why:
    print(_why, flush=True)
tt_bits_now = min(max(_start_bits, 12), args.tt)
if E.lib.th_tt_init(tt_bits_now) != 0:
    sys.exit(f"could not allocate a 2^{tt_bits_now}-entry table "
             f"({(1 << tt_bits_now) * 16 // 2**20} MiB). Use a smaller --tt-start.")


def maybe_grow_tt(growth, next_depth):
    """Between depths only: the helpers are joined, so the rehash is safe.

    Sizes for the NEXT depth, not the one that just finished: entries grow by
    roughly the same factor as nodes, so the projection is fill x growth, and
    the table is grown until that projection sits at or under half. Reactive
    growth was measured to lag -- a depth run on a table that saturated
    mid-search cost 11.0M nodes against 9.6M on one sized for it.
    """
    global tt_bits_now
    fill = E.lib.th_tt_fill()
    occ = fill / (1 << tt_bits_now)
    line = f"          tt 2^{tt_bits_now} | {fill:,} entries | {occ:.0%} full"
    projected = fill * growth
    want_bits = tt_bits_now
    while want_bits < args.tt and projected > 0.5 * (1 << want_bits):
        want_bits += 1
    if (want_bits > tt_bits_now or occ >= TT_GROW_AT) and tt_bits_now < args.tt:
        # Multi-worker runs jump STRAIGHT to the cap on the first trigger.
        # Measured at 6 workers: stepped growth reached the same final size but
        # drew ~28% more nodes at depth 20 (median 1.41G vs 1.10G over 8 runs
        # each), because entries lost to replacement in the intermediate tables
        # are exactly what stops lazy-SMP helpers duplicating work. Single
        # worker measured no such cost, so stepping stays for workers 1.
        #
        # That justification is STALE and --tt-growth exists to retest it. It
        # was taken at 6 workers, not the 16 now used, and it reasons about
        # which entries replacement discards -- which is precisely what the
        # 4-way bucketed table changed. Blind overwrite and depth-preferred
        # replacement do not lose the same entries. The cost of jumping also
        # scales with the cap: at --tt 31 the first growth puts depths 16-20 on
        # a 32 GiB table at under 7% occupancy, paying full memory latency for
        # capacity nothing uses until depth 24. Default stays `jump` until a
        # measurement at 16 workers on the bucketed build says otherwise.
        if args.workers > 1 and args.tt_growth == "jump":
            want_bits = args.tt
        new_bits = min(max(want_bits, tt_bits_now + 1), args.tt)
        # Step DOWN to the largest size that fits rather than refusing to grow.
        # Refusing outright is catastrophic, not conservative: a Black hunt with
        # 35.3 GiB free missed a 32.0 GiB target by 0.2 GiB and stayed at the
        # 2^20 START size, then searched depth 24 through a 16 MiB table and
        # drew 101.91G nodes where the same depth costs 24.5G on a right-sized
        # one. 2^30 would have fitted with 19 GiB to spare.
        free = free_bytes()
        capped = new_bits
        while free and (1 << new_bits) * 16 > free * 0.9 and new_bits > tt_bits_now:
            new_bits -= 1
        # th_tt_grow holds BOTH tables live across the rehash, so the figure
        # that matters is a NEW allocation of the target size ON TOP of the
        # current one, not the difference between them. Reporting "needs 32.0
        # GiB" while 16.0 GiB is already held reads as a total and invites the
        # reasonable objection that only 16 more are wanted. Peak is spelled out.
        held = (1 << tt_bits_now) * 16
        tgt = (1 << capped) * 16
        cost = (f"a new {gib(tgt)} block alongside the live {gib(held)} "
                f"({gib(tgt + held)} peak)")
        if new_bits <= tt_bits_now:
            print(line + f" | 2^{capped} needs {cost}, only ~{gib(free)} free,"
                  f" and no smaller size beats 2^{tt_bits_now}; STAYING PUT."
                  f" Growing early avoids this: --tt-start {capped} allocates it once,"
                  f" up front, while the table is still empty.", flush=True)
            return
        # Not printed here: the grow line below reports the size actually taken,
        # and two GREW claims for one growth read as two growths.
        capped_note = ""
        if new_bits < capped:
            capped_note = (f" | 2^{capped} wanted {cost}, only ~{gib(free)} free,"
                           f" so this may strand the run below 2^{capped}")
        want = (1 << new_bits) * 16
        t0 = time.perf_counter()
        if E.lib.th_tt_grow(new_bits) != 0:
            print(line + f" -- growth to 2^{new_bits} failed to allocate; "
                  f"staying at 2^{tt_bits_now}", flush=True)
            return
        kept = E.lib.th_tt_fill()
        print(line + f" | GREW to 2^{new_bits} ({gib((1 << new_bits) * 16)})"
              f" for depth {next_depth} | {kept:,} entries carried over in "
              f"{time.perf_counter() - t0:.1f}s" + capped_note, flush=True)
        tt_bits_now = new_bits
    else:
        print(line + (f" | cap 2^{args.tt}" if tt_bits_now < args.tt else " | at cap")
              + f" | sized for depth {next_depth}", flush=True)

# Everything that changes what a completed depth MEANS. `build` is the engine
# fingerprint: "no forced win through depth 20" is a claim about the code that
# proved it, so a checkpoint must not be inherited across a source edit.
IDENT_KEYS = ("tfen", "color", "seed", "tt_bits", "build")
state = {"tfen": args.tfen, "color": args.color, "seed": args.seed, "tt_bits": args.tt,
         "build": E.lib.th_build_id(),
         "tt_bits_now": tt_bits_now,
         "proven_no_win_through": 0, "result": None, "depths": []}
if state_path.exists() and not args.fresh:
    loaded = json.loads(state_path.read_text())
    differs = [k for k in IDENT_KEYS if loaded.get(k) != state[k]]
    if not differs:
        state = loaded
        # the table may have grown before the checkpoint: reopen at that size
        tt_bits_now = min(state.get("tt_bits_now", args.tt), args.tt)
        if E.lib.th_tt_init(tt_bits_now) != 0:
            sys.exit(f"could not allocate the checkpoint's 2^{tt_bits_now}-entry table")
        rc = E.lib.th_tt_load(str(tt_path).encode())
        print(f"resumed from {state_path}: no win through depth "
              f"{state['proven_no_win_through']}, "
              + {0: "table reloaded", -1: "no table dump (re-searching)",
                 -2: "table dump size or seed mismatched (ignored)",
                 -3: "table dump is from a different engine build (ignored)"}[rc])
    else:
        print(f"checkpoint {state_path} differs in {', '.join(differs)}; starting fresh")

pos = E.to_c(T.Position.from_tfen(args.tfen))
bm = E.ffi.new("uint16_t *")
hunt_snd = E.ffi.new("int *")
name = "WHITE" if args.color == 0 else "BLACK"
tty = sys.stdout.isatty()


# The progress JSON is written FIRST and on purpose: a proven depth is the
# expensive result and must survive even if the table dump cannot be written.
# The dump only saves re-searching it.
last_save_ok = True


def save_state():
    """Record the proven depths, and dump the table unless asked not to.

    The dump is the same size as the TABLE, not the search: a 2^31 run writes
    32 GiB per completed depth. That is worth it for a multi-hour hunt, where
    re-searching a depth costs more than the write. It is never worth it for a
    test -- and the slow tests deliberately drive absurd --tt values, so one of
    them wrote a 256 GiB dump to a pytest tmpdir before this existed.
    """
    global last_save_ok
    state_path.write_text(json.dumps(state, indent=2))
    if args.no_tt_dump:
        last_save_ok = False
        return
    rc = E.lib.th_tt_save(str(tt_path).encode())
    last_save_ok = rc == 0
    if not last_save_ok:
        print(f"  WARNING: could not write the table dump to {tt_path}. Every "
              f"proven depth is still recorded in {state_path}, but resuming "
              f"will re-search the current depth from an empty table.", flush=True)


def seed_advice(depth):
    """TH-06: the second-seed re-run is for the NEGATIVE bounds too.

    The horizon-unsoundness and ply-budget arguments are both directional, so
    neither can turn a real mate into a "no win". A 64-bit Zobrist collision
    has no directional structure at all: it substitutes an unrelated position's
    value, and in the hunt window a colliding TT_UPPER entry with v <= alpha
    prunes a subtree that may hold a real mate. The risk is HIGHER here than
    for the wins, on two counts - the negative runs are the high-node-count
    ones, and any low-valued colliding entry suffices, whereas a false positive
    needs a collision that happens to hold a mate score.
    """
    if args.seed:
        return f"  (already under seed {args.seed:#x}; agreement across seeds is the check)"
    return ("  a 64-bit Zobrist collision could have pruned a subtree holding a real"
            " mate. Re-run under a second seed to make the two collision sets"
            " independent:\n"
            f"  python solve_hunt.py {args.color} --tt {args.tt} "
            f"--maxdepth {depth} --seed 0xC0FFEE --fresh")


def advise_on_bound():
    """Print the second-seed advice for the deepest NEGATIVE bound reached.

    At the end of the run, not per depth: the command it prints has to name the
    depth actually being trusted.
    """
    if state["result"] is None and state["proven_no_win_through"]:
        print(f"  bound so far: no forced {name} win within "
              f"{state['proven_no_win_through']} plies", flush=True)
        print(seed_advice(state["proven_no_win_through"]), flush=True)


def on_sigint(sig, frm):
    if last_save_ok:
        print("\ninterrupted; checkpoint is current, re-run the same command to resume")
    else:
        print("\ninterrupted; the last table dump FAILED to write (see the warning "
              "above), so resuming re-searches from the last depth that saved")
    advise_on_bound()
    sys.exit(130)


signal.signal(signal.SIGINT, on_sigint)

print(f"hunting forced {name} win from {args.tfen}")
print(f"workers {args.workers}, tt 2^{tt_bits_now} entries "
      f"({(1 << tt_bits_now) * 16 // 2**20} MiB, growing toward cap 2^{args.tt})"
      + (f", zobrist seed {args.seed:#x}" if args.seed else "")
      + f", state {state_path}", flush=True)

prev_nodes = state["depths"][-1]["nodes"] if state["depths"] else None
growth = 8.0
if len(state["depths"]) >= 2:
    growth = max(state["depths"][-1]["nodes"] / max(state["depths"][-2]["nodes"], 1), 2.0)


# Node counts from one completed pass of each colour: 16 workers, tt 2^31,
# seed 0, on the build of 2026-08-28. These exist because the growth ratio is
# NOT smooth and extrapolating from it fails exactly where it matters. White
# ran x4.7, x3.6, x4.3, x3.9 for four straight transitions and then broke
# x8.5 at depth 28; Black did the same thing at the same depth. An estimate
# built from the previous ratio called depth 28 at 416.51G, so the run read
# "36% done" while sitting at 633G and under a quarter of the way. That number
# is the one a person uses to decide whether to wait or kill a run.
#
# NOT reproducible to the digit. Lazy SMP makes node counts vary run to run,
# and they move with worker count, table size, seed and any search change. The
# table supplies the SHAPE of the curve; estimate_nodes rescales it on the
# deepest depth this run and the table share, so a run that is 30% heavier
# than the table gets a 30% heavier prediction. Extend it when a depth
# completes rather than deriving new entries by arithmetic.
MEASURED_NODES = {
    0: {6: 6_258, 8: 24_792, 10: 118_634, 12: 694_895, 14: 5_106_380,
        16: 25_426_785, 18: 185_673_747, 20: 1_515_326_418, 22: 6_203_192_837,
        24: 27_175_129_261, 26: 106_389_944_366, 28: 720_270_063_779},
    1: {6: 1_012, 8: 3_341, 10: 20_726, 12: 133_967, 14: 847_243,
        16: 5_652_828, 18: 48_484_866, 20: 188_823_771, 22: 1_206_789_405,
        24: 11_602_010_099, 26: 24_576_885_226, 28: 210_033_942_206,
        30: 762_410_631_416},
}


def estimate_nodes(color, depth, depths_done, growth):
    """Nodes the depth about to run will cost, or None at the first depth.

    Three sources, best first. A measured count for this colour and depth,
    rescaled by what this run has actually cost at the deepest shared depth.
    Failing that, the OTHER colour's ratio across the same transition, which
    is what would have caught the depth-28 step: both colours take it, and
    neither colour's own history predicts it. Failing that, the previous
    growth factor, which is where this started.
    """
    done = {e["depth"]: e["nodes"] for e in depths_done}
    prev = done.get(depth - 2)
    table = MEASURED_NODES.get(color, {})
    if depth in table:
        shared = [d for d in done if d in table and table[d] > 0]
        scale = done[max(shared)] / table[max(shared)] if shared else 1.0
        return table[depth] * scale
    other = MEASURED_NODES.get(1 - color, {})
    if prev and depth in other and other.get(depth - 2):
        return prev * (other[depth] / other[depth - 2])
    return prev * growth if prev else None


def fmt(n):
    for u, d in (("G", 1e9), ("M", 1e6), ("k", 1e3)):
        if n >= d:
            return f"{n/d:.2f}{u}"
    return str(int(n))


# TH-43: size the table for the depth about to run, not the one that ended.
# maybe_grow_tt was called ONLY at the tail of the depth loop, so a resumed run
# reopened at the checkpoint's tt_bits_now and walked straight into the next
# depth without ever reconsidering it. That turned a one-off growth refusal
# into a permanent one: a Black hunt refused 2^31 by 0.2 GiB, checkpointed
# tt_bits_now=20, and every later resume inherited the 16 MiB table -- depth 24
# passed 164G nodes still searching through it, and the step-down fix could not
# help because nothing on the resume path calls it.
#
# Sizing here also covers the case the growth policy was never asked about: a
# machine that has since freed memory, or a --tt raised between runs.
if state["depths"]:
    maybe_grow_tt(growth, state["proven_no_win_through"] + 2)
    state["tt_bits_now"] = tt_bits_now

start_depth = max(6, state["proven_no_win_through"] + 2)
def progress_line(d, n, nps, dt, est):
    """One live progress line for the depth in flight.

    Once the run passes its estimate the line says SO, rather than clamping to
    "99% ... eta ~0m" and holding there. The old form did exactly that for over
    a thousand seconds on a Black hunt whose estimate was 5x low, which reads
    as "nearly done" when the truth is "this estimate is worthless". A wrong
    ETA is worse than no ETA: it is the one number a person uses to decide
    whether to wait or kill the run.

    The estimate comes from estimate_nodes, so it is a rescaled measurement
    where one exists and a guess otherwise -- a table that saturates mid-depth
    still breaks it, which is precisely when the run is slowest and the ETA
    matters most.
    """
    line = f"depth {d:2d}  RUNNING  {fmt(n)} nodes | {fmt(nps)}nps | {dt:.0f}s"
    if not est:
        return line
    if n < est:
        return line + f" | ~{n/est*100:.0f}% of est {fmt(est)} | eta ~{(est-n)/max(nps,1)/60:.0f}m"
    return line + f" | PAST est {fmt(est)} by {n/est:.1f}x | eta unknown"


for d in range(start_depth, args.maxdepth + 1, 2):
    t0 = time.perf_counter()
    n0 = E.lib.th_nodes()
    est = estimate_nodes(args.color, d, state["depths"], growth)
    done = threading.Event()
    result = {}

    def run():
        result["v"] = E.lib.th_mate_hunt_mt(pos, d, args.color, args.workers, bm, hunt_snd)
        result["snd"] = hunt_snd[0]
        done.set()

    th = threading.Thread(target=run, daemon=True)
    th.start()
    while not done.wait(2.0 if tty else 20.0):
        n = E.lib.th_nodes() - n0
        dt = time.perf_counter() - t0
        nps = n / max(dt, 1e-9)
        print("\r" + progress_line(d, n, nps, dt, est) + "  ",
              end="" if tty else "\n", flush=True)
    th.join()
    dt = time.perf_counter() - t0
    n = E.lib.th_nodes() - n0
    if prev_nodes:
        growth = max(n / max(prev_nodes, 1), 2.0)
    prev_nodes = n
    v = result["v"]
    if tty:
        print("\r" + " " * 118, end="\r")
    # The old layout printed stats, then the table line, then the verdict, so a
    # depth's ANSWER landed two lines below its heading with unrelated sizing
    # output in between; and a finished depth read "depth 22" while the running
    # one read "d24", which made them hard to tell apart while scrolling. Now
    # the verdict is on the heading, both states share the "depth NN" prefix,
    # and DONE/RUNNING says which.
    verdict = (f"{name} FORCES A WIN in {30000 - v} plies" if v > 29000
               else f"no forced {name} win within {d} plies")
    print(f"depth {d:2d}  DONE     {verdict}", flush=True)
    print(f"          {n:,} nodes | {dt:.1f}s | {fmt(n/max(dt,1e-9))}nps"
          f" | growth x{growth:.1f} | best {T.move_str(bm[0]) if bm[0] else '-'}", flush=True)
    state["depths"].append({"depth": d, "value": v, "nodes": n, "seconds": round(dt, 1)})
    if v > 29000:
        # TH-34: the one self-consistency check the discarded flags made
        # impossible. A root fail-high above MATE_BOUND must carry SND_LB in
        # the winner's frame. Only on THIS branch: the negative branch is
        # flag-free by design, and asserting anything there would fire at every
        # depth of every real hunt.
        if not (result["snd"] & 1):
            sys.exit(f"INTERNAL: depth {d} reported a forced win ({v}) whose root "
                     f"result carries no lower-bound soundness flag (snd={result['snd']}). "
                     f"That contradicts the search's own invariants; do not trust this run.")
        state["result"] = {"proven": f"{name} forces a win", "plies": 30000 - v, "depth": d}
        save_state()
        print("          checkpointed", flush=True)
        print(seed_advice(d), flush=True)
        break
    state["proven_no_win_through"] = d
    maybe_grow_tt(growth, d + 2)
    state["tt_bits_now"] = tt_bits_now
    save_state()
    print("          " + ("checkpointed" if last_save_ok
                          else "depth recorded, table dump skipped (--no-tt-dump)"
                          if args.no_tt_dump
                          else "WARNING: progress recorded, no table dump"), flush=True)

advise_on_bound()
