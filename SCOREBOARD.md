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
| 2 | THB-02 | 1 | **CONFIRMED** | parse-time rejection; no node-count effect (perft(7) 1,355,253 unchanged) | `ee9a07a` |
| 3 | THB-03 | 1 | **CONFIRMED** | parse-time rejection; no node-count effect (perft(7) 1,355,253 unchanged) | `fe7d586` |
| 4 | THB-05 | 1 | **CONFIRMED** | perft(7) 1,355,253 unchanged; whole-suite cost of validating every to_c call is 4.63s -> 4.68s (noise) | `6e2fa60` |
| 5 | THB-04 | 1 | **CONFIRMED** | perft(7) 1,355,253 unchanged; guard is a no-op on legal input (no king capture is generated from a validated position) | `4182411` |
| 6 | THB-06 | 1 | **CONFIRMED** | parse-time rejection; perft(7) 1,355,253 unchanged | `61709fd` |
| 7 | TH-21 | 3 | **CONFIRMED** | coverage; suite 59 -> 61 tests, +0.0s | `1e17566` |
| 8 | THB-07 | 1 | **CONFIRMED** | foreign-rule dump: rc 0 -> -3; header 24 -> 32 bytes, so pre-existing dumps are invalidated by design | `cb6a56d` |
| 9 | THB-08 | 1 | **CONFIRMED** | failed save: silent exit-0 -> WARNING + intact previous dump; perft(7) 1,355,253 unchanged | `33ed079` |
| 10 | THB-10 | 1 | **CONFIRMED** | depth 0 and -5 now clamp to 1; repo DB had 0 rows to clean (4 rows, depths 8/14) | `e937cc7` |
| 11 | THB-09 | 1 | **CONFIRMED** | unproven rows no longer stored; build_book 8 1 keeps 0 of 7 visited (nothing that shallow is proven) | `a7f89c8` |
| 12 | TH-41 | 1 | **CONFIRMED** | labelling only; no engine or node-count effect | `d995bb2` |
| 13 | TH-42 | 1 | **CONFIRMED** | cache namespace now moves with the engine: editing #define MATE moved it 3697319324787062899 -> 8643824827813915791 (was: unchanged) | `f128cf0` |
| 14 | TH-40 | 1 | **CONFIRMED** | mirrored pair now reports snd 2 vs 1 (was 1 vs 1); cache namespace moves automatically via TH-42 | `5c9e9af` |
| 15 | THB-11 | 1 | **CONFIRMED** | contended trivial request: unbounded wait -> 503 after 20s; GUI depth cap 22 -> 16 on measured cost (d16 10.25s, d18 98.77s cold) | `b20476c` |
| 16 | TH-44 | 1 | **CONFIRMED** | planted IsADirectoryError: absolute path in a 400 body -> 500 'internal error', path only on stderr | `7c2f5cd` |
| 17 | TH-43 | 1 | **CONFIRMED** | node-identical (9,616,663 hunt d16 and 1,319,149 solve d14 on both arms); time x0.993/x1.000, inside spread | `a784459` |
| 18 | THB-15 | 1 | **CONFIRMED** | flag on: import now raises; divergence Python 6/36/274/2181/19317 vs C 6/33/241/1855/16021 | `2a4e605` |
| 19 | THB-14 | 1 | **CONFIRMED** | flags-only edit: dylib unchanged (sha1 4a7c8c7f) -> rebuilt (afeba22c -> 9d16118d) | `125e934` |
| 20 | THB-12 | 1 | **CONFIRMED** | browser-verified: two unawaited clicks record 1 move, not 2 (guard removed: 2 moves, wrong position) | `72f1344` |
| 21 | THB-13 | 1 | **CONFIRMED** | browser-verified: F~ then c1 builds fuwk/3p/P3/KWF~F[-] w; palette 11 -> 17 entries | `72f1344` |
| 22 | TH-01 | 2 | **CONFIRMED** | docs only; the claim is true after THB-01 but its stated reason never was | `eaa9a45` |
| 23 | TH-02 | 2 | **CONFIRMED** | docs only; 4 sites, no code path touched (perft(7) 1,355,253, suite 80) | `18fb481` |
| 24 | TH-05 | 2 | **CONFIRMED** | default workers 2 -> 1; node counts now reproducible run to run (467/3,420/23,635 three for three vs 786/807/792 at 2 workers) | `c1d0ac2` |
| 25 | TH-03 | 2 | **CONFIRMED** | PV replay: 9/9 plies legal, 0 repetitions, terminal result -1; perft(7) 1,355,253 unchanged | `a7a4699` |
| 26 | TH-06 | 2 | **CONFIRMED** | advice now on the negative branch; verified on normal exit, SIGINT (exit 130) and the win branch | `080916f` |
| 27 | TH-04 | 2 | **CONFIRMED** | docstring restated; depth-2 divide 5/6/6/3/6/7 = 33 now pinned (the artifact the claim assumed) | `d298404` |
| 28 | TH-07 | 2 | **MOOT** | no-op: the comment already reads 'at most twice' after THB-05's refactor; 8 full / 11 under-full literals confirm the doc was the half to change | `713e188` |
| 29 | TH-19 | 3 | **CONFIRMED** | in-process repeats 757,431/839,298/845,107/1,345,672/795,066 -> 757,431 x5 with th_clear_history; bench_workers prints 757,431 not '1M' | `5ab4df8` |
| 30 | TH-18 | 3 | **CONFIRMED** | 9 pinned cases green; sensitivity measured: values catch 0 of 5 planted mutations, node counts catch 4 of 5 | `e2792a4` |
| 31 | TH-20 | 3 | **CONFIRMED** | catches 5 of 5 planted mutations (vs 0 of 5 for TH-18's value pin); deterministic, digest 651da0519b02a4b7 / 6,476,533 nodes, ~2s | `0b26df1` |
| 32 | TH-22 | 3 | **CONFIRMED** | 20 of 20 cdef symbols now have a contract assertion (5 previously untouched); catches 4 of 4 planted cdef errors | `ebf9491` |
| 33 | TH-28 | 3 | **CONFIRMED** | both directions pinned; a build with a sound non-terminal horizon fails it | `7d410b4` |
| 34 | TH-30 | 3 | **CONFIRMED** | keys asserted to differ, not values; a no-op th_seed fails it | `7d410b4` |
| 35 | TH-27 | 3 | **CONFIRMED** | workers 1/2/4 all give 29991 + b4c2 at d9 and 0 at d8; helper-depth mutation passes (the budget guard absorbs it) | `7d410b4` |
| 36 | TH-32 | 3 | **CONFIRMED** | null-hypothesis calibration: identical builds measure +0.4% / -0.6% against 1.1-1.2% spread, both reported NULL; noise floor ~1% | `dd9aa78` |
| 37 | TH-31 | 3 | **CONFIRMED** | contract pinned: counter unchanged across th_tt_init/th_seed and across perft(5)=16,021; no reset added | `47cca17` |
| 38 | TH-34 | 3 | **CONFIRMED** | win branch snd=1 at d9/d11, negative branch snd=0 at d8/10/12/14 (assertion gated accordingly) | `4b8c511` |
| 39 | TH-35 | 3 | **CONFIRMED** | d1c2 now reports -29990 with snd 2 (SND_UB); all five quiet moves snd 0 | `4b8c511` |
| 40 | TH-24 | 3 | **CONFIRMED** | walk now starts from all 5 oracle roots (was 1); +0.2s | `f6070ce` |
| 41 | TH-23 | 3 | **CONFIRMED** | 94,624 comparisons, 0 mismatches; catches 3 of 3 planted geometry bugs | `f6070ce` |
| 42 | TH-26 | 3 | **CONFIRMED** | resume, --fresh and build-mismatch paths all pinned by subprocess | `a064fd6` |
| 43 | TH-33 | 3 | **CONFIRMED** | sub-problem 131,976 analytic == 131,976 brute force; headline 17,669,515,462,968 unchanged and pinned against RULES.md | `a064fd6` |
| 44 | TH-29 | 3 | **CONFIRMED** | proven draw found: 2K1/4/4/2k1[-] w -> v=0 snd=3 at depth 100 (117M nodes, 6.9s); unproven at 14 and 40 | `d0e1350` |
| 45 | TH-25 | 3 | **REJECTED** | orbit adds 0 detections: identity perft catches 8 of 8 planted rules bugs, orbit-only catches 0 more | `94ea4f2` |
| 46 | TH-08 | 4 | **CONFIRMED** | +4.04% solve d14, +3.69/+3.93% hunt d16 vs a 0.2-0.4% control; NULL on drop-heavy; node-identical | see below |
| 47 | TH-09 | 4 | **CONFIRMED** | +5.24% solve d14, +5.56/+5.15% hunt d16, +6.06% drop-heavy vs 0.0-0.8% controls; perft +1.00% (reported 1.071x); node-identical | see below |
| 48 | TH-10 | 4 | **CONFIRMED** | +7.92% solve d14, +7.44/+7.47% hunt d16, +3.78% drop-heavy, perft +0.34% (no regression); KEY_PARANOIA clean over 123M nodes incl. SMP | see below |
| 49 | TH-12 | 4 | **CONFIRMED** | +10.16% perft(7), +39.56% drop-heavy perft, +2.53% solve d14, +2.95% hunt d16 vs controls under 0.4%; node-identical | see below |
| 50 | TH-11 | 4 | **CONFIRMED** | perft +28.46% start, +110.83% drop-heavy; inside search -0.78%/-0.68% so shipped OFF there; perft equivalence checked on 8 positions incl. 3 promoted-mao | see below |
| 51 | TH-16 | 5 | **REJECTED** | Class A form: NULL on perft(7) (+0.41% vs 0.67% control) and -1.33% on the mao-check position it targets; the search form is node-changing (digest 811f304f1eef7998), so the item moves to tier 5 | see below |
| 52 | TH-15 | 4 | **CLOSED PRE-MEASUREMENT** | ceiling is 0.6% of interior nodes (only 1.1% have a TT move at all), below the ~1% noise floor | see below |

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

### TH-41 · cache hits replayed the producing computation's provenance

Re-read after THB-09 landed, and the item is **smaller than filed**. The
"depth is replayed too" half is now vacuous: rows are keyed on `(tfen, depth)`
and stored under the depth they were computed at, so the stored `depth` always
equals the requested one. What made it look otherwise was THB-09 -- a depth-6
key holding a depth-14 answer -- and that is fixed.

What survives is real but small: a proven row can carry a tiny node count,
because the search that produced it had a warm table, and rendering that as the
current request's cost reads as "15 nodes proved a mate in 9". The GUI now
prints `depth N · from cache` instead of numbers that describe a different
computation. The API keeps `nodes`/`time` for scripted consumers, next to the
`cached` flag that says what they mean.

Not a measurement item: no node count and no timing changes.

### TH-42 · `ENGINE_VERSION` was hand-bumped

Reproduced end to end in a scratch mirror (repo files symlinked, `tinyhouse.c`
and `server.py` copied so the edit could not touch the working tree):

| mirror state | build id | ENGINE_VERSION |
|---|---|---|
| stock | `0xf8a8f60c9b0c4539` | 3697319324787062899 |
| after editing `#define MATE 30000` -> `30002` | `0xbc127ab8fe9e11c5` | 8643824827813915791 |

The rebuild fires, the engine changes, and under the old hand-maintained `2`
the cache key did not move at all. It is now `th_build_id() ^ sha1(server.py)`:
the engine decides the values, this file decides the payload shape and the
frames they are expressed in, so both belong in the namespace.

The stock mirror and the repo agree exactly, which is the consistency check
that the derivation depends on nothing incidental about the path.

**Named cost**: any edit to either file invalidates the whole cache. It is
gitignored and rebuildable, and over-invalidating is the safe direction. This
also removes the manual bump TH-40 would otherwise have needed.

### TH-40 · `/api/analyze` mixed frames

Reproduced with a colour-mirrored pair at depth 10:

| position | side | mover value | served value | served snd |
|---|---|---|---|---|
| `fuwk/3p/P1F1/KWU1[-] b` | Black | +29991 | **-29991** | 1 |
| its sigma mirror | White | +29991 | **+29991** | 1 |

The values negate correctly. The flags do not move with them: `snd=1` is
`SND_LB`, a *lower* bound on +29991 for White and an *upper* bound on -29991
for Black, served under the same name. The reported sign correction is right
and load-bearing -- `SND_LB`/`SND_UB` are duals of the value they describe, so
the bits swap when the value is negated.

**Latent for today's GUI, and the acceptance test that would ship the bug is
exactly the obvious one.** `index.html:120` tests only `snd === 3`, which is
invariant under the swap, and `fmtVal` short-circuits on `|v| > 29000` before
consulting `snd` at all. A test asserting "badge proven only when snd == 3"
passes on both the broken and the fixed code. The test written here compares
the mirrored pair instead, and asserts the two differ.

**Cache namespace**: the item requires a bump in the same commit. TH-42 landed
first, so it happens by construction -- `ENGINE_VERSION` hashes `server.py`.

### THB-11 · one abandoned `/api/analyze` pinned `ENGINE_LOCK`

The handler runs to completion and only then dies on `BrokenPipeError`, so the
work outlives the client. The backlog's correction stands and is now pinned by
a test: only `/api/analyze` **cache misses** block. `/api/position` returns 200
while the lock is held.

Two changes, and the second is the one that came out of measurement here.
`ENGINE_LOCK.acquire(timeout=20)` turns an unbounded wait into a 503. And the
depth dropdown offered 18, 20 and 22, which are not interactive depths at all.
Measured cold on an M2 Pro, one `/api/analyze` (th_solve plus th_root_moves)
from the start position:

| depth | wall | nodes |
|---|---|---|
| 10 | 0.04s | 88,443 |
| 12 | 0.13s | 478,989 |
| 14 (GUI default) | **1.10s** | 3,735,810 |
| 16 (new cap) | **10.25s** | 36,446,568 |
| 18 | **98.77s** | 396,652,273 |

Depth 18 is a 99-second hold of a global lock, and 20/22 are the multi-hour
bound runs. `MAX_GUI_DEPTH = 16`, and the dropdown stops there; `solve_hunt.py`
is the tool for deeper. The 20s timeout sits comfortably above the 10.25s
worst case, so a legitimately queued request still succeeds rather than 503ing.

**Deliberately not fixed**: `index.html` still wires `depth.onchange = analyze`.
It is a `<select>`, so a mouse selection fires once; keyboard arrow navigation
can fire per option in some browsers, and with the cap at 16 the worst that
queues is a 10s search that now times out instead of hanging.

### TH-44 · error responses echoed absolute filesystem paths

The blanket `except Exception: send_json({"error": str(e)}, 400)` returned
whatever the exception carried, and plenty carry a path -- `IsADirectoryError`
on a subdirectory of `/pieces/` has the full absolute path as its message. It
applies to **every** endpoint, and the `127.0.0.1` bind was the only mitigation.

Now typed: `ValueError` still echoes, because those are this project's own
validation messages and they quote the caller's own input. `KeyError` becomes a
named missing-parameter error. Everything else is a 500 saying `internal
error`, with the traceback printed locally where the operator can see it.

Pinned by planting the exception rather than by creating a directory inside the
repo, since the defect is generic and a test must not write to a repo path.

### TH-43 · `/api/analyze?depth=1` returned no best move

Reproduced: depth 1 gave `best=None` while listing six scored moves; depths 2
and 3 gave `c1b3`.

**The mechanism is not the one filed.** The item says the horizon branch
returns before any store. At depth 1 the root is not a horizon node at all --
it searches its children at depth 0 and computes a best move perfectly well.
What fails is the *reporting*: `root_search` recovered the move by probing the
TT, and unproven depth-1 stores are skipped deliberately (they are most of the
write traffic and nearly worthless), so the probe found nothing. The searcher
already knew the move and simply was not handing it back. It now does, with the
probe left as the fallback for `depth <= 0` roots where no search ran.

Reachable because THB-10 put the floor at 1; before that, depth 1 was one of
several depths that misbehaved.

**Node-identical, measured rather than asserted** (fresh process per repeat,
interleaved, tt 2^22, first repeat discarded):

| workload | pre | post | identical | time |
|---|---|---|---|---|
| hunt d16 White, start | 9,616,663 | 9,616,663 | yes | x0.993 (spread 2.1-3.9%) |
| solve d14, start | 1,319,149 | 1,319,149 | yes | x1.000 (spread 0.2%) |

### THB-15 · `DOUBLE_STEP` has no C counterpart

Divergence re-measured on this build: Python with the flag on gives
`perft(1..5) = 6/36/274/2181/19317`, C gives `6/33/241/1855/16021`. Different
games from ply 2.

The backlog's downgrade is confirmed: **"no test can catch a flip" is false.**
The constant is module level, so flipping it is global at import and the suite
goes red. That is not the exposure.

The exposure is the one verification found and no report filed: `server.py`
drives **both** engines in one process. `position_info` enumerates the GUI's
legal move list from the *Python* generator while `analyze` evaluates with the
*C* engine, so a flipped toggle would offer `a2a4=W` in the UI and then return
an evaluation from an engine whose ruleset has no such move. The guard is
therefore in `engine_c.py`, at the point where the C engine is loaded, and it
raises rather than asserts because asserts vanish under `-O`.

### THB-14 · the rebuild trigger ignored the compile flags

Demonstrated in a scratch mirror, old trigger against new, same edit
(`-O2` -> `-O0` and nothing else):

| trigger | dylib sha1 before | after |
|---|---|---|
| mtime (old) | `4a7c8c7f...` | `4a7c8c7f...` — **no rebuild** |
| content + flags (new) | `afeba22c...` | `9d16118d...` — rebuilt |

The cdef half is confirmed **REFUTED as filed**, and no guard is added for it: a
`ffi.cdef` edit is Python-side and needs no rebuild *by construction*, so
"editing the cdef does not trigger a rebuild" is a category error rather than a
defect. What a cdef edit actually needs is signature coverage, and that is a
separate hole -- TH-22, still pending in tier 3.

mtime was also wrong in the other direction: `git checkout` of an **older**
`tinyhouse.c` silently rebuilds backwards. A content stamp handles both.

Scope note from the backlog stands: the dylib is gitignored, so this is
per-developer-machine only.

### THB-12 · a click before `load()` resolved corrupted the history

Reproduced **and** closed in the running GUI, then re-opened deliberately to
prove the guard is load-bearing. Clicking `a2a3` and `d1c2` without awaiting:

| build | `hist.moves` | landed on |
|---|---|---|
| guard removed (`loading = false` injected) | `["a2a3", "d1c2"]` | `fuwk/3p/P1F1/KWU1[-] b` |
| shipped | `["a2a3"]` | `fuwk/P2p/4/KWUF[-] b` |

In the broken run the history claims two moves while the position reflects only
one: `d1c2` was resolved against the *pre-click* map, so the recorded line and
the recorded position disagree. The backlog's correction is confirmed -- the
existing `if (!next) return;` cannot catch it, because it checks the move
against the stale map, i.e. against the wrong position. "Only masks it" was too
generous; the corrupt entry is plainly visible in the history strip.

Client-side only. The search always runs on the TFEN the server received, so no
proof is affected.

### THB-13 · setup mode silently stripped the promoted flag

Elevated from the reporter's "GUI-only" framing on the backlog's evidence: a
captured promoted piece returns to hand as a **pawn**, so the flag decides which
game is analysed. From `K3/4/2k1/2F~1[-] b`, `c2c1` yields `...[p] w`; without
the marker the same move yields `...[f] w`.

Landed in `72f1344`, the THB-12 commit, rather than in one of its own -- both
edits touch `index.html` and I committed them together. That is one logical
change too many for a commit and is recorded here rather than repaired with
a revert-and-reapply pair that would leave the same history.

Verified in the running GUI: the palette now offers 17 entries, the six
promoted ones rendering a `~`, and selecting `F~` then clicking c1 builds
`fuwk/3p/P3/KWF~F[-] w` -- previously impossible to express at all.

---

## Tier 1 closing gate

Whole batch re-verified at `72f1344`, after all 19 items:

| gate | result |
|---|---|
| `pytest -q` | **80 passed** (43 at the campaign's start) |
| `perft(7)` from start | 1,355,253 |
| Python/C parity walk | green |
| mate in 9 / 13 / 13 | 29991 / 29987 / 29987, default seed **and** `0xC0FFEE` |
| negative hunts d12/14/16, both colours | 0 everywhere |

**The whole tier is node-identical on the search path.** The d12/14/16 counts
below are byte-for-byte the ones recorded immediately after THB-01 landed, so
none of the nineteen correctness fixes moved a single node:

| depth | White | Black |
|---|---|---|
| 12 | 172,052 | 9,717 |
| 14 | 1,244,163 | 222,736 |
| 16 | 9,616,663 | 1,791,866 |

That matters for the tiers that follow: this is the baseline tiers 4 and 5 will
be measured against, and it is unchanged from the one taken at the top of the
campaign.

### TH-01 · "there are no search extensions, so the ply budget is exact"

Re-read after THB-01 landed, and the item needs restating rather than applying
as filed. The **claim** is now true: form M guarantees a reported mate distance
never exceeds the depth. The **reasoning** was never right -- extensions were
not what broke it, a TT cutoff at a node with no budget left was, and removing
extensions would not have helped. So the correction is not the backlog's
"a reported mate distance may exceed d" (which describes the pre-fix engine and
would now be false); it is to name both of the things that make the budget
exact, so that deleting either one is visibly a contract change.

### TH-02 · one proof grade sold for two claim strengths

All four sites the merge counted were verified still present and all four are
edited: `README.md`, `solve_status.json` (whose `note` restated the grade and
whose key names, `proven_bounds` and `proven_wins_found`, use one word for
both), the `th_mate_hunt` comment in `tinyhouse.c`, and `fmtVal` in
`index.html`.

The wording now separates three grades, and the separation had to be corrected
in **both** directions the backlog names:

- a reported mate is a proof of the win **and**, since `TT_BUDGET_GUARD`, of
  the distance -- "exposed to the TT-extension defect" would overstate it, the
  defect made "within N plies" false, never the proof itself;
- a negative bound is **not** unconditional either: immune to horizon
  unsoundness, to a cutoff overrunning its budget and to store-side GHI, but
  carrying the Zobrist-collision residual (TH-06), which is unquantified rather
  than zero;
- `snd === 3` is an exact *game* value, not the "exact at this depth" the GUI
  claimed -- that one was a mis-claim, not an over-claim.

Key names in `solve_status.json` are left alone on purpose: they are the
machine-readable contract the GUI reads, and the note now says what they mean.

### TH-05 · the recorded method contradicted the documented command

The contradiction is confirmed by git order: `--workers` defaulted to 2 from
`7b3b902`, and `2125a70` then recorded `"method": "... single thread"`. The
README's reproduction commands passed no `--workers` at all, so following them
did not reproduce the recorded condition.

**Fixed at the source rather than in the prose.** The default is 1 now, and
this is why (three fresh runs each, `--tt 20`, start position, White):

| workers | depth 6 | depth 8 | depth 10 |
|---|---|---|---|
| **1** | **467 / 467 / 467** | **3,420 / 3,420 / 3,420** | **23,635 / 23,635 / 23,635** |
| 2 | 786 / 807 / 792 | 3,810 / 3,802 / 3,817 | 26,149 / 26,064 / 26,103 |

Lazy SMP cannot reproduce its own node count, let alone anyone else's, and one
and two workers tie within noise at depth 18 (median 27.8s vs 28.4s), so
determinism costs nothing measured.

**What could not be repaired, said plainly**: the worker count in force for the
two recorded runs is not knowable now. `solve_status.json` says so rather than
asserting "single thread", and records the deepening schedule (one process,
from depth 6 in steps of 2) that was missing. The *claims* never depended on
any of it -- a null-window hunt returning 0 proves the negative whatever the
thread count -- only the node counts do, and they are now labelled as not
exactly reproducible.

### TH-03 · rep-safety "keeps the graph-history interaction problem out"

Confirmed overclaim, and re-read against the current code: the probe applies no
path condition and `TTView` records nothing about which path an entry came
from, so rep-safety governs the **store** side only. `README.md` pointed
readers at this block as the authority, so both were edited.

Both mitigations the reports did not credit are checked and stated: the
path-repetition scan runs **before** the probe, so a node repeating a
current-path ancestor can never take a stored decisive value; and the residual
is one-directional, landing on a possible over-claimed win and never on a
fabricated "no win". The threefold caveat is recorded too -- under real
threefold rules a winning strategy may pass through a once-repeated position,
which this engine scores as a draw, so its negatives are *conservative* with
respect to threefold rather than identical to it.

**The item's cheap mitigation was run, not just described.** The recorded
mate-in-9 PV replays move by move from `fuwk/3p/P1F1/KWU1[-] b`: all nine plies
legal, **no position repeats**, and it ends with White to move and checkmated
(`result == -1`). It is now a test, so a change that made the published line
illegal or repetition-dependent would fail rather than be argued about.

### TH-06 · the negative bounds need the second-seed re-run too

Confirmed at the cited site: the prompt lived inside `if v > 29000:` and the
negative branch printed nothing. The argument survives because it is not
covered by the other two immunity arguments -- horizon unsoundness and the
ply-budget guard are both *directional*, and a 64-bit collision has no
directional structure at all. In the hunt window a colliding `TT_UPPER` entry
with `v <= alpha` prunes a subtree that may hold a real mate.

The risk is **higher** for the negatives than for the wins, on two counts: the
negative runs are the high-node-count ones, and *any* low-valued colliding
entry suffices, whereas a false positive needs a collision that happens to hold
a mate score.

Printed at the **end** of the run rather than per depth, so the command it
prints names the depth actually being trusted. Verified on all three exits:

- normal exit at maxdepth 10 -> `bound so far: no forced WHITE win within 10 plies` plus the seeded re-run command;
- **SIGINT** (a real `kill -INT` against a running hunt) -> exit 130, "checkpoint is current", advice naming depth 16, the deepest proven;
- win branch -> unchanged, still prints it.

A run already under `--seed` says so instead of suggesting a third seed.

**Incidental confirmation of TH-19**: the interrupted run reported 9,746,928
nodes at depth 16, against 9,616,663 for the same depth run cold in its own
process. Iterative deepening in one process carries `history` over. That is the
instrument tier's problem and it is real.

### TH-04 · the `PERFT_ORACLE` docstring overclaimed its provenance

All three defects confirmed, and the merge's first-hand note is upheld: nothing
in the repo enumerated the 33 depth-2 nodes, the "three independent
implementations" were three models of one family working from one document and
none of them is in the tree, and `perft(6)`/`perft(7)` had no stated provenance
at all.

**Rather than only weakening the claim, the missing artifact was produced.**
Depth 2 is now decomposed per root move -- `a1b2` 5, `a2a3` 6, `b1b2` 6,
`c1b3` 3, `c1d3` 6, `d1c2` 7, summing to 33 -- which is small enough to check
against `RULES.md` by hand, and that is what "hand-verified" should have meant.
Depth 1 was already pinned move by move.

The rest is restated honestly: the from-spec cross-check was real but is a
transcription check rather than independent derivation, since `tinyhouse.c`
declares itself a mirror of `tinyhouse.py`; and `perft(6)`/`perft(7)` are
config-drift signatures, pinning that the engine has not changed rather than
that it was ever right. **Not wrong**: every oracle number itself.

### TH-07 · "exists exactly twice" vs code rejecting only `> 2` — MOOT

Already resolved, and not deliberately: the comment moved into
`Position.validate()` during THB-05's refactor and was rewritten as "exists **at
most** twice in the game (board plus both hands)", which is exactly the change
this item asks for. Verified at `tinyhouse.py:204`. Implementing it again would
be a no-op, so it is recorded MOOT rather than CONFIRMED.

The item's own reasoning is re-measured and holds: of the 33 TFEN literals in
the repo's Python, **8 are full, 11 are under-full** and 14 are deliberately
malformed rejection cases. Enforcing `n != 2` would reject most of the rules
suite, so softening the doc was the right direction and tightening the code
would have been wrong.

### TH-19 · `history` was never reset, so in-process repeats were not samples

Reproduced with causation, five repeats of an identical depth-13 hunt, fresh
`th_tt_init(22)` before every one:

| | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| one process | 757,431 | 839,298 | 845,107 | **1,345,672** | 795,066 |
| separate processes | 757,431 | 757,431 | 757,431 | 757,431 | 757,431 |

A **+78%** worst case, worse than the +11.5% the backlog measured, and the
backlog's correction stands: the repeats get *slower*, not faster, and they do
not converge back.

**Two questions, deliberately answered separately.** Measurement wants the
table cleared between repeats: that is `th_clear_history()`, an explicit call
for harnesses that changes no search behaviour whatsoever. Search strength is a
different and still-open question -- carry-over across successive
iterative-deepening depths may well be worth keeping -- so
`CLEAR_HISTORY_AT_ROOT` exists and stays **0** until someone measures that
experiment, which is not this one.

**Instrument demonstrated against a known case, as the tier requires.** With
`th_clear_history()` between repeats the in-process five become
757,431 five times, identical to the separate-process baseline. And
`scripts/bench_workers.py --depth 13 --workers 1,2` now prints
`median nodes 757,431` -- matching the cold-process number exactly, where
before the fix its `{n/1e6:8.0f}M` format printed `1M` for both arms.

The damage was **between** arms, not within them: the script loops worker
counts in the outer position, so the first count was the only arm ever holding
a cold-history sample, and helper threads are always cold. The bias sat in
precisely the comparison the script exists to make.

### TH-18 · pin the recorded proofs

The invariant holds on the current engine and is as robust as the merge found:
`th_root_moves(start, d)` gives `d1c2 = -29990` with the other five root moves
0, across **depths 10/11/12, five Zobrist seeds, and table sizes 2^0 through
2^24** (2^0 being one entry, effectively no table). Nine parametrised cases,
all green.

**But the backlog calls this "the highest-value instrument in the backlog", and
that is measured to be wrong.** Five mutations planted in `search()`, each
built and run against this exact pin:

| planted mutation | values | node count |
|---|---|---|
| TT mate-score ply re-basing removed | miss | **catch** (99,143 vs 95,783) |
| root killers not reset | miss | miss |
| mate-distance pruning clamp removed | miss | **catch** (106,568) |
| history update removed | miss | **catch** (98,562) |
| rep-safety store gate removed | miss | **catch** (95,781) |

**Values catch 0 of 5. Node counts catch 4 of 5.** The stability that makes
this a good pin for a *published number* is exactly what makes it a poor
*regression detector*: it is a proof, and a proof is robust to almost any
change that does not break soundness outright.

So the value assertion stays -- it is the right guard for the headline claim,
and the backlog's warning against asserting the node count here is well taken,
since a warm table collapses it from ~95,783 to 6. But the regression detector
is TH-20's node field, not this. That reorders the tier: TH-20 is the
high-value instrument, and this is the record-keeping one.

(The killers mutation is invisible to both because `th_root_moves` calls
`search()` directly and never goes through `root_search`, where the reset
lives. A real coverage gap, recorded rather than papered over.)

### TH-20 · paired nodes-to-depth + solver-digest harness

`scripts/regress.py`, 8 frozen positions x depths 10 and 12, fresh table and
cleared history per entry, ~2s. Deterministic: three consecutive runs give
digest `651da0519b02a4b7` and 6,476,533 nodes exactly.

**Calibrated, not assumed.** The same five mutations planted for TH-18, each
built and run through this harness:

| planted mutation | caught by | margin |
|---|---|---|
| TT mate-score ply re-basing removed | digest (values changed) | — |
| root killers not reset | nodes | +3.53% |
| mate-distance pruning clamp removed | nodes | +0.30% |
| history update removed | nodes | **+22.97%** |
| rep-safety store gate removed | nodes | **-0.02% (4 nodes)** |

**Five of five, against zero of five for the published-value pin.** The killers
mutation is the interesting one: TH-18 misses it because `th_root_moves` calls
`search()` directly, while this goes through `root_search` where the reset
lives. Coverage of the real entry point is what made the difference.

The margins span three orders of magnitude, so the honest claim is bounded: a
mutation quieter than four nodes is not ruled out, and neither field is a
soundness proof. The docstring says so, and says a green run means "nothing
detectably changed".

The backlog's depth guidance is adopted -- 10/12, not 6/8, because at the
shallow pair a path-dependent-store mutation is a one-node difference, which is
luck rather than signal. Its cost estimate was also generous: the harness is
about 110 lines including the comparison and `--lib` calibration path, not the
~48 it projected for the measurement alone.

### TH-22 · the search API had zero cffi signature coverage

Confirmed by audit: of the 20 symbols in the cdef, five (`th_in_check`,
`th_init`, `th_mate_hunt_mt`, `th_search`, `th_solve_mt`) were reached by no
test at all, and `th_key` only appeared inside a comment.

Every declared symbol now has a contract assertion, and the set comparison at
the end means **adding a cdef line without covering it fails the test**.
Calibrated in a scratch mirror against four planted cdef errors:

| planted cdef error | caught |
|---|---|
| `th_key` declared `int` (truncating the 64-bit key) | yes |
| `th_mate_hunt` loses its `color` argument | yes |
| `th_solve` loses its `snd` out-parameter | yes (as an error, in the fixture) |
| a new cdef line with no contract check | yes |

**Two things this cost me, both worth recording.** My first width check was
`assert k1 >> 32`, and it **passed** against the truncated-key mutation: a key
truncated to a signed int comes back negative (-256,898,319), and in Python a
negative `>> 32` is -1, which is truthy. The check is `> 0xFFFFFFFF` now. And a
64-bit return declared `int` is undetectable while the real value stays under
2^31, so `th_nodes` is only pinned as monotonic; the docstring says so rather
than implying coverage it does not have.

Separately, the first draft asserted that `th_tt_save` refuses a *directory*
path. True for a real directory, but `rename()` onto a **symlink** to one
succeeds and replaces the link -- which it duly did to a symlink in the scratch
mirror. The check uses a path under a non-existent directory instead.

### TH-28 · the horizon "non-terminal is UNSOUND" invariant

Invariant #1 -- the reason a mate score this engine reports is a proof at all --
and nothing guarded it. Pinned in both directions on purpose: a non-terminal
horizon node returns `(0, snd 0)`, and a *terminal* reached at the horizon
returns `(-30000, snd 3)` for mate and `(+30000, snd 3)` for stalemate (which
wins here). Pinning only the first would pass a build that set
`SND_LB|SND_UB` unconditionally at the horizon.

Calibrated: a scratch build returning `SND_LB|SND_UB` for a non-terminal
horizon node **fails** this test.

### TH-30 · the Zobrist reseed contract

Landed with the source report's own self-kill heeded: asserting a *value* is
equal under two seeds passes even if reseeding is a complete no-op, so the
contract pinned is that the **keys differ**, over three positions, and that
restoring the original seed restores the original keys.

Calibrated: a scratch build whose `th_seed` returns early after the first call
**fails** this test.

### TH-27 · the SMP hunt agrees with one thread

Workers 1, 2 and 4 all return 29991 with best move `b4c2` at depth 9 on the
recorded line, and 0 at depth 8. Node counts are deliberately not compared:
helpers perturb move ordering, so they differ by construction.

**Honest limit, measured.** A scratch build whose helpers search `depth + 6`
instead of `depth + (i & 1)` **passes** this test. That is not a hole in the
pin so much as the ply-budget guard doing its job -- the deeper entries such a
helper writes are refused at reuse when their mate distance overruns the
budget. The pin asserts that the proof agrees, which is what it claims, and not
that the helper schedule is unchanged.

### TH-32 · a paired NPS bench for the C search

`scripts/bench_ab.py`. `bench_workers.py` answers "how many threads", which is
a different question; this answers "did this change to tinyhouse.c pay".

Built around the three things that make that measurable here: a **fresh process
per repeat** (history carry-over is worth up to 78% of a node count on its
own), **interleaved A/B/A/B** rather than blocked AAA/BBB because this machine
throttles, and the **first repeat discarded** with medians and spread reported.
It reports node identity separately from time, and prints NULL itself when the
delta is inside the worst spread.

**Calibrated against the null hypothesis**: two byte-identical builds compared
through it give **+0.4%** (hunt d14) and **-0.6%** (perft 7), both inside a
1.1-1.2% spread, both correctly reported NULL. That fixes the noise floor for
the tiers that follow at roughly **1%**, so a tier 4 claim below about 2% has
to be treated as unproven rather than small.

It also uses CPU time rather than wall clock, which is the one that does not
move when something else on the machine wakes up.

### TH-31 · `th_nodes()` has no reset, and does not count perft

Both facts re-verified: neither `th_tt_init` nor `th_seed` resets the counter,
and `th_perft` does not feed it at all -- `th_nodes()` is byte-identical across
a `perft(5)` returning 16,021. All three shipped callers difference correctly,
so nothing is broken; what was missing is that the contract was written down
nowhere and nothing would catch it changing.

**No reset entry point added, deliberately.** Differencing is correct under
concurrency and a reset is not, and every caller already differences. The
counter's contract is now in the code and pinned by a test, which is the
smaller change and the one that keeps working when a second thread appears.

### TH-34 · expose `snd` from `th_mate_hunt_mt`

A literal 0 was passed through, so the one self-consistency check available
here could not be run at all. The framing correction is upheld: the PROVEN
verdict does not rest on these flags -- with no static eval a mate score can
only come from a real terminal, so a root fail-high above `MATE_BOUND` is
already a proof -- but a check nobody can run is worth nothing.

**The trap is real and was measured before wiring the check.** Root flags by
branch:

| hunt | depth | value | snd |
|---|---|---|---|
| start, White | 8 / 10 / 12 / 14 | 0 | **0 at every depth** |
| recorded mate-in-9, Black | 9 / 11 | 29991 | 1 (`SND_LB`) |

So the assertion is gated on the win branch only, exactly as the backlog warns.
Asserting anything on the negative branch would fire at every depth of every
real hunt. `solve_hunt.py` exits with a loud message if a reported win ever
lacks `SND_LB`.

The flags are returned in the hunted colour's frame, which needs the same
LB/UB swap as everything else on the negated branch.

### TH-35 · expose `snd` from `th_root_moves`

**The sign correction is right and load-bearing, and it is now visible in the
API.** From the start at depth 10, `d1c2` scores **-29990 with snd 2**
(`SND_UB`) -- an *upper* bound in White's frame. The raw child flag is
`SND_LB`; a badge reading it unswapped prints "lower bound" for an upper one.

And the obvious acceptance test would have shipped that bug: "proven only when
`snd == 3`" is invariant under the swap. The test written here asserts the
mate row is specifically 2.

The payoff correction is confirmed too: **all five quiet root moves carry snd 0**
at depth 10. Proven draws are not reachable at GUI depths, so what this
actually carries is mate-row soundness -- which is what the GUI now shows, via
`fmtVal(mv.value, mv.snd)` instead of a hardcoded 0.

### TH-24 · the Python/C parity walk started only from the start position

Random play from the start reaches promotion and full hands vanishingly rarely,
which is exactly where the two engines are most likely to diverge. The walk is
parametrised over the five `PERFT_ORACLE` roots now, which between them begin
with eight pieces in hand, a promotion one push away, and a mao check with a
single blocking drop. Cost: 0.2s.

### TH-23 · `attacked()` against an independent geometric oracle

Confirmed as **missing coverage, not a suspected defect** -- and nothing is
hiding in it. An oracle written from `RULES.md` prose and deliberately derived
in the opposite direction (the engine reads reverse tables to ask "who attacks
this square"; the oracle walks pieces forward and asks "where does this piece
attack") agrees over **94,624 comparisons, 0 mismatches**.

**Sensitive, checked rather than assumed.** Three planted geometry bugs, each
in `tinyhouse.attacked()`:

| planted bug | caught |
|---|---|
| king no longer attacks orthogonally | yes |
| only the first mao origin considered | yes |
| pawn attack direction flipped | yes |

**Scope note, carried from the backlog and still true**: this covers the ATTACK
direction only. `ORTH`/`DIAG`/`PCAPS` are also consumed by `pseudo_moves`
alongside `KINGN` and `MAO_MOVES`, and that direction is still verified by
nothing but perft.

### TH-26 · `solve_hunt` resume/checkpoint round trip

Three runs against one scratch checkpoint, plus a fourth: prove through depth
8; resume and continue at 10 without redoing 6 or 8 (`resumed from ... table
reloaded`); `--fresh` starts over from 6; and a checkpoint whose recorded
`build` is altered prints `differs in build; starting fresh` rather than
laundering one engine's proof into another's. Resume is the documented
overnight workflow and had no test at all.

### TH-33 · cross-check `state_count.py`, delete its dead stub

The `placements()` stub raised `NotImplementedError` and was called from
nowhere; a `dup` variable was computed, multiplied only by 1, and never used;
`Counter` was imported inside the innermost of four nested loops. All gone, and
the headline is unchanged at **17,669,515,462,968** (`/4` = 4,417,378,865,742),
matching `RULES.md` to the digit.

**The arithmetic now has something checking it.** The full count cannot be
enumerated -- that is the point of it -- so `--verify` counts a sub-problem two
ways: two kings plus the two W units, analytically by the same class-multiset
technique the full count uses, and by brute-force enumeration sharing no line
of code with it. **131,976 both ways.** That validates the technique, not the
arithmetic of the larger loops, and the comment says exactly that.

`opus-5`'s kill of the Burnside claim is confirmed by argument and recorded in
the file: the group acts **freely** here, so `total/4` is exact. The file mirror
fixes no square (a<->d, b<->c, no central file), so the white king can never map
to itself, and sigma maps white pieces to black ones. No correction is needed
or correct.

### TH-29 · pin a draw-by-repetition proof — and the backlog's premise is wrong

The item says a hand-crafted position where no line reaches the horizon is
required, on the evidence that 3,613 low-material positions searched to depth
14 produced **zero** proven draws. **It is not the position that was missing.
It is the depth.**

**Why, measured before searching for one.** A draw proof needs every line to
reach a terminal or a repetition before the horizon, so it needs a
**terminal-free** closed component. 400 random low-material roots, closure
computed exactly with a 3,000-state cap:

| | |
|---|---|
| closure computable at all | 169 of 400 |
| terminal-free components among them | **169 of 169** |
| distinct component sizes seen | **312, and only 312** |
| terminal-free AND small enough (<= 60 states) to search cheaply | **0** |

Every terminal-free component is the same one: bare kings, **312 states**,
which is 156 non-adjacent ordered king pairs times two sides to move -- an
independent confirmation of `state_count.py`'s king-pair term, arrived at by
graph search rather than by combinatorics. Everything with material has a
terminal on some line, so its value is a win or a loss, not a draw.

**The proof exists.** `4/4/4/K2k[-] w`, one process, fresh table each depth:

| depth | 8-74 | 76, 78 | **80** |
|---|---|---|---|
| snd | 0 | 2 | **3** |

`v = 0, snd = SND_LB\|SND_UB` -- the code's own encoding of an exact game value.
335M nodes, 19.5s. The node curve is why depth 14 never had a chance: it grows
x3.6 per 4 plies to depth 40 and then **flattens to x1.0-1.1** by depth 64 as
repetition closes the component off, which is the shape of a search running out
of new states rather than one exploding.

Seven bare-king roots were then measured for the cheapest exact proof;
`2K1/4/4/2k1[-] w` at depth 100 costs 117M nodes and **6.9s**, and that is what
the test uses. Marked `slow` and excluded from the default `pytest -q`, with
the counterpart test asserting the same position is **not** proven at depths 14
and 40 -- without which an engine returning `snd == 3` everywhere would pass.

This also corrects the merge's own note on TH-36: "cannot prove a draw at any
depth at which any line still reaches the horizon" is right, and the honest
addition is that such a depth is reachable today for bare kings. It is
nowhere near reachable for the start position, which is what df-pn is for.

### TH-25 · symmetry-orbit perft — REJECTED, measured

The factual half is confirmed: all four orbit members (identity, file mirror,
sigma, and their composition) of all five `PERFT_ORACLE` positions match the
published counts exactly, 0 mismatches.

The value proposition is refuted, and independently of the merge's own
measurement. Eight rules bugs planted in `pseudo_moves`, each run against both
the identity-position assertion and the orbit-only members:

| planted rules bug | identity | orbit-only |
|---|---|---|
| ferz loses two diagonals | CAUGHT | caught |
| wazir loses one direction | CAUGHT | caught |
| king loses its diagonals | CAUGHT | caught |
| mao ignores its blocker | CAUGHT | caught |
| pawn droppable on rank 4 | CAUGHT | caught |
| pawn pushes two squares | CAUGHT | caught |
| promotion offers only F | CAUGHT | caught |
| capture-promotion offers only W | CAUGHT | caught |
| **total** | **8 of 8** | **0 additional** |

The merge measured 6/8 for the orbit against 8/8 for the identity and killed it
on that; this measures 8/8 against 8/8, which is the same verdict reached from
the other side -- the orbit is strictly dominated either way, because it is
blind to any error symmetric under the group, which is every uniform geometry
error. Roughly 30 lines of test for zero measured detection: **not merged**.

The residue is kept where it does pay: `sigma` lives in `test_server.py`, where
a colour-mirrored pair is exactly the right instrument for the TH-40 frame
duality.

---

## Tier 4 — NPS. Measurement conditions

Apple M2 Pro, 10 cores, 16 GiB, Darwin 25.5.0. `pgrep solve_hunt|server.py`
empty for every run, but the machine was **not otherwise quiet** -- Chrome was
using 60-70% of a core throughout, load average ~3. That is why every result
below carries a **same-build control arm** measured in the same interleaved
session: individual runs scatter 3-11%, while the medians of two byte-identical
builds land within 0.2-1.1%. The control delta is the noise floor, not the
spread.

### TH-08 · horizon fast path — CONFIRMED, and smaller than reported

Node-identical, which is the acceptance test: 1,319,149 / 9,616,663 / 97,099 on
every arm, and the regression digest `651da0519b02a4b7` unchanged.

| workload | control | TH-08 | verdict |
|---|---|---|---|
| solve d14, start | +0.36% | **+4.04%** | signal |
| hunt d16, start | -0.23% | **+3.69%** | signal |
| hunt d16, start (second session) | +0.44% | **+3.93%** | signal |
| solve d12, drop-heavy `1k2/4/2K1/4[PFUWpfuw] w` | +1.09% | +0.51% | **NULL** |

**Two corrections to the backlog, both measured.** The reported gains were
1.104x on the hunt and 1.124x on solve d14; the real figures are **1.037-1.040x**
and **1.040x** -- about a third of the claim, consistently across three
sessions. And the reported **1.210x on a drop-heavy position does not reproduce
at all**: +0.51% against a +1.09% control is NULL. That is the workload the
item singles out as its best case.

**The toggle-off pin is node-identical but not time-identical, and that is
worth saying.** `HORIZON_FAST_PATH 0` measures **-2.42%** against the original
tree, so the restructuring alone (hoisting `pseudo_moves` past the horizon
branch and moving the existence test into its own function) costs about 2.4%,
and the fast path itself buys about 6.5% over that. The net gain over the
previous tree, which is the number that counts, is **+3.9%**.

### TH-09 · drops from a precomputed empty-square set — CONFIRMED

Node-identical on every arm (1,319,149 / 9,616,663 / 97,099 / perft 1,355,253),
digest unchanged. Ascending square order preserved deliberately: emission order
is what move ordering sees.

| workload | control | TH-09 | verdict |
|---|---|---|---|
| solve d14, start | +0.10% | **+5.24%** | signal |
| hunt d16, start | -0.02% | **+5.56%** | signal |
| hunt d16, start (second session) | +0.26% | **+5.15%** | signal |
| solve d12, drop-heavy | -0.78% | **+6.06%** | signal |
| perft(7), start | +0.43% | +1.00% | marginal |

**Toggle-off is a clean pin here**, unlike TH-08: `DROP_EMPTY_MASK 0` measures
**-0.04%** against the original tree, node- and time-identical, because the
`#else` branch is literally the old loop.

**Correction to the backlog on perft.** The reported perft figure is 1.071x;
measured, it is **1.010x**, seven times smaller. The reason is visible in the
change itself -- the mask loop is gated on a non-empty hand, and hands are
empty for most of a perft from the start position, so there is nothing to save.
The search figures do broadly hold up (reported 1.063x / 1.087x, measured
1.052x / 1.056x), and the drop-heavy case is the best of them at 1.061x.

**The trap the item names is left alone on its evidence**: the mask is built in
its own gated loop and NOT accumulated inside the piece loop, which already
walks all 16 squares and looks like the better place for it. That variant was
reported 6.5% slower and was not re-litigated here.

### TH-10 · incremental Zobrist key — CONFIRMED, and the reported downside designed out

Node-identical; digest unchanged.

| workload | control | TH-10 | verdict |
|---|---|---|---|
| solve d14, start | -0.11% | **+7.92%** | signal |
| hunt d16, start | +0.05% | **+7.44%** | signal |
| hunt d16, start (second session) | +0.02% | **+7.47%** | signal |
| solve d12, drop-heavy | -0.24% | **+3.78%** | signal |
| perft(7), start | +0.14% | +0.34% | neutral |

**The backlog's "omitted downside" is designed out rather than accepted.** It
reports perft(8) at 0.955x -- a 4.7% loss -- because make/unmake would maintain
a key that perft and `th_moves` never read, and says avoiding it needs two
make() variants that no report budgeted for. Threading the key through
`search()` as a parameter instead costs those callers **nothing**: perft
measures **+0.34%**, neutral, and no second make() variant exists.

**Both reported traps are disposed of by the same choice.** There is no shared
"current key" to go stale, so the SMP trap cannot occur -- the main thread and
every helper call `th_key()` for their own root. And the hand-count update does
use **two** xors, because `th_key` xors `zob_hand` for every count including 0.

**Soundness checked, not argued.** A `KEY_PARANOIA` build asserts
`key == th_key(p)` at every node. Under it: the whole regression harness
(6,476,533 nodes, digest unchanged), all three published proofs at their exact
distances, the depth-100 draw proof (117M nodes), and a 4-worker SMP hunt --
**zero mismatches**. The toggle ships at 0 and is one line to flip.

Toggle-off measures +0.24% against the original tree: a clean pin.

### Tier 4 cumulative after TH-08, TH-09, TH-10

| workload | tier-4 start | now | control |
|---|---|---|---|
| hunt d16, start | 3.033s | **2.594s** | +0.10% |
| solve d14, start | 0.427s | **0.366s** | -0.66% |

**+16.9% on both**, node-identical throughout (9,616,663 and 1,319,149 on every
arm). The three individual gains multiply to 1.175 against a measured 1.169,
which is the consistency check that they are independent and really additive.

### TH-12 · hoist `king_sq` out of the legality loop — CONFIRMED, and the unmeasured half is now measured

Node-identical; digest unchanged; the slow proofs still pass.

| workload | control | TH-12 | verdict |
|---|---|---|---|
| perft(7), start | +0.02% | **+10.16%** | signal |
| perft(4), drop-heavy `1k2/4/2K1/4[PFUWpfuw] w` | -0.11% | **+39.56%** | signal |
| solve d14, start | -0.33% | **+2.53%** | signal |
| hunt d16, start | +0.19% | **+2.95%** | signal |

The item calls the search-side effect **UNMEASURED**; it is **+2.5 to +3.0%**.
Its perft figure (1.092x at low load, 1.059x under contention, 1.144x at
perft(8)) brackets the +10.16% measured here at perft(7), so "not reproducible
as a single number" is fair and the range holds.

The **+39.56% on drop-heavy perft** is new. It follows from the mechanism: a
drop-heavy node has many pseudo-moves, and the hoisted 16-square scan was paid
once per move.

**The trap the item names is in the code and load-bearing.** The drop test comes
first, because for a drop `M_FROM(m)` is the piece TYPE (0-3), which aliases
square indices 0-3 -- a bare `M_FROM(m) == ks` would false-positive whenever the
mover's own king stands on rank 1, which is where it starts.

### TH-11 · fast legality — CONFIRMED for perft, REJECTED inside search

Both halves built and measured separately, which is why the item ships with two
toggles rather than one. Node-identical on every arm; digest unchanged.

| workload | control | `FAST_LEGALITY` (shipped) | also in `search()` |
|---|---|---|---|
| perft(7), start | -0.56% | **+28.46%** | +29.00% |
| perft(4), drop-heavy | +0.04% | **+110.83%** | +110.83% |
| solve d14, start | +0.01% | +0.03% (NULL) | **-0.78%** |
| hunt d16, start | +0.07% | +0.07% (NULL) | **-0.68%** |

**The backlog's verdict is confirmed exactly**: a large win for perft, a small
but real **loss** inside the search. Its own correction to the reported 3-6%
search regression -- "overstated, measured 0.1% to 2.1%" -- also holds: I
measure a 0.68-0.78% loss. `FAST_LEGALITY_IN_SEARCH` stays **0**, with the
measurement in the file next to it.

**The perft figures are lower than reported (1.391x / 2.193x against 1.285x /
2.108x), and the reason is the campaign's own re-baselining rule.** TH-12
landed first and made the legality test this skips cheaper, so there is less
left to save. Measured against the original tree the merge's numbers would
stand; measured against the tree as it now is, these are the numbers.

**Both traps are in the code, and the equivalence is checked rather than
argued.** Perft agrees with the toggle-off build on eight positions including
three with a **promoted mao** (`3k/2U~1/4/K3[-] b` 8,112; `2k1/1U~2/4/1K2[-] b`
10,097; `1k2/2U~1/1K2/4[f] b` 18,687), which is trap B's exact case -- the
origin test is `TYPE(pc) == U`, since `attacked()` ignores the promoted bit and
a pawn can promote to U. Trap A is the `!in_chk` gate: a mover in check must
block, and without the gate perft(6) reads 3,226,861 against 139,141.

The underlying theorem is worth stating plainly, because it is what makes this
safe at all: **this game has no sliders**, so nothing can be pinned. A move can
only expose the mover's own king by moving the king, by being made while
already in check, or by vacating the leg square of an enemy mao aimed at the
king. A capture cannot open a line, because the captured square stays occupied
by the capturer.

### TH-16 · prune drops that cannot resolve a check — the Class A form REJECTED, item reclassified

Built and measured, then reverted. The item promises perft identity "because
every pruned drop was illegal anyway", and that half is true -- `perft(7)` and
the drop-heavy perft both matched exactly. What is not true is that it pays.

**Perft / `th_moves` form (Class A, node-identical), measured:**

| workload | control | TH-16 | verdict |
|---|---|---|---|
| perft(7), start | +0.67% | +0.41% | **NULL** |
| perft(6), `3k/1U2/4/K3[f] b` (a mao check with one blocking drop) | +1.10% | **-1.33%** | **loss** |

It is a small **loss on the exact position it targets**. In-check nodes are a
small minority, the drop section it skips was already cheap, and
`check_block_square` has to walk `ORTH`, `DIAG`, `PCAPS` and `MAO_ATT` to find
out whether it may skip anything.

**And the search form is not node-identical, which is the finding that matters.**
Applying it inside `search()` moved node counts by up to **+7.28%** and
**-5.63%** on individual regression rows and changed the digest --
`811f304f1eef7998` against `651da0519b02a4b7` -- with two positions returning a
different best move. The cause is tie-breaking: `order_score` produces ties
(equal history, typically 0), the selection sort takes the first index holding
the maximum, and removing entries from the list changes which index that is.
So the shortcut reorders tied legal moves.

That is a **Class B change**, and the campaign's own rule -- if you cannot tell,
it is Class B -- puts it in tier 5, not tier 4. It measured **+7.91% with 1.7%
fewer nodes** on hunt d16 in passing, which is worth taking seriously, so the
item is reclassified rather than killed, and gets measured properly on
nodes-to-depth there.

**The regression harness earned its keep here.** The node identity claim was
mine, it was wrong, and the harness said so before the change could ship.

### TH-15 · staged movegen, TT move first — CLOSED PRE-MEASUREMENT

Not implemented, because a probe build measured the ceiling first and it is
below the instrument's noise floor. Counters added to `search()`, run on
hunt d16 and solve d14 from the start position:

| | hunt d16 | solve d14 |
|---|---|---|
| interior nodes (generated a move list) | 4,959,734 | 5,646,912 |
| ...that had a TT move at all | **53,429 (1.1%)** | 55,171 (1.0%) |
| ...where the first searched move cut off | 4,313,893 (87.0%) | 4,907,267 (86.9%) |
| ...and that first move *was* the TT move | **32,218 (0.6%)** | 33,141 (0.6%) |
| moves generated | 91,369,473 (18.4/node) | 103,913,845 (18.4/node) |

The node-identical subset can only skip generation where a TT move exists and
cuts off first: **0.6% of interior nodes**. Even saving 100% of the work there
lands under the ~1% noise floor measured in tier 3, and it would be bought with
a `is_pseudo_legal` validator for TT moves -- which is a new wrong-PROVEN vector
if it is ever wrong, since a colliding entry would otherwise hand `make()` an
illegal move.

Why so few TT moves: unproven depth-1 stores are skipped deliberately (they are
~74% of write traffic) and the hit rate never exceeds ~5.3%.

**Two numbers worth keeping from the probe**, because they price other work:
**87% of interior nodes cut off on their first searched move** -- the ordering
is already doing its job, which is exactly why a TT move adds so little -- and
**18.4 moves are generated per node** to use one. That is the case for *lazy*
generation, which is the item's non-node-identical half, and it is a tier 5
question rather than a tier 4 one.
