# Scoreboard

One row per campaign item, in the order they were closed. Every item lands
here, including the rejected ones — **a rejected item that is measured,
reverted and recorded is a success**; an item that lands unmeasured is not.

## Measurement protocol (tiers 4-5)

- Machine: Apple M2 Pro, 10 cores, 16 GiB, Darwin 25.5.0. Every number below is
  from this machine unless stated otherwise.
- Each repeat is a **fresh process**. The thread-local `history[2][2048]` table
  carries over between in-process searches, which is worth up to 38% of the node
  count on its own (TH-19).
- At least 3 repeats, **interleaved A/B/A/B**, never blocked AAA/BBB — this
  machine throttles.
- The first run of a session is discarded.
- `pgrep -fl "solve_hunt|server.py"` must be empty before a measurement.
- **A delta smaller than the spread is NULL, not a win.**
- Re-baseline after every accepted item.

## Standing oracles

| Oracle | Value |
|---|---|
| `pytest -q` | green |
| `perft(7)` from start | 1,355,253 |
| `th_root_moves(start, 10)` | `d1c2 = -29990`, all other root moves 0 |
| mate-in-9 proof | `th_mate_hunt(fuwk/3p/P1F1/KWU1[-] b, 9, BLACK) = 29991` |

## Closed items

| # | ID | Tier | Verdict | Metric | Commit |
|---|---|---|---|---|---|
| 1 | THB-01 | 0 | **CONFIRMED** | fix costs nothing on the bounds path: start-position negative hunt d16 White 9,913,857 -> 9,616,663 nodes (-3.0%), Black 1,824,606 -> 1,791,866 (-1.8%); repro position d13 8,279,609 -> 8,988,304 (+8.6%) | `8b2e81c` |
| 2 | THB-02 | 1 | **CONFIRMED** | parse-time rejection; no node-count effect (perft(7) 1,355,253 unchanged) | see below |
| 3 | THB-03 | 1 | **CONFIRMED** | parse-time rejection; no node-count effect (perft(7) 1,355,253 unchanged) | see below |
| 4 | THB-05 | 1 | **CONFIRMED** | perft(7) 1,355,253 unchanged; whole-suite cost of validating every to_c call is 4.63s -> 4.68s (noise) | see below |
| 5 | THB-04 | 1 | **CONFIRMED** | perft(7) 1,355,253 unchanged; guard is a no-op on legal input (no king capture is generated from a validated position) | see below |

### THB-01 · TT cutoff broke the ply-budget contract

**Reproduced first, as a red test.** Cold process, `th_tt_init(22)`, 1 worker,
`f1w1/2k1/K2p/W1UF[Up] b`, hunting Black: d11 -> 0, **d12 -> 29985 ("Black wins
in 15" out of a 12-ply budget)**, d13 -> 29987. True distance is 13, so the
honest depth-12 answer is 0. Wrong verdict and wrong distance.

**The backlog's recommended fix is insufficient, and this is measured, not
argued.** Form **H** (`if (ply > 0 && depth > 0)`) closes the horizon arm only.
Sound exact mate entries are still reused at *interior* nodes carrying less
budget than the distance they encode. Populating the table with `th_solve`
depth 10 on the recorded mate-in-9 line and then asking for a win within 4
plies:

| build | warm hunt d2 | d4 | d6 | d8 | d10 |
|---|---|---|---|---|---|
| guard 0 (pre-fix) | 29991 | 29991 | 29991 | 29991 | 29991 |
| guard 1 (form H) | 29991 | 29991 | 29991 | 29991 | 29991 |
| **guard 2 (shipped)** | **0** | **0** | **0** | **0** | 29991 |

Form H does not move a single one of those. That path is the documented resume
workflow -- `solve_hunt.py` reloads a dumped table and can then be asked for a
shallower depth -- so it is live, not contrived. **Shipped form M**: refuse a
cutoff exactly when the mate distance it carries exceeds the depth remaining at
that node.

**Toggle-off pin exact.** `TT_BUDGET_GUARD 0` reproduces the pre-change node
counts to the node: 1,496,977 / 2,458,275 / 8,279,609 at d11/12/13.

**Record intact.** All three published wins reproduce at their exact distances
(29991, 29987, 29987), each in a cold process and again under Zobrist seed
`0xC0FFEE`; the mate-in-9 is still absent at depth 8. Every start-position
negative hunt at d12/14/16 still returns 0 for both colours.

**Weak instrument, recorded as such.** A 720-probe random scan (120 positions x
depths 6/8/10 x both colours, fresh table each) found **0** violations on the
*pre-fix* build, so it is not sensitive at those depths and its silence on the
fixed build proves nothing. The warm-table experiment above is the sensitive
one.


### THB-02 · `from_tfen` accepted a promoted king

Reproduced red: `KK~2/4/4/3k[-] w` parsed to a board carrying **two** white
kings (values 5 and 13) and round-tripped unchanged, because the king count
looks for the unpromoted value and the unit-count loop skips `ptype == K`.

Root cause is one line wider than the item: `~` was applied to *any* type. The
guard is therefore "only F, U and W can be promoted", which closes the promoted
**pawn** in the same stroke (`3k/2P~1/4/K3[-] b`, also accepted before). The
backlog had the promoted-pawn half filed under THB-03 and marked the
count-invisibility claim REFUTED; both are true at once -- `P~` counts
correctly, and it is still not a legal piece.

perft(7) unchanged at 1,355,253; the five `PERFT_ORACLE` round-trips are green,
so no legal TFEN in the repo used `~` on a P or K.

### THB-03 · `from_tfen` accepted a pawn on rank 1 or rank 4

All four families reproduced red before the fix -- `P3/4/4/K2k[-] w`,
`3k/4/4/K2p[-] b`, `3p/4/4/K2k[-] b`, `3k/4/4/P2K[-] w` -- each parsing and
round-tripping unchanged. The parse loop checked characters, file overflow and
file coverage; the post-loop block checked unit counts, king counts and
side-not-to-move-in-check. Pawn *placement* was checked nowhere, and the only
pawn-rank rule in the codebase lived in the drop predicate.

The two families are illegal for different reasons, which is why the guard is
stated as a rank rule and not as an "immobile piece" rule: on its own promotion
rank the pawn is frozen (promotion is forced, so it generates no moves), while
on the far rank it plays on normally and is merely unreachable.

perft(7) unchanged at 1,355,253; all five `PERFT_ORACLE` round-trips green.

### THB-05 · `to_c` validated nothing

Reproduced red on the shipped build. A hand-built `T.Position()` -- empty board,
no kings, never through `from_tfen` -- reached `th_solve` and returned
**`value=30000, snd=3`** at depths 2, 4 and 6. `snd == SND_LB|SND_UB` is the
code's own encoding of an exact, PROVEN game value, and 30000 is `MATE` itself,
a distance-zero mate: a fabricated proof computed off out-of-bounds reads,
because `king_sq` returns -1 and `attacked()` then indexes `ORTH[-1]`. The
black-kingless variant returned `29999, snd=1`. An over-full hand is the same
class: `th_key` indexes `zob_hand[c][t][n]` and that dimension is 3.

The backlog reported `-29998`; this build gives `+30000`. Same defect, and the
difference is the point -- the item warned the blast radius is build- and
stack-layout-dependent, so the *value* is not a stable signature.

**Fixed at the root, not at the call site.** The rules moved out of `from_tfen`
into `Position.validate()`, which both boundaries now call, so `from_tfen` is
left with syntax only and nothing can drift between the two. That also closes
THB-04 and THB-06 from every reachable direction, since neither can be reached
without an illegal position or a fabricated move.

perft(7) unchanged at 1,355,253. Suite cost of validating on every `to_c`
(~1,200 calls in the parity walk alone): 4.63s -> 4.68s, inside the noise.

### THB-04 · `make`/`unmake` wrote `hands[us][4]` on a king capture

Both directions reproduced against a pre-fix build of the same tree.

**Black capturer** (white king a1, black wazir a2, black king d4, Black to
move): `th_moves` alone returned with the caller's `stm` flipped **1 -> 0**.
`unmake` restores `stm` and *then* decrements the alias, so the corruption is
precisely the half that survives the call.

**White capturer** (white wazir a1, black king b1, white king d4): after
`th_make(Wa1xb1)`, `hands[1] == [1, 0, 0, 0]` on the pre-fix build and
`[0, 0, 0, 0]` on the shipped one -- a black **pawn** fabricated out of
`hands[0][4]`, which is the same byte as `hands[1][0]`.

**The paired-perft oracle the backlog asks for does not fire, and that is worth
recording.** On this position perft(1/2/3) is 5/12/63 on *both* builds. The
kingless side's `king_sq` returns -1, `attacked()` reads `ORTH[-1]` and reports
"attacked", so every phantom pawn drop is filtered straight back out as leaving
the king in check. Two defects cancel. The hand array itself is the oracle, not
a node count.

perft(7) from the start unchanged at 1,355,253, so the guard is a no-op on
legal input.
