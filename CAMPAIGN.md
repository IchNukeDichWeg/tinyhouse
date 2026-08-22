# Campaign ledger

The live status of every item in `IMPROVEMENTS.md`. This file is the resume
point: an interrupted campaign continues by reading it, not by re-deriving the
tier assignment. Updated after **every** item, including rejections.

Verdicts: `CONFIRMED` · `REJECTED` · `NULL` · `KEPT-ON-NULL` ·
`CLOSED PRE-MEASUREMENT` · `MOOT` · `BLOCKED` · `PENDING`.

Measurements and their protocol live in `SCOREBOARD.md`; this file carries one
line per item.

## Baseline gate (2026-08-22, at `d8d951f`)

| Gate | Result |
|---|---|
| `git status --short` | clean (one tooling commit was needed: `d8d951f`) |
| `pytest -q` | 43 passed |
| `perft(7)` from start | 1,355,253 |
| `pgrep solve_hunt\|server.py` | empty |

## Tier counts

| Tier | What | Items | Batched |
|---|---|---|---|
| 0 | P0 soundness | 1 | no |
| 1 | correctness bugs | 19 | yes |
| 2 | doc overclaims | 7 | yes |
| 3 | instruments | 18 | yes |
| 4 | NPS / node-identical speed | 8 | **never** |
| 5 | efficiency / nodes-to-depth | 3 | **never** |
| 6 | new ideas | 3 | no |
| 7 | GUI/UX | 3 | yes |
| | **total** | **62** | |

---

## Tier 0 — P0 soundness

| ID | Item | Status |
|---|---|---|
| THB-01 | TT cutoff at a horizon node breaks the ply-budget contract | **CONFIRMED** |

## Tier 1 — correctness bugs

| ID | Item | Status |
|---|---|---|
| THB-07 | `.tt` dump carries no identity of the code that produced it | **CONFIRMED** |
| THB-05 | `to_c` is the real trust boundary and validates nothing | **CONFIRMED** |
| THB-02 | `from_tfen` accepts a promoted king | **CONFIRMED** |
| THB-03 | `from_tfen` accepts a pawn on rank 1 or 4 | **CONFIRMED** |
| THB-04 | `make`/`unmake` write `hands[us][4]` on a king capture | **CONFIRMED** |
| THB-06 | `str_move('K@a1')` fabricates a king drop | **CONFIRMED** |
| THB-08 | `save_state()` discards `th_tt_save`'s return; save truncates on open | **CONFIRMED** |
| THB-09 | sqlite cache row is a function of live TT state, not of its key | **CONFIRMED** |
| THB-10 | `/api/analyze` clamps depth above but not below | **CONFIRMED** |
| THB-11 | one abandoned `/api/analyze` pins `ENGINE_LOCK` | **CONFIRMED** |
| THB-15 | `DOUBLE_STEP` has no C counterpart | **CONFIRMED** |
| THB-14 | dylib rebuild trigger ignores the compile flags | **CONFIRMED** |
| THB-13 | setup mode silently strips the promoted flag | **CONFIRMED** |
| THB-12 | GUI history corrupted by a click before `load()` resolves | **CONFIRMED** |
| TH-40 | `/api/analyze` mixes frames: `value` white-view, `snd` mover-view | **CONFIRMED** |
| TH-42 | `ENGINE_VERSION` is hand-bumped | **CONFIRMED** |
| TH-44 | error responses leak absolute filesystem paths | **CONFIRMED** |
| TH-43 | `th_solve` at `depth <= 0` returns no best move | **CONFIRMED** |
| TH-41 | cache hits replay the first computation's `nodes`/`time`/`depth` | **CONFIRMED** |

## Tier 2 — doc overclaims

| ID | Item | Status |
|---|---|---|
| TH-01 | "no search extensions, so the ply budget is exact" is false | **CONFIRMED** |
| TH-02 | one proof grade sold for two claim strengths | **CONFIRMED** |
| TH-05 | `solve_status.json` says "single thread"; the tool defaults to 2 | **CONFIRMED** |
| TH-03 | rep-safety "keeps the GHI problem out" overclaims | **CONFIRMED** |
| TH-06 | the negative bounds need the second-seed re-verification too | **CONFIRMED** |
| TH-04 | `PERFT_ORACLE` docstring overclaims its provenance | **CONFIRMED** |
| TH-07 | "exists exactly twice" vs code rejecting only `> 2` | **MOOT** |

## Tier 3 — instruments

| ID | Item | Status |
|---|---|---|
| TH-19 | clear `history` at the root (unblocks tiers 4-5) | **CONFIRMED** |
| TH-18 | pin the recorded proofs | **CONFIRMED** |
| TH-22 | cffi signature coverage for the search API | **CONFIRMED** |
| TH-28 | pin the horizon "non-terminal is UNSOUND" invariant | **CONFIRMED** |
| TH-21 | pin the TT save/load round trip and the seed/size refusals | **CONFIRMED** |
| TH-32 | a paired NPS bench for the C search | **CONFIRMED** |
| TH-20 | paired nodes-to-depth + solver-digest regression harness | **CONFIRMED** |
| TH-31 | `th_nodes()` has no reset and does not count perft | **CONFIRMED** |
| TH-27 | assert the SMP hunt returns the same proof as single-threaded | **CONFIRMED** |
| TH-34 | expose `snd` from `th_mate_hunt_mt` | **CONFIRMED** |
| TH-35 | expose `snd` from `th_root_moves` | **CONFIRMED** |
| TH-30 | test the Zobrist reseed contract | **CONFIRMED** |
| TH-24 | extend the Python/C parity walk beyond the start position | **CONFIRMED** |
| TH-23 | pin `attacked()` against an independent geometric oracle | **CONFIRMED** |
| TH-29 | pin a draw-by-repetition proof | **CONFIRMED** |
| TH-26 | test the `solve_hunt` resume/checkpoint round trip | **CONFIRMED** |
| TH-33 | cross-check `state_count.py`, delete its dead stub | **CONFIRMED** |
| TH-25 | assert published perft counts on the symmetry orbit | **REJECTED** |

## Tier 4 — NPS (node-identical), one at a time

| ID | Item | Status |
|---|---|---|
| TH-08 | horizon fast path | PENDING |
| TH-09 | drops from a precomputed empty-square mask | PENDING |
| TH-10 | incremental Zobrist key | PENDING |
| TH-12 | hoist `king_sq` out of the legality loop | PENDING |
| TH-11 | fast legality (perft/`th_moves` half only) | PENDING |
| TH-16 | prune drops that cannot resolve a check | PENDING |
| TH-15 | staged movegen: TT move before the full list | PENDING |
| TH-14 | bitboard movegen and `attacked()` | PENDING |

## Tier 5 — efficiency (nodes-to-depth), one at a time

| ID | Item | Status |
|---|---|---|
| TH-13 | credit the symmetric `SND_LB` in mate-distance pruning | PENDING |
| TH-39 | the `--tt 26` default is unmeasured | PENDING |
| TH-17 | enemy-king-proximity bonus for quiet drops | PENDING |

## Tier 6 — new ideas

| ID | Item | Status |
|---|---|---|
| TH-37 | reachable-position census | PENDING |
| TH-36 | df-pn as a second engine | PENDING |
| TH-38 | bounded retrograde terminal shell | PENDING |

## Tier 7 — GUI/UX

| ID | Item | Status |
|---|---|---|
| TH-45 | history numbering inverted for the whole game | PENDING |
| TH-46 | no check indicator of any kind | PENDING |
| TH-47 | `/pieces/` hardcodes `image/svg+xml` | PENDING |
