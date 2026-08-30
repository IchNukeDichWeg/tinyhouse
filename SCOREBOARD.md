# Scoreboard

One row per campaign item, in the order they were closed. Every item lands
here, including the rejected ones — **a rejected item that is measured,
reverted and recorded is a success**; an item that lands unmeasured is not.

## Measurement protocol (tiers 4-5)

- Machine: recorded as Apple M2 Pro, 10 cores, 16 GiB, Darwin 25.5.0 — that
  attribution was never verified and the project has since been found running on
  an Apple M5 Pro, 18 cores, 64 GiB. Ratios between arms measured in the same
  session remain valid (that is what the control arm is for); absolute times and
  anything tied to core count or RAM should be re-measured before being trusted.
  Every number below is
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
| 1 | THB-01 | 0 | **CONFIRMED** | fix costs nothing on the bounds path: start-position negative hunt d16 White 9,913,857 -> 9,616,663 nodes (-3.0%), Black 1,824,606 -> 1,791,866 (-1.8%); repro position d13 8,279,609 -> 8,988,304 (+8.6%) | `4b2fea1` |
| 2 | THB-02 | 1 | **CONFIRMED** | parse-time rejection; no node-count effect (perft(7) 1,355,253 unchanged) | `92d50ec` |
| 3 | THB-03 | 1 | **CONFIRMED** | parse-time rejection; no node-count effect (perft(7) 1,355,253 unchanged) | `f0c9ffb` |
| 4 | THB-05 | 1 | **CONFIRMED** | perft(7) 1,355,253 unchanged; whole-suite cost of validating every to_c call is 4.63s -> 4.68s (noise) | `8299c65` |
| 5 | THB-04 | 1 | **CONFIRMED** | perft(7) 1,355,253 unchanged; guard is a no-op on legal input (no king capture is generated from a validated position) | `72bcc55` |
| 6 | THB-06 | 1 | **CONFIRMED** | parse-time rejection; perft(7) 1,355,253 unchanged | `08ca8eb` |
| 7 | TH-21 | 3 | **CONFIRMED** | coverage; suite 59 -> 61 tests, +0.0s | `885669e` |
| 8 | THB-07 | 1 | **CONFIRMED** | foreign-rule dump: rc 0 -> -3; header 24 -> 32 bytes, so pre-existing dumps are invalidated by design | `3f5113b` |
| 9 | THB-08 | 1 | **CONFIRMED** | failed save: silent exit-0 -> WARNING + intact previous dump; perft(7) 1,355,253 unchanged | `55cd265` |
| 10 | THB-10 | 1 | **CONFIRMED** | depth 0 and -5 now clamp to 1; repo DB had 0 rows to clean (4 rows, depths 8/14) | `09e1b17` |
| 11 | THB-09 | 1 | **CONFIRMED** | unproven rows no longer stored; build_book 8 1 keeps 0 of 7 visited (nothing that shallow is proven) | `804931c` |
| 12 | TH-41 | 1 | **CONFIRMED** | labelling only; no engine or node-count effect | `9ab8c06` |
| 13 | TH-42 | 1 | **CONFIRMED** | cache namespace now moves with the engine: editing #define MATE moved it 3697319324787062899 -> 8643824827813915791 (was: unchanged) | `c0a10a7` |
| 14 | TH-40 | 1 | **CONFIRMED** | mirrored pair now reports snd 2 vs 1 (was 1 vs 1); cache namespace moves automatically via TH-42 | `df08006` |
| 15 | THB-11 | 1 | **CONFIRMED** | contended trivial request: unbounded wait -> 503 after 20s; GUI depth cap 22 -> 16 on measured cost (d16 10.25s, d18 98.77s cold) | `f8a45ed` |
| 16 | TH-44 | 1 | **CONFIRMED** | planted IsADirectoryError: absolute path in a 400 body -> 500 'internal error', path only on stderr | `8a87d45` |
| 17 | TH-43 | 1 | **CONFIRMED** | node-identical (9,616,663 hunt d16 and 1,319,149 solve d14 on both arms); time x0.993/x1.000, inside spread | `6adb911` |
| 18 | THB-15 | 1 | **CONFIRMED** | flag on: import now raises; divergence Python 6/36/274/2181/19317 vs C 6/33/241/1855/16021 | `8edae02` |
| 19 | THB-14 | 1 | **CONFIRMED** | flags-only edit: dylib unchanged (sha1 4a7c8c7f) -> rebuilt (afeba22c -> 9d16118d) | `e1cb624` |
| 20 | THB-12 | 1 | **CONFIRMED** | browser-verified: two unawaited clicks record 1 move, not 2 (guard removed: 2 moves, wrong position) | `af9dbc6` |
| 21 | THB-13 | 1 | **CONFIRMED** | browser-verified: F~ then c1 builds fuwk/3p/P3/KWF~F[-] w; palette 11 -> 17 entries | `af9dbc6` |
| 22 | TH-01 | 2 | **CONFIRMED** | docs only; the claim is true after THB-01 but its stated reason never was | `c9e589f` |
| 23 | TH-02 | 2 | **CONFIRMED** | docs only; 4 sites, no code path touched (perft(7) 1,355,253, suite 80) | `4734fc2` |
| 24 | TH-05 | 2 | **CONFIRMED** | default workers 2 -> 1; node counts now reproducible run to run (467/3,420/23,635 three for three vs 786/807/792 at 2 workers) | `f067123` |
| 25 | TH-03 | 2 | **CONFIRMED** | PV replay: 9/9 plies legal, 0 repetitions, terminal result -1; perft(7) 1,355,253 unchanged | `3eea775` |
| 26 | TH-06 | 2 | **CONFIRMED** | advice now on the negative branch; verified on normal exit, SIGINT (exit 130) and the win branch | `7301d70` |
| 27 | TH-04 | 2 | **CONFIRMED** | docstring restated; depth-2 divide 5/6/6/3/6/7 = 33 now pinned (the artifact the claim assumed) | `7e5574d` |
| 28 | TH-07 | 2 | **MOOT** | no-op: the comment already reads 'at most twice' after THB-05's refactor; 8 full / 11 under-full literals confirm the doc was the half to change | `802d613` |
| 29 | TH-19 | 3 | **CONFIRMED** | in-process repeats 757,431/839,298/845,107/1,345,672/795,066 -> 757,431 x5 with th_clear_history; bench_workers prints 757,431 not '1M' | `85da37f` |
| 30 | TH-18 | 3 | **CONFIRMED** | 9 pinned cases green; sensitivity measured: values catch 0 of 5 planted mutations, node counts catch 4 of 5 | `c6cf64c` |
| 31 | TH-20 | 3 | **CONFIRMED** | catches 5 of 5 planted mutations (vs 0 of 5 for TH-18's value pin); deterministic, digest 651da0519b02a4b7 / 6,476,533 nodes, ~2s | `6cc9acb` |
| 32 | TH-22 | 3 | **CONFIRMED** | 20 of 20 cdef symbols now have a contract assertion (5 previously untouched); catches 4 of 4 planted cdef errors | `0916b41` |
| 33 | TH-28 | 3 | **CONFIRMED** | both directions pinned; a build with a sound non-terminal horizon fails it | `2533261` |
| 34 | TH-30 | 3 | **CONFIRMED** | keys asserted to differ, not values; a no-op th_seed fails it | `2533261` |
| 35 | TH-27 | 3 | **CONFIRMED** | workers 1/2/4 all give 29991 + b4c2 at d9 and 0 at d8; helper-depth mutation passes (the budget guard absorbs it) | `2533261` |
| 36 | TH-32 | 3 | **CONFIRMED** | null-hypothesis calibration: identical builds measure +0.4% / -0.6% against 1.1-1.2% spread, both reported NULL; noise floor ~1% | `2e5bb87` |
| 37 | TH-31 | 3 | **CONFIRMED** | contract pinned: counter unchanged across th_tt_init/th_seed and across perft(5)=16,021; no reset added | `f23550c` |
| 38 | TH-34 | 3 | **CONFIRMED** | win branch snd=1 at d9/d11, negative branch snd=0 at d8/10/12/14 (assertion gated accordingly) | `014e8b6` |
| 39 | TH-35 | 3 | **CONFIRMED** | d1c2 now reports -29990 with snd 2 (SND_UB); all five quiet moves snd 0 | `014e8b6` |
| 40 | TH-24 | 3 | **CONFIRMED** | walk now starts from all 5 oracle roots (was 1); +0.2s | `ef9cb83` |
| 41 | TH-23 | 3 | **CONFIRMED** | 94,624 comparisons, 0 mismatches; catches 3 of 3 planted geometry bugs | `ef9cb83` |
| 42 | TH-26 | 3 | **CONFIRMED** | resume, --fresh and build-mismatch paths all pinned by subprocess | `4fa63d1` |
| 43 | TH-33 | 3 | **CONFIRMED** | sub-problem 131,976 analytic == 131,976 brute force; headline 17,669,515,462,968 unchanged and pinned against RULES.md | `4fa63d1` |
| 44 | TH-29 | 3 | **CONFIRMED** | proven draw found: 2K1/4/4/2k1[-] w -> v=0 snd=3 at depth 100 (117M nodes, 6.9s); unproven at 14 and 40 | `08cca0b` |
| 45 | TH-25 | 3 | **REJECTED** | orbit adds 0 detections: identity perft catches 8 of 8 planted rules bugs, orbit-only catches 0 more | `e6c342b` |
| 46 | TH-08 | 4 | **CONFIRMED** | +4.04% solve d14, +3.69/+3.93% hunt d16 vs a 0.2-0.4% control; NULL on drop-heavy; node-identical | `2f63cb4` |
| 47 | TH-09 | 4 | **CONFIRMED** | +5.24% solve d14, +5.56/+5.15% hunt d16, +6.06% drop-heavy vs 0.0-0.8% controls; perft +1.00% (reported 1.071x); node-identical | `bcb9ec8` |
| 48 | TH-10 | 4 | **CONFIRMED** | +7.92% solve d14, +7.44/+7.47% hunt d16, +3.78% drop-heavy, perft +0.34% (no regression); KEY_PARANOIA clean over 123M nodes incl. SMP | `4acea58` |
| 49 | TH-12 | 4 | **CONFIRMED** | +10.16% perft(7), +39.56% drop-heavy perft, +2.53% solve d14, +2.95% hunt d16 vs controls under 0.4%; node-identical | `93ab223` |
| 50 | TH-11 | 4 | **CONFIRMED** | perft +28.46% start, +110.83% drop-heavy; inside search -0.78%/-0.68% so shipped OFF there; perft equivalence checked on 8 positions incl. 3 promoted-mao | `6fbb581` |
| 51 | TH-16 | 5 | **REJECTED** | Class A form: NULL on perft(7) (+0.41% vs 0.67% control) and -1.33% on the mao-check position it targets; the search form is node-changing (digest 811f304f1eef7998), so the item moves to tier 5 | `50494fa` |
| 52 | TH-15 | 4 | **CLOSED PRE-MEASUREMENT** | ceiling is 0.6% of interior nodes (only 1.1% have a TT move at all), below the ~1% noise floor | `abf626c` |
| 53 | TH-14 | 4 | **REJECTED** | profile ceiling 40.5% (pseudo_moves 24.5% + attacked 16.0%); the cheap flat-table form measures -1.78/-1.80/-8.52% on three of four workloads | `d0bfa0d` |
| 54 | TH-16 (class B) | 5 | **KEPT-ON-NULL** | nodes +3.04% on the frozen suite (rows -5.63% to +7.28%, tie-break noise); time +8.15/+22.85/+7.91% on three hunts, -3.09% on mao-check perft; 74,702 positions move-set-identical to the Python engine | `8dc56c2` |
| 55 | TH-13 | 5 | **CONFIRMED** | 4 of 200 root flags upgraded, 0 value changes, nodes exactly unchanged at depth 8 and -0.01% at most on the deeper suite | `22c729b` |
| 56 | TH-17 | 5 | **REJECTED** | regression suite -11.21% at weight 512, but the deep hunts go +13.12/+15.17/+19.33% at d14/16/18 and +70.02% on the Black d18 hunt | `c0747ce` |
| 57 | TH-39 | 5 | **CONFIRMED** | node-optimal size moves with depth (2^20 at d16, 2^24 at d18); 2^26 is 14.9% full at d18, so the default is kept for the depth-20+ runs it exists for | `3c5e385` |
| 58 | TH-37 | 6 | **CONFIRMED** | plies 1-8 reproduced exactly and independently (2,036,092 cumulative, no hashing); growth ~6/ply bending to 5.09 by ply 10 | `38c9532` |
| 59 | TH-36 | 6 | **BLOCKED** | prototype returns a wrong DISPROVED on the recorded mate in 9, so none of its diagnostics can be trusted; shipped as groundwork with a strict xfail | `0ce66b1` |
| 60 | TH-38 | 6 | **CLOSED PRE-MEASUREMENT** | no material reduction in crazyhouse, so no shrinking axis; terminals are 0.03-0.16% of positions and grow 6x/ply like everything else; cannot label DRAW | `9efaa6a` |
| 61 | TH-45 | 7 | **CONFIRMED** | browser-verified: black start gives 1...d3d2 / 2.a2a3, white start 1.a2a3 / d3d2 | `e534200` |
| 62 | TH-46 | 7 | **CONFIRMED** | browser-verified: banner, king-square highlight, and c1b3+ in the moves table | `e534200` |
| 63 | TH-47 | 7 | **CONFIRMED** | hardcoded type kept as the safer choice; .svg suffix now required, so it is provably correct | `e534200` |

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
cache setup out of `server.py`'s import (commit `787ee27`) broke
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

Landed in `af9dbc6`, the THB-12 commit, rather than in one of its own -- both
edits touch `index.html` and I committed them together. That is one logical
change too many for a commit and is recorded here rather than repaired with
a revert-and-reapply pair that would leave the same history.

Verified in the running GUI: the palette now offers 17 entries, the six
promoted ones rendering a `~`, and selecting `F~` then clicking c1 builds
`fuwk/3p/P3/KWF~F[-] w` -- previously impossible to express at all.

---

## Tier 1 closing gate

Whole batch re-verified at `af9dbc6`, after all 19 items:

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

### TH-14 · bitboard movegen and `attacked()` — REJECTED, on a measurement of the cheap form

**Ceiling measured first.** A sampling profile of a real depth-18 hunt, self
time:

| function | self |
|---|---|
| `search` | 50.8% |
| `pseudo_moves` | 24.5% |
| `attacked` | 16.0% |
| `key_after` | 6.6% |
| `th_in_check` | 0.6% |

The two functions the item targets are **40.5%** of the work, so a 1.5-2x
rewrite of both would be worth roughly +16% to +25%. That is a real ceiling and
it is why the item was not dismissed on effort.

**Then the cheap form of the same hypothesis was built and measured, and it
loses.** `attacked()` is the half whose result is provably unchanged -- it
returns a boolean, so there is no emission order to preserve -- and the flat
single-table version (one contiguous array of {origin, type-mask, blocker}
instead of four 0xff-terminated walks with four different type tests) measures:

| workload | control | flat table | verdict |
|---|---|---|---|
| solve d14, start | -0.39% | **-1.78%** | loss |
| hunt d16, start | -0.05% | **-1.80%** | loss |
| perft(7), start | +0.25% | **-8.52%** | loss |
| perft(4), drop-heavy | +0.10% | +3.67% | win |

Node-identical throughout, so this is purely representation. Three of four
workloads regress, `perft(7)` badly. The four specialised loops beat one general
one: each is small enough for the compiler to specialise, the common case
(`ORTH`, a wazir or king) returns before the rest is touched, and the flat form
pays a mask test and a wider entry for every candidate.

**Verdict.** The cheap form of "replace the attack representation" is refuted on
this machine, which raises rather than lowers the bar for the expensive form.
True bitboards would need masks maintained through make/unmake -- which TH-10
already showed leaks cost into perft and `th_moves` -- or threaded through the
search, and the item's own verdict is PLAUSIBLE, UNMEASURED, high effort, and
**not node-identical**. Rejected with the profile kept, so a future attempt
starts from the ceiling rather than from a guess.

---

## Tier 4 closing gate and cumulative measurement

Gate at `d0bfa0d`: 106 fast tests + 2 slow, `perft(7) = 1,355,253`, regression
digest `651da0519b02a4b7` unchanged, all three published proofs at their exact
distances, tree clean.

**Campaign start (`4e22dcd`) to now**, same-build control arm in the same
interleaved session, 9 repeats, fresh process each:

| workload | control | tier-4 start | **now** |
|---|---|---|---|
| hunt d16, start | -0.03% | +2.32% | **+22.79%** |
| solve d14, start | +0.52% | -0.21% | **+21.08%** |
| perft(7), start | -0.43% | -0.38% | **+42.48%** |
| perft(4), drop-heavy | +0.13% | -0.85% | **+206.75%** |

Tiers 0-3 moved speed by nothing measurable, which is what they were for. All
of tier 4 is node-identical, so its whole contribution is time per node.

**Separating the two effects on hunt d16**, because they are different claims:
node counts fell **9,913,857 -> 9,616,663 (-3.0%)**, and that happened once, at
THB-01, the P0 soundness fix -- not in tier 4. So the honest split is

- **nodes per second: +19.1%** (`1.2279 / (9913857/9616663)`)
- **nodes to depth: -3.0%**, a side effect of restoring the ply-budget contract

and the wall-clock figure of +22.79% is the two together.

### Why the tier stopped where it did

The campaign's stop condition -- three consecutive non-wins in a performance
tier -- fired on TH-16, TH-15 and TH-14, and it coincides with the tier being
exhausted. Its diagnosis is "either the backlog's estimates are systematically
wrong or your instrument is lying". **The instrument is not lying**: the control
arm measured 0.03-0.52% in the same sessions, and five items in the same tier
measured clean, repeatable wins. The estimates are the part that was off, in
both directions -- TH-08 came in at a third of its claim and TH-10 above its
claim, while TH-16's and TH-14's cheap forms are net losses.

---

## Tier 5 — efficiency (nodes-to-depth)

**Measurement conditions changed part-way through this tier**: from TH-13 onward
the machine is running other work the user started, so **wall-clock and CPU
figures below the TH-16 row are not taken**. Nodes-to-depth is load-independent
and is this tier's metric anyway; anything that needs clean timing is deferred
and handed over rather than guessed at.

### TH-16 (class B) · prune drops that cannot answer a check — KEPT-ON-NULL

**Correctness first, because this removes moves from the list.** 74,702
positions walked from five roots, **7,961 of them in check**, legal move sets
compared against the *Python* engine: **0 mismatches**. All three published
proofs at their exact distances, mate-in-9 still absent at depth 8, the
depth-100 draw proof still `v=0 snd=3`, negative bounds 0 at d12/14/16 both
colours.

**Nodes-to-depth, this tier's metric: a regression.** The frozen 16-row suite
goes **6,476,533 -> 6,673,711, +3.04%**. Individual rows swing from **-5.63%**
to **+7.28%**, which is the shape of tie-break reordering rather than of an
efficiency change: `order_score` produces ties and the selection sort takes the
first index holding the maximum, so shortening the list changes which tied legal
move goes first.

**Time, which is what the change actually acts on:**

| workload | nodes | control | time |
|---|---|---|---|
| hunt d16 White, start | -1.66% | +0.51% | **+8.15%** |
| hunt d16 Black, start | -0.35% | +0.54% | **+22.85%** |
| hunt d13, THB-01 repro | +10.64% | +0.18% | **+7.91%** |
| solve d14, start | +11.60% | -4.67% | -4.46% (NULL) |
| perft(7), start | 0 | +0.42% | +1.32% |
| perft(6), mao check | 0 | -1.40% | **-3.09%** |

**Kept, and the reasoning is the point.** On this tier's metric it is null to
slightly negative, and on the tier-4 metric it is a large win that tier 4 could
not judge because the change is not node-identical. The mechanism explains the
split: a mate hunt is full of in-check nodes, where skipping the empty-square
scan and the drop emission is most of the node's work; perft from the start has
few, which is why perft(6) on a mao-check position measures **-3.09%** -- a real
cost, recorded rather than buried.

The regression baseline is updated in the same commit, deliberately: digest
`651da0519b02a4b7` -> `811f304f1eef7998`.

### TH-13 · credit the symmetric `SND_LB` in mate-distance pruning — CONFIRMED

Mate-distance pruning clamps alpha up to `-(MATE - ply)` and beta down to
`MATE - ply`, and on `alpha >= beta` returned the value crediting **only** the
top of the clamp. If alpha sits at the smallest value reachable from this ply,
the true value is at least that, and that lower bound was being thrown away.

**Sound by construction**: the value returned is identical either way, so this
can only tighten flags. Confirmed empirically -- **0 value changes** over 200
random positions at depth 8, and the regression suite shows no value, soundness
or best-move change on any of its 16 rows.

| measured | |
|---|---|
| root flags upgraded, 200 positions at depth 8 | **4 (2.0%)** |
| value changes | **0** |
| nodes at depth 8, 200 positions | 1,620,473 -> 1,620,473, **exactly 0** |
| nodes on the regression suite (depths 10 and 12) | **-0.01% at most**, on 6 of 16 rows |

The merge measured 2 upgrades in 200 and called it "nearly worthless"; this
measures 4 in 200 and agrees with the characterisation. It is a one-line commit
for flag tightness, not a performance change, and the six rows that move do so
downward by a hundredth of a percent -- tighter flags let a few more cutoffs
fire. Baseline updated in the same commit.

### TH-17 · enemy-king-proximity bonus for quiet drops — REJECTED

Filed PLAUSIBLE and UNMEASURED. Built, swept over five weights, and rejected on
the workload it would actually run on.

**The weight sweep on the regression suite looked like a clear win:**

| weight | regression-suite nodes | vs 0 |
|---|---|---|
| 0 | 6,673,441 | — |
| 8 | 6,131,067 | -8.13% |
| 32 | 6,112,573 | -8.40% |
| 128 | 6,039,086 | -9.51% |
| **512** | **5,925,106** | **-11.21%** |
| 2048 | 5,970,798 | -10.53% |

**On the deep hunts it is the opposite sign, and it gets worse with depth:**

| workload | w=0 | w=512 | delta |
|---|---|---|---|
| hunt d14, White, start | 1,238,385 | 1,400,805 | **+13.12%** |
| hunt d16, White, start | 9,697,568 | 11,168,770 | **+15.17%** |
| hunt d18, White, start | 86,755,179 | 103,521,808 | **+19.33%** |
| hunt d16, Black, start | 1,784,342 | 1,756,471 | -1.56% |
| hunt d18, Black, start | 9,135,325 | 15,531,425 | **+70.02%** |
| solve d14, start | 1,472,142 | 1,539,404 | +4.57% |
| hunt d12, drop-heavy | 85,883 | 86,118 | +0.27% |

The deep start-position hunt is the workload that produced the published bounds
and the one `solve_hunt.py` runs overnight. It regresses **13%, 15%, 19%** at
depths 14, 16 and 18, monotonically worse, and the Black hunt at depth 18 is
**+70%**. Rejected.

**A methodological result worth more than the item.** The regression harness
runs at depths 10 and 12, and it reported an 11% *improvement* for a change that
costs 19% at depth 18. It is a **regression detector, not a performance proxy**,
and its own header now has to say so -- a fixed shallow depth pair cannot stand
in for the depth the product actually runs at.

### TH-39 · the `--tt 26` default was unmeasured — CONFIRMED, default kept

Measured with a new `--tt-sweep` mode and a new `th_tt_fill()` occupancy
accessor. Single worker, White hunt from the start, fresh table and cleared
history per run. **Nodes are the honest column** -- the machine is running other
work, so the time column is recorded but not leaned on.

**Depth 16:**

| size | nodes | occupancy |
|---|---|---|
| 2^16 | 11,158,134 | 100.0% |
| 2^18 | 10,124,520 | 99.2% |
| **2^20** | **9,559,754** | 68.6% |
| 2^22 | 9,697,568 | 25.4% |
| 2^24 | 9,624,672 | 7.0% |

**Depth 18:**

| size | nodes | occupancy |
|---|---|---|
| 2^20 | 94,883,571 | 100.0% |
| 2^22 | 86,755,179 | 92.1% |
| **2^24** | **81,918,782** | 45.9% |
| 2^26 (the default) | 86,697,633 | **14.9%** |

Two things fall out. The node curve does **not** flatten monotonically -- 2^26
is 5.8% *worse* than 2^24 at depth 18, which is locality, not noise, since a
one-worker run with a cleared history table is deterministic. And the depth at
which each size bottoms out moves: 2^20 at depth 16, 2^24 at depth 18.

**The default stays at 26**, and the reason is the item's own warning turned
around: occupancy at 2^26 is only **14.9%** at depth 18 and occupancy is what
rises with depth, so the size that matters is the one for a depth-20+ overnight
run. Lowering the default on a depth-18 curve would repeat exactly the mistake
of lowering it on a depth-16 one.

**The depth-20+ sweep is a long job and is handed over, not run**, which is what
the item asks for. The tool and the command are in the README.

---

## Tier 6 — new ideas

### TH-37 · the reachable-position census — CONFIRMED, reproduced independently

`scripts/census.py`. Positions are deduplicated on the exact 20-byte state --
board, both hands, side to move -- so there is **no hashing and no collision
tail**: every count is exact rather than probable.

Plies 1 through 8 reproduce the merge's figures **to the position**, from an
implementation that shares nothing with it:

| ply | new | cumulative | growth |
|---|---|---|---|
| 1 | 6 | 7 | 6.00 |
| 2 | 33 | 40 | 5.50 |
| 3 | 193 | 233 | 5.85 |
| 4 | 1,220 | 1,453 | 6.32 |
| 5 | 7,751 | 9,204 | 6.35 |
| 6 | 45,979 | 55,183 | 5.93 |
| 7 | 291,007 | 346,190 | 6.33 |
| 8 | 1,689,902 | 2,036,092 | 5.81 |

23 seconds in Python to ply 8. Plies 9 and 10 (9,630,829 and 49,003,553) are
carried from the merge's C run **with its parameters attached** -- 185s wall,
3.06 GB RSS, hashbits 27, 16-byte keys -- because the same item once carried a
"12 seconds, 1.8 GB" claim that did not reproduce. Ply 9 was not re-run here:
it needs a couple of gigabytes, and the machine is running the user's own work.

Plies 1 and 2 equal perft 1 and 2, as they must, and that is what makes the
script non-vacuous: a census that had drifted from the move generator fails
there first. That check is now a test.

**What it buys**, which is the item's own claim and now holds: the state-space
verdict in `RULES.md` is a measurement rather than an argument. Growth sits near
6 per ply and begins to bend by ply 10 (5.09), so the reachable space is far
smaller than the 1.77e13 the notation can express -- and still far too large for
a retrograde table.

### TH-36 · df-pn as a second engine — CONFIRMED (reopened after being BLOCKED)

**First pass: BLOCKED.** The prototype failed its own validation case and I
declined to read the milestone off it. Reopened on request, debugged, and the
milestone has now actually been run. What follows replaces that verdict; the
original write-up is kept below it, because being wrong first is part of the
record.

**Two bugs, and the second is the interesting one.**

1. The depth limit was tested **before** the terminal check, so a mate reached
   exactly at the limit was scored as the attacker failing. A depth-9 search
   therefore could not see a mate in 9.
2. **The conservative store rule destroyed df-pn's progress guarantee.** df-pn
   advances by re-reading a child after searching it. A child whose value was
   withheld as path-dependent reads back as the `(1, 1)` initial estimate, so
   the parent selects it again, searches it again, and never terminates. That
   is what pinned the table at 15 entries over a million nodes -- an infinite
   loop, not starvation. The fix is a per-node **local** cache: a value that is
   path-dependent is still valid within one call of `mid()`, where the path
   prefix is fixed, so it is usable there while still being kept out of the
   global table.

**Validated, which is what makes any of the rest quotable:**

| check | result |
|---|---|
| recorded mate in 9, unbounded | **PROVED in 2,770 nodes** |
| recorded mate in 9, depth-limited to 9 | PROVED in 1,863 nodes (backlog reported ~1,949) |
| White has no win from the same position | DISPROVED |
| agreement with `th_mate_hunt` at depths 4, 6, 8 | **178 agree, 0 disagree** |

The cross-check is the real validation: with a depth limit d, df-pn answers
exactly the question `th_mate_hunt(d)` answers, and the two engines share no
code beyond the move generator.

**The gating milestone, run at last.** df-pn on "White forces a win" from the
start, per root move, `dn` from White's side:

| nodes | resolved | rep leaves | withheld | a1b2 | a2a3 | b1b2 | c1b3 | c1d3 | d1c2 |
|---|---|---|---|---|---|---|---|---|---|
| 300k | 0/6 | 47,662 | 110,980 | 7 | 367 | 8 | 1 | 334 | 4 |
| 600k | 1/6 | 99,647 | 232,712 | 7 | 520 | 8 | 1 | 475 | **DISPROVED** |
| 1.2M | 1/6 | 216,189 | 500,328 | 7 | 712 | 8 | 1 | 666 | **DISPROVED** |
| 2.4M | 1/6 | 434,212 | 980,157 | 7 | 968 | 8 | 1 | 948 | **DISPROVED** |

**The milestone's answer is NO for this formulation.** Three columns are frozen
across an eightfold increase in nodes and two are *rising* -- the disproof is
getting further away, not closer. One root move resolves: `d1c2` is DISPROVED,
which is independently correct, since that move is the published Black mate in
9. That single result is worth noting on its own -- it is a positive **disproof
of a win**, the thing alpha-beta structurally cannot produce, because its
horizon returns an unsound 0.

**What the conservative rule costs, measured at 600k nodes**, against an
UNSOUND arm that stores path-dependent values anyway (its answers cannot be
trusted; only its bookkeeping is informative):

| store rule | tt entries | withheld | a1b2 | a2a3 | b1b2 | c1b3 | c1d3 |
|---|---|---|---|---|---|---|---|
| sound | 244,290 | **232,712 (39%)** | 7 | 520 | 8 | 1 | 475 |
| unsound | 365,351 | 10,880 (1.8%) | 287 | 628 | 652 | 585 | 585 |

The sound arm withholds **39%** of everything it computes. Its tiny frozen
numbers (7, 8, 1) are not a nearly-finished disproof; they are amnesia -- small
estimates re-derived from scratch because nothing accumulates. The unsound arm's
larger numbers reflect knowledge actually retained. **Neither arm converges on
the start position**, so twin entries alone would not close it either.

**Scope, stated plainly.** This is a Python prototype at roughly 5,000 nodes per
second, and 2.4M nodes is a small budget by df-pn standards. The honest verdict
is "not viable in this formulation at this budget", not "df-pn cannot work
here". The next step, if anyone takes it, is a C implementation with
Kishimoto-Muller twin entries -- and the 39% figure above is the specific thing
twins would attack.

---

#### Original first-pass write-up (verdict since superseded)

### TH-36 · df-pn as a second engine — BLOCKED

A df-pn prototype is written and committed (`scripts/dfpn.py`), and it **fails
its validation case**, so the gating milestone cannot be read off it.

Validation case: the recorded mate in 9 on `fuwk/3p/P1F1/KWU1[-] b`, which the
alpha-beta engine proves at depth 9 under two Zobrist seeds and which the
campaign has pinned as a test since tier 0.

| configuration | result | nodes | tt |
|---|---|---|---|
| depth-limited to 9, sound store | still open | 1,000,001 | 71 |
| depth-limited to 9, store anyway | still open | 1,000,001 | 416 |
| unbounded, sound store | still open | 1,000,001 | 15 |
| unbounded, store anyway | **DISPROVED** (wrong) | 858 | 746 |

The last row is the one that settles it: it returns a confident disproof of a
position with an independently verified proof, so **nothing this prototype
reports can be trusted**, including its diagnostics.

**What I will not claim.** With the sound store rule, 99.99% of values are
withheld as path-dependent and the table freezes at 15-71 entries over a million
nodes -- which is exactly what the backlog predicted ("essentially every value
becomes path-dependent and unstorable under the conservative rule") and would be
a strong argument for Kishimoto-Muller twin entries. **It is not claimed here**,
because a defect in this implementation would produce the same symptom, and I
did not separate the two. Reporting the number as a finding would be reporting
my own bug as a property of the algorithm.

**Verdict BLOCKED**, with the blocker named precisely: the milestone needs an
implementation that proves the mate in 9, and this one does not. The prototype
ships as groundwork with the validation case wired up as a **strict xfail** --
it fails today, it states exactly what "working" means, and if someone fixes it
the suite says so by failing the other way.

The item's premise is untouched by any of this. The alpha-beta engine's horizon
returns an unsound 0, so a draw is the absence of a proof; the campaign did
prove one for bare kings at depth 80-100 (TH-29), and nothing like it is
reachable for the start position. A horizon-free search is still the only
formulation that can close the draw claim.

### TH-38 · bounded retrograde terminal shell — CLOSED PRE-MEASUREMENT

Costed against TH-37's census, as the item asks, and closed without building it.

**The structural point first, because it decides the shape of the thing.** In
crazyhouse **material never leaves the game** -- a capture moves a unit to the
capturer's hand -- so every reachable position holds exactly the same 8 units
and 2 kings. The axis a classical endgame tablebase shrinks along **does not
exist here**. A bounded retrograde must therefore be bounded by
distance-to-terminal, not by piece count, which is a different and much less
favourable construction.

**Terminal density, measured on the exact reachable set:**

| ply | positions | terminal | mate | stalemate | terminal share |
|---|---|---|---|---|---|
| 4 | 1,220 | 2 | 2 | 0 | 0.164% |
| 5 | 7,751 | 2 | 2 | 0 | 0.026% |
| 6 | 45,979 | 20 | 19 | 1 | 0.044% |
| 7 | 291,007 | 380 | 370 | 10 | 0.131% |

Terminals are one to two per thousand positions, and their absolute count grows
at the same ~6x per ply as everything else. A k-ply predecessor shell therefore
grows as roughly terminals x 6^k and never becomes a small set relative to the
frontier it would serve.

**Against a payoff that is close to zero.** The search already detects terminals
exactly and for free at every node, with both soundness flags set, and TH-15's
probe measured **87% of interior nodes cutting off on their first searched
move** -- the last few plies before a terminal are exactly where the search is
already cheapest. A shell would buy the cheapest part of the tree.

**And the item concedes the decisive limit itself**: a bounded retrograde can
label WIN and LOSS but never DRAW, and the draw is the open question. It cannot
close the claim it would be built for.

---

## Tier 7 — GUI

All three verified in the running GUI, not just by presence checks.

### TH-45 · history numbering was inverted for the whole game — CONFIRMED

The numbering was `i % 2 === 0`, which assumes a white-to-move start. The
correction in the backlog is confirmed: from a black-to-move start it inverts
for the **entire game**, not just the first move.

| start | history strip |
|---|---|
| black to move | `1...d3d2` · `2.a2a3` |
| white to move | `1.a2a3` · `d3d2` |

Both are correct chess convention now. No new state field was added, as the
backlog suggests: the starting side is recoverable from `state.hist[0]`, and a
`startStm` field would have needed resetting in three places.

### TH-46 · no check indicator of any kind — CONFIRMED

`in_check` was computed, serialised and read by nothing. On
`3k/1U2/4/K3[f] b`: the banner reads **"Black is in check"**, and square 15 (d4,
the black king) is highlighted. On a position that is not in check the banner is
empty.

The item is **under-inclusive as filed**, and that half is fixed too: `move_str`
never appended `+` either. It cannot -- a move string says nothing about the
position it lands in -- so `position_info` returns a separate `checks` list and
the GUI renders the marker, leaving the move key intact as the identity used
everywhere else. Verified: on `3k/4/4/K1U1[-] w` the moves table shows
`a1b1 · a1a2 · a1b2 · c1a2 · c1d3 · c1b3+`, with the marker on exactly the mao
check.

### TH-47 · `/pieces/` hardcodes `image/svg+xml` — CONFIRMED, hardcode kept

The backlog's own assessment is upheld: hardcoding is **safer** than guessing,
because a wrong guess would introduce a sniffing risk the route does not
otherwise have. So the type stays hardcoded and what was missing is added
instead -- the route now requires a `.svg` suffix, which makes the hardcoded
type **provably** correct rather than incidentally correct. `/pieces/foo.txt`
is a 404, and the traversal guard the merge probed exhaustively is untouched.

---

## Campaign reconciliation

```
backlog in 62  =  confirmed 55 + rejected 4 + closed-pre-measurement 2 + moot 1
```

TH-16 appears twice on purpose: its class A (node-identical) form is REJECTED
and its class B form is KEPT-ON-NULL. It is counted once above, under rejected,
with the kept form recorded separately.

| tier | items | verdicts |
|---|---|---|
| 0 P0 soundness | 1 | 1 confirmed |
| 1 correctness | 19 | 19 confirmed |
| 2 doc overclaims | 7 | 6 confirmed, 1 moot |
| 3 instruments | 18 | 17 confirmed, 1 rejected |
| 4 NPS | 7 | 5 confirmed, 1 rejected, 1 closed pre-measurement |
| 5 efficiency | 4 | 2 confirmed, 2 rejected (1 of them kept in its other form) |
| 6 new ideas | 3 | 2 confirmed, 1 closed pre-measurement |
| 7 GUI | 3 | 3 confirmed |

TH-16 was reclassified from tier 4 to tier 5 mid-campaign, on the measurement
that it is not node-identical, which is why tier 4 shows 7 and tier 5 shows 4.

## Final gate

| gate | result |
|---|---|
| `pytest -q` | **112 passed**, 3 deselected (43 at the start) |
| `pytest -q -m ""` | **115 passed** (the df-pn xfail is now three real tests) |
| `perft(7)` from start | 1,355,253 |
| regression digest | `811f304f1eef7998`, 6,673,441 nodes |
| mate in 9 / 13 / 13 | 29991 / 29987 / 29987, default seed **and** `0xC0FFEE` |
| negative hunts d12-d18, both colours | 0 everywhere |
| `git status` | clean |

Node counts on the negative hunts at the end of the campaign: d12 171,059 /
9,700 · d14 1,238,385 / 220,875 · d16 9,697,568 / 1,784,342 · d18 86,755,179 /
9,135,325 (White / Black).

## Total measured gain

Campaign start (`4e22dcd`) to the end of tier 4 (`d0bfa0d`), same-build control
arm, 9 repeats, fresh process each:

| workload | control | gain |
|---|---|---|
| hunt d16, start | -0.03% | **+22.79%** |
| solve d14, start | +0.52% | **+21.08%** |
| perft(7), start | -0.43% | **+42.48%** |
| perft(4), drop-heavy | +0.13% | **+206.75%** |

Split into its two parts on hunt d16: **+19.1% nodes per second** and **-3.0%
nodes to depth**, the latter a one-off side effect of THB-01's soundness fix.

Tier 5 added TH-16, which is +8.15% and +22.85% on the two start-position hunts
but costs 3.04% more nodes on the regression suite; it is not folded into the
figures above, because those are node-identical and this one is not.

### TH-36 (second pass) · the C df-pn engine with Kishimoto-Muller twin entries

`th_dfpn` / `th_dfpn_init` in `tinyhouse.c`, sharing the movegen, make/unmake,
Zobrist keys and `key_after` with the alpha-beta engine. `scripts/dfpn.py`
stays as the slow Python reference the C is checked against.

**Twin entries, and the measurement that chose their shape.** A value that used
a repetition is only valid on paths still containing the ancestor it repeated.
The conservative rule throws every such value away. A twin instead stores the
value *with* its conditioning ancestors and reuses it when those are on the
current path. Width was measured before it was chosen: on a 200k-node Python
sample, 90.0% of path-dependent values depended on exactly one ancestor, 9.9%
on two, 0.08% on three. **That shallow sample does not extrapolate** -- at 48M
C nodes, 29% exceed two.

**Validation. Three independent implementations, zero disagreements anywhere.**

| check | comparisons | disagreements |
|---|---|---|
| C df-pn vs `th_mate_hunt`, 400 positions x depths 4/6/8/10/12 x both colours | **3,960** | **0** |
| C df-pn vs `th_mate_hunt`, 60 positions x depths 4/6/8/10 (twins on and off) | 480 x2 | 0 |
| C df-pn vs the Python reference | 90 | 0 |
| twins on vs twins off, unbounded | 114 resolved | **0 verdict differences** |

The cross-check works because with a depth limit d, df-pn answers exactly the
question `th_mate_hunt(d)` answers, and the two engines share no search code.

**Speed.** The recorded mate in 13 is proven at depth limit 13 in **0.11s**;
the Python reference could not prove it at all within 257k nodes and 14s. The
mate in 9 takes 2,806 nodes with twins and 2,770 without.

**The twin-width sweep, which is the result that matters.** Start position,
White, 12M nodes, twins on:

| `DF_DEPS_MAX` | withheld | root dn | twin hits |
|---|---|---|---|
| 1 | 13.9% | 8,397 | 1,464,788 |
| 2 (shipped) | 2.1% | 9,529 | 902,735 |
| 4 | 0.1% | 10,960 | 739,986 |
| **8** | **0.0%** | 10,700 | 728,371 |

At width 8 **the GHI store problem is gone entirely** -- nothing is withheld --
and the disproof number is *worse* than at width 1. Twins do exactly what they
are supposed to do, and it changes nothing.

**The gating milestone, C engine, twins on, up to 96M nodes:**

| nodes | resolved | rep leaves | withheld | a1b2 | a2a3 | b1b2 | c1b3 | c1d3 | d1c2 |
|---|---|---|---|---|---|---|---|---|---|
| 12M | 1/6 | 458,133 | 287,035 | 1,337 | 1,480 | 2,005 | 2,520 | 2,180 | **DISPROVED** |
| 24M | 1/6 | 3,712,943 | 3,082,767 | 1,619 | 1,615 | 2,653 | 3,345 | 3,066 | **DISPROVED** |
| 48M | 1/6 | 17,682,792 | 13,783,272 | 2,315 | 2,179 | 2,408 | 1,684 | 4,285 | **DISPROVED** |
| 96M | 1/6 | 59,269,335 | 44,172,466 | 1,251 | 2,237 | 4,536 | 3,288 | 5,242 | **DISPROVED** |

**Verdict: NO, and now for a reason rather than for lack of an engine.** The
disproof numbers rise with more search, one root move of six resolves, and
**62% of all nodes are repetition leaves** at 96M. The backlog expected
Kishimoto-Muller twins to be the missing piece; they are built, they work, they
eliminate withholding completely at width 8, and the answer does not move.

**What did come out of it**: `d1c2` is DISPROVED -- White has no forced win
after `1.Fd1-c2` -- which is a positive disproof of a win, the thing the
alpha-beta engine structurally cannot produce because its horizon returns an
unsound 0. That is a real, new, independently cross-checked result about this
game.

---

## Post-campaign: bitboard search and TT prefetch — both REJECTED

Asked directly: can the solve itself be made faster with the bitboard movegen,
and how do TT probes get cheaper? Both built, both measured, neither pays.

**Bitboard generation inside `search()`** (BState derived per node; generation,
in-check test and legality filter all mask-based; mailbox kept authoritative
for make/unmake and keys). Measured **node-identical on every workload tried**
-- six real hunts/solves and all 16 regression rows byte-identical -- so wall
time was the only judge, against a same-build control arm:

| workload | tt | control | bbsearch | prefetch-only | both |
|---|---|---|---|---|---|
| hunt d16 White | 2^22 | +0.63% | -0.87% | +0.09% | +0.22% |
| solve d14 | 2^22 | +0.33% | -0.03% | +0.09% | -0.05% |
| hunt d16 White | 2^26 | -0.19% | -0.26% | -0.42% | +0.00% |

Everything within or against the noise. The tier-4 profile said movegen is
~40% of a search node; replacing it with masks moved nothing, which means the
mailbox generator was never the bottleneck inside the search -- the profile
measures where time is spent, not what would change if it were removed.

**TT prefetch** (`__builtin_prefetch` on the child's slot at `key_after` time,
~10-50 ops before the child probes it): NULL at 2^22 where the table is
cache-resident, and NULL at 2^26 where every probe is a genuine DRAM miss.
The plausible mechanism for the null: the child's key is computed before
make(), so the probe's address is available early and an M2-class out-of-order
window issues the load long before the value gates anything -- the hardware is
already doing what the hint asks for. Consistent with TH-39's finding that
node counts stop improving past 2^24: neither capacity nor latency of the
table is currently binding.

Both live only as scratch builds; nothing shipped, nothing to revert. The
bitboard stays where it measured 2.1-2.5x: perft.

## Post-campaign: the WHITE bound to depth 24, and the table saturating

The White bound moved from depth 20 to **depth 24**: no forced White win from
`fuwk/3p/P3/KWUF[-] w` within 24 plies. One run, 16 workers, `--tt 30` (16 GiB
cap grown from 2^20), build `15349806521889203565`, Apple M5 Pro 18 cores /
64 GiB. 128,553,886,981 nodes over the whole iteratively-deepened run in 35.9
minutes, about 60 Mnps. The old depth-20 White bound is retired, not beaten:
different machine, different worker count, older build.

| depth | 18 | 20 | 22 | 24 |
|---|---|---|---|---|
| nodes | 204,891,546 | 1,394,397,984 | 7,848,706,198 | 119,073,867,480 |
| seconds | 3.6 | 24.3 | 133.1 | 1990.2 |
| growth | x7.4 | x6.8 | x5.6 | **x15.2** |
| occupancy after | 2% | 13% | 54% | **100%** |

**The finding is in the last two rows.** Node growth per 2 plies had been
*falling* -- 7.4, 6.8, 5.6 -- and then tripled to 15.2 at precisely the depth
where the table hit 100%. That is what saturation-forced re-search should look
like, and it agrees in sign and rough magnitude with the one controlled number
already on record (a 91.7%-full table at 216.6s against 100.3s for the next
size up, same work). But this is a single uncontrolled run, so the honest
status is **consistent with, not evidence for**. Some of x15.2 is real tree
growth; nobody has separated the two. The A/B that would -- depth 24 at 2^30
against 2^31 -- costs about 70 minutes and has not been run.

**On the choice of 2^30 for this run.** It was picked by inference before the
fact, not measured, and the run happened to vindicate it arithmetically: depth
22 wrote 581,931,417 entries, which is 108% of a 2^29 table, so 2^29 would have
saturated a full depth earlier. That is a reason to believe 30 beat 29 here; it
is still not an A/B between them.

**Consequence for depth 26.** Extrapolating x15 off 119G gives roughly 1.8
trillion nodes, upwards of 8 hours at this nps before counting whatever a
saturated table adds. 2^31 (32 GiB) is the largest the memory guard allows on a
64 GiB box without `--force-tt`, and it will fill too. The table has stopped
being a lever that can be pulled much further on this machine.

**Not yet done:** the bound is single-seed. A 64-bit Zobrist collision has no
directional structure and could have pruned a subtree holding a real mate, so
the depth-24 claim carries the same unquantified residual as every other bound
here until it is re-run under `--seed 0xC0FFEE`.

## Post-campaign: TT replacement policy — bucketing CONFIRMED, aging REJECTED

Prompted by a per-core throughput comparison against Pygin (a Python+C chess
engine, 4.19 Mnps single-thread pre-NNUE, ~68 Mnps at 16 threads). Tinyhouse
was at 3.74 Mnps/core on the saturated depth-24 run. The depth-20 tt sweep at
16 workers showed where the time really goes:

| table | 2^22 | 2^24 | 2^26 | 2^28 | 2^30 |
|---|---|---|---|---|---|
| nodes | 13.79G | 7.13G | 3.17G | 2.79G | 2.62G |
| time | 179.5s | 105.9s | 48.9s | **44.9s** | 46.2s |
| nps | **76.8M** | 67.4M | 64.9M | 62.2M | 56.6M |

Node count falls 5.3x on table size alone, so this search is transposition-
bound rather than per-node-cost-bound. **The nps column is the cautionary
one**: 2^22 posts the highest throughput in the table, beating Pygin's 68M,
and takes four times as long. NPS is a gameable metric here and every verdict
below is taken on time.

**TT_BUCKETS (CONFIRMED, shipped at 1).** Four 16-byte entries per 64-byte
cache line: same one DRAM miss per probe, but 4-way associativity and
proven-then-deeper replacement instead of blind overwrite. solve_hunt to
depth 18, one worker, table pinned at 2^20, two interleaved repeats
reproducing to the byte: 74,450,920 nodes / 10.7s against 91,759,732 / 12.6s.
**18.9% fewer nodes, 15.1% less time**, and per-2-ply growth fell x9.9 -> x7.8.
At 16 workers, depth 20, 2^26 (98.9% full), interleaved with a same-build
control arm: +22.8% against the slower control, +13.0% against the faster,
over a 6.8% control-arm noise floor. NPS went the WRONG way (6.96M against
7.28M), which is the expected shape for a change that wins by searching less.

**TT_AGING (REJECTED, kept at 0).** Generation stamp in the 16 spare bits of
the existing entry, staleness penalised at 8 depth-points per generation.
Same instrument: 83,494,481 nodes / 11.6s against 74,450,920 / 10.7s, **12%
worse**. In an iteratively-deepened solve the previous iteration's entries are
the most valuable ones in the table, so a staleness penalty discards exactly
what the next iteration wants. The motivating idea -- evict what is no longer
reachable -- has no cheap sound test in this game at all: material is
conserved, so the chess filter "discard anything with more material than the
root" has no analogue, and inside one hunt every stored position shares the
root's material signature.

**A harness error worth recording.** Both changes were first measured with
bench_ab.py, which runs ONE search per repeat on a fresh table. That reported
bucketing at -5.08% and aging at an exact tie. Both were artifacts: a
replacement policy only shows itself once a table accumulates across
iterations, and root_search bumps the generation once per call so aging never
fired at all. The verdicts above are from solve_hunt, which deepens
iteratively over one table. bench_ab.py remains right for node-identical
per-node changes and wrong for anything about the table's contents.

## Post-campaign: bucketing measured on the real workload — x3.08 to depth 24

The controlled follow-up to the x15.2 growth factor recorded two sections above
as "consistent with saturation, not evidence for it". Same command both times
(`solve_hunt.py 0 --tt 30 --workers 16 --maxdepth 24`), same machine, one run
per build, differing only in TT_BUCKETS.

| depth | 18 | 20 | 22 | 24 | total |
|---|---|---|---|---|---|
| nodes, direct | 204,891,546 | 1,394,397,984 | 7,848,706,198 | 119,073,867,480 | 128.55G |
| nodes, bucketed | 249,483,005 | 1,422,108,390 | 6,732,390,460 | **29,410,245,520** | **37.85G** |
| time, direct | 3.6s | 24.3s | 133.1s | 1990.2s | 35.9 min |
| time, bucketed | 4.4s | 25.4s | 119.6s | **548.5s** | **11.6 min** |
| growth, direct | x7.4 | x6.8 | x5.6 | **x15.2** | |
| growth, bucketed | x8.9 | x5.7 | x4.7 | **x4.4** | |
| occupancy after | 2% | 14% | 64% | **100%** | |

**x3.08 overall; x3.63 at depth 24 alone, on 4.05x fewer nodes.**

**The win is entirely where the mechanism says it must be.** Depths 18-20 run
at 2-14% occupancy, where a 4-way bucket nearly always finds a free slot and
behaves like the direct-mapped table; the +21.8% at depth 18 is 16-worker
nondeterminism, not a regression. Depth 24 is the only depth at 100%
occupancy, and it is the only depth that moves. A change that helped
everywhere equally would have been evidence of something else.

**The x15.2 is explained and retired.** It was replacement thrashing, not tree
growth: with associativity the factor falls monotonically (x8.9, x5.7, x4.7,
x4.4) instead of tripling at saturation. The earlier hedge -- that some of
x15.2 was real tree growth and nobody had separated the two -- resolves as
almost all of it being thrashing.

**NPS fell from 59.83M to 53.62M while the run got 3.08x faster.** Fourth
instance in this session of throughput moving opposite to time. Recorded
because it is now the most extreme one: a 3x speedup that a nps-based
acceptance test would have rejected.

**Corroboration, not just speed.** The depth-24 bound now rests on two
independent builds whose node counts differ by 4x. A defect in the
direct-mapped replacement policy cannot have produced both.

Depth 26 projects to ~130G nodes and ~40 minutes at x4.4, against the
"upwards of 8 hours" this file carried when the projection used x15. That
projection crosses a saturation boundary and the last one of those was wrong
by 3x, so it is a prediction to be checked, not a number to plan around. The
table is already 100% full at depth 24, so `--tt 31` is the setting to use.

## Post-campaign: stop probing the table at horizon nodes — CONFIRMED

`search()` probed the transposition table before testing `depth <= 0`, so every
horizon node paid a full probe. Horizon nodes are the most numerous class in
the tree and they NEVER store: they return before the store block. The largest
group of probes in the search was write-only-never, on a table where a probe is
a DRAM and TLB miss.

Expected to be node-changing, since a stored entry can carry a proven mate
distance the horizon cannot derive. Measured node-IDENTICAL, arm to arm and
against the frozen suite. TT_BUDGET_GUARD (THB-01) already refuses any mate
cutoff whose distance overruns the remaining budget, and at depth <= 0 that is
every one of them, so the surviving cutoffs only ever returned what the horizon
computes anyway. Pure cost, no benefit. Class A.

Measured on solve_hunt to depth 18, one worker, table pinned at 2^30 so probes
miss, three interleaved repeats, nodes identical at 69,529,202:

| | time | nps |
|---|---|---|
| HORIZON_SKIP_TT 1 | 14.1 / 13.8 / **13.8s** | **5.03M** |
| HORIZON_SKIP_TT 0 | 15.8 / 15.7 / **15.7s** | 4.45M |

**-12.1% time, +13.0% nps.** The same A/B at 2^20 measured nothing: the probe
being removed was cache-resident there. The win scales with table size, so it
compounds with the multi-GiB tables the deep hunts use, and the depth-18 figure
is a floor for what depth 24 should see rather than an estimate of it.

This is the one change in this session where nps is the honest metric, because
the node count is pinned. Everywhere else it moved opposite to time.

**Two table ideas closed alongside it.** Shrinking TTEntry from 16 bytes to 8
would double capacity, but the payload only compresses to 37 bits (value 16,
move 11, depth 6, flag 2, sound 2), leaving 27 bits for the key check against
today's 64. At ~3e10 probes that is roughly 1,800 expected false hits per
depth-24 run against effectively zero now, and a false hit returns another
position's bound, which can prune a subtree holding a mate. The 64-bit key is
the sole documented soundness residual on every published bound; capacity is
not worth spending it. Tagging entries as invalidated by pawn moves fails for
the same reason TH-38 did: pawn drops are legal on ranks 2 and 3, exactly the
range a pawn advances through, so a pawn captured on rank 3 can be dropped back
on rank 2 and the earlier position recurs in full. Crazyhouse conserves
everything, so there is no monotone axis to age against.

## Post-campaign: the WHITE bound reaches depth 26

No forced White win from `fuwk/3p/P3/KWUF[-] w` within **26 plies**. One run,
16 workers, `--tt 31` (32 GiB cap grown from 2^20), build
`17058640857953325544`, Apple M5 Pro 18 cores / 64 GiB. 137,949,700,606 nodes
over the whole iteratively-deepened run in 2273.3s (37.9 min).

Same command across three engine builds:

| depth | direct, tt30 | bucketed, tt30 | + horizon skip, tt31 |
|---|---|---|---|
| 22 | 7,848,706,198 / 133.1s | 6,732,390,460 / 119.6s | 6,759,498,689 / 102.2s |
| 24 | 119,073,867,480 / 1990.2s | 29,410,245,520 / 548.5s | **24,516,888,146 / 397.6s** |
| 26 | - | - | **105,022,380,063 / 1747.6s** |
| whole run | 128.55G / 35.9 min | 37.85G / 11.6 min | 137.95G / 37.9 min |

**Depth 24 is x5.01 faster than the first run, on 4.86x fewer nodes.** The
whole-run line is the honest headline: the original engine spent 35.9 minutes
reaching depth 24; the current one reaches depth 26 in 37.9.

**Growth held across the saturation boundary.** d22->d24 x3.6, d24->d26 x4.3,
with occupancy going 33% -> 92% -> 100%. The direct-mapped run tripled to x15.2
the moment its table filled. This one saturates at depth 26 and stays near x4,
which is the strongest evidence yet that x15.2 was replacement thrashing rather
than tree growth.

**Prediction scored.** Depth 26 was projected here at ~130G nodes and ~40
minutes, explicitly as a floor rather than a forecast. Actual: 105.0G and 29.1
minutes. The pre-bucketing extrapolation for the same depth was ~1.8 trillion
nodes and 8-10 hours, i.e. 17x off.

**Attribution limit, stated rather than implied.** The depth-24 improvement
from 548.5s to 397.6s mixes TWO changes -- the horizon probe skip and the cap
moving 2^30 -> 2^31 -- and this run cannot separate them. Only the x3.08 from
bucketing is cleanly attributed, because that pair of runs differed in one
toggle.

**Still single-seed.** A 64-bit Zobrist collision could have pruned a subtree
holding a real mate. The depth-26 claim carries the same unquantified residual
as every other bound here until re-run under `--seed 0xC0FFEE`.

Depth 28 projects to ~450G nodes at x4.3, roughly two hours, and the table is
already 100% full at 2^31 -- which is 32 GiB, half of this machine's RAM and
the largest the memory guard allows without `--force-tt`. Capacity, not
replacement policy, is now the binding constraint.

## Post-campaign: the BLACK bound reaches depth 28

No forced Black win from `fuwk/3p/P3/KWUF[-] w` within **28 plies**, superseding
a depth-22 bound taken on the old 10-core M2 Pro under a long-dead build. Both
sides now stand on the same engine and machine for the first time:
**26 White / 28 Black**.

One run, 16 workers, build `17058640857953325544`, M5 Pro 18 cores / 64 GiB.
189,713,209,576 nodes over the whole run in 2742.1s (45.7 min).

| depth | 22 | 24 | 26 | 28 |
|---|---|---|---|---|
| nodes | 2,620,590,190 | 14,278,837,586 | 21,454,124,057 | 150,555,712,885 |
| seconds | 27.4 | 215.7 | 341.3 | 2153.0 |

**These timings are contaminated and must not be pooled with the White run.**
Depths through 22 were searched through a stunted 2^20 table caused by the
growth/resume bug fixed the same session, so the depth-22 count measures the
bug and not Black's tree, and the d24->d26 growth of x1.5 reflects the table
reaching 2^30 mid-run rather than anything about the search. The BOUND is
unaffected -- a null-window hunt returning 0 proves the negative whatever size
the table was -- but the seconds column is not a measurement of anything.

The run also never reached its requested `--tt 31`. Growth to 2^31 needs a new
32 GiB block alongside the live 16 GiB, and the machine could not spare 48 GiB
peak, so depths 24-28 ran at 2^30, 100% full from depth 26 on.

**Repetition, measured while answering whether shuffle lines are wasted work.**
They are cut, before the TT probe and before any generation, and they are
negligible: at depth 18 only 0.11% of White nodes and 0.07% of Black nodes exit
by repetition. They are also not waste -- in a "no forced win" proof the
defender's ability to repeat is exactly what proves the negative, which is why
`rep_min` gates the store rather than the search pruning them.

The mechanism's real cost is 8.3 path compares per node, paid at EVERY node
because this game has no irreversible moves: chess scans back only to the last
capture or pawn move, and here there is no such point. A presence filter over
the path would skip most of those compares, but the ceiling is 1-2%, at or
under the noise floor these campaigns measure at. Left alone deliberately.

## Post-campaign: check detection by mask instead of list walk — CONFIRMED

`order_score` asks "does this move give direct check" for EVERY move of EVERY
interior node -- about 528 million calls in a depth-18 hunt -- and answered it
by walking the destination square's neighbour list looking for the king.

The question inverts. For a FIXED enemy king square the set of squares a given
piece type checks from is a constant, so it is a 16-bit mask indexed by (type,
king square) and the test becomes one shift. The mao is the only case needing
more than a bit, because it checks only when its leg is empty, and the leg for
(from -> ks) is unique since the orthogonal step is determined by the
destination.

The masks are DERIVED from the same neighbour tables the loops walked, in
init_tables, so correctness follows by construction rather than from a second
hand-written movegen -- the failure mode that produced the double-mao-check bug
earlier in this project.

Node-identical, so `bench_ab.py` is the right instrument and nps is an honest
metric for once. Depth 18, one worker, 2^24, five interleaved repeats, with a
same-build control arm:

| arm | nodes | cpu | vs baseline |
|---|---|---|---|
| control A | 82,712,965 | 14.483s | baseline |
| control B | 82,712,965 | 14.459s | +0.17% (noise floor) |
| **masks** | 82,712,965 | **13.385s** | **+8.20%** |

**+8.20% against a 0.17% noise floor**, 48x the floor, node identity confirmed
across all three arms. NPS 5.71M -> 6.18M.

Found by re-profiling after the horizon change: `search` self-time stayed at
51% while pseudo_moves sat at 25.6% and attacked at 15.3%, and the profile
could not see gives_direct_check because order_score is inlined. The call
COUNT, not the profile, is what identified it.

## Post-campaign: lazy move generation at the horizon — CONFIRMED (+2.06%)

`horizon_has_move` answers one yes/no question -- is there a legal move -- and
built the ENTIRE pseudo-move list to do it. Instrumented over a depth-18 hunt:

| | |
|---|---|
| horizon nodes | 28,308,177 = **34.2% of all nodes** |
| answered by HORIZON_FAST_PATH | 10,073,005 = 35.6% |
| fell back to full generation | 18,235,172 = **64.4%** |
| moves generated in the fallback | 158,765,117 |
| moves ever tried | 41,483,858 = **26.1% of generated** |
| horizon nodes with NO legal move | 289,118 = **1.0%** |

So 74% of generated moves were never looked at, and the answer is "yes" 99% of
the time. The fix generates a PREFIX first and only builds the rest when the
prefix yields nothing.

**Deliberately a limit on the one generator, not a second "any legal move"
routine.** A hand-written second opinion on move legality is exactly what
produced the double-mao-check bug in this project, and that bug survived 74,702
walked positions and every perft number. `any_legal` is also shared by both
passes so they cannot diverge.

Node-identical: only a boolean escapes horizon_has_move. Depth 18, one worker,
2^24, seven interleaved repeats, same-build control arm:

| arm | cpu | vs control |
|---|---|---|
| eager (control A/B) | 13.101s / 13.101s | 0.01% noise floor |
| limit 2 | 12.740s | +2.84% |
| **limit 4 (shipped)** | 12.837s | **+2.06%** |
| limit 6 | 12.808s | +2.29% |

The three limits sit within 0.8% of each other, inside the 4.9-8.0% per-run
spread, so the limit VALUE is not resolvable here -- only that laziness pays.

**Estimate was wrong and is recorded as such.** Sizing this from the 74% waste
predicted 4-5%; it measured 2%. The first attempt measured only +1.69% because
`pseudo_moves` routed through the limit check for every caller, paying a
per-square branch in the hottest function for a feature only the horizon uses.
Marking the core always_inline so `limit` constant-folds at both call sites
recovered the rest.

## Post-campaign: the interior node — CONFIRMED (+10.97%)

The horizon had been worked twice, so this pass instrumented the INTERIOR node
instead. Depth-18 hunt, one worker, 2^24, 82,712,965 nodes of which 39,643,912
are interior:

| | per interior node | total |
|---|---|---|
| moves generated | 16.68 | 661,321,697 |
| `order_score` calls | 16.68 | 661,321,697 |
| selection-sort comparisons | **30.82** | **1,221,861,665** |
| moves actually searched | 2.09 | 82,712,964 |
| moves found illegal | 0.77 | 30,589,281 |
| repetition-scan iterations | 14.69 (7.04 per node) | **582,301,361** |
| repetition-scan HITS | | **78,141** |
| TT move present | 0.03 | 1,145,298 |

Two numbers set the agenda. **99.6% of cutoffs are taken on the first searched
move**, and the repetition scan yields 0.013%.

### TH-51 · fuse the first max-scan into the scoring pass — CONFIRMED

The scoring loop and the sort's first pass walk the same array asking the same
question, and that first pass is the one that nearly always decides the node.
Tracking the running maximum while scoring drops n-1 of the 30.8 comparisons.

Node identity rests entirely on the tie-break: `>` keeps the FIRST index
holding the maximum, exactly as the sort did. Ties are common (equal history,
usually 0), so `>=` would have silently reordered the tree while looking
correct.

### TH-52 · one in-check test per node — CONFIRMED, and it revives a rejected toggle

`FAST_LEGALITY_IN_SEARCH` was measured neutral-to-negative and left off. The
reason was not the shortcut: `DROP_CHECK_PRUNE_IN_SEARCH` already calls
`attacked()` on the mover's king, and the toggle called `attacked()` on the
same square with the same arguments a few lines later, `king_sq()` doubled the
same way. Hoisting both to one computation turns it positive.

**A toggle measured negative can be negative for a reason that has nothing to
do with the idea in it.** This one sat rejected while its cost was a duplicated
line, not the shortcut it was testing.

### TH-50 · Bloom-gate the repetition scan — CONFIRMED, and small

582M iterations for 78,141 hits looked like the obvious target. A 64-bit Bloom
filter of the path keys skips ~80% of the loops and bought +0.89% against a
0.74% floor. The loop was already L1-resident and well predicted, so there was
never much there. Kept because it is free of risk and grows with depth.

### The measurement, and a false reading it produced first

| arm | cpu | vs baseA |
|---|---|---|
| baseA / baseB | 12.318s / 12.228s | **0.74% floor** |
| Bloom-gated rep scan | 12.210s | +0.89% |
| fused max-scan | 11.361s | **+8.42%** |
| both | 11.244s | +9.56% |
| + fast legality in search | 11.101s | **+10.97%** |

Depth 18, one worker, 2^24, 11 interleaved repeats, first discarded. Nodes
identical at 82,712,965 across all six arms; perft(7) 1,355,253; regress digest
811f304f1eef7998 unchanged.

**The first run of this A/B was taken on a loaded machine and read the Bloom
gate at +3.55%, four times its real value.** Load average was 25 with seven
other processes at ~125% CPU; per-run spread was 35% and the control floor
2.71%. An earlier 5-repeat pass on the same busy machine had the Bloom gate at
**-2.76%**, i.e. the wrong sign. The interleaving keeps the control floor
honest but it cannot manufacture resolution that is not in the samples.
`time.process_time` is not load-proof either -- shared LLC and memory bandwidth
still move it.

### What is left in the interior node

Movegen still builds 16.68 moves to search 2.09, and 82.9% of generated moves
are never tried. That is the biggest remaining block and it is what staged
generation (TH-15, closed at a ~1.5% ceiling) was aimed at. The TT move is
present at only 2.9% of interior nodes at 2^24 with one worker, so the ordering
statistics above are NOT the deep-hunt operating point and should be re-taken
at 2^30 / 16 workers before anything is designed on them.

## Post-campaign: TH-53 · staged quiet drops — REJECTED

The interior-node instrumentation said 13.88 of the 16.68 moves a node
generates are quiet non-checks, mostly drops, and that 81.1% of cutoffs come
from a capture or a check. At 86.2% x 81.1% = 70% of interior nodes that whole
block is generated, scored and never looked at. Deferring it looked like the
biggest single lever left.

Built as `gen_drops(p, out, sel, eks)` emitting drops in the canonical order
(type ascending, then square ascending) and filterable to the checking ones or
the rest, using the SAME masks `gives_direct_check` reads so the generator and
the ordering cannot disagree about what a checking drop is. `search()` starts
with piece moves plus checking drops and generates the quiet block only when
the best remaining move scores below the capture floor of 1<<20 -- or when
stage A runs out, which happens when every one of its moves was illegal and
which, missed, reports "no legal move" and invents a mate.

**Not node-identical, and that is what kills it.** Deferring the quiet drops
puts them at the end of `buf` instead of interleaved with the checking drops,
and the selection sort resolves ties by array position. Depth 18, one worker,
2^24, nine interleaved repeats, control floor 0.16%:

| arm | nodes | cpu |
|---|---|---|
| base A / B | 82,712,965 | 11.632s / 11.613s |
| staged | **87,817,720** (+6.2%) | 12.039s (**-3.38%**) |

Per node it is 2.5% faster (140.6 -> 137.1 ns). It searches 6.2% more nodes,
so it loses.

### What the 2.5% actually means

Skipping 9.7 of 16.68 generated moves at 70% of interior nodes is worth 2.5%.
**A move that is generated and never searched costs about 2-3 cycles, not the
10 assumed when sizing this.** The expensive parts of a node -- make/unmake,
`attacked`, the recursive call -- are already paid only for moves that ARE
searched, so removing generation volume removes almost nothing.

This is the second independent measurement saying so. The earlier bitboard
experiment replaced generation, the in-check test AND the legality filter with
masks inside `search()` and measured node-identical and time-null on six
workloads. Both results contradict the tier-4 profile's "movegen is ~40% of a
search node", and both are right: a profile measures where time is spent, not
what would change if that work were removed.

### The path that would make it node-identical, and why it was not taken

Ties would have to break on something derived from the MOVE rather than its
array position -- then layout would stop mattering. That is a two-step
campaign: change the tie-break first (Class B, node effect a coin flip), then
stage on top of it (Class A). With the ceiling measured at 2.5% per node, it is
not worth the two measurements.

**Estimate was 4x high, the third time in a row in the same direction.** Sizing
from waste counts (74% of horizon moves unused -> predicted 4-5%, got 2.06%;
58% of interior movegen unused -> predicted ~10%, got 2.5%) systematically
overshoots, because the waste is counted in MOVES and the cost is not
proportional to moves.

## Post-campaign: pricing the hot operations by duplication

`sample` needs sudo on this machine and gprof is unusable on Darwin, so the
operations were priced by DUPLICATION instead: build an arm that performs one
operation twice, XOR the redundant result into a global so it cannot be
elided, and read the marginal cost off the delta. Node-identical by
construction -- every arm returned 82,712,965 -- and it measures what removing
the work would save, which is the question a profile does NOT answer.

Depth 18, one worker, 2^24, nine interleaved repeats, base 11.121s, control
floor 0.97%:

| one extra call of | cost | count | per call |
|---|---|---|---|
| **selection-sort pass** | **10.62%** | ~1.22G comparisons | ~1.1 ns |
| **`order_score`** | **8.96%** | 661M | ~1.65 ns |
| make + unmake | 2.67% | 82.7M | ~3.7 ns |
| `tt_probe` | 2.50% | 42.1M | ~6.6 ns |
| `attacked` | 2.34% | (not counted separately) | |

Ordering is where the time is, which is why both of this session's wins landed
there (check masks +8.20%, fused max-scan +8.42%) and why replacing the
generator with masks measured null twice.

`tt_probe`'s 2.50% is at 2^24, where the table is 256 MB. At the 2^31 the deep
hunts use, a probe is a genuine DRAM miss and this row is worth much more --
it is the one number here that does not transfer to the real operating point.

### Where the sort cost actually sits

| interior nodes | share | sort comparisons | per node |
|---|---|---|---|
| with a cutoff | 86.2% | 17.2% | 3.0 |
| **without a cutoff** | **13.8%** | **82.8%** | **90.6** |

The 13.8% of nodes that never cut off pay 83% of all sorting, because the
selection sort is O(n^2) and they run it to completion over ~16.7 moves. A
proper sort would take 90.6 comparisons to roughly 68 -- about 1.2% overall,
and NOT node-identical, since the selection sort's swaps do not produce a
stable order. Not worth a node measurement.

### The lead that died in one check

`order_score` at ~5.8 cycles looked like it might be paying for thread-local
access: it touches `killers[ply][0]`, `killers[ply][1]`, `history[stm]` and
`tl_jitter`, four `_Thread_local` objects, 661M times. On Darwin ARM64 a
thread-local in a dylib can go through a TLV descriptor CALL. Disassembling the
shipped build shows zero `tlv_get_addr` sites and `order_score` fully inlined,
so the compiler had already resolved and hoisted them. Nothing to win; recorded
so it is not re-derived.

## Post-campaign: WHITE to depth 28, BLACK to depth 30

First pair of bounds taken in one session on one build at one table size, so
the per-depth timings are directly comparable for the first time. 16 workers,
tt 2^31 (32 GiB) from depth 6, seed 0, Apple M5 Pro.

| | White | Black |
|---|---|---|
| bound | **no forced win within 28 plies** | **no forced win within 30 plies** |
| deepest slice | 720,270,063,779 nodes / 10,231.6s | 762,410,631,416 / 9,796.2s |
| whole run from depth 6 | 861,770,708,152 / 3.41 h | 1,010,074,226,106 / 3.65 h |
| average | 70.3 Mnps | 76.8 Mnps |
| table | 100% full from depth 26 | 100% full from depth 28 |

**The session's engine work, measured on the real workload: +16.2% nps.** White
depth 26 went 1747.6s to 1523.1s on 1.3% more nodes (lazy-SMP noise), 60.10 ->
69.85 Mnps.

That is BELOW the +21.79% measured at depth 18 with one worker, and the gap is
worker count, not table size. An earlier claim in this file that the gain "does
not dilute as the table grows" was tested at ONE worker at 2^24 and 2^28 and is
true there; at 16 workers more of the time is memory stalls that none of these
changes touch. **Quote +16.2% for the deep hunts and +21.79% for single-thread
work; they are different questions.**

### The depth-28 step, and the ETA it broke

| growth into | d20 | d22 | d24 | d26 | d28 | d30 |
|---|---|---|---|---|---|---|
| White | x8.2 | x4.1 | x4.4 | x3.9 | **x6.8** | - |
| Black | x3.9 | x6.4 | x9.6 | x2.1 | **x8.5** | x3.6 |

Both colours step at depth 28 and NEITHER colour's own history predicts it.
White sat in x3.9-x4.4 for three straight transitions; the ETA extrapolated
from the previous growth factor and called depth 28 at 416.51G against an
actual 720.27G. The run therefore printed "36% of est" while under a quarter of
the way through, for over an hour. A wrong ETA is worse than none: it is the
number a person uses to decide whether to wait or kill a run.

Fixed by estimating from MEASURED_NODES -- the counts above -- rescaled by what
the live run is actually costing, with the other colour's ratio as the fallback
where a depth has not been measured. Still a guess: borrowing Black's x8.5 for
White's depth 28 gives 909G against 720G, 26% high. A better class of wrong.

**Two live estimates of my own, both stated too confidently.** Black to depth 30
was called at ~2.6h (range 2.0-4.2h) and took 3.65h. White's remaining depth-28
time was called at ~65 min with a 40-100 min band and took ~20 min, BELOW the
band -- the x8.545 anchor from Black overshot White's actual x6.77. The
direction of the miss flipped between the two, which is the useful part: these
are single-anchor extrapolations across an unmeasured depth, and a stated band
should have been wider in both cases.

### Owed

Neither bound has been re-run under a second Zobrist seed. That is the one
unquantified soundness residual for both, and it is the same one the run itself
prints at the end. Depth 30 for White projects to ~2.6T nodes at Black's x3.6,
about 10 hours, on a table that has had nothing left to give for two plies --
capacity, not replacement policy, is the binding constraint now.

## Post-campaign: the transposition table — +19.5%, and a correction

### First, the pricing table above is wrong about `tt_probe`

The duplication method -- perform an operation twice, read the marginal cost
off the delta -- is valid for compute and **invalid for memory latency**. The
duplicate probe reads the SAME bucket, so the first probe pulls the line into
L1 and the second measures L1, not the miss. The tell was the scaling:

| extra same-bucket probe | 2^24 | 2^28 | 2^30 |
|---|---|---|---|
| cost | 2.58% | 0.88% | **0.38%** |

A DRAM cost that gets cheaper as the table grows is not a DRAM cost. It only
looks smaller because the baseline is slower (11.0s -> 14.8s), so the same
absolute L1 latency is a smaller share.

Corrected instrument: probe a DIFFERENT bucket (`key * 0x9E3779B97F4A7C15 + 1`),
which is a genuine miss. At 2^30 that costs **-3.53%** for 42.2M extra probes,
i.e. **~12.4 ns per probe** -- nine times what the broken instrument said. Read
as an upper bound: the extra access also evicts useful lines.

**`order_score` and the sort pass are unaffected** -- both are compute, both
were measured correctly, and they remain the two biggest single rows.

### TH-53 · stop probing at depth 1 — CONFIRMED, +19.5%

`HORIZON_SKIP_TT` stopped one ply too late. Probe distribution over a depth-18
hunt:

| depth | probes | hit % | share of stores |
|---|---|---|---|
| **1** | **29,386,814 = 70%** | **4.5%** | 2.6% |
| 2 | 4,919,627 | 12.7% | 39.4% |
| 3 | 5,773,587 | 19.1% | 42.7% |
| >= 4 | 1,977,280 | 23-43% | 15.3% |

70% of every probe in the tree is taken at depth 1, hits 4.5% of the time, and
the store gate already refuses unproven depth-1 stores. The most numerous probe
in the search is a random multi-GiB access that almost never writes back.

Class B on purpose: those 4.5% carry real cutoffs, so the tree grows 7.0% and
the run is still far faster.

| workload | control floor | gain |
|---|---|---|
| 1 worker, d18, 2^30 | 0.21% | **+19.5%** (83,473,350 -> 89,301,909 nodes) |
| 16 workers, d20, 2^30 | 6.2% | **+19.2%** |
| 1 worker, d18, 2^24 | 0.23% | **+13.7%** |

It pays even at a small table, and it pays at the worker count the hunts
actually use. **It cannot affect a bound**: refusing a TT cutoff means
computing the value instead of reading it, so it adds work and can never
remove a proof. Digest 811f304f1eef7998 and every regression VALUE unchanged;
only node counts moved, which is the correct signature for this class.

Skipping depths 1 and 2 measured +19.0%, worse -- depth-2 probes hit 12.7% and
carry the 39.4% of stores depth 1 does not.

### TH-54 · prefetch the child bucket — KEPT, magnitude unresolved

Prefetch was rejected as NULL by an earlier campaign at 2^22 and 2^26. That
verdict stands for those sizes; at 2^30 on the base build it measures **+2.11%**
against a 0.16% floor.

**The gate is the whole content of the change.** Written the obvious way, as
`depth >= 2`, it prefetches for depth-1 children that TH-53 just stopped
probing: +15.4% against TH-53's own +19.5%, a fifth of the win handed back as
wasted bandwidth. Gated on `depth - 1 >= TT_MIN_PROBE_DEPTH` the two toggles
cannot drift.

On top of TH-53 two runs gave +0.55% (floor 0.43%) and +4.7% (floor 1.0%), the
second on a machine carrying GUI load with 21-25% per-run spreads. Positive in
every run, one instruction, node-identical -- kept, with **no number claimed**.

## Post-campaign: TH-55 · ordering at depth 1 — CONFIRMED, +19%

The depth-1 probe gate raised the obvious next question: what ELSE does a
depth-1 node do that it does not need? Instrumented by depth over a depth-18
hunt:

| depth | share of interior | moves generated | moves tried | cutoff % | cut on 1st |
|---|---|---|---|---|---|
| **1** | **72.6%** | **17.21** | **0.99** | 99.4% | **100.0%** |
| 2 | 11.1% | 13.27 | 9.14 | 2.3% | 48.5% |
| 3 | 11.9% | 16.66 | 1.02 | 98.6% | 99.1% |
| 4 | 1.9% | 13.43 | 8.61 | 6.1% | 56.1% |

Depth-1 nodes are 72.6% of all interior nodes, generate 17.21 moves, search
0.99 of them, and **every single one of their cutoffs comes on the first move
tried**. That is structural: in a null-window mate hunt, at depth 1 any move
whose child returns the horizon's unknown 0 already fails high, so which move
goes first cannot matter. The node was still scoring all 17.21 and running a
full max-scan over them -- 512M of the search's 661M `order_score` calls.

**Depth 1 only, and the sweep is the argument.** Odd depths all look alike in
the table, which invites a higher threshold. It loses badly, because a higher
threshold also catches depth 2, where ordering is doing real work:

| ORDER_MIN_DEPTH | nodes at d17 | result |
|---|---|---|
| **2** (depth 1 only) | 59.3M -> 64.1M | **+19.15%** |
| 3 (also depth 2) | -> 129.6M (+118%) | -16.43% |
| 4 | -> 156.3M (+163%) | -28.14% |

| workload | passes | floor | gain |
|---|---|---|---|
| 1 worker, d17, 2^24 | 1.1937 / 1.1897 / 1.1915 | 0.40pp | **+19.15%**, p=2.33e-10 |
| 16 workers, d20, 2^30 | 1.2303 / 1.1694 / 1.1967 | 6.09pp | **+19.67%**, p=0.000488 |

Class B, and correctness rests on the plainest fact in alpha-beta: the value is
independent of move order, so no bound is at risk. The harness confirms rather
than assumes it -- digest 811f304f1eef7998 with every value AND soundness flag
identical across all 16 rows, on 4.26% FEWER nodes.

### Compiler flags — all NULL

Never questioned before: `engine_c.py` builds with a plain `-O2 -pthread
-shared` on Apple Silicon. Six variants, every one inside the noise, none with
p below 0.07: `-O3` -0.70%, `-mcpu=native` -0.13%, `-O3 -mcpu=native` -0.57%,
`-flto` +0.43%, `-O3 -mcpu=native -flto` +0.38%, `-funroll-loops` -0.25%.
`-O2` is leaving nothing on the table here, and that is now measured.

### What this pair of depth-1 changes says

Both wins this round came from the same observation: **the most numerous node
class in the tree was paying for machinery that class cannot use.** Depth 1 is
72.6% of interior nodes; it was probing a multi-GiB table that hits 4.5% of the
time, and ordering 17 moves to search one. Neither was found by a profiler --
both came from counting what each depth actually does.

Also worth recording: these are NOT nps wins. Both search MORE nodes at one
worker (+7.0% and +8.0%) and are ~19% faster in time to depth. Reported as nps
they would read as regressions, which is why `scripts/nps.py` now picks the
metric from the node counts instead of from the operator.

## Post-campaign: TH-56 · lazy generation at unordered depths — REJECTED

After TH-55 stopped ordering at depth 1, those nodes search moves in
GENERATION order -- so the first move tried is the first move generated, and a
prefix generator would pick the same one. Depth-1 nodes generate 17.21 moves
and try 0.99, so building the other 16 looked like free money, and unlike the
staged-drop attempt this version is genuinely node-identical: gated on the node
being unordered, regenerating the full list re-emits the same moves in the same
order into the same buffer, and TH-55's swap guard keeps the already-searched
prefix untouched.

It delivered the node identity and lost anyway.

| | |
|---|---|
| nodes | 64,074,809 both arms -- identical, as claimed |
| passes | 0.9589 / 0.9595 / 0.9575 |
| floor | 0.20pp between passes |
| result | **-4.11%**, 0 of 33 ratios favoured it, p=2.33e-10 |

### Three independent measurements now say the same thing

**Move generation volume is not the lever in this engine.**

| attempt | outcome |
|---|---|
| bitboard generation, in-check test and legality filter inside `search()` | node-identical, time NULL on six workloads |
| staged quiet drops (TH-53 in an earlier section) | 2.5% per node, lost to a 6.2% node increase |
| prefix generation at unordered depths (this) | node-identical, **-4.11%** |

The common cause is the price of a generated move that is never searched:
about 2-3 cycles. Removing that work saves almost nothing, while the machinery
to avoid it -- an extra branch in the hottest loop, a third instantiation of
`pseudo_moves_n` and its instruction-cache footprint, and a full regeneration
whenever the prefix is exhausted -- costs more than it saves. Every attempt to
generate fewer moves has now failed, and the tier-4 profile's "movegen is ~40%
of a search node" has been contradicted three times.

**What has worked instead, every time, is removing work per node that the node
could not use**: the horizon's TT probe, the depth-1 TT probe, check detection
by mask, the fused max-scan, and ordering at depth 1. Not less generation --
less machinery around it.

## Post-campaign: both bounds reproduced under a second Zobrist seed — CONFIRMED

Every "no forced win within N plies" claim in this repo carried the same
caveat: the bound is immune to horizon unsoundness, to a TT cutoff overrunning
its budget and to store-side graph-history interaction, but NOT to a 64-bit
Zobrist collision, which has no directional structure and could prune a subtree
holding a real mate. That residual was unquantified rather than zero.

Re-run under `--seed 0xC0FFEE --fresh`, on the shipped build
(4202529700557302426), 16 workers, tt 2^31:

| | White | Black |
|---|---|---|
| seed 0 | no forced win through **28** | no forced win through **30** |
| seed 0xC0FFEE | no forced win through **28** | no forced win through **30** |
| depths where the values disagree | **0** | **0** |
| seed-0xC0FFEE cost | 805,234,472,864 nodes / 2.32 h | 1,097,208,238,876 / 3.05 h |

**The node counts are not supposed to match, and do not.** Different keys mean
a different table, so per-depth counts move by -87% to +37% and the totals by
-6.6% (White) and +8.6% (Black). A run that reproduced the node counts would
mean the seed had not changed. The result is that the VALUES agree at every
completed depth.

What this buys: a collision that hid a mate would have to strike the same
subtree under two independent key sets. The residual is now negligible rather
than unquantified. **It is not zero** -- two seeds are two samples, not a
proof -- but it is no longer the weakest link in the claim.

### The engine work, measured on the real workload

These runs are the first full hunts on the post-TT, post-ordering build, so
they price the session's gains against the runs that produced the bounds:

| | seed-0 run | seed-0xC0FFEE run | |
|---|---|---|---|
| White | 70.26 Mnps | **96.35 Mnps** | +37.1% |
| Black | 76.83 Mnps | **100.03 Mnps** | +30.2% |

Wall clock moved 3.41 h -> 2.32 h and 3.65 h -> 3.05 h, but those two figures
are not comparable on their own: the trees differ by -6.6% and +8.6%. **nps is
the right column here** precisely because the seed changed the tree, which is
the reverse of the usual rule in this file -- and it agrees with the +28-30%
the controlled A/B runs measured.
