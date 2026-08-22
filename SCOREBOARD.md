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
| 6 | THB-06 | 1 | **CONFIRMED** | parse-time rejection; perft(7) 1,355,253 unchanged | see below |
| 7 | TH-21 | 3 | **CONFIRMED** | coverage; suite 59 -> 61 tests, +0.0s | see below |
| 8 | THB-07 | 1 | **CONFIRMED** | foreign-rule dump: rc 0 -> -3; header 24 -> 32 bytes, so pre-existing dumps are invalidated by design | see below |
| 9 | THB-08 | 1 | **CONFIRMED** | failed save: silent exit-0 -> WARNING + intact previous dump; perft(7) 1,355,253 unchanged | see below |
| 10 | THB-10 | 1 | **CONFIRMED** | depth 0 and -5 now clamp to 1; repo DB had 0 rows to clean (4 rows, depths 8/14) | see below |
| 11 | THB-09 | 1 | **CONFIRMED** | unproven rows no longer stored; build_book 8 1 keeps 0 of 7 visited (nothing that shallow is proven) | see below |

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

### THB-06 · `str_move` produced moves the encoding cannot hold

Reproduced: `str_move("K@a1")` returns 320, drop type 4. Feeding it to
`th_make` from the start position leaves `hands[1] == [-1, 0, 0, 0]` -- the
same `hands[0][4] == hands[1][0]` alias THB-04 found, driven negative. `th_key`
then indexes `zob_hand[1][0][-1]`, so every TT key derived from that position
is poisoned, and a `tfen()` round trip cannot see it because `"P" * -1` is `""`.

The `=K` half is confirmed as the *quiet* defect the backlog described, not a
memory bug: `a1b2=K` and `a1b2=P` both parsed to a plain `a1b2` with the promo
field masked to 0 by `& 3`, silently dropping a forced promotion. Both are now
rejected; they are different severities and stay separately described.

Latent in the shipped product either way -- the only caller passing strings to
`str_move` is the test suite. perft(7) unchanged at 1,355,253.

### TH-21 · TT save/load round trip and the seed/size refusals

**Landed out of tier order, on purpose.** THB-07 widens the dump header, and
the backlog's own note says this has to exist first or the widening cannot be
verified. Pulling the dependency forward beat marking THB-07 BLOCKED.

All eight documented codes verified on the shipped build before writing the
test: save 0 · load same seed 0 · wrong entry count -2 · wrong seed -2 ·
missing -1 · bad magic -1 · truncated -1 · save or load with no table -1. Save
to a directory path is also -1.

**Demonstrated against a planted mutation**, since a coverage test that has
never failed proves nothing. A scratch build with the `hdr[2] != tt_seed_used`
check deleted returns **0** where the test asserts **-2**.

The fixture restores `th_seed(0x9E3779B97F4A7C15)` afterwards: reseeding
rebuilds the Zobrist tables process-wide, so a test that forgets silently
changes every key for every later test in the run.

### THB-07 · a `.tt` dump carried no identity of the code that wrote it

Reproduced end to end. A scratch build with one genuinely different rule (a
ferz iterating `KINGN`, so `perft(1..4) = 7/43/362/3171` against the stock
`6/33/241/1855`) wrote a dump that the **stock** build loaded with **rc = 0**.
`th_key` depends only on (board, hands, stm, seed), and every one of those
survives a rules change unchanged, so the keys are perfectly valid -- the
`xkey ^ data == key` trick validates against corruption, never provenance.

After the fix the same foreign dump returns **-3**. The fingerprint is the sha1
of `tinyhouse.c` itself, passed as `-DTH_BUILD_ID` by `engine_c.py`. A
hand-maintained `TT_FORMAT_ID` was rejected on exactly the backlog's ground:
nobody bumps a format id when editing `pseudo_moves`.

`solve_hunt.py` records the same id in the checkpoint, because "no forced win
through depth 20" is a claim about the code that proved it. Verified end to
end: a fresh run proves depths 6 and 8, a second run resumes at depth 10, and
with the recorded build edited it prints `differs in build; starting fresh`.

**Cost, stated plainly**: every existing `.tt` dump is now unreadable (the
header grew from 3 words to 4). That is correct rather than unfortunate -- the
build changed, so the entries are from a different engine either way.

### THB-08 · a failed save destroyed the previous checkpoint

Both arms reproduced on the shipped build.

**Silent failure.** With a directory at the `.tt` path, `solve_hunt.py` printed
`=> no forced WHITE win within 6 plies (proven, checkpointed)` and exited 0
with nothing written. The docstring promises "an interrupted run costs at most
the depth it died in" and the SIGINT handler prints "checkpoint is current";
neither consulted the return value.

**Destroy-on-open.** `fopen(fname, "wb")` truncated the live dump before a byte
was written: saving a 2^12 table over a 2^18 dump took it from 4,194,336 bytes
to 65,568, and reloading at 2^18 returned -2. The good dump was unrecoverable
from the moment the new save started, not from the moment it failed.

Now `<name>.tmp` + `fsync` + `rename`, which is atomic within a filesystem, so
the old dump stands until the new one is complete on disk. `solve_hunt` reports
the failure, says what survived it (every proven depth is in the JSON, which is
written first on purpose), and the "checkpointed" wording and the SIGINT
message both follow the actual result now.

perft(7) unchanged at 1,355,253.

**Incidental**: two `solve_hunt` runs of the same depth reported 820 and 807
nodes. That is not drift, it is `--workers 2` -- lazy SMP is nondeterministic
by construction. Every campaign measurement uses one worker.

### THB-10 · `/api/analyze` clamped depth above but not below

Reproduced against the real handler: `depth=0` and `depth=-5` both reached the
engine and came back labelled `"depth": 0` / `"depth": -5`.

The backlog's correction is the one that matters, and it holds: the top-level
`value` does **not** show a mate, because the root skips the TT cutoff
(`ply > 0`). The mate appears only inside `moves`, which is worse than a plain
wrong number -- the payload is self-contradictory, a headline "no forced win
within horizon" sitting directly above a move listed as a forced win. And the
row is then frozen into the cache under a key no honest search can reproduce.

Clamped both ways, and `init()` deletes any `depth < 1` row left in an older
database. The repo's own `analysis.sqlite` has none (4 rows, depths 8 and 14),
so this is prophylactic rather than a repair.

### THB-09 · an unproven analysis was frozen into the cache

The mechanism reproduced: `th_solve` probes a table earlier requests filled and
the cutoff fires on a proven entry regardless of depth, so `analyze()` is not a
function of `(tfen, depth)` at all. Asking depth 14 and then depth 6 on the same
server returns the depth-14 answer, and the old code stored it permanently under
the depth-6 key -- after which an honest cold depth-6 request could never be
served for that key again.

The value served is **not wrong**, and the fix keeps that distinction. A proven
result is the true game value: depth-independent, and no later search can
contradict it, so caching it is sound. An **unproven** result is the one that
depends on what preceded it, and that is what `CACHE_ONLY_PROVEN` refuses to
freeze.

**Named cost**: unproven positions now recompute on every request. Measured on
the book: `build_book.py 8 1` visits 7 positions near the start and stores
**0** -- nothing that shallow is proven. The script's summary line now reports
proven-of-visited rather than visited, so the book cannot look bigger than it is.

**A regression I introduced, found here and fixed here**: moving the engine and
cache setup out of `server.py`'s import (commit `3004d6f`) broke
`scripts/build_book.py`, which reaches `analyze()` by import and got
`db is None`. Nothing covered it. It now calls `init()`, takes a database path
so a test need not touch the repo's, and has a smoke test.

**One test rewritten in the same commit**, not disabled: the round trip
asserted a cache hit on the start position at depth 8, which is unproven and
correctly no longer cached. It now asserts the hit on a proven position.
