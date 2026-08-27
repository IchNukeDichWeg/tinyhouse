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
| `scripts/bench_ab.py` | A/B benchmark: fresh process per repeat, interleaved arms |
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
short, there is no forced White win within 20 plies (729M nodes) and no forced Black
win within 22 plies (303M nodes). The value of the game is still open, and consistent
with a draw.

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

## Pushing the bounds deeper

`solve_hunt.py` prints live nodes, nps and elapsed time with a per-depth ETA, plus one
summary line per completed depth.

```bash
.venv/bin/python solve_hunt.py 0 --tt 31 --workers 16 --maxdepth 26
```

```bash
.venv/bin/python solve_hunt.py 1 --tt 31 --workers 16 --maxdepth 28
```

Run them one after the other; two concurrent 16-worker hunts would oversubscribe
even an 18-core machine.

Measured, White from the start position, 16 workers, `--tt 30`, on an 18-core M5 Pro
(one run, not a median):

| depth | 18 | 20 | 22 | 24 |
|---|---|---|---|---|
| nodes | 205M | 1.39G | 7.85G | 119G |
| time | 3.6s | 24.3s | 133.1s | 1990.2s |
| growth over previous | x7.4 | x6.8 | x5.6 | **x15.2** |
| table occupancy after | 2% | 13% | 54% | **100%** |

The whole run to depth 24 was 128.6G nodes in 35.9 minutes at about 60 Mnps. That is
well under the 70 minutes for depth 24 alone that this file used to extrapolate from
six workers on the old 10-core box, so treat the old figure as retired rather than
merely beaten: it was a different machine, a different worker count and an older build.

**Read the last two rows together.** The per-2-ply node growth factor had been falling
(x7.4, x6.8, x5.6) and then tripled to x15.2 at exactly the depth where the table
filled. That is consistent with saturation forcing re-search, and it matches the
directly measured saturation penalty quoted under `--tt` below, but it is a
correlation from a single run and not a controlled A/B, so do not quote x15.2 as the
cost of a full table.

The practical consequence is that depth 26 is not a 2x step. Extrapolating x15 off
119G puts it near 1.8 trillion nodes, which at 60 Mnps is upwards of 8 hours even
before whatever extra a saturated 2^31 table costs. Hence `--tt 31` above, and hence
running it on an otherwise idle machine.

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

The game value itself. Neither side has a forced win within 24 (White) or 22 (Black)
plies; past that it is open. A draw can only be proven where no line still reaches the horizon, which
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
