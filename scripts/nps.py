#!/usr/bin/env python3
"""nps.py -- the house speed instrument. Builds its own arms; you name a change.

    scripts/nps.py --toggle TT_MIN_PROBE_DEPTH=1,2
    scripts/nps.py --rev HEAD~1                    # that rev vs the working tree
    scripts/nps.py --rev 85edfc7 --rev HEAD
    scripts/nps.py --null                          # the instrument against itself

WHY THIS EXISTS, given bench_ab.py already measures
---------------------------------------------------
bench_ab.py is correct and stays: fresh process per repeat, interleaved arms,
first repeat discarded, a same-build control arm. What it does NOT do is build
the arms, and that is where the mistakes live. Every measurement in the TT
campaign needed a scratch directory, a hand-written sed, two `cc` lines and a
`--lib name=path` for each arm, and remembering to pass the SAME dylib twice so
there was a control at all. Forget the control and the run still prints a
confident percentage.

This wraps it. Name a toggle or a revision, get arms built, a control implied,
and a verdict that refuses to be read when the box was busy.

WHAT IT ADDS TO THE PROTOCOL
----------------------------
* PAIRED RATIOS, not medians of absolutes. bench_ab takes median(A) and
  median(B) and divides. Here A and B run back to back and the RATIO is the
  sample, so thermal drift inside a pair cancels instead of landing in one
  arm's median. Borrowed from Pygin's nps13.py, which is the same instrument
  for the same job on a chess engine.

* A SIGN TEST on those ratios. bench_ab reports a spread; a spread does not say
  whether the direction is real. This prints how many ratios favoured B and the
  two-sided binomial p.

* --repeat, and the BETWEEN-RUN spread as the floor. This is the load-bearing
  one and it is not intuitive: a tight within-run spread and p=0.001 do NOT
  license a small claim. Pygin measured one unchanged build against the same
  baseline at +0.06% and then +0.23%, both internally clean, p=0.720 and
  p=0.001 -- the instrument was being asked a finer question than it can
  answer. Anything priced under the observed between-run spread is not
  decidable, and more rounds do not fix it.

* A METRIC THAT FOLLOWS THE NODE COUNTS. If the arms search identical trees the
  question is nps. If they do not -- TT_MIN_PROBE_DEPTH searches 7% more nodes
  and is 19.5% faster -- nps is the wrong judge and the answer is time to
  depth. The tool decides this from the measurement instead of trusting the
  operator to remember, and says which one it used.

* A LOAD GUARD. Two readings in the TT campaign were taken on a box at load
  average 9 with another agent running, and both were wrong in the flattering
  direction: a change that removes memory traffic looks better under memory
  contention. One of them read +45% for something worth +20%. The guard reads
  the load before and after and refuses the verdict when it moved.

CHOOSING THE DEPTH -- the search must dominate the measurement
--------------------------------------------------------------
Measured on this machine, one worker, tt 2^24, hunt from the start position:

    depth 14   0.20s      depth 17   5.70s
    depth 15   0.62s      depth 18  10.68s
    depth 16   1.36s

Default is 16: the shortest that clears ~1s, so thread spin-up, the table
allocation and the first-touch page faults cannot be what is being ranked.
Escalate deliberately -- a bigger effect needs less instrument:

    priced > 5%      depth 16, rounds 9              ~30s
    priced 1-5%      depth 17, rounds 16 --repeat 3  ~10 min
    priced < 1%      depth 18, rounds 16 --repeat 3  ~20 min, and read the floor

AT --workers > 1 THE QUESTION CHANGES, and the tool changes with it. Lazy SMP
helpers duplicate work, so more nps can mean less search; the metric becomes
time to depth and varying node counts stop being a warning. Threads also finish
the same tree sooner, so raise the depth with them -- roughly +2 plies per
doubling -- or the ratio measures which helper won the race.
"""
import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from math import comb
from pathlib import Path

ROOT = Path(__file__).parent.parent
BENCH_AB = Path(__file__).parent / "bench_ab.py"
CFLAGS = ["-O2", "-pthread", "-shared"]
START = "fuwk/3p/P3/KWUF[-] w"

# The regression suite's positions, which already exist and already cover the
# shapes that matter: drop-heavy, promotion, mao check, a published mate.
# A single-position speed claim is a claim about one tree.
SUITE = [
    "fuwk/3p/P3/KWUF[-] w",          # start
    "f1w1/2k1/K2p/W1UF[Up] b",       # ply-budget repro
    "1k2/4/2K1/4[PFUWpfuw] w",       # drop-heavy: eight pieces in hand
    "1uwk/P3/3p/K2F[UWf] w",         # promotion and hands in play
]


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def source_for_rev(rev):
    r = sh(["git", "show", f"{rev}:tinyhouse.c"], cwd=ROOT)
    if r.returncode:
        sys.exit(f"cannot read tinyhouse.c at {rev}:\n{r.stderr}")
    return r.stdout


def source_with_toggle(src, name, value):
    """Rewrite `#define NAME <anything>` to the given value.

    Fails loudly on no match. A silent no-op here would build two identical
    arms and report a NULL, which reads exactly like a change that did not
    pay -- the worst possible failure for this tool.
    """
    pat = re.compile(rf"^#define {re.escape(name)}\b.*$", re.M)
    out, n = pat.subn(f"#define {name} {value}", src)
    if n != 1:
        sys.exit(f"--toggle {name}: expected exactly one '#define {name}' in "
                 f"tinyhouse.c, found {n}")
    return out


def build(src, path):
    csrc = path.with_suffix(".c")
    csrc.write_text(src)
    r = sh(["cc", *CFLAGS, "-DTH_BUILD_ID=1ULL", "-o", str(path), str(csrc)])
    if r.returncode:
        sys.exit(f"build failed for {path.name}:\n{r.stderr}")
    return path


def run_one(lib, mode, tfen, depth, color, tt, workers):
    """One search in its own interpreter, via bench_ab's child protocol.

    Reusing that child rather than reimplementing it keeps ONE measurement
    path in the repo: two harnesses that agree until they quietly do not is
    how the same change gets two verdicts.
    """
    arg = json.dumps([str(lib), mode, tfen, depth, color, tt, workers])
    r = sh([sys.executable, str(BENCH_AB), "--lib", "x=x", "--work", "x|x|0|0", "--child", arg])
    if r.returncode:
        sys.exit(f"child failed:\n{r.stderr}")
    return json.loads(r.stdout)


def sign_test(ratios):
    """Two-sided binomial p for 'B is not different from A'."""
    n = sum(1 for x in ratios if x != 1.0)
    k = sum(1 for x in ratios if x > 1.0)
    if not n:
        return k, n, 1.0
    tail = min(k, n - k)
    p = 2.0 * sum(comb(n, i) for i in range(tail + 1)) / (2.0 ** n)
    return k, n, min(1.0, p)


def one_pass(arms, works, rounds, tt, workers, quiet):
    """Interleaved A/B/A/B. Returns (ratios, nodes_by_arm, seconds_by_arm)."""
    # Node counts are tracked PER WORK ITEM, not pooled. Pooling them across a
    # suite makes four different positions look like a node-count difference,
    # which mislabels every suite run as node-changing.
    ratios = []
    nodes = {n: {w: set() for w in range(len(works))} for n, _ in arms}
    secs = {n: [] for n, _ in arms}
    for r in range(rounds):
        for wi, (mode, tfen, depth, color) in enumerate(works):
            cell = {}
            # ALTERNATE the order inside the pair. Running A first every time
            # is a systematic bias, not a wash: whichever arm goes second
            # inherits a warm page cache and a warm memory allocator. Caught by
            # a null run of this very tool, which read +0.79% with 7 of 8
            # ratios favouring B on two byte-identical builds. Back-to-back
            # cancels drift; alternating cancels position.
            order = arms if r % 2 == 0 else arms[::-1]
            for name, lib in order:
                got = run_one(lib, mode, tfen, depth, color, tt, workers)
                cell[name] = got
                nodes[name][wi].add(got["nodes"])
                secs[name].append(got["cpu"])
            if r == 0:
                continue                                 # first round pays the page faults
            a, b = arms[0][0], arms[1][0]
            if cell[b]["cpu"] > 0:
                ratios.append(cell[a]["cpu"] / cell[b]["cpu"])
        if not quiet:
            print(f"    round {r + 1}/{rounds}", end="\r", flush=True, file=sys.stderr)
    return ratios, nodes, secs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--toggle", metavar="NAME=A,B",
                    help="build two arms from one #define in tinyhouse.c")
    ap.add_argument("--rev", action="append", default=[], metavar="REV",
                    help="git revision of tinyhouse.c; give once (vs working tree) or twice")
    ap.add_argument("--null", action="store_true",
                    help="the working tree against itself: measures the instrument's own floor")
    ap.add_argument("--depth", type=int, default=16)
    ap.add_argument("--tt", type=int, default=24)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--color", type=int, default=0)
    ap.add_argument("--rounds", type=int, default=9, help="first is always discarded")
    ap.add_argument("--repeat", type=int, default=1,
                    help="whole passes; the spread BETWEEN them is the resolution floor")
    ap.add_argument("--suite", action="store_true",
                    help="four positions in solve mode instead of the start-position hunt")
    ap.add_argument("--tfen", default=START)
    ap.add_argument("--keep", action="store_true", help="keep the built arms and print the paths")
    a = ap.parse_args()

    live = (ROOT / "tinyhouse.c").read_text()
    tmp = Path(tempfile.mkdtemp(prefix="nps-"))
    if a.null:
        label = ("working tree", "working tree (same build)")
        srcs = (live, live)
    elif a.toggle:
        name, _, vals = a.toggle.partition("=")
        va, _, vb = vals.partition(",")
        if not vb:
            sys.exit("--toggle needs two values, e.g. --toggle NAME=0,1")
        label = (f"{name}={va}", f"{name}={vb}")
        srcs = (source_with_toggle(live, name, va), source_with_toggle(live, name, vb))
    elif a.rev:
        if len(a.rev) == 1:
            label = (a.rev[0], "working tree")
            srcs = (source_for_rev(a.rev[0]), live)
        else:
            label = (a.rev[0], a.rev[1])
            srcs = (source_for_rev(a.rev[0]), source_for_rev(a.rev[1]))
    else:
        sys.exit("give --toggle, --rev or --null")

    if srcs[0] == srcs[1] and not a.null:
        print("NOTE: the two arms are byte-identical. This is a null run.", file=sys.stderr)

    arms = [("A", build(srcs[0], tmp / "A.dylib")), ("B", build(srcs[1], tmp / "B.dylib"))]
    works = ([("solve", t, a.depth, a.color) for t in SUITE] if a.suite
             else [("hunt", a.tfen, a.depth, a.color)])

    print(f"A = {label[0]}")
    print(f"B = {label[1]}")
    print(f"work: {'suite of 4, solve' if a.suite else 'hunt ' + a.tfen}, depth {a.depth}, "
          f"tt 2^{a.tt}, {a.workers} worker(s)")
    print(f"      {a.rounds} rounds x {a.repeat} pass(es), first round of each discarded")
    load0 = os.getloadavg()[0]

    passes = []
    for i in range(a.repeat):
        ratios, nodes, secs = one_pass(arms, works, a.rounds, a.tt, a.workers, a.repeat == 1)
        if not ratios:
            sys.exit("no ratios collected; --rounds must be at least 2")
        passes.append((statistics.median(ratios), ratios, nodes, secs))
        if a.repeat > 1:
            print(f"  pass {i + 1}: x{passes[-1][0]:.4f}")
    load1 = os.getloadavg()[0]

    med = statistics.median(p[0] for p in passes)
    all_ratios = [x for p in passes for x in p[1]]
    k, n, pval = sign_test(all_ratios)
    _, _, nodes, secs = passes[-1]
    na, nb = nodes["A"], nodes["B"]
    identical = all(len(na[w]) == 1 and na[w] == nb[w] for w in na)
    varies = any(len(na[w]) > 1 or len(nb[w]) > 1 for w in na)
    tot_a = sum(min(na[w]) for w in na)
    tot_b = sum(min(nb[w]) for w in nb)
    per_search = statistics.median(secs["A"])

    print()
    print(f"nodes  A {tot_a:,}   B {tot_b:,}"
          + ("   (summed over the suite)" if len(na) > 1 else "")
          + ("   VARIES run to run" if varies else ""))
    if identical:
        metric = "nps (node-identical: same tree, so speed is the whole story)"
    elif a.workers > 1:
        metric = "time to depth (lazy SMP: node counts vary by design, nps would mislead)"
    else:
        metric = ("TIME TO DEPTH -- node counts DIFFER, so this is NOT an nps figure. "
                  f"B searches {tot_b / tot_a - 1:+.1%} nodes")
    print(f"metric {metric}")
    print(f"median x{med:.4f}  = {(med - 1) * 100:+.2f}%     "
          f"({len(all_ratios)} ratios, {k}/{n} favour B, sign test p={pval:.3g})")

    if a.repeat > 1:
        mids = [p[0] for p in passes]
        spread = (max(mids) - min(mids)) * 100
        sd = statistics.stdev(mids) * 100 if len(mids) > 2 else float("nan")
        print(f"floor  between-pass spread {spread:.2f}pp"
              + (f", SD {sd:.2f}pp" if len(mids) > 2 else "")
              + "   <- anything smaller than this is not decidable here")
        verdict = "signal" if abs(med - 1) * 100 > spread else "NULL (inside the floor)"
    else:
        print("floor  UNMEASURED -- one pass. Re-run with --repeat 3 before claiming "
              "anything under ~2%.")
        verdict = "signal" if pval < 0.05 else "NULL (sign test)"

    warn = []
    if per_search < 1.0:
        warn.append(f"each search took only {per_search:.2f}s: below ~1s the ratio "
                    f"measures setup, not the engine. Raise --depth.")
    if max(load0, load1) > 2.0:
        warn.append(f"load average {load0:.1f} -> {load1:.1f}: the box was busy. Memory "
                    f"contention flatters changes that cut memory traffic. Re-run idle.")
    if a.workers > 1 and a.repeat < 3:
        warn.append("--workers > 1 without --repeat 3: at these thread counts a single "
                    "pass cannot see its own floor.")

    print(f"VERDICT {(med - 1) * 100:+.2f}% -> {verdict}")
    for w in warn:
        print(f"  WARNING: {w}")
    if warn:
        print("  ^ treat the number above as provisional until these are cleared.")

    if a.keep:
        print(f"arms kept in {tmp}")
    else:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
