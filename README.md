# Tinyhouse

Rules engine, solver, and GUI for the chess.com variant
[Tinyhouse](https://chess-variants.fandom.com/wiki/Tinyhouse): 4x4 crazyhouse with
King, Ferz, Wazir, Xiangqi Horse and one Pawn per side, forced F/U/W promotion, and
the stalemated player winning. Full rules with sources: [RULES.md](RULES.md).

## Layout

| File | What |
|---|---|
| `tinyhouse.py` | Python rules engine (movegen, make/unmake, hands, TFEN, perft) |
| `tinyhouse.c` | C hot path: same encodings, plus the solving search (TT, mate hunt) |
| `engine_c.py` | cffi (ABI) wrapper; auto-builds `libtinyhouse.dylib` with `cc` |
| `server.py` + `index.html` | Local web GUI, stdlib only |
| `solve_hunt.py` | Deep one-color forced-win hunt from the start position |
| `solve_status.json` | Current proven solve bounds (shown in the GUI) |
| `scripts/build_book.py` | Precompute analyses near the start into `analysis.sqlite` |
| `scripts/state_count.py` | Exact syntactic state-space count |

## Setup and tests

```bash
python3 -m venv .venv && .venv/bin/pip install pytest cffi
```

```bash
.venv/bin/python -m pytest -q
```

## GUI

```bash
.venv/bin/python server.py 8653
```

Then open <http://127.0.0.1:8653/>. Click or drag to move, click a hand piece then a
square to drop, promotion opens a picker. Setup mode edits the board, hands, and side
to move freely. Analyses are cached in `analysis.sqlite` (queryable:
`sqlite3 analysis.sqlite 'SELECT json FROM analysis'`).

## Solve status

The game is **not solved**. What is proven so far (machine-readable in
`solve_status.json`):

- no forced **White** win within **20 plies** (729M nodes)
- no forced **Black** win within **22 plies** (303M nodes)

so the game value is still open, consistent with the draw its reception suggests.
Genuine forced wins ARE proven and shown when they are in range, e.g. `1.Fd1-c2??`
loses by force: `1...Uxc2 2.Wb2 F@a3 3.Wxc2 dxc2 4.U@b3 Kd3 5.Uxd2 W@b1#` (mate in 9).

These bounds are proof-grade, not heuristic: the search returns an *unsound* 0 at the
horizon and sound values only at terminals and repetitions, so a mate score it reports
is a proof, and a null-window hunt returning 0 proves no win exists within that budget.
See the solver comment block in `tinyhouse.c`.

**The two claims are not equally strong, and the difference is worth stating.** A
reported mate is a proof of a forced win *and*, since the ply-budget guard, of the
distance it names. A "no forced win within N plies" bound is immune to horizon
unsoundness, to a transposition-table cutoff overrunning its budget, and to
store-side graph-history interaction — but not to a 64-bit Zobrist collision, which
has no directional structure and could prune a subtree holding a real mate. That
residual is unquantified rather than zero, and re-running under a second seed
(`--seed`) is the cheap check against it, for the negative bounds as much as for the
wins.

### Pushing the bounds deeper

`solve_hunt.py` prints live nodes/nps/elapsed with a per-depth ETA and one summary
line per completed depth. Ctrl-C is safe — every completed depth is already printed.

```bash
.venv/bin/python solve_hunt.py 0 --tt 27
```

```bash
.venv/bin/python solve_hunt.py 1 --tt 27
```

`color 0` hunts a White forced win, `1` hunts Black. `--tt BITS` is log2 of TT
entries (27 = 2 GiB). `--maxdepth D` stops early, `--tfen` hunts from another
position, `--seed S` re-runs a proof under different Zobrist keys.

**It resumes.** Progress is checkpointed after every completed depth (to
`solve_state/`, together with a dump of the transposition table), so re-running the
same command skips proven depths and reloads the table. An interrupted run costs at
most the depth it died in. Ctrl-C is safe and leaves a usable checkpoint; `--fresh`
ignores it.

**On `--workers`:** scaling is depth-dependent and only measured shallow. At depth 18
(M2 Pro, 3 repeats, fresh table each run) 1 and 2 threads tie within noise, 3+
regresses hard. Deeper runs may scale better as the shared table fills — that is
unmeasured, so measure at your real target depth rather than trusting a shallow
number:

```bash
.venv/bin/python scripts/bench_workers.py --depth 22 --workers 1,2,4 --repeats 2
```

**There is no honest overall ETA** — the proof depth, if one exists, is unknown. The
printed ETA covers the current depth only, extrapolated from the measured growth
factor between the last two depths (roughly 7x per 2 plies).
