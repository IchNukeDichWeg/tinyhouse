# Tinyhouse

A rules engine, solver and web GUI for the chess.com variant
[Tinyhouse](https://chess-variants.fandom.com/wiki/Tinyhouse). It is crazyhouse on a
4x4 board: King, Ferz, Wazir, Xiangqi Horse and one Pawn a side, promotion forced to
F/U/W, and the stalemated player wins. [RULES.md](RULES.md) has the full rules and
where each one came from.

## Layout

| File | What |
|---|---|
| `tinyhouse.py` | Python rules engine (movegen, make/unmake, hands, TFEN, perft) |
| `tinyhouse.c` | C hot path: mailbox + uint16-bitboard movegen, the search, a df-pn engine |
| `engine_c.py` | cffi (ABI) wrapper; auto-builds `libtinyhouse.dylib` with `cc` |
| `server.py` + `index.html` | Local web GUI, stdlib only |
| `solve_hunt.py` | Deep one-colour forced-win hunt from the start position |
| `solve_status.json` | The proven bounds, also shown in the GUI |
| `scripts/build_book.py` | Precompute analyses near the start into `analysis.sqlite` |
| `scripts/state_count.py` | Exact syntactic state-space count |
| `scripts/census.py` | Exact count of positions reachable from the start, by ply |
| `scripts/dfpn.py` | Python df-pn reference, and the drivers for the C engine |
| `scripts/regress.py` | Paired nodes-to-depth and solver-digest regression harness |
| `scripts/nps.py` | **Speed instrument.** Name a toggle or a revision, it builds both arms and measures |
| `scripts/bench_ab.py` | The A/B engine underneath it: fresh process per repeat, interleaved arms |
| `scripts/bench_workers.py` | Pick `--workers` and `--tt` by measuring at your depth |
| `CAMPAIGN.md`, `SCOREBOARD.md` | Every backlog item, its verdict, and the measurement behind it |

## Setup and tests

```bash
python3 -m venv .venv && .venv/bin/pip install pytest cffi
```

```bash
.venv/bin/python -m pytest -q
```

Three of the tests take seconds rather than milliseconds, the draw proof below being
one of them, so they sit behind a marker and are skipped by default. `pytest -q -m
slow` runs only those, and `pytest -q -m ""` runs everything.

## GUI

```bash
.venv/bin/python server.py 8653
```

Open <http://127.0.0.1:8653/>. Click or drag to move, click a hand piece and then a
square to drop, and promotions open a picker. Setup mode lets you edit the board,
the hands and the side to move. Analyses are cached in `analysis.sqlite`, which you
can query directly with `sqlite3 analysis.sqlite 'SELECT json FROM analysis'`.

## What is proven

The game is not solved. `solve_status.json` has the machine-readable version; in
short, there is no forced White win within **28** plies (861.8G nodes) and no forced
Black win within **30** plies (1,010.1G nodes). The value of the game is still open,
and consistent with a draw.

Forced wins are proven and displayed when they fall inside the horizon. The sharpest
one is that `1.Fd1-c2??` loses outright:
`1...Uxc2 2.Wb2 F@a3 3.Wxc2 dxc2 4.U@b3 Kd3 5.Uxd2 W@b1#`, mate in 9.

Two results here need a second engine, because alpha-beta cannot reach them at all.
Its horizon returns an unsound 0, so "no win" is the absence of a proof rather than a
proof. The df-pn engine in `tinyhouse.c` produces a positive disproof that White has
any forced win after `1.Fd1-c2`. And a draw can be proven outright, which was thought
out of reach: bare kings (`2K1/4/4/2k1[-] w`) come back at depth 100 as `value 0,
snd 3`, an exact game value. What was missing was depth, not a cleverer position. The
only terminal-free component within reach is the 312-state bare-kings one and its
lines are long.

The bounds are proof-grade rather than heuristic. The search returns an unsound 0 at
the horizon and sound values only at terminals and repetitions, so any mate score it
reports is a proof, and a null-window hunt that returns 0 proves no win exists inside
that budget. The solver comment block in `tinyhouse.c` also says what rep-safety does
not cover: it keeps path-dependent values out of the table, but the reuse side is
unguarded.

The two claims are not equally strong. A reported mate proves the win and, since the
ply-budget guard, the distance it names. A "no forced win within N plies" bound is
immune to horizon unsoundness, to a transposition-table cutoff overrunning its
budget, and to store-side graph-history interaction, but not to a 64-bit Zobrist
collision. A collision has no directional structure and could prune a subtree holding
a real mate. That residual is unquantified rather than zero, which is why re-running
under a second seed matters for the bounds as much as for the wins.

## Measuring a speed change

```bash
.venv/bin/python scripts/nps.py --toggle TT_MIN_PROBE_DEPTH=1,2
```

Builds both arms from `tinyhouse.c`, runs them paired and interleaved with the
order alternating, discards the first round, and reports the median ratio with a
sign test. `--rev HEAD~1` compares a revision against the working tree; `--null`
measures the instrument against itself, which is the only way to learn what it
can actually resolve.

It picks the metric from the measurement rather than from the operator: arms
that search identical trees are judged on nps, arms that do not are judged on
**time to depth** and told so. That distinction is not cosmetic -- the depth-1
probe gate searches 7% more nodes and is 20% faster, and reading it as nps gets
the sign of the conclusion wrong.

Two habits worth keeping. Anything priced under ~2% needs `--repeat 3`, and the
spread BETWEEN passes is the floor -- a tight within-run spread and a small p do
not license a small claim. And the tool warns when the load average was above 2:
memory contention flatters changes that cut memory traffic, which is how one
reading in this repo came in at +45% for something worth +20%.

## Pushing the bounds deeper

`solve_hunt.py` prints live nodes, nps and elapsed time with a per-depth ETA, plus one
summary line per completed depth.

```bash
.venv/bin/python solve_hunt.py 0 --tt 31 --workers 16 --maxdepth 28
```

```bash
.venv/bin/python solve_hunt.py 1 --tt 31 --workers 16 --maxdepth 30
```

Run them one after the other; two concurrent 16-worker hunts would oversubscribe
even an 18-core machine.

Measured, White from the start position, 16 workers, on an 18-core M5 Pro. Three
runs of the same command across three engine builds, one run each, not medians:

| depth | 18 | 20 | 22 | 24 | 26 | 28 | whole run |
|---|---|---|---|---|---|---|---|
| direct-mapped, `--tt 30` | 3.6s | 24.3s | 133.1s | 1990.2s | - | - | 128.6G / **35.9 min** |
| 4-way bucketed, `--tt 30` | 4.4s | 25.4s | 119.6s | 548.5s | - | - | 37.8G / **11.6 min** |
| + horizon skip, `--tt 31` | 2.9s | 22.4s | 102.2s | 397.6s | 1747.6s | - | 137.9G / **37.9 min** |
| + ordering work, `--tt 31` | 2.5s | 20.0s | 85.7s | **402.6s** | **1523.1s** | **10231.6s** | 861.8G / **3.41 h** |

**Depth 24 is x4.94 faster than it was, on 4.38x fewer nodes.** The clearest way
to read the table is the last column: the original engine needed 35.9 minutes to
reach depth 24, and the current one reaches **depth 26** in 33.9. Two extra plies
for two fewer minutes.

Read the per-depth seconds across rows with care. Only the last two rows share a
table size, and only the last row ran with the table at its 2^31 cap from depth 6
rather than growing into it, which slows the early depths (a 32 GiB table at 0%
occupancy is all cold DRAM) and speeds the late ones. Depth 24 looks 1.3% SLOWER
in the last row for that reason while depth 26 is 12.8% faster on 1.3% more nodes
-- the honest per-node figure between those two rows is **+16.2% nps**, measured
at depth 26 where both had a saturated table.

Per-2-ply growth, which is what actually decides whether the next depth is
affordable:

| | d18 | d20 | d22 | d24 | d26 | d28 | d30 |
|---|---|---|---|---|---|---|---|
| direct-mapped, White | x7.4 | x6.8 | x5.6 | **x15.2** | - | - | - |
| current, White | x7.3 | x8.2 | x4.1 | x4.4 | x3.9 | **x6.8** | - |
| current, Black | x8.6 | x3.9 | x6.4 | x9.6 | x2.1 | **x8.5** | x3.6 |

The x15.2 was replacement thrashing at 100% occupancy, not tree growth, and
associativity removed it.

**Depth 28 is where the growth factor jumps, for BOTH colours, and neither
colour's own history predicts it.** White sat between x3.9 and x4.4 for three
straight transitions and then stepped x6.8; Black stepped x8.5 at the same
place. This is not a curiosity: `solve_hunt.py` used to build its per-depth ETA
from the previous growth factor, which called White's depth 28 at 416.51G
against an actual 720.27G, so the run reported "36% of est" while under a
quarter of the way through. It now estimates from `MEASURED_NODES` instead --
the counts in this table -- rescaled to what the live run is costing.

Both colours ran with the table 100% full from depth 26 (White) and 28 (Black)
onward, so capacity, not replacement policy, is now the binding constraint.
Depth 30 for White would want roughly 2.6T nodes at Black's x3.6 -- about 10
hours, on a table that has had nothing left to give for two plies.

`color 0` hunts a White forced win and `1` hunts Black. `--tt BITS` is log2 of a
CAP on transposition-table entries, so 28 caps at 4 GiB — see below; it is not an
upfront allocation. `--maxdepth D` stops early,
`--tfen` hunts from a position other than the start, and `--seed S` re-runs a proof
under different Zobrist keys.

It resumes. Every completed depth is checkpointed to `solve_state/` along with a dump
of the transposition table, so re-running the same command skips the depths already
proven and reloads the table. An interrupted run costs at most the depth it died in.
Ctrl-C is safe and leaves a usable checkpoint, and `--fresh` ignores one.

### Choosing --workers

The default is 1, because lazy SMP is not deterministic. Helpers perturb move
ordering, so the same depth run twice gives different node counts. The proofs never
depended on the thread count, but reproducing the recorded node counts does.

Scaling depends on depth AND on the machine, and both have changed under this
project — the worker numbers below were taken on two different boxes, so read the
machine column, not just the worker count.

On an 18-core Apple M5 Pro at depth 20, interleaved arms, three repeats (one
discarded as contaminated), `--tt 26`:

| workers | 1 | 4 | 6 | 8 | 12 | 16 |
|---|---|---|---|---|---|---|
| median | 113.8s | 57.5s | 52.4s | 55.1s | 48.7s | **47.1s** |
| speedup | — | ×2.0 | ×2.2 | ×2.1 | ×2.3 | **×2.4** |

Gains flatten past 12; 16 is marginally best. Nodes rise steeply with workers
(674M at one, 3.15G at sixteen) because helpers duplicate work — the wall clock
still wins, which is the whole bet of lazy SMP.

The older 10-core measurements below are kept because they show the effect that
matters: the direction reverses between 18 and 20 (M2 Pro, 10
cores):

| workers | depth 18 (medians of 3) | depth 20 (1 sample) |
|---|---|---|
| 1 | 27.8s | 164.6s |
| 2 | 28.4s | 88.5s |
| 4 | 49.7s | 87.5s |
| 6 | | 66.1s |
| 8 | | 88.8s |

Past two threads depth 18 regresses hard, while at depth 20 six threads are 2.49x
faster than one. The shared table has presumably stopped being mostly empty by then.
For a deep overnight run `--workers 6` is the measured choice, though depth 20
predicting depth 26 is still an extrapolation, so measure at your own target depth:

```bash
.venv/bin/python scripts/bench_workers.py --depth 22 --workers 1,2,4,6,8 --repeats 2
```

### Choosing --tt

`--tt` is a **cap**. The table starts at `--tt-start` (default 2^20) and grows
between depths, sized by projecting the next depth's fill from the measured
growth factor; each step rehashes every entry across (the key is recoverable
from `xkey ^ data`) and prints occupancy, the projection, entries carried and
the time. Growth is refused with a message when free memory will not cover it,
so a high cap is safe on a loaded machine — it only materializes if occupancy
earns it. With `--workers` above 1 the first growth jumps straight to the cap:
stepping through intermediate sizes measured ~28% more nodes at depth 20,
because entries lost to replacement in the smaller tables are exactly what
stops lazy-SMP helpers duplicating work.

What the cap protects against is running *saturated* below it: a 91.7%-full
table measured 216.6s against 100.3s for the next size up on the same work.
The other direction is free — interleaved measurement of an oversized table
(2^24 vs 2^27 at depth 20) is within noise, so there is no penalty for capping
high. That retires most of the old hand-tuning; the sweep below remains for
checking the growth policy's choices at your real depth:

```bash
.venv/bin/python scripts/bench_workers.py --depth 20 --tt-sweep 22,24,26,27 --repeats 2
```

## Still owed

Written down so nobody has to work it out twice.

The game value itself. Neither side has a forced win within 26 (White) or 28 (Black)
plies; past that it is open. Both are now on the same engine and machine. Black runs
about a seventh of White's tree at equal depth, so it is the cheaper side to push. A draw can only be proven where no line still reaches the horizon, which
today means bare kings around depth 80 and nothing resembling the start position.

A second-seed re-verification of both published bounds at full depth. The wins have
been re-verified under `--seed 0xC0FFEE`; the bounds have not, and a Zobrist collision
is the one residual with no directional structure. `solve_hunt.py` prints the command
when a run ends.

The right `--workers` beyond depth 20, measured there and no further;
`scripts/bench_workers.py` is the tool for going deeper. `--tt` is better understood
now — occupancy is recorded to depth 24 and 2^30 saturates there — but nobody has run
the A/B that would say what a saturated table actually costs at that depth, so the
choice of 2^31 for depth 26 is reasoning from the depth-20 saturation measurement,
not a measurement at depth 26.

Any way at all to close the draw claim. `tinyhouse.c` has a df-pn engine with
Kishimoto-Muller twin entries, validated against the alpha-beta engine over 3,960
comparisons with no disagreements, and it answers the gating milestone no: at 96M
nodes the start position resolves 1 of its 6 root moves and the disproof numbers go
up rather than down. Twins were the hypothesised missing piece and are refuted as
such. Widening them to 8 conditioning keys drives the withheld fraction to 0.0% and
makes the disproof number slightly worse, so the bottleneck is the size of the search
and not the table.

Whether carrying history across iterative-deepening depths helps.
`CLEAR_HISTORY_AT_ROOT` exists and is off, because that is a different experiment from
repeats at one depth and nobody has run it.

There is no honest overall ETA, since the proof depth, if one exists, is unknown. The
ETA the tool prints covers the current depth only, extrapolated from the measured
growth between the last two depths, which runs at about 8.4x per 2 plies.
