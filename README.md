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
| `tinyhouse.c` | C hot path: same encodings, plus the search and a df-pn engine |
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
.venv/bin/python solve_hunt.py 0 --tt 27 --workers 6 --maxdepth 26
```

```bash
.venv/bin/python solve_hunt.py 1 --tt 27 --workers 6 --maxdepth 28
```

Run them one after the other. Six workers each would oversubscribe a 10-core machine.
At six workers, depth 22 takes roughly 9 minutes, depth 24 about 70, and depth 26
somewhere near 9 or 10 hours.

`color 0` hunts a White forced win and `1` hunts Black. `--tt BITS` is log2 of the
number of transposition-table entries, so 27 is 2 GiB. `--maxdepth D` stops early,
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

Scaling depends on depth, and the direction reverses between 18 and 20 (M2 Pro, 10
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

The default is 26, one GiB. Measured on this machine with a single worker, hunting a
White win from the start:

| depth | best on nodes | occupancy at 2^26 |
|---|---|---|
| 16 | 2^20 (9.56M; 2^26 is no better) | 7.0% at 2^24 |
| 18 | 2^24 (81.9M against 86.7M at 2^26) | 14.9% |

At depths that finish in seconds the default is oversized. Occupancy is what climbs
with depth, though, and the table that matters is the one a depth-20-plus overnight
run needs, so lowering the default on a depth-18 curve would be the wrong call.
Measure at the depth you actually intend to run:

```bash
.venv/bin/python scripts/bench_workers.py --depth 20 --tt-sweep 22,24,26,27 --repeats 2
```

## Still owed

Written down so nobody has to work it out twice.

The game value itself. Neither side has a forced win within 20 or 22 plies; past that
it is open. A draw can only be proven where no line still reaches the horizon, which
today means bare kings around depth 80 and nothing resembling the start position.

A second-seed re-verification of both published bounds at full depth. The wins have
been re-verified under `--seed 0xC0FFEE`; the bounds have not, and a Zobrist collision
is the one residual with no directional structure. `solve_hunt.py` prints the command
when a run ends.

The right `--tt` beyond depth 18, and the right `--workers` beyond depth 20. Both are
measured up to those depths and no further, and `scripts/bench_workers.py` is the tool
for going deeper.

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
