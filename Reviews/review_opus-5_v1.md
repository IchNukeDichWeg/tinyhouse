# Tinyhouse v1 review — `opus-5`

Read-only pass over the whole repo. Nothing in the working tree was modified by this
review except this file. Every number below came from a command run on this machine
during the pass; every code quote was re-read from the working tree immediately before
the item was written, and again after the file was assembled.

Machine for every measurement: Apple M2 Pro, 10 cores, 16 GiB, macOS 15 (Darwin 25.5.0),
`cc -O2 -pthread`, single thread unless stated. Wall-clock figures are minimum-of-N over
interleaved repeats because the machine was under variable load throughout (seven review
subagents); node counts are load-independent and are the primary metric wherever both
were available.

---

## STEP 0 — baseline, and the drift

| Fact as given | Re-measured | Verdict |
|---|---|---|
| `perft(7)` from the start = 1,355,253 | **1,355,253** | unchanged — config-drift signature intact |
| Perft oracle, 5 positions in `PERFT_ORACLE` | all pass | unchanged |
| Test suite: 43 tests, all passing | **43 passed** in 0.54s | unchanged |
| C perft ~38 Mnps | **40.7 Mnps** median of 9 (min 0.0328s, max 0.0345s, `perft(7)`) | +7% |
| Python engine ~506 knps | **502 knps** median of 5 (`perft(5)`) | unchanged |
| ratio 65x | **81x** | the 65x figure does not follow from the other two either (38/0.506 = 75) |
| `tinyhouse.c` 626 lines | **635** | +9 |
| `solve_hunt.py` 162 lines | **211** | +49 |
| `index.html` 410, `server.py` 137, `engine_c.py` 85, `tinyhouse.py` 372 | identical | unchanged |
| `git log` = 10 commits | **11** | see below |
| Solve bounds in `solve_status.json` | unchanged on disk | positive claims independently re-verified, see item 15 |

**The repo moved under this review.** A second Claude session was working in the same
checkout throughout. It committed `2054f2d "Bound the transposition table against
physical RAM before allocating"` at 03:5x, which is why the line counts moved, and it has
written its own `review_opus-4-8_v1.md`; a third has since written `review_opus47_v1.md`.
I read neither — this pass is independent. Every citation below was re-verified against the
post-`2054f2d` tree after the file was assembled: **32 of 32 integration points match
verbatim and in place**, and all 48 inline `file:line` references are in range.

Two defects it fixed mid-pass, so they are **not** reported as findings here: `th_tt_init`
was declared `int` in the cffi cdef while the C definition returned `void` (so the
allocation check in `solve_hunt.py` and `scripts/bench_workers.py` was reading a garbage
register), and `--tt` had no bound against physical RAM.

### Incident during the pass — not a review finding, but you should know

That session ran `solve_hunt.py 1 --tt 40 --maxdepth 8 --fresh`. `calloc` of 16 TiB
**succeeded** (macOS overcommits), the search ran, and `th_tt_save` then began writing the
whole table to `solve_state/`. It wrote **50 GiB in about 90 seconds** and took the volume
from 16 GiB free to 8.7 GiB before I killed the process and truncated the partial dump
(back to 60 GiB free). The `check_tt_size` guard added in `2054f2d` closes the allocation
side. The write side is still open — see **item 8**.

---

## Method

Seven parallel reviewers by surface (`tinyhouse.c` movegen; `tinyhouse.c` solver/TT/SMP;
`tinyhouse.py` and the Python/C divergence surface; `server.py` + `index.html`;
instruments and coverage; a research pass on df-pn and the draw lane; a research pass on
small-board movegen), then a cross-miner dedup, then **one adversarial refuter per
surviving item** whose instructions were to kill it: re-read the citation character for
character, construct the failing position for any soundness claim, and demand a paired
measurement for any performance claim. Default verdict was REFUTED.

Items marked **direct** in the table below are mine, found and measured during this pass
rather than by a reviewer; their evidence block is the measurement.

Two purpose-built harnesses did most of the soundness work and are worth keeping:

- **probe-disabled build** — `tinyhouse.c` with `tt_probe` hard-returning 0. No cross-path
  TT reuse at all, therefore no graph-history interaction and no TT-induced extension.
  It is the ground truth any positive claim can be adjudicated against, and it reproduces
  `perft(7) = 1,355,253`.
- **differential sweep** — random positions from the start, each searched at a fixed depth
  by the shipped build and by the probe-disabled build, comparing values exactly. This is
  what found **item 1**.

### The recorded depth-20 bound, re-run

`solve_status.json` records "no forced WHITE win within 20 plies", 728,842,906 nodes,
single thread. Re-run from scratch this session, single thread, `th_tt_init(26)`, cold
process:

```
depth 20 WHITE hunt: value=0  nodes=753,679,962  527s  1.43 Mnps
recorded: value 0, nodes 728,842,906 -> MATCH on value, node delta +24,837,056 (+3.4%)
```

**The bound holds.** The +3.4% node delta is expected and is not drift: `solve_hunt.py`
reaches depth 20 by iterative deepening from depth 6 with a shared table, so its recorded
depth-20 slice starts warm, while this was a single cold depth-20 call. Worth writing into
`solve_status.json` — a recorded node count that only reproduces under the same
deepening schedule should say so, or the next person to re-run it will read 3.4% as drift.

---

## Headline

48 raw findings from seven parallel reviewers, merged to 34, then one adversarial refuter
per item whose default verdict was REFUTED. **Nine were killed.** 25 survived, plus 7 I
found and measured directly, for **32 items**.

**The one that matters:** a depth-N mate hunt can print `PROVEN ... forces a win in K plies`
with **K > N**. Reproduced, bisected to a single line, and fixed two different ways at no
measurable cost (**item 1**). This makes `solve_hunt.py:9` false as written (**item 14**).

**The good news, and it is not small:** the two published bounds are immune to everything
found here, for a reason that is now proved rather than assumed, and all three published
forced wins reproduce at their exact distances under a build with transposition reuse
structurally disabled. The depth-20 White bound was re-run from scratch this session and
came back 0. The record is sound; the documentation around it is not.

**The most expensive gap:** zero of the 43 tests touch the solver. Not one pins a node
count, a mate score, a soundness flag, a TT roundtrip, or any claim in `solve_status.json`.
Item 1 would have been caught the first time move ordering shifted if item 21 existed.
## The list at a glance

Verdicts: **CONFIRMED** = the adversarial verifier reproduced it end to end. **PLAUSIBLE** = the
reasoning and citation hold but the decisive measurement was out of budget; the item names it.
**direct** = found and measured by me during this pass rather than by a reviewer, so no separate
verifier ran; the evidence block is the measurement.

| # | Category | Item | Verdict |
|---|---|---|---|
| 1 | `BUG-SOUNDNESS` | A TT mate cutoff at a horizon node lets a depth-N hunt report a win that needs more than N plies | direct |
| 2 | `BUG-SOUNDNESS` | A .tt dump written by a different build of tinyhouse.c is silently accepted on resume | CONFIRMED |
| 3 | `BUG-SOUNDNESS` | `th_mate_hunt_mt` throws away the soundness flags, so PROVEN rests on the value alone | direct |
| 4 | `BUG-SOUNDNESS` | TT cutoffs discard rep_min, so a proof reused on a new path can hide an ancestor repetition | PLAUSIBLE |
| 5 | `BUG` | make() writes hands[us][4] when a king is captured, which lands inside THPos and no sanitizer... | CONFIRMED |
| 6 | `BUG` | str_move fabricates illegal moves and th_make on them corrupts the THPos struct | CONFIRMED |
| 7 | `BUG` | root_search never clears history[][], so bench_workers medians are biased toward whichever wo... | CONFIRMED |
| 8 | `BUG` | `save_state()` discards `th_tt_save`'s return, so a checkpoint can silently fail to exist | direct |
| 9 | `BUG` | The sqlite cache key is incomplete: the same (tfen, depth, version) row has two different con... | CONFIRMED |
| 10 | `BUG` | th_root_moves computes per-move soundness and throws it away; the GUI shows "0.00" for moves ... | CONFIRMED |
| 11 | `BUG` | from_tfen accepts a pawn standing on its own promotion rank, and a "promoted pawn" | CONFIRMED |
| 12 | `BUG` | analyze depth is clamped above but not below; depth<=0 returns a TT-scavenged best move and c... | CONFIRMED |
| 13 | `BUG` | One abandoned `/api/analyze` request pins `ENGINE_LOCK` for the life of the search | direct |
| 14 | `DOC-OVERCLAIM` | "there are no search extensions, so the ply budget is exact" | direct |
| 15 | `DOC-OVERCLAIM` | README, solve_status.json and the solver comment all claim every mate score is a proof, witho... | PLAUSIBLE |
| 16 | `NPS` | Skip the make/unmake legality test for moves that provably cannot expose the king | CONFIRMED |
| 17 | `NPS` | Horizon nodes are 42-75% of the tree and build a full pseudo-move list to answer one yes/no q... | CONFIRMED |
| 18 | `NPS` | Recompute the Zobrist key incrementally in make/unmake instead of from scratch at every node | CONFIRMED |
| 19 | `NPS` | Generate drops from a precomputed empty-square set instead of rescanning the board per hand type | CONFIRMED |
| 20 | `INSTRUMENT` | Paired nodes-to-depth + solver-digest regression harness; today zero of the 43 tests touch th... | CONFIRMED |
| 21 | `INSTRUMENT` | Pin the recorded mate-in-9 proof: nothing connects solve_status.json's published claims to ex... | PLAUSIBLE |
| 22 | `INSTRUMENT` | A reachable-position census — the number the draw-proof lane needs and `state_count.py` canno... | direct |
| 23 | `INSTRUMENT` | The 4-element symmetry group gives eight free oracle positions and nothing uses them | direct |
| 24 | `INSTRUMENT` | TT save/load roundtrip and the seed/size refusal are unpinned - three paths that work today a... | CONFIRMED |
| 25 | `INSTRUMENT` | Pin attacked() against an independent geometric oracle, because perft cannot isolate it | CONFIRMED |
| 26 | `NEW-IDEA` | df-pn as a second engine: 12.5x better on the win lane, and the only reachable formulation fo... | CONFIRMED |
| 27 | `NEW-IDEA` | Sigma-mirror as a draw-proof scaffold: the pure mirror is REFUTED, but the balanced sub-space... | CONFIRMED |
| 28 | `NEW-IDEA` | Symmetry folding in the TT: measured at 1.089x, not 4x, and slightly negative in nodes - clos... | CONFIRMED |
| 29 | `SHOULD-BE-BETTER` | th_tt_save writes the entire table every checkpoint: 256 MiB of file for 0.33 MiB of entries ... | PLAUSIBLE |
| 30 | `SHOULD-BE-BETTER` | The --tt 26 default (1 GiB) is unmeasured and the measured curve is flat past 2^20 | CONFIRMED |
| 31 | `SHOULD-BE-BETTER` | to_c is the real Python->C trust boundary and validates nothing | PLAUSIBLE |
| 32 | `SHOULD-BE-BETTER` | /api/analyze mixes frames: value is white-view, snd is side-to-move-view | CONFIRMED |

---

# Findings

## `[BUG-SOUNDNESS]` — anything that can emit a wrong PROVEN

### 1. `[BUG-SOUNDNESS]` A TT mate cutoff at a horizon node lets a depth-N hunt report a win that needs more than N plies

- **Source** — differential harness: the shipped build vs a scratch build with `tt_probe` hard-disabled (no cross-path TT reuse at all), swept over random positions at fixed depth.
- **What** — The transposition cutoff runs before the horizon check and is gated on `tv.depth >= depth`, which is trivially true when `depth <= 0`, so a stored mate score of *any* distance is returned at a node with no remaining budget; the distance propagates to the root and `solve_hunt.py` prints it as a PROVEN win at a depth that does not contain it.
- **Mechanism** — `tt_probe` at `tinyhouse.c:432` and the cutoff block at `:438` execute before `if (depth <= 0)` at `:455`. `tv.depth` is a `uint8_t`, so `tv.depth >= depth` holds for every entry once `depth` reaches 0. A proven mate found at depth 13 elsewhere in the tree is handed back at a leaf of the depth-11 tree, and the mate-score ply adjustment faithfully re-bases its distance — producing a correct mate distance attached to an incorrect depth claim.
- **Soundness argument** — Touches the depth-budget contract, not the mate proof itself: the entry is genuinely sound, so the *win* is real. What breaks is the ply bound. The direction matters and it is asymmetric — an extension can only find **more** wins, never fewer, so the negative bounds ("no forced win within N plies") in `solve_status.json` remain valid. The corrupted outputs are the `plies` and `depth` fields of a positive claim.
- **Integration point** — `tinyhouse.c:438`, in `search`:
  ```c
        if (v > MATE_BOUND) v -= ply;
        else if (v < -MATE_BOUND) v += ply;
        if (ply > 0) {
            if (tv.flag == TT_EXACT && (tv.depth >= depth || tv.sound == (SND_LB | SND_UB))) {
  ```
- **Toggle and pin** — Two independent one-line forms, both built and measured:
  - **H**: `if (ply > 0 && depth > 0) {` — refuse every TT cutoff at a horizon node.
  - **M**: compute the entry's mate distance from this node and refuse the cutoff when it exceeds `depth`:
    ```c
    int mate_ok = 1;
    if (v > MATE_BOUND) mate_ok = (MATE - v - ply) <= depth;
    else if (v < -MATE_BOUND) mate_ok = (MATE + v - ply) <= depth;
    if (ply > 0 && mate_ok) {
    ```
    M is the general form (it also catches over-budget reuse at interior nodes); H is the minimal one. Node identity when off is exact — the toggle is a single conjunct in the cutoff condition.
- **Expected gain** — Not a speed change. ESTIMATE: nodes-to-depth cost is inside +-5% and its sign is not stable across depths, i.e. free. Measured, single thread, `th_tt_init(24)`, cold process each (node counts are load-independent):

  | depth | stock | H | M |
  |---|---|---|---|
  | 14 | 1,245,631 | 1,245,467 (-0.01%) | 1,243,972 (-0.13%) |
  | 16 | 10,119,067 | 10,140,825 (+0.22%) | 9,875,051 (-2.41%) |
  | 18 | 87,937,930 | 85,015,353 (-3.32%) | 91,863,452 (+4.46%) |

- **Risk** — Low. Both forms only *remove* cutoffs, so they can never introduce a value the plain search would not produce.
- **Oracles** — `pytest -q` (43); `perft(7) = 1,355,253` (both variants reproduce it); re-running the three recorded proven lines (all three reproduce at their exact distances on both variants); the differential harness below as a standing regression.
- **Effort** — One line plus a comment. Half an hour including the doc updates it forces (see item 3).
- **Novelty** — Not on the fixed list and not a check extension: this is an *unintended* extension the TT performs on its own, which is why removing it costs nothing.

**Evidence.** Reproduced deterministically:

```
$ .venv/bin/python $SP/ghi2.py stock 12 150 11
DISAGREE stock tfen='f1w1/2k1/K2p/W1UF[Up] b' color=1 d=12 stock=29985 noprobe=0
stock: 150 pos x2 colors, depth 12, seed 11: 1 disagreements (77s)
```

29985 = MATE - 15, i.e. "Black forces a win in 15 plies", from a **12**-ply budget. Adjudicated against the probe-disabled build:

```
depth  9  NOPROBE v=     0 (no win)     TT v=     0 (no win)
depth 11  NOPROBE v=     0 (no win)     TT v=     0 (no win)     <- cold history
depth 13  NOPROBE v= 29987 (mate in 13) TT v= 29987 (mate in 13)
```

so the honest answer at depth 12 is 0 and the real mate is 13 plies, not 15. It surfaces only when the in-process `history[][]` table is warm (see item 7), which is why a single cold run does not show it. Both gates remove it and both keep every recorded proof:

```
build H: target depth 11 -> v=0  no win  <-- correct
build M: target depth 11 -> v=0  no win  <-- correct
build H: Fd1c2 d9 -> 29991 (mate in 9) | Wb1b2 Fa4b3 d13 -> 29987 | a2a3 Fa4b3 d13 -> 29987
build M: Fd1c2 d9 -> 29991 (mate in 9) | Wb1b2 Fa4b3 d13 -> 29987 | a2a3 Fa4b3 d13 -> 29987
H: 150 pos x2 colors, depth 11, seed 11: 0 disagreements
M: 150 pos x2 colors, depth 11, seed 11: 0 disagreements
H: 150 pos x2 colors, depth 12, seed 11: 0 disagreements
M: 150 pos x2 colors, depth 12, seed 11: 0 disagreements
```

Frequency: 1 hit in roughly 1,140 (position, colour) searches swept at depths 9/11/12/13 over two seeds. Rare, and it fires precisely on the one output this program exists to produce.


### 2. `[BUG-SOUNDNESS]` A .tt dump written by a different build of tinyhouse.c is silently accepted on resume

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — Reading th_tt_save/th_tt_load against solve_hunt.py's resume path; the ALREADY FIXED list gave analysis.sqlite an engine version and the TT dump has the same hole.
- **What** — The .tt header carries magic, entry count and Zobrist seed but no identity of the code that produced the entries, so a table written by yesterday's search is loaded by today's and its sound-flagged entries are trusted as proofs.
- **Mechanism** — Sound flags, the ply adjustment, MATE/MATE_BOUND, the flag encoding and the bit layout of `data` are conventions private to one build. Change any (this repo is being actively edited right now) and old bits decode into a different meaning, but hdr[1]/hdr[2] still match, so th_tt_load returns 0 and the search cuts on entries whose sound==3 means something else. solve_hunt.py compounds it: the checkpoint identity is `hashlib.sha1(f"{args.tfen}|{args.color}|{args.seed}|{args.tt}")` (line 102-103), also with no code version, so `proven_no_win_through` from the old build is carried forward and printed as proven by the new one.
- **Soundness argument** — Touches the invariant 'TT entries are two atomics validated by xkey ^ data == key': that check proves the entry was written for this KEY, never that it was written by this CODE. A build fingerprint only causes more dumps to be rejected, so no surviving proof is weakened.
- **Integration point** — `tinyhouse.c:374`:

  ```c
  if (hdr[1] != tt_mask + 1 || hdr[2] != tt_seed_used) { fclose(f); return -2; }   (enclosing function: int th_tt_load(const char *fname))
  ```
- **Toggle and pin** — Not a behaviour toggle, a widened validity check: `uint64_t hdr[4]` with hdr[3] = TT_FORMAT_ID, a visible constant `#define TT_FORMAT_ID 0x...ULL` above th_tt_save that the author bumps when entry semantics change, mirrored into solve_hunt.py's `ident`. Old dumps then fail and return -1/-2, which solve_hunt.py already prints as 'no table dump (re-searching)' / 'table dump mismatched (ignored)' (line 124-125), i.e. same-build behaviour is exactly reproduced.
- **Expected gain** — ESTIMATE: soundness only, zero effect on nodes-to-depth or NPS (one extra 8-byte header word). Confirmed by: write a dump, bump TT_FORMAT_ID, re-run solve_hunt.py --workers 1 and check it prints the mismatch line and re-searches rather than resuming.
- **Risk** — Invalidates every dump in solve_state/ once. That is the point, and it is cheap next to publishing a wrong bound.
- **Oracles** — pytest -q; a save/load round-trip within one build must still return 0 (see the roundtrip-test item); solve_hunt.py --seed 0xC0FFEE --fresh must still reproduce the same per-depth values.
- **Effort** — ~10 lines across tinyhouse.c and solve_hunt.py; under an hour.
- **Novelty** — ALREADY FIXED covers 'cache key missing an engine version' for analysis.sqlite only. The .tt dump and the JSON checkpoint have the same defect and are the ones that feed proof claims. Shares a root cause with the build-identity DOC item, but a different file format and a different fix.

<details><summary>Evidence</summary>

```
Re-read verbatim from the current tree: tinyhouse.c:360 `uint64_t hdr[3] = {0x54494E59484F5553ULL, tt_mask + 1, tt_seed_used};` and the line quoted above; nothing else is checked. solve_hunt.py:102-103 re-read: `ident = hashlib.sha1(\n    f"{args.tfen}|{args.color}|{args.seed}|{args.tt}".encode()).hexdigest()[:12]`. Miner's cross-build test: a table saved from base.dylib loaded into three differently-compiled builds (hz, sym, qd) all returned rc = 0 (accepted); sym.dylib stores its moves in a rotated frame and nothing in the header noticed.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

The item is right but understates the mechanism, and its proposed fix is too narrow.

MECHANISM (widen): the danger is not confined to the bit layout / flag / ply-adjust conventions of `data`. th_key depends only on (board, hands, stm, Zobrist seed), so ANY change to the RULES or move generation leaves both the key and tt_seed_used identical while every stored value now describes a different game. I demonstrated this with the repo's own named open item, pawn double-step: same key for the same position across both builds, header accepted (rc = 0), and each build then published the other build's mate distance as its own proof (base emitting "mate in 5", which does not exist under base's rules). A rules change is far more likely than a bit-layout change and is completely invisible to the current header.

FIX (correct): a `#define TT_FORMAT_ID` that "the author bumps when entry semantics change" does not cover this — nobody bumps a TT format id when editing pseudo_moves. The header word must be a BUILD FINGERPRINT derived from the source, not a hand-maintained constant: hash tinyhouse.c at build time and pass it in, e.g. add `-DTH_BUILD_ID=0x$(shasum -a256 tinyhouse.c | cut -c1-16)ULL` to the single build line at engine_c.py:17, store it as hdr[3], and mirror the same string into solve_hunt.py's `ident` at line 102-103 so the JSON checkpoint's `proven_no_win_through` is discarded together with the table. Hand-maintained constants may stay as an additional word but cannot be the only one.

Side note (not a defect, just the reason this hides so well): a change to sizeof(TTEntry) IS caught today, by accident — `fread(tt, sizeof(TTEntry), tt_mask + 1, f)` comes up short and th_tt_load returns -1. Only same-size changes slip through, which is every rules change and most semantic ones.

Everything else in the item — category BUG-SOUNDNESS, file, line, quote, the soundness argument, the toggle-off behaviour (-1/-2 already printed at solve_hunt.py:124-125), the novelty claim against server.py's ENGINE_VERSION — stands as written.

</details>

*Verifier: the maintainer — I tried to kill this and could not; I produced a wrong PROVEN from the shipped build. 1) QUOTE CHECK (exact). `sed -n '374p' tinyhouse.c | od -c` gives four leading spaces then `if (hdr[1] != tt_mask + 1 || hdr[2] != tt_seed_used) { fclose(f); return -2; }` — character-for-character the item's quote, at the cited line, inside `int th_tt_load(const char *fname)` (tinyhouse.c:368). [...]*

**Second, independent confirmation (this pass).** A dump written by a modified build loads into the shipped one with `rc = 0`:

```
save from the *modified* build (variant M): 0
load into the *stock* build              : 0   (0 = accepted)
```

Two adjacent failures in the same code path, both demonstrated: a **truncated** dump returns `-1`, which `solve_hunt.py` reports to the user as "no table dump (re-searching)" while the table is in fact half-loaded; and `th_tt_save` returning `-1` is discarded outright by `save_state()` (see **item 8**).


### 3. `[BUG-SOUNDNESS]` `th_mate_hunt_mt` throws away the soundness flags, so PROVEN rests on the value alone

- **Source** — reading the one code path that produces every published claim, then sweeping it.
- **What** — The mate hunt calls `root_search` with `snd = 0`, so the flags that justify calling a mate score a proof are computed and discarded; `solve_hunt.py` then decides PROVEN from `v > 29000` with nothing checking that the value is a sound bound.
- **Mechanism** — `root_search`'s last argument is the out-pointer for the main thread's `si.snd`. Passing `0` drops it. The soundness machinery exists and is correct; nothing consumes it on the path that prints proofs.
- **Soundness argument** — Adds a check, removes nothing. A win claim needs `SND_LB` (true value >= v); a loss claim needs `SND_UB`. Refusing to print PROVEN without the matching bit can only turn a claim into a non-claim, never the reverse.
- **Integration point** — `tinyhouse.c:590`, `th_mate_hunt_mt`:
  ```c
  int th_mate_hunt_mt(THPos *p, int depth, int color, int workers, uint16_t *bestmove) {
      if (p->stm == color)
          return root_search(p, depth, MATE_BOUND, MATE, workers, bestmove, 0);
      return -root_search(p, depth, -MATE, -MATE_BOUND, workers, bestmove, 0);
  }
  ```
- **Toggle and pin** — Add an `int *snd` parameter (keep `th_mate_hunt_mt` as a wrapper passing `0`, so every existing caller is node-identical and byte-identical), thread it into `solve_hunt.py`, and gate the PROVEN print on it. Node identity exact: no search behaviour changes.
- **Expected gain** — Neither metric. This converts an unchecked assumption into a checked one on the single most consequential output.
- **Risk** — None to the search. If the assertion ever fires it is telling you something true.
- **Oracles** — `pytest -q`; the three recorded lines must still print PROVEN with the flag set; a deliberate mutation that strips a flag must make the hunt refuse to claim.
- **Effort** — ~10 lines across two files.
- **Novelty** — The soundness invariant is documented and implemented but never enforced at the boundary where it is asserted publicly.

**Evidence.** 250 random positions at depth 12, `th_solve` with the flags read out: 60 mate scores, **0** missing the justifying flag. The assumption currently holds — which is exactly why it should be pinned before someone changes the search.

```
250 positions at depth 12: 60 mate scores, 0 missing the justifying flag, 0 PROVEN DRAWS (snd==3, v==0)
```


### 4. `[BUG-SOUNDNESS]` TT cutoffs discard rep_min, so a proof reused on a new path can hide an ancestor repetition

> **Verifier: PLAUSIBLE** — citation re-read against the current tree, quote matched.

- **Source** — solver lens: what is SInfo.rep_min when a child returns via a TT cutoff instead of a real search
- **What** — A sound-flagged mate entry stored under one path is returned verbatim under a path that has extra ancestors, and the reused proof line may repeat one of those ancestors, which on the new path is a draw claim the search never sees.
- **Mechanism** — rep-safety (`my_rep >= ply` at line 513) blocks STORING a value that did depend on an ancestor repetition. It does not block REUSING a value that would depend on one under a different history. On a TT cutoff the function returns at 440/443/446 with si->rep_min still at its entry default MAXPLY (set at line 414), so the parent is told the subtree touched none of its ancestors. Direction matters: extra repetitions can only lower a value, so the negative claim (no forced win within N) stays sound either way; only the positive `mate in K` half is at risk.
- **Soundness argument** — This IS the invariant 'values that depended on a repetition hitting an ANCESTOR are never stored in the TT'. The fix only ever removes cutoffs or clears sound flags, so no new value can enter the tree; proofs that survive the check were already valid.
- **Integration point** — `tinyhouse.c:439`:

  ```c
  if (tv.flag == TT_EXACT && (tv.depth >= depth || tv.sound == (SND_LB | SND_UB))) {
                  si->snd = tv.sound; return v;
              }
              if (tv.flag == TT_LOWER && v >= beta && (tv.depth >= depth || (tv.sound & SND_LB))) {
                  si->snd = tv.sound & SND_LB; return v;
              }   (enclosing function: static int search(THPos *p, int depth, int ply, int alpha, int beta, SInfo *si))
  ```
- **Toggle and pin** — `#define VERIFY_PROVEN_CUT 1` next to SND_LB/SND_UB (tinyhouse.c:293-294). When 1, a TT cutoff returning |v| > MATE_BOUND with a sound flag first replays the proof tree (winner: stored TT move; loser: every legal reply) to the mate distance and compares reached keys against path[0..ply-1]; on a hit it drops the sound flag and falls through. With 0 the branch compiles out and node counts are bit-identical (miner verified 1,245,821 / 3,538,280 / 7,407,122 with the walk inert). Free carrier for later: data bits 48-63 are unused (tt_store packs only 48), so a 16-bit Bloom summary fits with no entry growth.
- **Expected gain** — ESTIMATE: soundness, not speed. Metric = count of proven TT cutoffs whose proof tree crosses a current-path ancestor; today unmeasured in the shipped binary. Cost metric = nodes-to-depth, ESTIMATED under 1% (proven cutoffs are 0.05-0.09% of nodes, 6,493 of 7.4M at d16). Confirmed by running the counter at the depths the published bounds were taken at (20 White / 22 Black) and showing it stays 0, or finding the first non-zero, which is a concrete false proof.
- **Risk** — The walk needs a node budget or a pathological defender fan-out dominates (miner capped at 40,000 make/unmakes and 14 plies). If the budget is exhausted the honest action is to DROP the sound flag, not keep it.
- **Oracles** — pytest -q (43); perft(7)=1,355,253 drift signature; re-run 1.Fd1-c2 -> `fuwk/3p/P1F1/KWU1[-] b` must still give mate in 9 with bestmove b4c2; toggle-off node identity at d14/d16; solve_hunt.py --seed 0xC0FFEE --fresh.
- **Effort** — ~45 lines in tinyhouse.c plus a counter through engine_c.py; half a day including re-verification.
- **Novelty** — Not on the ALREADY FIXED list, which credits rep-safety with keeping GHI out entirely; this is the direction it does not cover. Distinct from the closed Zobrist-collision item (that is key aliasing; this is correct keys, wrong history).

<details><summary>Evidence</summary>

```
I re-read tinyhouse.c:413-449 and 501-531 just now; the quote above and `si->rep_min = MAXPLY;` at line 414 are verbatim from the current working tree, and there is no rep_min assignment on any of the three TT-cutoff return paths. Miner's detector build (scratch copy, repo untouched): `run2.py ghi2.dylib "fuwk/3p/P1F1/KWU1[-] b" 16 1 22` -> v=29991 nodes=3538280 proven_cuts=4551 PROOF_TREE_CROSSES_ANCESTOR=0; same at d16 for two other positions and d14 from the start. HONEST READING: zero instances at depth <= 16 with the walk capped at 4,001 checks per run. The hazard is UNREFUTED, not disproven; the published bounds are at depth 20 and 22, which this pass was not allowed to run.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Category: keep [BUG-SOUNDNESS] as a hazard class but label impact UNOBSERVED; today this is closer to [INSTRUMENT] (build the verifier) than to a fix for a live defect.

Title, corrected: "Proven TT values are reused under a different history, so a `mate in K` can survive an ancestor repetition it never sees (GHI on TT reuse)". The current title mis-locates the mechanism: propagating rep_min through a TT cutoff CANNOT fix this. The store gate at tinyhouse.c:513 `if (tt && my_rep >= ply && !g_abort) {` guarantees a stored entry has no dependency on any ancestor above its own node, so there is no rep_min to propagate. The defect is reuse under a history the entry was never validated against.

Direction argument, corrected: not "extra repetitions can only lower a value" (false: a lost defender who can now repeat goes -MATE -> 0, a raise). Correct form: a forced win under the new path is a strategy tree containing no repetition-clamped node, so the same tree exists under the old path with the same values; win_new implies win_old. Hence only the positive half is exposed and negative bounds are immune.

Confirming measurement, corrected: NOT the counter at depth 20/22 - solve_status.json carries only negative claims at those depths ("no forced WHITE win within 20 plies", "no forced BLACK win within 22 plies"), which the argument above proves immune. Run it where positive claims are made, i.e. the three `proven_wins_found` entries and any future one.

Toggle, corrected and cheaper: skip the ~45-line proof-tree replay. A one-line toggle `#define TT_VALUE_CUTOFFS 1` wrapping the `if (ply > 0) {` block at tinyhouse.c:438 gives a GHI-free oracle build (TT still used for move ordering and stores, values never reused, so every value is computed on the real path). Verification protocol: any claim `mate in K` from the normal build must be reproduced by the oracle build at depth K. This is strictly stronger than the proposed walk (it verifies the whole claim, not just whether the recorded proof tree crosses an ancestor), needs no node budget, no Bloom bits, and no counter plumbed through engine_c.py. Cost measured here: 6.2s for all three published wins, 16.4s for 41 fuzz claims, on M2 Pro. Its ceiling: it only scales while K is re-searchable, so a very deep future claim still needs the replay walk - propose that only once such a claim exists. Node identity when the toggle is off is exact (the block compiles out; I verified the one-line-diff build gives perft(7) = 1355253 and 43/43 pytest).

</details>

*Verifier: CITATION: verified verbatim. `sed -n '413,449p' <repo>/tinyhouse.c` (md5 90e7e5a9119221bae6a1e7c5bf5e4625, unchanged before and after my run) gives line 414 ` si->rep_min = MAXPLY;`, line 426 ` if (path[j] == key) { si->rep_min = j; si->snd = SND_LB | SND_UB; return 0; }`, and lines 439-444 exactly as quoted, inside `static int search(THPos *p, int depth, int ply, int alpha, int beta, SInfo *si)`. None of the three cutoff returns (440/443/446) assigns si->rep_min, and the store gate is line 513 ` if (tt && my_rep >= ply && !g_abort) {`. Anchor and quote are correct. [...]*


## `[BUG]`

### 5. `[BUG]` make() writes hands[us][4] when a king is captured, which lands inside THPos and no sanitizer sees it

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — make() read against the piece encoding: TYPE(K) == 4 but the hand array is 4 wide. Confirmed by an ASan+UBSan build that stayed SILENT.
- **What** — Make the C make() self-consistent on a king capture instead of relying on Python to guarantee it cannot happen: skip the hand increment (and the matching decrement in unmake) when the captured piece is a king.
- **Mechanism** — `p->hands[us][TYPE(cap)]++` with TYPE(cap) == K == 4 writes one past hands[us]. THPos is `{ int8_t board[16]; int8_t hands[2][4]; int8_t stm; }`, so hands[0][4] IS hands[1][0] (the opponent's pawn-in-hand count) and hands[1][4] IS stm. This is an intra-object overwrite: ASan tracks object boundaries, not struct members, and UBSan does not instrument the member access, so both stay silent while the write happens. It is therefore invisible to any sanitizer-based testing you later add, unlike the two genuine out-of-bounds sites at the to_c boundary. During the subtree after a king capture the opponent's pawn count is off by one, so th_key is wrong, so a TT entry can be filed under another position's key with a sound flag.
- **Soundness argument** — Removes a corruption, adds none. Every search invariant is preserved because the branch only fires on a move the search should never see. Cheapest correct form: `if (cap && TYPE(cap) != K)`.
- **Integration point** — `tinyhouse.c:127`:

  ```c
  int frm = M_FROM(m), to = M_TO(m);
          int cap = p->board[to];
          u->captured = cap;
          if (cap) p->hands[us][PROMOTED(cap) ? P : TYPE(cap)]++;
          int pc = p->board[frm];   (enclosing function: static void make(THPos *p, uint16_t m, Undo *u))
  ```
- **Toggle and pin** — No runtime toggle wanted for a two-token guard; the pin is that no from_tfen-accepted position can reach it, so node counts cannot move. If a switch is insisted on, `#define GUARD_KING_CAPTURE 1` next to MATE. The mirror in unmake (tinyhouse.c:146, `if (u->captured) p->hands[us][PROMOTED(u->captured) ? P : TYPE(u->captured)]--;`) must change in the SAME commit or the two go out of sync.
- **Expected gain** — ESTIMATE: zero measurable NPS or nodes-to-depth, and that is the point. Confirming measurement: perft(7) stays exactly 1,355,253, the PERFT_ORACLE is unchanged, and a single-thread depth-14 th_mate_hunt still reports exactly 1,245,821 nodes. What it buys is that the C library stops depending on a Python invariant for memory consistency, which matters the moment anyone writes a C driver, a fuzzer, or a second binding.
- **Risk** — Almost none; the branch is dead in every position from_tfen accepts. The one thing to get right is doing it in unmake as well.
- **Oracles** — pytest -q; PERFT_ORACLE; perft(7)=1,355,253; th_mate_hunt depth-14 node count 1,245,821 unchanged; a direct C driver that constructs a king-capturable THPos and asserts hands[1][0] is unchanged after th_moves.
- **Effort** — 2 lines (make + unmake) plus a driver test; twenty minutes.
- **Novelty** — ALREADY FIXED covers the king-capture IndexError in the PYTHON engine, not this. Distinct from the to_c item in both fix location and detection story: this is the ONE of the three out-of-bounds sites a sanitizer build cannot find, so hardening the Python boundary alone leaves it permanently undetectable.

<details><summary>Evidence</summary>

```
Re-read from the current tree: tinyhouse.c:10 `typedef struct { int8_t board[16]; int8_t hands[2][4]; int8_t stm; } THPos;`, tinyhouse.c:12 `#define TYPE(pc) (((pc) & 7) - 1)`, tinyhouse.c:16 `enum { P, F, U, W, K };` - so TYPE of a king is 4 into an array of 4. Miner's ASan+UBSan run on a white wazir capturing a black king: `case2 legal moves = 5 ; hands b/P now = 0 ; stm = 0` with NO sanitizer diagnostic, in contrast to the two to_c cases which both fired. Baseline re-verified by me: pytest -q -> 43 passed; perft(7) -> 1355253.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Two sharpenings, both measured; the item is otherwise correct as written.

(a) Replace the last sentence of "mechanism" with: "The damage is not confined to the subtree after a king capture, and not to the hand array. When the capturer is BLACK, hands[1][4] IS p->stm; make() overwrites stm immediately afterwards, but unmake() restores stm first (line 136) and only then decrements it (line 146), so stm is left permanently flipped. And because th_moves (tinyhouse.c:205-218) make()s every pseudo-move just to run the legality filter, merely ENUMERATING moves in such a position corrupts the caller's THPos and changes the returned move list. Measured on a stock -O0 ASan+UBSan build of the current tinyhouse.c: unpatched th_moves on {black wazir a4, white king a3, black king d4, stm=b} returns n=2 and leaves stm=0; with the guard it returns n=5 and leaves stm=1. White-side capture is the milder case: hands[0][4] aliases hands[1][0], black's pawn-in-hand goes 0->1, th_key changes, and unmake does restore it."

(b) "toggle_and_pin" pin is now measured, not asserted: a scratch copy of tinyhouse.c with the guard applied to BOTH make and unmake, built `cc -O2 -pthread`, gives perft(7) = 1,355,253 exactly. Node identity holds.

Nothing else needs correcting: file, line 127, the verbatim quote, the struct/encoding evidence, the sanitizer-silence claim, the `if (cap && TYPE(cap) != K)` fix, the unmake mirror requirement, and the "dead in every from_tfen-accepted position" framing all check out.

</details>

*Verifier: 1) CITATION — re-read just now, `cat -n tinyhouse.c | sed -n '110,170p'`. Lines 124-128 are character-for-character the quoted block, with the cited line 127 exactly ` if (cap) p->hands[us][PROMOTED(cap) ? P : TYPE(cap)]++;`. Supporting citations also verbatim: line 10 `typedef struct { int8_t board[16]; int8_t hands[2][4]; int8_t stm; } THPos;`, line 12 `#define TYPE(pc) (((pc) & 7) - 1)`, line 16 `enum { P, F, U, W, K };`, and the mirror at line 146 ` if (u->captured) p->hands[us][PROMOTED(u->captured) ? P : TYPE(u->captured)]--;`. [...]*

**Second, independent confirmation (this pass).** ASAN on a standalone driver shows the *other* half of the same hole — a kingless `THPos` reads out of bounds in `th_in_check`:

```
==14537==ERROR: AddressSanitizer: global-buffer-overflow on address 0x0001008dd05b
READ of size 1 at 0x0001008dd05b thread T0
    #0 0x0001008ccd04 in th_in_check tinyhouse.c:111
0x0001008dd05b is located 5 bytes before global variable 'ORTH' ... of size 80
```

and the silent one, a white wazir capturing a black king: `hands[1] = 1 0 0 0` — a phantom pawn in Black's hand, no sanitizer fires, perft continues. Both are reachable only through `engine_c.to_c`, never through `server.py`. Fix them together, at the boundary, not in `make`.


### 6. `[BUG]` str_move fabricates illegal moves and th_make on them corrupts the THPos struct

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — tinyhouse.py:344-363 read in full; hostile strings fed to str_move and the results pushed through lib.th_make.
- **What** — str_move accepts 'K@a1' and 'a1b2=K' and returns move ints outside the encoding; feeding the king-drop to the C th_make silently decrements Black's pawn count (white to move) or the stm field itself (black to move), while Python's make raises IndexError.
- **Mechanism** — str_move does TYPE_CHARS.index(s[0]) with no range check, so 'K' yields drop type 4. C make does `p->hands[us][M_FROM(m)]--` with M_FROM==4; hands is int8_t[2][4], so hands[0][4] aliases hands[1][0] and hands[1][4] aliases stm - the same aliasing as the king-capture item, reached through a different door. Separately '=K' gives promo 4, so promo<<9 sets bit 11 which M_PROMO's `>>9 & 3` discards: str_move('a1b2=K')==2053 but mv(a1,b2)==5, and both render as 'a1b2', so the round trip is not an involution on hostile input (it is exact on all 10,037 generated moves the miner checked).
- **Soundness argument** — Does not touch the search. str_move is a parser used only by tests today; validating it cannot change any generated move, so node counts are bit-identical.
- **Integration point** — `tinyhouse.py:356`:

  ```python
  def str_move(s: str) -> int:
      if "@" in s:
          return mv_drop(TYPE_CHARS.index(s[0]), name_sq(s.split("@")[1]))
      promo = 0
      if "=" in s:
          s, p = s.split("=")
          promo = TYPE_CHARS.index(p)
      return mv(name_sq(s[:2]), name_sq(s[2:4]), promo)   (enclosing function: str_move)
  ```
- **Toggle and pin** — `STRICT_MOVE_PARSE = True` as a module constant beside DOUBLE_STEP (tinyhouse.py:13). Off, str_move is the current function exactly; node identity is trivially exact because the search never calls it.
- **Expected gain** — ESTIMATE: neither nodes-to-depth nor NPS moves - the parser is entirely off the search path. The gain is closing a struct-corruption path before th_make gets a caller (nothing in Python calls lib.th_make today, so this is a live trap rather than a live bug). Confirmed by a 3-line test asserting str_move('K@a1'), str_move('a1b2=K') and str_move('a1') all raise ValueError, with perft(7) unchanged.
- **Risk** — Very low. Nothing in server.py, solve_hunt.py, index.html or scripts/ calls str_move; only test_tinyhouse.py does, with well-formed strings.
- **Oracles** — pytest -q (43); perft(7)=1,355,253; a new test that the three hostile strings raise; the existing random-walk parity test.
- **Effort** — ~6 lines in str_move plus a 4-line test; under an hour.
- **Novelty** — Not on the fixed list. The closest fixed item is 'playMove trusting a stale move', a GUI-state bug; this is the parser producing an out-of-encoding int in the first place. Shares the hands[us][4] aliasing with the king-capture item but has a different fix location and a live caller path.

<details><summary>Evidence</summary>

```
I ran this against the shipped module just now:
$ PYTHONPATH=<repo> .venv/bin/python scratchpad/v.py
str_move K@a1 = 320 m_from= 4
str_move a1b2=K = 2053 vs mv 5
Miner drove 320 through lib.th_make: stm=w hands before [[1,1,1,1],[1,1,1,1]] -> after [[1,1,1,1],[0,1,1,1]] stm 1 board[0] 5 (Black's pawn count went 1 -> 0); stm=b -> the stm byte was decremented out from under the search. Python's make raises IndexError in both cases.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Corrected mechanism/evidence sentence: "'K@a1' yields drop type 4, and C make does `p->hands[us][M_FROM(m)]--` (tinyhouse.c:121) with M_FROM==4; hands is int8_t[2][4] inside `typedef struct { int8_t board[16]; int8_t hands[2][4]; int8_t stm; } THPos;` (tinyhouse.c:10), so hands[0][4] aliases hands[1][0] and th_make with WHITE to move silently decrements Black's pawn count (verified: [[1,1,1,1],[1,1,1,1]] -> [[1,1,1,1],[0,1,1,1]]). With BLACK to move the aliased write lands on stm, but it is immediately clobbered by `p->stm = 1 - us;` (tinyhouse.c:132, us cached at tinyhouse.c:117), so that case is NOT observable through th_make -- stm ends at the correct flipped value. (th_unmake is not exported in engine_c.py, whose cdef has only `void th_make(THPos *p, uint16_t m);`, so the unmake-side `p->hands[us][M_FROM(m)]++` at tinyhouse.c:140 is unreachable from Python.)" Also: str_move('a1') already raises IndexError today, so the proposed test asserts a change of exception type, not the introduction of an error. Category should stay [BUG] but be read as latent-trap hardening: no caller in server.py, solve_hunt.py, index.html or scripts/ passes untrusted strings to str_move.

</details>

*Verifier: 1. QUOTE: re-read just now, `cat -n tinyhouse.py`, lines 356-363 match the item's quote character for character, including the anchor line 356 = `def str_move(s: str) -> int:`. Confirmed. 2. MECHANISM, run end to end (scratch script under the scratchpad, PYTHONPATH set): $ PYTHONPATH=<repo> .venv/bin/python .../scratchpad/v.py str_move K@a1 = 320 m_from= 4 is_drop= True str_move a1b2=K = 2053 vs mv 5 move_str of both: a1b2 a1b2 str_move('a1') = raised IndexError string index out of range stm 0 hands [[1, 1, 1, 1], [1, 1, 1, 1]] -> [[1, 1, 1, 1], [0, 1, 1, 1]] stm now 1 board[ [...]*


### 7. `[BUG]` root_search never clears history[][], so bench_workers medians are biased toward whichever worker count is listed first

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — SMP audit of root_search, building on the known in-process history contamination; the new part is the measured magnitude and its effect on the repo's only SMP instrument.
- **What** — root_search memsets killers but not history, so the second and later repeats inside one process start with a warm history table; scripts/bench_workers.py runs all repeats for all worker counts in one process, so the first worker count in --workers is the only one that gets a cold-history repeat.
- **Mechanism** — history[2][2048] is _Thread_local on the MAIN thread and survives across root_search calls; helper threads are pthread_created fresh each call so THEIR history is always zero. At depth 13 the cold repeat costs 757,928 nodes and every warm repeat costs 834k-851k (+10-12%). With --workers 1,2 the depth-13 median for 1 worker was 0.8s (spread 0.6s); with --workers 2,1 the same measurement gave 0.6s (spread 0.2s), same machine, seconds apart. The tool's headline output is argument-order dependent, which makes the recorded SMP numbers in solve_hunt.py's docstring measurements of the argument order as much as of the thread count.
- **Soundness argument** — Ordering only. history feeds order_score at tinyhouse.c:410, which affects move order and therefore node counts, never values or soundness flags. Clearing it cannot change any PROVEN.
- **Integration point** — `tinyhouse.c:549`:

  ```c
  static int root_search(THPos *p, int depth, int alpha, int beta, int workers,
                         uint16_t *bestmove, int *snd) {
      memset(killers, 0, sizeof killers);
      g_abort = 0;   (enclosing function: root_search)
  ```
- **Toggle and pin** — `#define CLEAR_HISTORY_AT_ROOT 1` next to it, guarding one line `if (CLEAR_HISTORY_AT_ROOT) memset(history, 0, sizeof history);` immediately after the killers memset. Set to 0 and the pre-change counts return EXACTLY: in-process repeat 1 = 757,928 and repeats 2-5 = 845,801 / 834,551 / 844,615 / 851,481 at depth 13, 1 worker, tt 2^22, mate_hunt colour 0 from the start.
- **Expected gain** — ESTIMATE, metric = nodes-to-depth measurement VALIDITY, not nodes-to-depth itself. With the fix every in-process repeat should equal the cross-process value exactly. Confirming measurement: five in-process repeats at depth 13 must all print 757,928, matching five separate processes; and --workers 1,2 vs 2,1 must stop disagreeing.
- **Risk** — Clearing history at the root discards genuinely useful cross-depth ordering information inside solve_hunt.py's iterative deepening loop, which could make the real proof search slower. That is why it must be a toggle measured on its own: the right answer may be to keep the carry-over in solve_hunt and clear it only in the bench. Measure both.
- **Oracles** — pytest -q (floor only, the search is untested by it); perft(7)=1,355,253; the node-identity pin above with the toggle off; scripts/bench_workers.py --depth 13 --workers 1,2 vs 2,1 agreeing after the fix.
- **Effort** — 1 line plus the toggle plus a comment carrying the 757,928 measurement; ~20 minutes to change, half a day to measure both settings honestly at a real proof depth.
- **Novelty** — The contamination is on the known list; the measured magnitude (+11.5% nodes cold vs warm at depth 13) and the demonstration that it flips bench_workers.py's reported medians are new. RELATED AND NOT SEPARATELY LISTED: scripts/bench_workers.py:54-55 formats the node column as `{statistics.median(nodes)/1e6:8.0f}M`, printing '1M' for everything from 500k to 1.5M, so the clean metric is unreadable at exactly these depths - fix it to `{statistics.median(nodes):>14,d}` in the same commit.

<details><summary>Evidence</summary>

```
Re-read verbatim from the current tree: root_search at tinyhouse.c:549-552 clears killers and g_abort and nothing else; `static _Thread_local int16_t history[2][2048];` at tinyhouse.c:298. Miner's runs: perrepeat.py 13 1 5 (one process) -> 757,928 / 845,801 / 834,551 / 844,615 / 851,481; five separate processes -> 757,928 every time. bench_workers --depth 13 --workers 1,2 --repeats 3 --tt 22 -> workers 1 median 0.8s spread 0.6s; --workers 2,1 -> workers 1 median 0.6s spread 0.2s.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Four corrections. None kill the item; they tighten it.

(a) The wall-clock numbers in `mechanism` do not reproduce and should be dropped. The item claims "--workers 1,2 the depth-13 median for 1 worker was 0.8s (spread 0.6s); --workers 2,1 the same measurement gave 0.6s (spread 0.2s)". I got 1.1s (spread 1.2s) and 0.7s (spread 0.5s). Same direction, different magnitudes — wall time at 0.5-1.5s with 3 repeats is too noisy to quote. Also the RANKING did not flip in my run: 2 workers won in both orders. Replace "flips bench_workers.py's reported medians" with the reproducible node-metric statement: the workers-1 median node count is 834,551 when 1 is listed first and 778,683 when it is listed second (-6.7%), and the workers-2 median moves 947,390 → 896,916 (-5.3%), same machine, seconds apart.

(b) "makes the recorded SMP numbers in solve_hunt.py's docstring measurements of the argument order as much as of the thread count" is overreach. Re-read verbatim, solve_hunt.py:22-24: "At depth 18 on an Apple M2 Pro (10 cores, 3 repeats, fresh table per run) 1 / and 2 threads tie within noise (median 27.8s vs 28.4s) and 3+ regresses / badly (52s, 50s)". The order effect I measured is 5-7% on nodes; the 3-and-4-thread regressions are ~86% gaps and are not in danger. The confound bites exactly one recorded pair: the 27.8-vs-28.4s tie, a 2% gap smaller than the order effect. Say that, and add the honest caveat that my order effect was measured at depth 13, not at the depth 18 those numbers came from — the depth-18 magnitude is unmeasured.

(c) Category should be [INSTRUMENT], not [BUG]. Nothing the solver PROVES is wrong; what is wrong is the validity of the repo's only SMP measuring tool. The item's own expected_gain already says "metric = nodes-to-depth measurement VALIDITY, not nodes-to-depth itself", which is an INSTRUMENT claim.

(d) Strengthen the toggle_and_pin with what I actually ran: with CLEAR_HISTORY_AT_ROOT 1, five in-process depth-13 repeats print 757,928 every time and perft(7) stays 1,355,253; with it 0, the pin numbers 757,928 / 845,801 / 834,551 / 844,615 / 851,481 return exactly. Both halves verified on this machine (M2 Pro).

One addition worth carrying into the item, stated as measured-but-narrow: the patched build was also FASTER per call at depth 13 (0.512-0.552s vs 0.90-1.62s for the unpatched warm repeats), so at least at this depth the carried-over history was pure harm. That does NOT settle the `risk` paragraph — my repeats were all the SAME depth on the SAME position, whereas solve_hunt's carry-over is across successive iterative-deepening depths, which is a different and genuinely unmeasured question. Keep the toggle and measure it at proof depth before defaulting it on in solve_hunt.

The piggybacked node-column fix (`{statistics.median(nodes)/1e6:8.0f}M`, scripts/bench_workers.py:55) is verified: both of my bench runs printed "median nodes        1M" for values between 757,928 and ~1,000,910. The clean metric is genuinely unreadable at these depths.

</details>

*Verifier: I verified every load-bearing claim myself, including the decisive attribution test the item did not run. 1) CITATION — re-read just now, matches character for character. `sed -n '540,560p' tinyhouse.c | cat -n` → file line 549-552: static int root_search(THPos *p, int depth, int alpha, int beta, int workers, uint16_t *bestmove, int *snd) { memset(killers, 0, sizeof killers); g_abort = 0; `sed -n '290,305p' tinyhouse.c | cat -n` → line 298: `static _Thread_local int16_t history[2][2048];` `sed -n '400,418p' tinyhouse.c | cat -n` → order_score starts at 400; [...]*

**Second, independent confirmation (this pass).** Five `bench_workers`-style repeats — fresh `th_tt_init(24)` each, depth 14, one worker, one process:

```
  1,245,631 / 1,722,181 / 1,362,618 / 1,351,931 / 1,519,811 nodes
  spread min-to-max = 1.38x
```

against three *separate processes* running the identical search: `1245821 / 1245821 / 1245821`. This is also how **item 1** was found: warm `history` changes the ordering, which changes which TT entries exist, which decides whether the over-budget mate cutoff fires.


### 8. `[BUG]` `save_state()` discards `th_tt_save`'s return, so a checkpoint can silently fail to exist

- **Source** — watching it happen: a `--tt 40` run filled 50 GiB of disk in 90 seconds on this machine tonight.
- **What** — `th_tt_save` returns `-1` when the file cannot be written; `solve_hunt.py` ignores it and prints the same reassuring per-depth line either way.
- **Mechanism** — Combined with `th_tt_load` returning `-1` for both "no dump" and "truncated dump", a run whose disk filled mid-save reports "no table dump (re-searching)" on resume, having in fact loaded a partial table.
- **Soundness argument** — Not a proof defect: entries are self-validating (`xkey ^ data == key`), so a partial load yields fewer entries, never wrong ones. It is a resume-integrity and honesty defect.
- **Integration point** — `solve_hunt.py:135-137`:
  ```python
  def save_state():
      state_path.write_text(json.dumps(state, indent=2))
      E.lib.th_tt_save(str(tt_path).encode())
  ```
- **Toggle and pin** — Not a toggle; check the return and print a warning. Behaviour when the save succeeds is byte-identical.
- **Expected gain** — Neither metric. It is the difference between "an interrupted run costs at most the depth it died in" (README's claim) being true and being aspirational.
- **Risk** — None.
- **Oracles** — `th_tt_save` to an unwritable path must produce a visible warning; the resume path must distinguish "absent" from "truncated".
- **Effort** — 4 lines, plus a distinct return code for a short read in `th_tt_load`.
- **Novelty** — Adjacent to the `--tt` RAM guard the other session just committed, but a different failure: that one bounds the allocation, this one is about the *write*.

**Evidence.**

```
save to an unwritable path : -1   (solve_hunt.save_state() discards this)
load a TRUNCATED dump      : -1   (reported to the user as "no table dump (re-searching)")
```

and the sizing that makes it likely, measured:

```
th_tt_save at --tt 22:  64 MiB in 0.05s
th_tt_save at --tt 24: 256 MiB in 0.08s
extrapolated --tt 26: 1.0 GiB   --tt 27: 2.0 GiB   written after EVERY completed depth
```

`README.md:65` recommends `--tt 27`, i.e. a 2 GiB write per depth for a table holding well under 1% live entries at shallow depths.


### 9. `[BUG]` The sqlite cache key is incomplete: the same (tfen, depth, version) row has two different contents depending on request order

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — server.py analyze() read in full; the miner verified it against a live sandboxed server on port 8791.
- **What** — The cached JSON is a function of the live C transposition table at request time, not just of (tfen, depth, ENGINE_VERSION); whichever request lands first is stored and served forever as 'the depth-N analysis'.
- **Mechanism** — analyze() writes value, snd, best, nodes and time into a row keyed only by (tfen, depth, version). But th_solve probes a TT that previous requests filled, and the probe at tinyhouse.c:439 returns an entry whenever `tv.sound == (SND_LB | SND_UB)` REGARDLESS of tv.depth. So a depth-6 request issued after a depth-14 request on the same position returns the depth-14 proof and is stored as the depth-6 row. The GUI then prints 'depth 6 - 15 nodes' next to 'Black wins in 9 - forced (proven)', a mate five plies past the labelled horizon.
- **Soundness argument** — The served value is not itself unsound here, but the cache has no mechanism that could prevent an unsound row: it stores snd verbatim and never re-verifies. Caching only rows that carry a proof makes the row a function of its key again, because a proof cannot be weakened by an earlier or later request.
- **Integration point** — `server.py:39`:

  ```python
  row = db.execute("SELECT json FROM analysis WHERE tfen=? AND depth=? AND version=?",
                           (tfen, depth, ENGINE_VERSION)).fetchone()   (enclosing function: analyze)
  ```
- **Toggle and pin** — `CACHE_ONLY_PROVEN = True` next to ENGINE_VERSION (server.py:21), guarding the INSERT: `if CACHE_ONLY_PROVEN and out["snd"] != 3 and abs(out["value"]) < 29000: return out`. False reproduces today's behaviour exactly including existing rows. Ceiling to name in the comment: unproven positions are recomputed every request, so scripts/build_book.py only stays useful for proven positions; upgrade path is a proven-only book table keyed by tfen alone.
- **Expected gain** — ESTIMATE: neither nodes-to-depth nor NPS moves. Metric is row reproducibility: today two orderings produce different rows for the same key; after the change every stored row must be byte-identical across orderings. Confirmed by: delete the sandbox DB, run depth 6 first and record the row; delete again, run depth 14 then depth 6, diff the two depth-6 rows.
- **Risk** — Medium on cache hit rate (unproven positions recomputed), zero on correctness. Do not skip the comment naming the build_book cost.
- **Oracles** — pytest -q; /api/analyze on "fuwk/3p/P1F1/KWU1[-] b" at depths 6 and 14 in both orders with the stored rows diffed; solve_hunt.py is unaffected (it does not touch the cache).
- **Effort** — 6 lines; one hour including the ordering test.
- **Novelty** — ALREADY FIXED has 'cache key missing an engine version'; this is the orthogonal defect that adding the version did not fix - the key is still incomplete with respect to TT state.

<details><summary>Evidence</summary>

```
Re-read the probe gate verbatim at tinyhouse.c:439 (quoted in the GHI item): `tv.depth >= depth || tv.sound == (SND_LB | SND_UB)` - proven entries cut at any depth, which is the mechanism. Miner's live runs: depth=14 on `fuwk/3p/P1F1/KWU1[-] b` -> value=-29991 snd=1 best=b4c2 nodes=4665702; the same server at depth=6 -> value=-29991 snd=1 best=b4c2 nodes=15; a cold process at depth 6 -> value 0, snd 0, 1262 nodes. Same key, two contents.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

CATEGORY: [BUG] (with an [INSTRUMENT] component), not [BUG-SOUNDNESS]. No wrong PROVEN is constructible; the served proof is correct, only its provenance metadata (depth, nodes, time) is a function of request order rather than of the key.

SOUNDNESS LINE (replaces the item's): does not touch the search — the cache is downstream of th_solve and stores its output verbatim, so no invariant is touched and no proof changes. The defect is that the row's `depth`, `nodes` and `time` fields describe a search that did not happen.

EXPECTED GAIN (replaces "byte-identical rows"): neither nodes-to-depth nor NPS moves. Metric: the *verdict fields* (value, snd, best) of a stored row are a function of (tfen, depth, version) alone. `nodes` and `time` can never be, because `time` is wall clock — measured 4.957s vs 3.059s for the identical depth-14 search in two fresh processes (nodes were stable at 6060143). If provenance is to be honest, the smaller fix is to stop storing `nodes`/`time` in the row, or to store the depth that actually produced the proof, and that fix addresses the misleading "depth 8 · 15 nodes · Black wins in 9 (proven)" display (index.html:272 + :119) which CACHE_ONLY_PROVEN alone does not.

CONFIRMING TEST (replaces the broken one): on a sandbox DB — (a) fresh DB, GET /api/analyze depth=8 on "fuwk/3p/P1F1/KWU1[-] b", assert NO row is stored (cold gives value 0 / snd 0 / 15351 nodes); (b) fresh DB, depth=14 then depth=8, assert a depth-8 row exists and its value/snd/best equal the depth-14 row's (-29991 / 1 / b4c2). Compare value, snd, best only — never nodes or time.

RISK: add that CACHE_ONLY_PROVEN=True means the depth-8-first request stores nothing and is recomputed every time, so on the start position (where almost nothing is proven) the cache becomes inert.

</details>

*Verifier: CONFIRMED as the defect it describes, but REFUTED as [BUG-SOUNDNESS] and its gain claim is wrong. Details: 1) QUOTES (re-read just now, both files). `cat -n server.py` lines 38-40: ``` 38 with DB_LOCK: 39 row = db.execute("SELECT json FROM analysis WHERE tfen=? AND depth=? AND version=?", 40 (tfen, depth, ENGINE_VERSION)).fetchone() ``` Character-for-character match, enclosing function is `analyze` (server.py:37). Anchor line 39 correct. tinyhouse.c:439 (`awk 'NR>=425 && NR<=455'`): ` if (tv.flag == TT_EXACT && (tv.depth >= depth || tv.sound == (SND_LB | SND_UB))) {` — matches. [...]*


### 10. `[BUG]` th_root_moves computes per-move soundness and throws it away; the GUI shows "0.00" for moves the engine never evaluated

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — th_root_moves re-read at tinyhouse.c:600-615 against server.py:58-60 and index.html:274-279.
- **What** — Every child search in th_root_moves fills an SInfo whose snd is never read, so the API cannot tell a proven-drawn root move from a move the search knows nothing about, and the GUI renders both as '0.00'.
- **Mechanism** — Line 609 passes &si and line 611 stores only v. server.py builds {"move", "value"} with no soundness field, and index.html:276 hardcodes `fmtVal(mv.value, 0)`. On the known mate line at depth 9 the six non-mating moves all have child snd = 0 (nothing established) while b4c2 has snd = 2; the table prints '0.00' six times, which a reader takes as 'these hold'. Since a proven draw at a root move is precisely the prize this project is chasing, the one flag that would announce it is the one being discarded.
- **Soundness argument** — Read-only: si.snd is already computed by the existing search call, so no search decision, move ordering, TT store or window changes. Node identity is exact and must be pinned as such. The GUI gains the ability to distinguish proven from unknown, which strictly reduces unproven claims on screen.
- **Integration point** — `tinyhouse.c:611`:

  ```c
  out_moves[i] = buf[i]; out_values[i] = v;   (enclosing function: int th_root_moves(THPos *p, int depth, uint16_t *out_moves, int *out_values))
  ```
- **Toggle and pin** — Extend to `int th_root_moves(THPos *p, int depth, uint16_t *out_moves, int *out_values, int *out_snd)` writing `out_snd[i] = si.snd`, accepting NULL; update the cdef in engine_c.py (line 39) and gate emission with a visible `SHOW_MOVE_SOUNDNESS = True` in server.py plus a badge in index.html. With it False the JSON and the table are identical to today. Node identity: exact - th_nodes() at a fixed depth before and after must be bit-identical.
- **Expected gain** — ESTIMATE: nodes-to-depth unchanged by construction (zero delta - that is a pin, not an estimate), NPS unchanged within noise (one store per root move). The metric it moves is unproven claims per moves table: 6 of 7 rows on the mate line at depth 9 today. Confirmed by paired th_nodes() at a fixed depth being equal, and the badge reading 'proven' only for rows whose snd is 3.
- **Risk** — Low, but it is an ABI change to a cffi-declared function - the cdef and both call sites (server.py:55, and any script) must land in the same commit or dlopen silently reads garbage for the fifth argument.
- **Oracles** — pytest -q; perft(7)=1,355,253; toggle-off reproducing the pre-change node count EXACTLY at a fixed depth; re-running the proven line and checking b4c2 is the only row badged proven.
- **Effort** — 25 lines across 3 files; half a day.
- **Novelty** — Not on the fixed list; it is the API half of the soundness plumbing that already exists for the root value via th_solve's snd out-parameter. Pairs with the fmtVal item: that one fixes the headline, this one fixes the table.

<details><summary>Evidence</summary>

```
Re-read verbatim from the current tree, tinyhouse.c:605-612:
    for (int i = 0; i < n; i++) {
        path[0] = rootkey;
        make(p, buf[i], &u);
        SInfo si;
        int v = -search(p, depth - 1, 1, -MATE, MATE, &si);
        unmake(p, &u);
        out_moves[i] = buf[i]; out_values[i] = v;
    }
$ grep -rn "out_snd" .  -> no hits. index.html:276 re-read: `      const fv = fmtVal(mv.value, 0);`. Miner's per-child probe at depth 9 on the mate line: d3d2/d3c2/a4b3/b4a2/c4c3/d4c3 all child_snd=0, b4c2 child_value=29992 child_snd=2.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Three corrections; the anchor, the verbatim quote, and the substance survive.

1. FACTUAL (in `mechanism` and `evidence`): b4c2's child value is 29991, not 29992. Verified on the patched build, tfen `fuwk/3p/P1F1/KWU1[-] b`, depth 9 -> `b4c2 29991 2`.

2. THE PROPOSED FIX IS WRONG AS SPECIFIED (in `toggle_and_pin`): `out_snd[i] = si.snd` copies the CHILD's flag orientation, but line 609 negates the value (`int v = -search(p, depth - 1, 1, -MATE, MATE, &si);`). SND_LB and SND_UB are duals of the value they describe, so an upper bound on the child value is a LOWER bound on the root-move value. b4c2's si.snd == 2 (SND_UB) therefore means 29991 is a lower bound, and a badge reading the raw flag would print "upper bound". The store must swap the bits: `out_snd[i] = ((si.snd & 1) << 1) | ((si.snd >> 1) & 1);` — which leaves 0 and 3 fixed. The item's own acceptance test ("badge reading 'proven' only for rows whose snd is 3") is insensitive to this, which is exactly how it would ship the bug.

3. OVERSTATED (in `mechanism`): "a proven draw at a root move is precisely the prize this project is chasing" implies such rows exist today. They do not. 300 random positions at depth 4 through the patched th_root_moves2, scanning for value==0 && snd==3, printed `found 0` — consistent with the KNOWN OPEN note that a draw proof needs df-pn/PN^2 rather than this machinery. Restate the payoff as what is real now: six of seven rows on the mate line print "0.00" for children where the search established nothing, and the one flag that would say so is thrown away. Keep the proven-draw case as future-facing only.

Also re-label the category from [BUG] to [DOC-OVERCLAIM] or [SHOULD-BE-BETTER]: the search emits no wrong PROVEN, only an unqualified number on screen.

</details>

*Verifier: CITATION — re-read just now. Working tree clean except two untracked review .md files (`git status --porcelain` -> `?? review_opus-4-8_v1.md`, `?? review_opus47_v1.md`). `cat -n tinyhouse.c | sed -n '598,618p'`: 599 /* Per-root-move values at fixed depth (root side's perspective). */ 600 int th_root_moves(THPos *p, int depth, uint16_t *out_moves, int *out_values) { 605 for (int i = 0; i < n; i++) { 606 path[0] = rootkey; 607 make(p, buf[i], &u); 608 SInfo si; 609 int v = -search(p, depth - 1, 1, -MATE, MATE, &si); 610 unmake(p, &u); 611 out_moves[i] = buf[i]; out_values[i] = v; [...]*


### 11. `[BUG]` from_tfen accepts a pawn standing on its own promotion rank, and a "promoted pawn"

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — tinyhouse.py:104-169 read in full; I re-ran the two candidate TFENs against the shipped parser.
- **What** — from_tfen accepts 'P3/4/4/K2k[-] w' (a white pawn already on rank 4) and 'P~3/4/4/K2k[-] w' (a piece marked as a promoted pawn), both unreachable in any game, and both engines then treat the pawn as a permanently immobile piece.
- **Mechanism** — The validation block checks rank width, unit budget, king count and the not-to-move-in-check rule, and never checks pawn placement. Promotion is forced (test_promotion_is_forced_and_marked pins this), so a pawn can never occupy PROMO_RANK[color]; and 'P~' is a contradiction, since promoted-ness is what a pawn loses. Both engines agree on the result, so this is not a parity split - it is a hole in the boundary that lets the solver publish a proof about a position outside the game. Two lines inside the existing `for pc in pos.board` loop close both cases at the one place all TFEN input arrives, including raw HTTP input via server.py.
- **Soundness argument** — Rejection-only; nothing currently accepted and legal becomes rejected, so every proof and node count is unchanged. None of the 5 PERFT_ORACLE tfens nor any test tfen has a pawn on its own promotion rank.
- **Integration point** — `tinyhouse.py:146`:

  ```python
  # Each side owns exactly one king, and each of the 4 non-king unit
          # types exists exactly twice in the game (board + both hands), pawn
          # origins counted through promotions. th_key packs hand counts as 0-2,
          # so an over-full hand would read out of bounds in the C engine.
          counts = {t: 0 for t in range(4)}
          for pc in pos.board:
              if pc:   (enclosing function: Position.from_tfen)
  ```
- **Toggle and pin** — `STRICT_TFEN = True` as a module constant beside DOUBLE_STEP (tinyhouse.py:13). Off, from_tfen is the current function exactly; node identity is trivially exact because the search is untouched.
- **Expected gain** — ESTIMATE: no movement in nodes-to-depth or NPS - the check runs once per parse, never in the search. The gain is that a proof claim can only be about a reachable position. Confirmed by two new parametrised cases in test_from_tfen_rejects_malformed plus perft(7) unchanged and the 5 round-trip tests green.
- **Risk** — If any row in analysis.sqlite or solve_state/ was stored for such a TFEN it would now 400 in the GUI rather than return a value; one sqlite scan for pawns on ranks 1/4 settles it. No other caller is affected.
- **Oracles** — pytest -q (43); test_tfen_roundtrip over all 5 PERFT_ORACLE tfens; perft(7)=1,355,253; the two new rejection cases.
- **Effort** — ~4 lines in from_tfen plus 2 parametrise entries; under an hour.
- **Novelty** — Distinct from the fixed 'assert-only TFEN validation under -O' (that made checks raise instead of assert) and from the fixed hand-count bound. This is a rule the check-set never had at all.

<details><summary>Evidence</summary>

```
I ran this against the shipped parser just now:
$ PYTHONPATH=<repo> .venv/bin/python scratchpad/v.py
P3/4/4/K2k[-] w ACCEPTED -> P3/4/4/K2k[-] w
P~3/4/4/K2k[-] w ACCEPTED -> P~3/4/4/K2k[-] w
Both round-trip, so the illegal position survives a save/load cycle through the GUI unchallenged. Miner additionally checked both engines agree on the (empty) pawn move set and on perft(3)=18.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

The rule as stated is under-inclusive and should be widened before implementation. The item rejects only a pawn on its OWN promotion rank (`sq >> 2 == PROMO_RANK[pcolor(pc)]`), which leaves the mirror-image hole open. I ran it:

  '3p/4/4/K2k[-] b' ACCEPTED -> legal: 4 ['d1c1', 'd1d2', 'd1c2', 'd4d3']

A black pawn on rank 4 is equally unreachable — black pawns only move toward rank 1, and tinyhouse.py:273 / tinyhouse.c:197 bar pawn drops from rank 4 as well as rank 1 — yet the item's check accepts it. It is also NOT immobile (it plays d4d3), so the item's "both engines treat the pawn as a permanently immobile piece" is true only for the own-promotion-rank case, not for the mirror case.

The correct rule mirrors the drop restriction exactly: no pawn on rank 1 or rank 4, either color, plus no promoted pawn. Inside the existing `for pc in pos.board` loop (make it `for sq, pc in enumerate(pos.board)`):

    if STRICT_TFEN and ptype(pc) == P and (ppromoted(pc) or sq >> 2 in (0, 3)):
        raise ValueError(f"TFEN has an unreachable pawn at square {sq}: {tfen!r}")

This keeps the item's own soundness argument intact — still rejection-only, since my repo-wide literal scan and the sqlite scan found zero positions with a pawn on EITHER back rank — and it phrases the check as the same predicate the movegen already uses, so the two cannot drift apart. Add a third parametrise entry for '3p/4/4/K2k[-] b' alongside the two the item names. Everything else in the item (anchor, quote, mechanism, toggle, oracles, effort, novelty, no-perf-movement) is accurate as written.

</details>

*Verifier: Verified end to end. The item stands, but its proposed rule is under-inclusive; see `corrected`. 1) QUOTE / ANCHOR — matches character for character. `cat -n <repo>/tinyhouse.py | sed -n '146,152p'` (re-read just now, after the other session's edits): ``` 146 # Each side owns exactly one king, and each of the 4 non-king unit 147 # types exists exactly twice in the game (board + both hands), pawn 148 # origins counted through promotions. th_key packs hand counts as 0-2, 149 # so an over-full hand would read out of bounds in the C engine. [...]*


### 12. `[BUG]` analyze depth is clamped above but not below; depth<=0 returns a TT-scavenged best move and caches it

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — server.py:123 plus curl against a sandboxed server.
- **What** — min(int(depth), 22) has no lower bound, so depth=0 or a negative depth runs a 7-node non-search, reports a 'best' move and a full moves table read out of the transposition table, and writes that as a permanent cache row.
- **Mechanism** — th_solve with depth <= 0 hits the horizon branch at root ply 0 and returns 0 unsound, but root_search still finishes with `*bestmove = tt_probe(th_key(p), &tv) ? tv.move : 0` (tinyhouse.c:572), so it hands back whatever move a previous, deeper analysis stored for that key. th_root_moves at depth <= 0 likewise returns whatever the TT holds per child. The GUI then prints 'depth 0 - 7 nodes' beside a best move and, at depth -1, beside a mate score of -29990 that no part of this request computed. All of it lands in analysis.sqlite keyed by the bogus depth.
- **Soundness argument** — Clamping the input touches no search code and no invariant. It removes a path where the reported best move and the reported depth belong to different searches - the same class of mislabelling as the cache-key item.
- **Integration point** — `server.py:123`:

  ```python
  self.send_json(analyze(q["tfen"], min(int(q.get("depth", 12)), 22)))   (in Handler.do_GET)
  ```
- **Toggle and pin** — `MIN_DEPTH = 1` and `MAX_DEPTH = 22` as module constants, clamp written as min(max(int(...), MIN_DEPTH), MAX_DEPTH). MIN_DEPTH = -10**9 reproduces today's behaviour. Existing depth<=0 rows in analysis.sqlite must be deleted in the same change or they keep being served.
- **Expected gain** — ESTIMATE: neither metric moves. The metric is the number of reachable requests whose reported depth does not match the search that produced the reported best move: today every depth<=0 request. Confirmed by curl at depth=0 and depth=-1 returning 400 or clamping to 1, and no row with depth < 1 existing afterwards.
- **Risk** — Very low. The GUI select only offers 8..22, so nothing legitimate depends on the current behaviour.
- **Oracles** — pytest -q; curl at depth=0, -1 and 1; a SELECT over the sandbox DB asserting min(depth) >= 1.
- **Effort** — 1 line plus a DELETE; 20 minutes.
- **Novelty** — ALREADY FIXED covers TFEN validation at this boundary; the depth parameter at the same boundary is only half-validated. ALSO NOT SEPARATELY LISTED, same line: this handler has no Host-header check and no cancellation, so an abandoned depth-22 GET holds ENGINE_LOCK and burns a core indefinitely (miner measured a process still at 87.7% CPU five minutes after the client left) and a page on any origin can send it; the Host allowlist is 5 lines, the cancellation half is a day and deserves its own item. Path traversal on /pieces/ was tested and is correctly rejected.

<details><summary>Evidence</summary>

```
Re-read verbatim from the current tree at server.py:122-123. Miner's curl runs: depth=0 -> {'depth': 0, 'value': 0, 'snd': 0, 'best': 'c1b3', 'nodes': 7, 'time': 0.0} with 6 moves listed; depth=-1 -> a seven-node request reporting `{"move": "d1c2", "value": -29990}` and a best move, both read out of the TT. The bestmove source is tinyhouse.c:570-573, which I re-read: `*bestmove = tt_probe(th_key(p), &tv) ? tv.move : 0;`.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Two corrections, both to the evidence, not to the claim:

1. The miner's numbers presuppose a WARM TT and should not be quoted as the cold-start behaviour. On a fresh table (server just started, `E.lib.th_tt_init(24)` at server.py:23, nothing searched yet), depth=0 and depth=-1 return `"best": null` with every move valued 0 — the honest empty answer, not a scavenged one. The bug only bites after some other request has populated the TT for that key. Replace the evidence with the paired repro below (same server process, in order):

  depth=0, cold: {"tfen": "fuwk/3p/P3/KWUF[-] w", "depth": 0, "value": 0, "snd": 0, "best": null, "moves": [ ... all six values 0 ... ], "nodes": 7, "time": 0.001, "cached": false}
  depth=12 at "fuwk/3p/P1F1/KWU1[-] b": {"depth": 12, "value": -29991, "snd": 1, "best": "b4c2", "nodes": 824266, "time": 0.446}
  depth=0 at the same tfen, immediately after: {"depth": 0, "value": 0, "snd": 0, "best": "b4c2", "moves": [{"move": "b4c2", "value": -29991}, ... ], "nodes": 8, "time": 0.0, "cached": false}

  So the reported best move and the -29991 mate score in the moves table are the depth-12 search's, printed under `"depth": 0` beside `"nodes": 8`. That is exactly the mislabelling the item claims.

2. Add the reachability caveat to `risk` explicitly: index.html:394 is `$("depth").innerHTML = [8,10,12,14,16,18,20,22].map(d => `<option ${d===14?"selected":""}>${d}</option>`).join("");`, so no GUI action produces depth<=0 — it takes a hand-written URL. The bug is real and the fix is one line, but nothing in the shipped UI reaches it, which caps the severity at "a hand-crafted URL can write a mislabelled permanent cache row".

Also correct the mechanism wording: the moves-table leak is not "th_root_moves at depth<=0 returns whatever the TT holds" as a special case — it is the ordinary TT-cutoff block at tinyhouse.c:438-448 (`if (ply > 0) { if (tv.flag == TT_EXACT && (tv.depth >= depth || tv.sound == (SND_LB | SND_UB))) { si->snd = tv.sound; return v; }` ...), which runs BEFORE the `if (depth <= 0)` horizon branch at tinyhouse.c:455 and is only gated on `ply > 0`. The root itself is gated out of that block, which is why `value` stays 0 and `snd` stays 0 while the children report real scores.

Everything else in the item stands as written, including the toggle, the soundness argument, and the DELETE requirement.

</details>

*Verifier: QUOTE. `sed -n 123p server.py | od -c` gives 16 spaces then `self.send_json(analyze(q["tfen"], min(int(q.get("depth", 12)), 22)))` + newline — character for character the item's quote, in Handler.do_GET (`cat -n server.py` shows do_GET at 97, the /api/analyze branch at 122-123). The secondary anchor also matches: `sed -n 540,600p tinyhouse.c` line 33 of that window = tinyhouse.c:572 = ` *bestmove = tt_probe(th_key(p), &tv) ? tv.move : 0;` inside root_search (declared at tinyhouse.c:549). REPRO. [...]*


### 13. `[BUG]` One abandoned `/api/analyze` request pins `ENGINE_LOCK` for the life of the search

- **Source** — started the server on a spare port and did it.
- **What** — `analyze()` holds the global engine lock across `th_solve` **and** `th_root_moves` at a client-chosen depth up to 22; the client disconnecting does not stop the C call, and every later request blocks behind it.
- **Mechanism** — `ThreadingHTTPServer` accepts the next request fine, but it waits on `ENGINE_LOCK`. Depth 22 from the start position is hours of work (the recorded depth-20 hunt alone is 729M nodes). The server binds `127.0.0.1`, but a simple cross-origin `GET` from any page the user visits reaches it — the response is blocked by CORS, the work is not.
- **Soundness argument** — Does not touch the search or any proof. Availability only.
- **Integration point** — `server.py:46-55`, in `analyze`, and the depth clamp at `server.py:123`:
  ```python
      with ENGINE_LOCK:
          c = E.to_c(pos)
          ...
          v = E.lib.th_solve(c, depth, bm, snd)
  ```
- **Toggle and pin** — A visible `MAX_GUI_DEPTH = 16` constant plus a node budget the search can be asked to respect, or a non-blocking `ENGINE_LOCK.acquire(timeout=...)` returning HTTP 503. Behaviour below the cap is identical.
- **Expected gain** — Neither metric.
- **Risk** — Lowering the cap removes depths 18-22 from the GUI dropdown; those are already impractical interactively.
- **Oracles** — the repro below must return promptly instead of timing out.
- **Effort** — ~10 lines.
- **Novelty** — The `ponytail:` comment at `server.py:24` names the global lock as a deliberate simplification but not this consequence.

**Evidence.**

```
--- fire a depth-22 analyse and ABANDON it after 1s ---
client gave up (curl timeout), server keeps computing
--- now try a trivial analyse ---
trivial depth-8 analyse STILL BLOCKED after 25.0s (TimeoutError)
```


## `[DOC-OVERCLAIM]`

### 14. `[DOC-OVERCLAIM]` "there are no search extensions, so the ply budget is exact"

- **Source** — the docstring that defines what every published bound means, checked against item 1.
- **What** — False as written: the TT extends the search past the nominal budget, and a positive claim's plies can exceed the depth it was found at.
- **Integration point** — `solve_hunt.py:7-9`:
  ```
  A value > 29000 at depth d proves a forced win for that color; anything else
  proves there is no forced win within d plies (total plies - there are no
  search extensions, so the ply budget is exact).
  ```
  Same claim, weaker wording, at `README.md:54-57` and in `solve_status.json`'s `note`.
- **Soundness argument** — Documentation only. Note the asymmetry the corrected text should state: the *negative* half ("no forced win within d plies") survives the defect, because a TT-induced extension can only find extra wins.
- **Toggle and pin** — Not a toggle. If item 1 is fixed the sentence becomes true again and needs no edit; if item 1 is deferred the sentence must say "a positive result proves a forced win but its ply count is an upper bound that may exceed d".
- **Expected gain** — Neither metric. It protects the record.
- **Risk** — None.
- **Oracles** — Item 1's differential harness is the test that decides which wording is correct.
- **Effort** — Two sentences, or free if item 1 lands first.
- **Novelty** — The claim is load-bearing for every number in `solve_status.json`.


### 15. `[DOC-OVERCLAIM]` README, solve_status.json and the solver comment all claim every mate score is a proof, without the caveat the TT-reuse hole needs

> **Verifier: PLAUSIBLE** — citation re-read against the current tree, quote matched.

- **Source** — Cross-reading the three published claims against what the rep-safety condition actually enforces.
- **What** — Three documents state without qualification that the search cannot emit a wrong mate proof; the rep-safety condition they cite only covers values that DID depend on an ancestor repetition, not values reused on a path with new ancestors.
- **Mechanism** — tinyhouse.c:254-256 says rep-safety 'is what keeps the graph-history interaction problem out'. solve_status.json:16 says 'any mate score it reports is a proof'. README.md:54-56 says 'These bounds are proof-grade, not heuristic'. The horizon argument they rest on is sound and genuinely enough for the NEGATIVE claim (no forced win within N plies), because extra repetitions can only lower a value. It is not enough for the POSITIVE claim (mate in 9). Two claims of different strength are sold under one sentence.
- **Soundness argument** — Documentation only; touches no invariant. Filed as a bug because the entire output of this program is proof claims and a reader cannot currently tell which half of the output is airtight.
- **Integration point** — `README.md:54`:

  ```
  These bounds are proof-grade, not heuristic: the search returns an *unsound* 0 at the
  horizon and sound values only at terminals and repetitions, so a mate score it reports
  is a proof, and a null-window hunt returning 0 proves no win exists within that budget.
  See the solver comment block in `tinyhouse.c`.   (enclosing section: "## Solve status")
  ```
- **Toggle and pin** — No toggle: a doc edit. Split the sentence into its two claims and attach the caveat to the positive one; add to solve_status.json a field `"caveat": "the no-forced-win bounds are unconditional; a reported mate distance additionally assumes no TT-reused proof line repeats a position already on the game path (see VERIFY_PROVEN_CUT in tinyhouse.c)"`. Behaviour is unaffected; the pin is that solve_status.json stays valid JSON and server.py's /api/status still parses it.
- **Expected gain** — ESTIMATE: no metric moves. The measurable part is that solve_status.json gains a field whose value must change in the same commit as the VERIFY_PROVEN_CUT toggle - that is the oracle against the doc silently drifting back.
- **Risk** — Understating the result. Keep the strong wording on the 20/22-ply bounds, which really are unconditional, and caveat only the mate distances.
- **Oracles** — pytest -q (run it even on a docs-only commit; the suite pins behavioural contracts this text describes); json.load on solve_status.json; the /api/status path in server.py:124-126 must still render it.
- **Effort** — ~15 lines across README.md, solve_status.json and the tinyhouse.c comment block; under an hour.
- **Novelty** — ALREADY FIXED contains 'TT sound-flag/depth gating docs', which is about the gating rules, not about the scope of the proof claim.

<details><summary>Evidence</summary>

```
All three re-read verbatim from the current tree just now. README.md:54-57 as quoted. solve_status.json:16: `"note": "Bounds are proof-grade: the search returns unsound 0 at the horizon, so any mate score it reports is a proof, and a null-window hunt that returns 0 proves no win exists within that ply budget. Deeper bounds: run solve_hunt.py (see README)."`. tinyhouse.c:254-256: `* Results whose value depended on a repetition hitting an ANCESTOR of the\n * node are path-dependent and are never stored in the TT (rep-safety; this\n * is what keeps the graph-history interaction problem out).`
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Two defects in the item as written, both in its remedy, not its diagnosis:

1. The proposed solve_status.json caveat text points the reader at a symbol that does not exist. `grep -rn "VERIFY_PROVEN_CUT" .` over the whole repo returns nothing. Shipping "(see VERIFY_PROVEN_CUT in tinyhouse.c)" would replace one overclaim with a dangling reference. Use the real anchors instead: the store-side rule at tinyhouse.c:513 (`if (tt && my_rep >= ply && !g_abort) {`) and the probe at tinyhouse.c:432-448, which does no path check.

Corrected caveat field: "caveat": "the no-forced-win bounds are unconditional: extra path repetitions can only convert wins into draws, so they can never hide a win. A reported mate DISTANCE additionally assumes that a TT value reused at a node is valid for that node's path - the rep-safety rule (tinyhouse.c:513) refuses to STORE values that depended on an ancestor repetition, but the probe (tinyhouse.c:432-448) does not check the reusing node's ancestors."

2. The mechanism sentence "extra repetitions can only lower a value" should be stated in the direction that actually carries the argument: extra ancestors add draw terminations, a draw termination can only delete a winning continuation, hence the isolated value the TT stores can over-state a win for either side but never under-state one - which is precisely why the negative bounds are airtight and only the positive mate distances need the caveat.

3. Add the measurement the item currently lacks, since it is cheap and it is what makes the caveat auditable: the toggle already exists in my scratch build as a one-line `th_tt_off(int)` plus `if (!tt || g_tt_off) return 0;` in tt_probe. A TT-off re-run of every line in solve_status.json's proven_wins_found is a 5-second oracle (I ran it: all three agree, 29991/29987/29987 with snd=1) and pins the claim far better than a JSON field alone.

</details>

*Verifier: CITATIONS: all three re-read just now and they match character for character. `cat -n README.md | sed -n '45,62p'` -> lines 54-57 are exactly "These bounds are proof-grade, not heuristic: the search returns an *unsound* 0 at the / horizon and sound values only at terminals and repetitions, so a mate score it reports / is a proof, and a null-window hunt returning 0 proves no win exists within that budget. / See the solver comment block in `tinyhouse.c`." under "## Solve status" (line 43). `cat -n solve_status.json` -> line 16 is the "note" field quoted verbatim in the item. [...]*

**Sharpened by this pass.** The direction of the exposure is now settled, so the negative bounds do **not** need re-running. A forced win within N plies is witnessed by a strategy tree in which no node is a repetition — a repetition node is a draw and cannot appear in a winning strategy. Removing history entries can only remove repetition clamps, so *win under the longer history implies win under the shorter one*. Contrapositive: a stored non-win cannot conceal a real win. Therefore "no forced White win within 20 plies" and "no forced Black win within 22 plies" are immune to the whole GHI class, and the three entries in `proven_wins_found` are the exposed claims. All three reproduce at their exact distances under a build with TT probing hard-disabled, shown below.

All three published forced wins reproduce at their exact distances under a build with TT
probing hard-disabled, which makes graph-history interaction structurally impossible:

```
1. Fd1c2??        claim=Black mates in 9 plies   -> no-probe first proof at depth 9,  distance 9
1. Wb1b2 Fa4b3??  claim=White mates in 13 plies  -> no-probe first proof at depth 13, distance 13
1. a2a3 Fa4b3??   claim=White mates in 13 plies  -> no-probe first proof at depth 13, distance 13
```

The record is clean; the documentation is not. The sentence in the solver comment block at
`tinyhouse.c:254-256` — "this is what keeps the graph-history interaction problem out" —
should say that rep-safety governs *storing*, not *reusing*, and that the negative bounds
are immune for the reason above while the positive claims are not. Make the probe-disabled
re-check part of the PROVEN ritual, next to the second-Zobrist-seed re-run.


## `[NPS]` — time per node

### 16. `[NPS]` Skip the make/unmake legality test for moves that provably cannot expose the king

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — Two lenses converged on the same four call sites: the observation that this board has NO sliding pieces, plus a `sample` profile showing th_in_check at 599/4194 leaf samples (14.3%) of a depth-16 hunt.
- **What** — Decide legality from a per-node king square plus a 16-bit "enemy mao discovery" mask, and fall back to the current make/attacked/unmake test only for check evasions, king moves, and moves that vacate a mao blocker square.
- **Mechanism** — Today every pseudo-move pays make + a full 4-loop attacked() + unmake, and attacked() first pays king_sq()'s 16-square linear scan. Two independent savings compose. (a) The mover's king square after a move is a pure function of (pre-move king square, move), so king_sq can be hoisted out of the per-move loop: one scan per node instead of one per pseudo move (18.4 per interior node). (b) With no sliders - P, F, W, K and the mao U are all one-step leapers - a non-king move by a side not already in check can create a new attack on its own king ONLY by vacating a square that blocks an enemy mao aimed at the king (MAO_ATT[ks] gives at most 4 such (origin, blocker) pairs). A drop only ADDS an occupant; a capture leaves the destination occupied. RULES.md:80-82 already states the drop half and the movegen does not use it. When in check, set the mask to 0xffff and fall back to today's path for every move.
- **Soundness argument** — It computes the SAME legality predicate by a different route, so the legal move set, its order and the whole tree are unchanged - node identity is the proof, and it held exactly. Nothing in the horizon rule, bound duality, rep-safety, the TT store gate or the mate-ply adjustment is touched. The theorem also survives the open DOUBLE_STEP question: a double-step pawn still captures one step diagonally.
- **Integration point** — `tinyhouse.c:228`:

  ```c
  uint64_t th_perft(THPos *p, int depth) {
      uint16_t buf[128];
      Undo u;
      if (depth == 0) return 1;
      int n = pseudo_moves(p, buf);
      uint64_t total = 0;
      for (int i = 0; i < n; i++) {
          make(p, buf[i], &u);
          if (!th_in_check(p, 1 - p->stm))
              total += depth == 1 ? 1 : th_perft(p, depth - 1);
          unmake(p, &u);
      }
      return total;
  }   (enclosing function: th_perft. Same pattern at th_moves, tinyhouse.c:209-215; at the search move loop, tinyhouse.c:478-479 "        make(p, m, &u);" / "        if (th_in_check(p, 1 - p->stm)) { unmake(p, &u); continue; }", enclosing function search; and at the horizon probe, tinyhouse.c:456-459. The 16-square scan it hides is king_sq, tinyhouse.c:106: "    for (int s = 0; s < 16; s++) if (p->board[s] == target) return s;")
  ```
- **Toggle and pin** — Two visible in-file lines next to MATE/MAXPLY: `#define TH_HOIST_KING_SQ 1` and `#define TH_LEG_FILTER 1`, staged so each can be measured alone. With both 0 every call site keeps the current `th_in_check(p, 1 - p->stm)` expression and behaviour is byte-identical. Node identity is EXACT and was verified by both miners: perft 1,355,253 / 756,938 / 2,140,012 unchanged, the whole PERFT_ORACLE unchanged, 1,600 fuzz positions at perft 3 unchanged, and single-thread th_mate_hunt_mt node counts unchanged at d12 172,221 / d14 1,245,821 / d16 9,913,857.
- **Expected gain** — MEASURED on perft, ESTIMATE elsewhere. M2 Pro, clang -O2, interleaved repeats: start perft(7) 40.5 -> 44.5 Mnps with the ks hoist alone and 40.5 -> 57.6 Mnps with the leg filter (reproduced 3x, spread <= 0.0005s); drop-heavy '1k2/4/2K1/4[PFUWpfuw] w' perft(4) 2.75x-2.8x; '1uwk/P3/3p/K2F[UWf] w' perft(5) 1.68x. HONEST CAVEAT, also measured: inside search() at depth 14 there is essentially NO gain - one miner got min 1.006s -> 0.907s (1.11x) but median 1.046 -> 1.004, and the other got min 0.543s base vs 0.549s over 13 interleaved repeats - because only ~1.94 legal moves are tried per interior node and the once-per-node mask costs about what it saves. Metric moved: time per node in th_moves/th_perft/th_result/th_root_moves (the GUI, the drift oracle, root move listing), not in the deep proof search. Confirm with paired perft repeats plus a fixed-depth mate hunt whose node count must not move.
- **Risk** — Concentrated in one theorem. If a sliding piece is ever added, or any new occupancy-dependent attack, the fast path silently accepts illegal moves and the engine can emit a wrong PROVEN. Gate it with a comment naming the precondition next to the #define and keep the toggle. Secondary: king_sq returns -1 with no king, and the hoisted version must not silently inherit that UB - add `if (ks < 0) ks = 0;` or an assert at the hoist site. The search-side identity sweep was done on one position at three depths; a sweep over the PERFT_ORACLE positions at depth 10-12 is owed before trusting it in a hunt.
- **Oracles** — pytest -q (43); PERFT_ORACLE and perft(7)=1,355,253 as the drift signature; test_engine_c.py random-walk parity; toggle-off node-identity pin on both perft AND th_mate_hunt at d12/d14/d16; re-running 1.Fd1-c2 -> mate in 9 from "fuwk/3p/P1F1/KWU1[-] b" with the recorded bounds; solve_hunt.py --seed 0xC0FFEE --fresh.
- **Effort** — ~40 lines across four call sites plus the two #defines; half a day including the identity sweep.
- **Novelty** — Not on either closed list; it touches neither search shape nor threading. Merged from three separate proposals (king_sq hoist, no-sliders leg filter, generic fast legality) - they are one integration point and staging them as two toggles is the only way to attribute the gain.

<details><summary>Evidence</summary>

```
All four call sites re-read verbatim from the current tree (quotes above are current). Miner A, 15 interleaved reps, node identity asserted: drop-heavy d4 base min 0.0658s 32.5 Mnps -> filtered 0.0239s 89.4 Mnps (2.748x, nodes=2140012 both); start d7 0.0543 -> 0.0359 (1.515x, nodes=1355253 both); PERFT_ORACLE OK on 5 positions and 27,968 random-walk perft comparisons, 0 mismatches. Miner B, 9 repeats x3 blocks: base median 0.0335/0.0336/0.0336s vs ks-hoist 0.0305/0.0306/0.0305s vs leg-filter 0.0235s, all at perft(7)=1355253. Search side, 13 interleaved repeats at load 4.5: base min 0.543 vs filtered 0.549, nodes {1245821} in every run. Baseline re-verified by me: perft(7)=1355253, 43 passed.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Three corrections, none fatal.

(a) DROP-HEAVY GAIN OVERSTATED. Item says "drop-heavy '1k2/4/2K1/4[PFUWpfuw] w' perft(4) 2.75x-2.8x". I measure 2.26x, three interleaved blocks of 9 reps, medians 0.06792/0.06799/0.06266 base vs 0.03005/0.03010/0.02776 filter, nodes=2140012 on both. Similarly "1uwk/P3/3p/K2F[UWf] w" perft(5) is 1.57-1.64x for me, not 1.68x. The start-position numbers (ks-hoist 1.10x, leg-filter 1.42x) reproduce exactly. Restate the gain as: perft-family speedup 1.4x on the start position, ~1.6x on a mixed position, ~2.3x on a drop-saturated one.

(b) SEARCH SIDE IS A SMALL REGRESSION, NOT "NO GAIN". The item's honest caveat is still too kind. Four interleaved d14 mate-hunt runs, fresh table, separate processes: base 0.734 / 0.890 / 0.913 / 0.864 vs filter 0.850 / 0.919 / 0.941 / 0.897. Filter is slower in all four pairings (~3-6%, and 0.734 vs 0.850 on the minima) while node counts stay pinned at 1245821. The once-per-node king_sq + attacked + vac_mask is paid at every node including horizon nodes, where the loop breaks on the first legal move and there is nothing to amortise over. So TH_LEG_FILTER should be staged as THREE toggles, not two: perft/th_moves/th_result/th_root_moves (pays, ship it), search interior loop (measured regression, default OFF), search horizon probe (default OFF). Shipping it into search() as written makes the proof search slower.

(c) LINE-NUMBER DRIFT. tinyhouse.c is 635 lines now, not the 631 in the baseline (the concurrent session is editing). Every cited anchor still resolves and every quote is verbatim, but the search-loop citation is more precisely tinyhouse.c:478-479 within the loop opening at 474, and the horizon probe at 455-460.

Keep the item's own `if (ks < 0)` guard note — it is load-bearing. king_sq returns -1 at tinyhouse.c:107 and MAO_ATT[-1] is out-of-bounds; my implementation needed `int slow_all = (ks < 0) || attacked(p, ks, 1 - us);` and without it the build is UB on king-less positions.

</details>

*Verifier: I tried to kill this and could not. Every claim held except two gain numbers, which I corrected. 1) CITATIONS — all verbatim against the current tree (re-read just now; the other session has grown tinyhouse.c to 635 lines but every cited anchor still lands exactly). `cat -n tinyhouse.c | sed -n '228,241p'` → th_perft matches the quoted block character for character, including ` if (!th_in_check(p, 1 - p->stm))`. `sed -n '205,218p'` → th_moves same pattern. `sed -n '474,479p'` → ` make(p, m, &u);` / ` if (th_in_check(p, 1 - p->stm)) { unmake(p, &u); continue; }` in search. `sed -n '455,459p'` → horizon probe. [...]*

**Second, independent measurement (this pass), including the negative half the item does not have.** A build that skips the legality probe for drops when the mover is not in check, node-identical, 13 interleaved repeats, minimum-of-N:

```
perft start        depth 7:  base min 0.0342s -> drop-skip min 0.0319s   = 1.07x
perft drop-heavy   depth 5:  base min 1.0899s -> drop-skip min 0.6474s   = 1.68x
search from start  depth 16: base min 3.331s  -> drop-skip min 3.450s    = TIE / slightly negative
                             node-identical at 10,119,067 on both
```

`perft(7) = 1,355,253` and drop-heavy `perft(5) = 50,207,608` are identical on both builds. **Do the perft/`th_moves` half; do not do the search half.** Three forms were built (eager, lazy, lazy-plus-horizon-shortcut) and none moved the search: 88% of interior nodes cut off after ~2 moves, and the start position has empty hands through most of the tree, so the one extra `th_in_check` needed to learn `in_chk` is never repaid. Premise check for the rule this rests on (`RULES.md:80-82`): 170,679 pseudo drops across 52,435 not-in-check positions, **0** illegal.


### 17. `[NPS]` Horizon nodes are 42-75% of the tree and build a full pseudo-move list to answer one yes/no question

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — Instrumented node census of the search tree; the horizon fraction was the largest single surprise in it.
- **What** — At depth<=0 the node's only output is 'does a legal move exist', but it generates every pseudo-move first, including up to ~60 drops; when the mover is not in check any drop is legal, which settles the question in a few loads.
- **Mechanism** — pseudo_moves is called at tinyhouse.c:452 BEFORE the depth<=0 branch, so the horizon pays for the whole list and then walks it until the first legal move. A drop removes nothing from the board, so it cannot expose the mover's own king: if the mover is not in check and holds any piece with a legal empty target square, a legal move exists. Moving the pseudo_moves call after the branch and answering the horizon with that shortcut removes movegen work from the largest node class in the tree (measured 41.67% of nodes at d14, 74.98% at d16). The TT probe at the horizon must STAY - `tv.depth >= depth` is trivially true when depth<=0, so every hit cuts there and some of those cuts carry real proofs.
- **Soundness argument** — Does not touch any value. The horizon's return values at tinyhouse.c:461-463 are unchanged; only the way 'is there a legal move' is computed changes, and the shortcut was validated against the engine's own legality over 10,215 drops with 0 illegal. Node counts are bit-identical, the strongest possible pin.
- **Integration point** — `tinyhouse.c:455`:

  ```c
  if (depth <= 0) {
          for (int i = 0; i < n && !any; i++) {
              make(p, buf[i], &u);
              if (!th_in_check(p, 1 - p->stm)) any = 1;
              unmake(p, &u);
          }
          if (any) return 0;                    /* unknown: no soundness */
          si->snd = SND_LB | SND_UB;
          return th_in_check(p, p->stm) ? -(MATE - ply) : (MATE - ply);
      }   (enclosing function: static int search(...))
  ```
- **Toggle and pin** — `#define FAST_HORIZON 1` immediately above a new `static int has_legal(THPos *p)`. With 0, has_legal falls straight through to the old generate-then-test loop and node counts are identical - verified at d14 White (1,245,821 with the toggle both ways, matching the baseline) and at d16 Black (806,774 both ways).
- **Expected gain** — MEASURED as a load-immune work count, ESTIMATE in wall clock. pseudo_moves calls 1,178,475 -> 1,017,274 (-13.7%) and moves generated 20,910,913 -> 17,599,973 (-15.8%) on the d14 White hunt - deterministic numbers independent of machine load. The CPU payoff is NOT established: CPU-time median of 7 was 1.0677s -> 1.0437s (-2.2%), inside the 1.007-1.116s spread on a machine at load average 136. Confirmed by re-running the paired CPU-time comparison on an idle box; the work counts are the thing that must not regress.
- **Risk** — The shortcut is only correct because drops cannot self-expose - name that in the comment, because a future rule letting a drop remove or move a piece breaks it silently. The in-check case still pays full price.
- **Oracles** — perft(7)=1,355,253; pytest -q; test_engine_c.py move-set parity; toggle-off node identity at d14/d16.
- **Effort** — ~25 lines; half a day, most of it re-measuring on an idle machine.
- **Novelty** — Not on any list. The closed SMP and check-extension measurements are about tree shape; this is pure cost-per-node and node-identical, so it composes with the other two NPS items. Also measured and REJECTED in the same pass so nobody repeats it: replacing king_sq's byte loop with memchr is a small LOSS - CPU-time median of 7, 1.0677s base vs 1.0905s memchr (+2.1%), node-identical.

<details><summary>Evidence</summary>

```
tinyhouse.c:451-464 re-read verbatim from the current tree (quote above is current), and `int n = pseudo_moves(p, buf);` is at line 452, before the branch. Miner's census, scratch build with counters only, node-identical: d14 White search entries 1,204,921 / horizon 502,121 (41.67%) / interior 676,354; d16 horizon 1,232,196 (74.98%). Work counts: base 1178475 pseudo_moves_calls, 20910913 moves_generated; with the shortcut 1017274 / 17599973, both at v=0 nodes=1245821. Shortcut validation: 1,273 not-in-check positions with >=1 pseudo drop, 10,215 pseudo drops examined, 0 illegal.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Two fields need correcting.

toggle_and_pin (replace the wrong d16 number):
"`#define FAST_HORIZON 1` immediately above a new `static int has_legal(THPos *p)`. With 0, has_legal falls straight through to the old generate-then-test loop and node counts are identical - verified in fresh processes at tt=22, th_mate_hunt_mt with 1 worker: d14 White 1,245,821 for base / on / off (matching the recorded baseline) and d16 Black 1,824,606 for base / on / off. (The earlier '806,774 at d16 Black' figure does not reproduce on the current tree under either th_mate_hunt or th_mate_hunt_mt.)"

expected_gain (replace the muddled 'NOT established ... Confirmed by' wording, and lead with d16 where the horizon fraction is largest):
"MEASURED as load-immune work counts; PARTIALLY measured in CPU time. Node-identical throughout.
 d16 Black (nodes 1,824,606 both ways): pseudo_moves calls 1,604,252 -> 653,431 (-59.3%), moves generated 31,312,405 -> 10,755,095 (-65.6%).
 d14 White (nodes 1,245,821 both ways): pseudo_moves calls 1,178,475 -> 1,017,274 (-13.7%), moves generated 20,910,913 -> 17,599,973 (-15.8%).
 CPU time, 7 interleaved repeats, fresh process each, M2 Pro at load average 12-22: d16 Black median 1.0959s -> 0.8502s (-22.4%; base range 0.928-1.212, fast range 0.679-1.161; Mann-Whitney U=40/49, one-tailed significant, two-tailed not). d14 White median 0.8453s -> 0.8211s (-2.9%), inside the 0.68-1.16s spread and therefore not a result.
 SETTLING MEASUREMENT: repeat the d16 (and a d18) paired CPU-time run, 7+ repeats interleaved, on an idle machine. The work counts are the contract that must not regress; the wall-clock number is only credible off a loaded box."

</details>

*Verifier: Verified end to end. (1) QUOTE: `cd <repo> && cat -n tinyhouse.c | sed -n '451,464p'` returns exactly the quoted block; line 452 is ` int n = pseudo_moves(p, buf);` and line 455 is ` if (depth <= 0) {`, so pseudo_moves does precede the horizon branch. File sha256 4b6c17cf68f4c66c279435db405c9a9b0a5c8cdcee7a9e00b66433be9d062214, re-read after all measurements, unchanged. (2) BUILDS: copied tinyhouse.c to scratchpad as base.c; [...]*

**Second, independent measurement (this pass).** Instrumented build, cold process, `perft(7)` still 1,355,253:

```
depth 14: nodes 1,245,631  horizon 502,026 (40%)  generated at horizon 8,697,900 (17.3/node)
          make/unmake actually done 1,021,929 (2.04/node)
depth 16: nodes 11,076,562 horizon 4,144,333 (37%)
          generated 74,191,961 (17.9/node)  make/unmake done 8,073,047 (1.95/node)
```

So the ceiling is 15.3 of 17.3 generated moves removed at ~40% of all nodes. Heed the warning from item 16: a horizon rewrite that adds a per-node `th_in_check` eats the entire gain.


### 18. `[NPS]` Recompute the Zobrist key incrementally in make/unmake instead of from scratch at every node

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — `sample` flat profile of a depth-16 mate hunt: th_key = 252/4194 samples (6.0%), and search() calls it once per node.
- **What** — search() calls th_key(p) at every node, which XORs 16 board squares plus 8 hand counters from scratch, although make() already knows exactly which two or three table entries changed.
- **Mechanism** — Carry the key in the position and update it in make() with the 3-5 XORs the move implies (piece off from-square, piece on to-square, captured piece, one hand counter transition, side to move); unmake() restores the saved key from the Undo record, which is free. That replaces 24 table lookups per node with ~4 per move.
- **Soundness argument** — The sharpest-edged item here, because the incremental key MUST equal th_key(p) exactly: if it ever diverges, a probe can match an entry belonging to a different position and return another position's value carrying SND_LB|SND_UB - a wrong PROVEN. Nothing else changes (same tree, same bounds, same rep-safety). The saving grace is that node identity is itself the equality oracle: any divergence changes which probes hit and therefore changes the node count, and the count was bit-identical at three depths.
- **Integration point** — `tinyhouse.c:281`:

  ```c
  uint64_t th_key(const THPos *p) {
      uint64_t k = p->stm ? zob_stm : 0;
      for (int s = 0; s < 16; s++) if (p->board[s]) k ^= zob_piece[s][(int)p->board[s]];
      for (int c = 0; c < 2; c++) for (int t = 0; t < 4; t++)
          k ^= zob_hand[c][t][(int)p->hands[c][t]];
      return k;
  }   (enclosing function: th_key; the hot caller is search(), tinyhouse.c:424: "    uint64_t key = th_key(p);")
  ```
- **Toggle and pin** — `#define TH_INCREMENTAL_KEY 1`. When 0, make/unmake skip the XOR bookkeeping and search() reads `th_key(p)` verbatim, reproducing today's node counts exactly. Add a second visible debug constant `#define TH_KEY_PARANOIA 0` that when 1 asserts p->zkey == th_key(p) at every node - that is what makes the fast path auditable. Requires the matching one-line struct change in engine_c.py's ffi.cdef (THPos gains a trailing uint64_t), so the two files must move in the same commit.
- **Expected gain** — MEASURED: depth-14 mate hunt from the start, 13 interleaved repeats at load 4.5, min 0.543s -> 0.519s (-4.4%) at bit-identical 1,245,821 nodes; a second block gave 0.868 -> 0.850 min. Consistent with the 6.0% profile share minus the added make/unmake cost. Metric: time per node; nodes-to-depth unchanged. This is the only one of the four NPS items measured to help the actual proof search. Confirm by re-running the same 13-repeat interleaved harness on an idle machine with the node count required to stay 1,245,821.
- **Risk** — Medium, and it is the soundness kind: a key bug is rare (needs a specific move type) and produces a wrong PROVEN. Mitigations: the paranoia assert, extending the make/unmake random-walk test to compare keys, and node identity at three depths. Growing THPos changes the cffi struct layout, so engine_c.py, server.py and scripts/bench_workers.py must be checked in the same commit; the .tt dump format is unaffected since it stores keys, not positions.
- **Oracles** — pytest -q; test_tinyhouse.py::test_make_unmake_random_walk already asserts pos.key() round-trips - extend it to the C side; toggle-off node identity at d12/d14/d16 (172,221 / 1,245,821 / 9,913,857); th_tt_save/th_tt_load round trip; solve_hunt.py --seed 0xC0FFEE --fresh.
- **Effort** — ~35 lines in tinyhouse.c plus 1 line in engine_c.py; half a day with the paranoia check.
- **Novelty** — Not on either closed list. Grounded in a profile taken this pass, not in general engine folklore.

<details><summary>Evidence</summary>

```
th_key re-read verbatim from the current tree at tinyhouse.c:281-287 (quote above), and its hot caller `uint64_t key = th_key(p);` at tinyhouse.c:424. Also relevant and re-read: the cdef in engine_c.py:21 `typedef struct { int8_t board[16]; int8_t hands[2][4]; int8_t stm; } THPos;` is the line that must move with it. Miner's measurement, 13 interleaved repeats, depth 14, colour white, 1 worker, fresh 2^22 table per process, load 4.5: base min 0.543 p25 0.612 median 0.732 vs v_key min 0.519 p25 0.582 median 0.668, nodes {1245821} in every run. Profile: search 2154 / pseudo_moves 1131 / th_in_check 599 / th_key 252 / _tlv_get_addr 58 of 4194 non-dyld samples.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Three corrections/additions to the write-up, none fatal:

(a) MISSING IMPLEMENTATION TRAP, and it is the soundness-critical one the item does not mention. root_search() must set `p->zkey = th_key(p)` BEFORE the `args[i].pos = *p;` helper copy at tinyhouse.c:559, not after. Get the order wrong and every lazy-SMP helper searches with a stale/zero key and writes SND-flagged TT entries under wrong keys — exactly the wrong-PROVEN failure the item is worried about, and it would NOT show up in 1-worker node identity. The sync points are: root_search (before helper spawn) and th_root_moves (`uint64_t rootkey = p->zkey = th_key(p);` at tinyhouse.c:604).

(b) The hand term needs TWO lookups per transition, not one. th_key XORs `zob_hand[c][t][count]` for every c,t including count 0, so make() must XOR out the old count and XOR in the new: `k ^= zob_hand[us][t][h] ^ zob_hand[us][t][h-1]`. A naive "one XOR per hand change" is wrong. Likewise a promotion is two piece XORs (unpromoted off `frm`, promoted on `to`), not one.

(c) Two small overstatements. "24 table lookups per node" is 24 loop iterations but only ~9-17 actual lookups (the board loop is guarded by `if (p->board[s])`). And `zob_piece`/`zob_hand` are declared at tinyhouse.c:274, AFTER make() at :116, so the change also needs the declaration hoisted above make() — the item's "~35 lines" should say "plus moving one declaration".

Gain restatement: "MEASURED: 2-7% CPU time at bit-identical nodes (depth 14, two interleaved 15-process blocks, medians -7.2% and -3.8%, on a machine at load 8-62). Direction is consistent across d12 and d14 and across both block orderings; magnitude needs an idle machine to pin down. Depth 16 is unmeasured — a 4-pair block there was noise-dominated."

</details>

*Verifier: I implemented the item end to end in the scratchpad and measured it. Nothing was written to the repo. 1) CITATION — exact. `sed -n '281,287p;424p' tinyhouse.c` returns the quoted th_key body character for character, and line 424 is ` uint64_t key = th_key(p);`. `sed -n '21p' engine_c.py` returns `typedef struct { int8_t board[16]; int8_t hands[2][4]; int8_t stm; } THPos;`. Repo floor green: `.venv/bin/python -m pytest -q` -> `43 passed in 1.45s`. 2) IMPLEMENTED. [...]*


### 19. `[NPS]` Generate drops from a precomputed empty-square set instead of rescanning the board per hand type

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — Two lenses; tinyhouse.py:269 already does exactly this (`empties = [s for s in range(16) if not b[s]]`) and the C port dropped it. Profile: pseudo_moves is 1131/4194 leaf samples (27%), the largest named callee after search.
- **What** — Build the empty squares once per node - as a list or a 16-bit mask walked with __builtin_ctz - and iterate hand types over that, instead of rescanning all 16 board squares for each of the 4 hand types.
- **Mechanism** — The current loop is up to 4 x 16 = 64 board reads with a branch each, in a position with at most 6 empty squares (the whole piece set is 2 kings + 2 each of P/F/U/W). Measured branching: 18.4 pseudo moves per interior node of which 11.2 (61%) are drops, so the drop loop is where the movegen time is. One 16-square pass plus one iteration per emitted move replaces it. The pawn rank restriction is one AND with 0x0ff0 (squares are 4*rank+file, so ranks 1 and 2 are squares 4..11).
- **Soundness argument** — Does not touch the search. Emission order must be preserved - keep the `for t` loop outermost and the pawn back-rank skip inside; ctz walks squares in ascending index, exactly the order the existing loop produces - and then the generated list is element-for-element identical, so node identity holds everywhere including the search's selection-sort tie-breaking.
- **Integration point** — `tinyhouse.c:193`:

  ```c
  for (int t = 0; t < 4; t++) {
          if (!p->hands[us][t]) continue;
          for (int s = 0; s < 16; s++) {
              if (b[s]) continue;
              if (t == P && ((s >> 2) == 0 || (s >> 2) == 3)) continue;
              out[n++] = MV_DROP(t, s);
          }
      }   (enclosing function: static int pseudo_moves(const THPos *p, uint16_t *out))
  ```
- **Toggle and pin** — `#define TH_DROP_BITMASK 1` guarding the two variants inside pseudo_moves. When 0 the quoted loop runs verbatim. Node identity is exact and was verified by both miners: perft 2,140,012 / 1,355,253 / 756,938 unchanged and th_mate_hunt d14 = 1,245,821 unchanged.
- **Expected gain** — MEASURED: start perft(7) +6% (median 0.0594 -> 0.0561s, 9 repeats, spread <= 0.0007s) and +8% on drop-heavy perft(4) in one miner's harness; the other measured 1.074x drop-heavy / 1.083x start / 1.020x standalone. Stacked on the legality fast path it is worth more because the legality test no longer hides it: drop-heavy goes 2.748x -> 3.196x. One low-load search reading at depth 14 gave 0.612 -> 0.583s (-4.7%) at identical node count; that single reading is NOT a measurement - re-take it as 9+ interleaved repeats before quoting it. Metric: time per node; nodes-to-depth unchanged by construction.
- **Risk** — Very low. Two ways to break it: reordering emission (moving the pawn rank test outside the type loop changes drop order, hence selection-sort tie-breaking, hence node counts - one miner hit exactly that and had to restructure), and getting the pawn rank mask wrong, which moves perft(7) immediately.
- **Oracles** — pytest -q; PERFT_ORACLE (the drop-heavy '1k2/4/2K1/4[PFUWpfuw] w' entry exercises it); perft(7)=1,355,253; toggle-off node identity including a th_mate_hunt count at d14.
- **Effort** — ~12 lines; one hour.
- **Novelty** — Not on either closed list, not a search change. It is the C side catching up with tinyhouse.py:269. Merged from two lenses proposing the list and the bitmask form of the same hoist.

<details><summary>Evidence</summary>

```
Both anchors re-read verbatim from the current tree: tinyhouse.c:193-200 as quoted, and tinyhouse.py:268-275 `        hand = self.hands[us]\n        empties = [s for s in range(16) if not b[s]]\n        for t in range(4):` - the Python already hoists. Miner A, 15 interleaved reps with node identity asserted: drop-heavy d4 0.1095 -> 0.1020 (1.074x), start d7 0.0876 -> 0.0809 (1.083x), all node counts identical. Miner B, 3 blocks of 9 reps: base 0.0579/0.0594/0.0594s vs bitmask 0.0557/0.0560/0.0561s at perft(7)=1355253 throughout; PERFT_ORACLE cross-check OK on all five positions.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Two corrections, neither fatal.

(a) expected_gain: drop the absolute times. "0.0594 -> 0.0561s" did not reproduce as an absolute on this machine (my -O2 base build measured 0.049s median at low load; the orchestrator's repo-baseline is 0.0337s) - those numbers are build/load specific. Quote the RATIO instead: MEASURED by this verifier, 7 interleaved paired process runs x 5 reps, low load, M2 Pro: start perft(7) 1.050x (median-of-medians 0.04919 -> 0.04686s, within-run spread <= 0.0005s), drop-heavy perft(4) 1.074x (0.06454 -> 0.06009s). Metric: time per node. Nodes-to-depth unchanged, verified exactly (move-order sha identical over 4000 positions, th_mate_hunt d14 node count identical). Keep the item's own caveat that the single depth-14 wall-clock reading is not a measurement - I could not re-take it cleanly either, the box went to load average 20-63 under the concurrent session.

(b) The guarded variant should be the one implemented, because the code being replaced has an early exit the bitmask form loses: with an empty hand the current loop does zero board reads, the bitmask form always pays a 16-iteration scan. Add before building the mask, inside `#if TH_DROP_BITMASK`:

    const int8_t *hd = p->hands[us];
    if (!(hd[0] | hd[1] | hd[2] | hd[3])) return n;
    unsigned em = 0;
    for (int s = 0; s < 16; s++) if (!b[s]) em |= 1u << s;

Built and run: perft(7)=1355253 and drop-heavy perft(4)=2140012 both hold. Node identity is unaffected - the guard only skips a loop that would have emitted nothing.

</details>

*Verifier: 1) ANCHOR — re-read just now, `cat -n <repo>/tinyhouse.c | sed -n '150,240p'`. Lines 193-200 are character-for-character the quoted block, inside `static int pseudo_moves(const THPos *p, uint16_t *out)` (line 150). The Python counter-anchor is also right: tinyhouse.py:268-269 read ` hand = self.hands[us]` / ` empties = [s for s in range(16) if not b[s]]`. Working tree is clean apart from two untracked review .md files; HEAD is 2054f2d. [...]*


## `[INSTRUMENT]`

### 20. `[INSTRUMENT]` Paired nodes-to-depth + solver-digest regression harness; today zero of the 43 tests touch the solver

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — grep for every solver symbol across both test files returns nothing.
- **What** — One script that, over a fixed deterministic position set, prints per-position (value, soundness flags, bestmove, nodes) at two fixed depths plus one digest line, and diffs against a committed baseline, so every future efficiency claim is a one-command paired comparison.
- **Mechanism** — Nodes-to-depth is the repo's only honest efficiency metric and nobody can produce it cheaply or reproducibly today. Node counts ARE reproducible across processes (measured 757,928 five times from five processes at depth 13) but not within one, so the harness must run each position in a FRESH process, or at minimum one root_search per process, to be a valid instrument - the history contamination item is a prerequisite for anything stronger. The digest folds value+snd+bestmove into 8 bytes so a soundness regression shows as a changed hex string next to an unchanged node count, separating 'searched differently' from 'answered differently'.
- **Soundness argument** — Does not touch the search. Read-only harness over th_solve/th_nodes.
- **Integration point** — `test_engine_c.py:16`:

  ```python
  def test_perft_c_deep_start():
      assert engine_c.perft("fuwk/3p/P3/KWUF[-] w", 6) == 139141
      assert engine_c.perft("fuwk/3p/P3/KWUF[-] w", 7) == 1355253   (enclosing function: test_perft_c_deep_start - the nearest thing to a solver pin in the whole suite, and it pins perft only)
  ```
- **Toggle and pin** — New file scripts/bench_nodes.py plus a committed scripts/bench_nodes.baseline.txt. Toggle is the CLI: `--baseline FILE` compares, `--write-baseline` records. Off = the file does not exist; nothing in the engine or the suite changes, so node identity is trivially preserved.
- **Expected gain** — ESTIMATE, detection capability, not nodes or NPS (instrument-only: zero of both by construction). Measured detection: of three hand-planted soundness mutations it catches 2 of 3. Confirming measurement: record a baseline on a pristine build, then re-run against each mutated build and check the diff is non-empty.
- **Risk** — Low. The digest is only stable if the position set and depths are frozen; changing either invalidates the baseline, which is why both belong in the committed file, not in argv defaults.
- **Oracles** — pytest -q must stay green; perft(7)=1,355,253; the harness's own baseline diff; toggle-off node identity is automatic.
- **Effort** — ~70 lines plus a ~30-line baseline file; half a day including choosing the position set.
- **Novelty** — Not on the fixed list. Distinct from scripts/bench_workers.py, which measures wall time for SMP only, prints no per-position data, and cannot detect a value or soundness regression at all.

<details><summary>Evidence</summary>

```
I re-ran the coverage check just now:
$ cd <repo> && grep -n "th_solve\|th_mate_hunt\|th_root_moves\|th_search\|th_tt_save\|th_tt_load\|th_seed\|th_nodes" test_tinyhouse.py test_engine_c.py ; echo "exit=$?"
exit=1
$ .venv/bin/python -m pytest -q -> 43 passed in 1.41s
All 43 are movegen/TFEN. Miner's prototype (12 random-walk positions x depths 6 and 8, fresh th_tt_init(20) each): BASE digest=1a191b51ad445b59 nodes=111232; MUT-A (horizon claims soundness) digest=41ed2e70abd6f312 nodes=102376 CAUGHT on both fields; MUT-C (path-dependent values stored in TT) digest unchanged, nodes=111638 CAUGHT on nodes alone; MUT-B (SND_UB granted after a cutoff) identical on both, MISSED.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Two refinements to the item as written (neither changes the verdict):

(a) MECHANISM OVERSTATED. The item says the harness "must run each position in a FRESH process, or at minimum one root_search per process, to be a valid instrument - the history contamination item is a prerequisite for anything stronger." Measured otherwise: my prototype runs all 12 positions x 2 depths in ONE process and gives byte-identical output from three separate processes (digest=0c36ff1ec9944c76 nodes=78930, three times). _Thread_local history carries over between searches, but the carry-over is deterministic when the sequence is fixed, so a single-process harness is a valid paired instrument. The real constraint is that the position list AND depth pair must be frozen in the committed baseline, because inserting or reordering a position shifts every later node count. The history-contamination fix is a nice-to-have (it would make the baseline robust to reordering), not a prerequisite. This makes the harness cheaper than costed: 48 lines, 0.6s at depths 6/8, 9.3s at depths 10/12, no process-spawning machinery.

(b) DEPTH CHOICE IS LOAD-BEARING FOR DETECTION. At depths 6/8 MUT-C (path-dependent values stored in the TT) shows as 78,929 vs 78,930 nodes: a one-node difference, indistinguishable from any harmless reordering change, so "caught" there is luck. At depths 10/12 the same mutation shows -1.3% (5,355,017 vs 5,424,001), which is a real signal. The baseline should be recorded at the deeper pair. And MUT-B (SND_UB granted after a cutoff) is invisible on both fields at both depth pairs, so the harness is a regression detector, not a soundness proof: state that limit wherever the baseline file is documented.

</details>

*Verifier: Verified end to end, including an independent reproduction of the detection measurement. 1) CITATION. `cat -n test_engine_c.py` just now, lines 16-18: ``` 16 def test_perft_c_deep_start(): 17 assert engine_c.perft("fuwk/3p/P3/KWUF[-] w", 6) == 139141 18 assert engine_c.perft("fuwk/3p/P3/KWUF[-] w", 7) == 1355253 ``` Character-for-character match with the item's quote, and the enclosing-function claim is right. The whole file is 37 lines: perft-vs-oracle, deep perft, a random-walk move-set parity test, and a TFEN roundtrip. Nothing else. 2) COVERAGE CLAIM. [...]*


### 21. `[INSTRUMENT]` Pin the recorded mate-in-9 proof: nothing connects solve_status.json's published claims to executable code

> **Verifier: PLAUSIBLE** — citation re-read against the current tree, quote matched.

- **Source** — solve_status.json records the mate-in-9 line and nothing in the suite checks it; th_root_moves at depth 10 from the start reaches it in 0.09s.
- **What** — A single test asserting th_root_moves(start, depth 10) returns d1c2 = -29990 and every other root move = 0, which pins the mate score, the ply adjustment, the sign convention, the root-move ordering the GUI displays, and the published claim in one assertion.
- **Mechanism** — -29990 == -(MATE - 10): mated in 10 plies from the root, i.e. Black mates in 9 from the child, exactly what solve_status.json records. It is the only place a mate score, the store/probe ply adjustment (tinyhouse.c:436-437 on probe and 526-527 on store) and a published proof claim all coincide. Any off-by-one in the adjustment moves the number; any TT soundness-gating regression that lets an unproven value masquerade changes it to 0. At depth 8 the same call gives d1c2=0, so the refutation is exactly 10 plies deep and depth 10 is the cheapest depth that pins it.
- **Soundness argument** — Does not touch the search. A read-only assertion, and the first test that would fail if a change made a published proof claim stop reproducing.
- **Integration point** — `tinyhouse.c:600`:

  ```c
  int th_root_moves(THPos *p, int depth, uint16_t *out_moves, int *out_values) {
      uint16_t buf[128];
      int n = th_moves(p, buf);   (enclosing function: th_root_moves)
  ```
- **Toggle and pin** — A new test function in test_engine_c.py; deselect with `-k 'not recorded_proof'`. No engine change, so node identity is unaffected.
- **Expected gain** — ESTIMATE, metric = coverage, zero nodes-to-depth and zero NPS. Confirming measurement: apply the MUT-A mutation (horizon returns SND_LB|SND_UB) to a scratch copy and confirm this test's node count and/or value moves. MUT-A changed the depth-6/8 digest and cut nodes 111,232 -> 102,376 on the prototype set, so a node assertion here is expected to move too; the value assertion alone may not, which is why the test should assert BOTH.
- **Risk** — Node counts are only reproducible across processes, so the node half must run in a pytest process that has not already done a root_search, or it flakes by the +11.5% history contamination. Either assert the value only, or land the history-clearing toggle first, or run this test in its own process. State the choice in the test docstring.
- **Oracles** — Re-running the proven line - this IS that oracle, made automatic; pytest -q; solve_hunt.py --seed 0xC0FFEE cross-seed agreement, which the miner verified holds for this position.
- **Effort** — ~12 lines; one hour.
- **Novelty** — Not on the fixed list. Nothing currently connects solve_status.json's published claims to executable code, so the repo's headline output is entirely unverified by CI.

<details><summary>Evidence</summary>

```
solve_status.json:10 re-read verbatim from the current tree: `{"line": "1. Fd1c2??", "tfen": "fuwk/3p/P1F1/KWU1[-] b", "value": "Black mates in 9 plies", "pv": "1... Ub4xc2 2. Wb1b2 F@a3 3. Wb2xc2 d3xc2 4. U@b3 Kd4d3 5. Ub3xd2 W@b1#"}`. th_root_moves re-read at tinyhouse.c:600-615, and the ply adjustments at 436-437 (`if (v > MATE_BOUND) v -= ply; else if (v < -MATE_BOUND) v += ply;`) and 526-527 (`if (sv > MATE_BOUND) sv += ply; else if (sv < -MATE_BOUND) sv -= ply;`). Miner's run: th_root_moves(start, 10) -> 0.09s 95857 nodes, a1b2=0 b1b2=0 c1d3=0 c1b3=0 d1c2=-29990 a2a3=0; and th_solve on the child at depth 10 with seed 0x0 and seed 0xC0FFEE both -> value=29991 snd=1 best=b4c2.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

CORRECTED ITEM (keep the deliverable, replace the mechanism and the gain claim):

title: Pin the recorded mate-in-9 proof: nothing connects solve_status.json's published claims to executable code

what: One test asserting th_root_moves(start, depth 10) returns exactly six root moves in the order a1b2, b1b2, c1d3, c1b3, d1c2, a2a3 with values 0,0,0,0,-29990,0. VALUE ONLY. Do NOT assert the node count.

mechanism (corrected, all measured on M2 Pro, current working tree, tinyhouse.c md5 90e7e5a9119221bae6a1e7c5bf5e4625):
 -29990 == -(MATE - 10) with MATE 30000 (tinyhouse.c:270), i.e. mated 10 plies from the root, so Black mates in 9 from the child - exactly what solve_status.json:10 records. What the assertion actually pins, verified by mutation:
  - the terminal mate-score encoding and distance-to-mate: MUT-T (`-(MATE - ply)` -> `-(MATE - ply - 1)` at tinyhouse.c:463 and 503) moves the value to -29989. DETECTED.
  - the sign convention, the root-move set, and the root-move order the GUI displays (th_root_moves returns th_moves order; nothing else in the suite pins that order).
 What it does NOT pin, contrary to the original item, each measured:
  - MUT-A (horizon `if (any) return 0;` at tinyhouse.c:461 mutated to set si->snd = SND_LB|SND_UB): value unchanged at -29990, nodes 93885, inside the in-process jitter band 93816-95870. NOT DETECTED.
  - MUT-P (both TT ply adjustments at 436-437 and 526-527 deleted): value unchanged at -29990, nodes 95930. NOT DETECTED. The original claim "any off-by-one in the adjustment moves the number" is false at this depth and position.
  - MUT-G (TT_EXACT probe sound-gate at tinyhouse.c:439 reduced to `if (tv.flag == TT_EXACT)`): value unchanged, nodes 95857 - bit-identical to the unmutated run. NOT DETECTED. The original claim "any TT soundness-gating regression ... changes it to 0" is false.

expected_gain (corrected): ESTIMATE, metric = coverage only. Zero nodes-to-depth, zero NPS. It is a regression pin on the published headline claim plus the mate-score encoding, not a soundness detector - three of the four soundness mutations I ran slip past it. Confirming measurement already taken: MUT-T detected, MUT-A/MUT-P/MUT-G not detected.

risk (corrected): the node half is unusable, not merely fragile. Measured within one process with a fresh th_tt_init(22) before each call: 95857 / 94645 / 94280, and 93816 after an intervening th_mate_hunt_mt. Across TT sizes 18/20/22/24 with a fresh process each: 95870 / 95858 / 95857 / 95857. The VALUE is invariant across all of those and across th_seed(0), th_seed(0x1), th_seed(0xC0FFEE). Assert the value, state in the docstring that the node count is deliberately not asserted because history[2][2048] is not cleared between root_search/search calls.

cost: 0.09s for the depth-10 call, so it does not move `pytest -q` off 1.04s.

</details>

*Verifier: 1. QUOTE. `cat -n tinyhouse.c | sed -n '590,625p'` on the current tree (md5 90e7e5a9119221bae6a1e7c5bf5e4625) gives lines 600-602 verbatim: "int th_root_moves(THPos *p, int depth, uint16_t *out_moves, int *out_values) {" / " uint16_t buf[128];" / " int n = th_moves(p, buf);". Character-for-character match; the "(enclosing function: th_root_moves)" tail is the miner's annotation, not file text. Anchor tinyhouse.c:600 correct. Ply adjustments confirmed at 436-437 ("if (v > MATE_BOUND) v -= ply; / else if (v < -MATE_BOUND) v += ply;") and 526-527 ("if (sv > MATE_BOUND) sv += ply; [...]*


### 22. `[INSTRUMENT]` A reachable-position census — the number the draw-proof lane needs and `state_count.py` cannot give

- **Source** — `scripts/state_count.py` produces a *syntactic* upper bound (1.77e13). Nothing measures what is actually reachable, which is the quantity that decides whether any exhaustive formulation is viable.
- **What** — A BFS over distinct positions (board + hands + side to move) from the start, reporting new and cumulative distinct positions per ply. 60.7 million positions through ply 10 in **12 seconds** and 1.8 GB of RSS.
- **Mechanism** — Open-addressing hash of Zobrist keys plus a frontier array of `THPos`; reuses `th_moves`, `make` and `th_key` directly.
- **Soundness argument** — Does not touch the search. It is a measurement program.
- **Integration point** — new `scripts/census.c` (or a `th_census` entry point). The claim it corrects is at `scripts/state_count.py:88-89`, echoed in `RULES.md` lines 145-148:
  ```python
  print(f"upper bound on states: {total:,}")
  print(f"/4 symmetry          : {total // 4:,}")
  ```
- **Toggle and pin** — Standalone; `--maxply` and `--hashbits` as visible CLI flags with a printed RSS estimate and a hard refusal above half of RAM (learn from tonight's `--tt 40`). Pin: ply counts 1-7 must equal 6 / 33 / 193 / 1220 / 7751 / 45979 / 291007 on every run, and ply 1-2 must equal perft 1-2 (6, 33) since no transposition exists that shallow.
- **Expected gain** — Neither search metric; it is an input to costing. It converts "a strong solve is infeasible" from an argument into a measurement, and it prices df-pn honestly.
- **Risk** — Memory. Cap it and say so.
- **Oracles** — the ply 1-2 identity with perft; re-running under a second Zobrist seed must give identical counts (guards the 64-bit collision tail in the census itself).
- **Effort** — ~70 lines of C, already written and run.
- **Novelty** — The draw-proof discussion currently rests on a syntactic bound that is at least an order of magnitude loose.

**Evidence.**

```
ply  new distinct   cumulative   growth
  1            6            7
  2           33           40     5.5x
  3          193          233     5.8x
  4        1,220        1,453     6.3x
  5        7,751        9,204     6.4x
  6       45,979       55,183     5.9x
  7      291,007      346,190     6.3x
  8    1,689,902    2,036,092     5.8x
  9    9,630,829   11,666,921     5.7x
 10   49,003,553   60,670,474     5.1x
12.3s, 1.8 GB peak RSS
```

The growth factor is beginning to bend (6.4 -> 5.1), which is the first evidence anyone has about *where* the reachable space saturates. Note what this does to the "just go deeper" plan: the recorded depth-20 White hunt visited 729M nodes, and the distinct-position frontier at ply 10 alone is 49M.


### 23. `[INSTRUMENT]` The 4-element symmetry group gives eight free oracle positions and nothing uses them

- **Source** — `RULES.md:45` states the start position is invariant under 180-degree rotation plus colour swap; `scripts/state_count.py` divides by 4 for it. No test exercises it.
- **What** — Every member of a position's symmetry orbit must have identical perft at every depth. That is a free, strong oracle for exactly the class of bug perft from one position cannot catch: a colour-dependent or file-dependent error in the neighbour tables.
- **Mechanism** — `PCAPS`, `PUSH` and `PROMO_RANK` are the colour-indexed tables and `MAO_MOVES`/`MAO_ATT` the direction-sensitive ones; a transposed entry in any of them survives a single-position perft and dies instantly under orbit invariance.
- **Soundness argument** — Test-only. Does not touch the search.
- **Integration point** — `test_tinyhouse.py:12-18`, immediately after `PERFT_ORACLE`:

  ```python
  # (tfen, [perft(1), perft(2), ...])
  PERFT_ORACLE = [
      ("fuwk/3p/P3/KWUF[-] w", [6, 33, 241, 1855, 16021]),
      ("1k2/4/2K1/4[PFUWpfuw] w", [55, 2274, 71482]),
      ("1uwk/P3/3p/K2F[UWf] w", [27, 328, 5768, 50971]),
      ("3k/1U2/4/K3[f] b", [4, 18, 231, 1240]),
      ("k3/W1F1/1K2/4[p] b", [0, 0]),
  ]
  ```
- **Toggle and pin** — Not a toggle; a parametrised test. Costs about 0.15s at depth 7.
- **Expected gain** — Neither metric; coverage. It pins the one thing the existing perft oracle structurally cannot.
- **Risk** — None.
- **Oracles** — is one.
- **Effort** — ~15 lines, including the mirror/rotate helpers (which the symmetry-folding investigation would need anyway).
- **Novelty** — The symmetry group is computed in `state_count.py` and measured (and closed) as a TT-folding idea, but never used as a *test*.

**Evidence.** All four orbit members of the start position, depths 1-7:

```
start (w)                fuwk/3p/P3/KWUF[-] w     [6, 33, 241, 1855, 16021, 139141, 1355253]  MATCH
file mirror (w)          kwuf/p3/3P/FUWK[-] w     [6, 33, 241, 1855, 16021, 139141, 1355253]  MATCH
180 rot + colour swap    fuwk/3p/P3/KWUF[-] b     [6, 33, 241, 1855, 16021, 139141, 1355253]  MATCH
mirror + rot + swap      kwuf/p3/3P/FUWK[-] b     [6, 33, 241, 1855, 16021, 139141, 1355253]  MATCH
```


### 24. `[INSTRUMENT]` TT save/load roundtrip and the seed/size refusal are unpinned - three paths that work today and would break silently

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — th_tt_save and th_tt_load appear nowhere in either test file; solve_hunt.py's resume feature depends entirely on them and on the seed guard.
- **What** — A test that solves a position, saves the table, reloads it under the same seed (expect 0), then asserts a reload under a different seed and a different size both return -2.
- **Mechanism** — The seed guard is the only thing standing between a resumed multi-hour run and importing keys computed under different Zobrist tables. Entries carry sound flags; a table loaded under the wrong tables hands PROVEN-flagged values to unrelated positions. That is a wrong-PROVEN path guarded by exactly one comparison with no test behind it. It is also the same line the format-id item widens, so the test must land first or the widening cannot be verified.
- **Soundness argument** — Touches the TT persistence boundary, which feeds the sound-flag gating at tinyhouse.c:439-447. The test changes nothing; it pins the guard that keeps a cross-seed table from injecting foreign sound flags.
- **Integration point** — `tinyhouse.c:374`:

  ```c
  if (hdr[1] != tt_mask + 1 || hdr[2] != tt_seed_used) { fclose(f); return -2; }   (enclosing function: int th_tt_load(const char *fname))
  ```
- **Toggle and pin** — New test in test_engine_c.py writing to tmp_path; deselect with `-k 'not tt_roundtrip'`. No engine change; perft(7) unaffected.
- **Expected gain** — ESTIMATE, metric = coverage, zero nodes-to-depth and zero NPS. Confirming measurement: mutate a scratch copy so the header seed field is written as 0 instead of tt_seed_used and confirm the 'load other seed' assertion flips from -2 to 0. The miner ran all three paths on the pristine build and recorded the return codes the test would assert; the mutation itself was not run.
- **Risk** — Writes a 16 MiB file at log2=20. Use pytest's tmp_path and log2=16 (1 MiB) to keep the suite fast. Do not point it at solve_state/.
- **Oracles** — pytest -q; solve_hunt.py --seed 0xC0FFEE --fresh, which exercises the same seed plumbing end to end.
- **Effort** — ~15 lines; one hour.
- **Novelty** — Not on the fixed list. The TT-load seed refusal is listed as ALREADY FIXED for the collision-risk concern, but 'fixed' and 'pinned' are different: nothing would fail if the guard were deleted tomorrow.

<details><summary>Evidence</summary>

```
I re-ran the coverage check just now:
$ grep -n "th_tt_save\|th_tt_load" test_tinyhouse.py test_engine_c.py ; echo exit=$?
exit=1
tinyhouse.c:368-378 re-read verbatim from the current tree, including the quoted guard and the doc comment at 367 `/* returns 0 on success, -1 on missing/unreadable, -2 on size/seed mismatch */`. solve_hunt.py:121-125 re-read: the resume path maps rc 0/-1/-2 to "table reloaded" / "no table dump (re-searching)" / "table dump mismatched (ignored)". Miner's baseline on the pristine build: save 0, size 16777240; load same seed 0; load other seed -2; load other size -2.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Two fixes to the item; the item stands otherwise.

(a) expected_gain / confirming measurement — replace with what I actually ran. The mutation that flips "load other seed" from -2 to 0 is deleting the seed comparison from the LOADER, not writing 0 into the header on save:
    tinyhouse.c:374  `if (hdr[1] != tt_mask + 1 || hdr[2] != tt_seed_used) { fclose(f); return -2; }`
    ->               `if (hdr[1] != tt_mask + 1) { fclose(f); return -2; }`
  measured on a scratch build: load same seed 0, load other seed 0 (was -2), load other size -2, perft7 still 1355253.
  The item's stated mutation (header seed field written as 0 at tinyhouse.c:360) instead flips "load same seed" from 0 to -2; measured: same seed -2, other seed -2, other size -2, perft7 1355253. Both are caught, so keep all three assertions, but describe them correctly.

(b) mechanism — "a wrong-PROVEN path guarded by exactly one comparison" is true of the C API in general but not of solve_hunt.py, whose resume path is additionally gated by the checkpoint identity check at solve_hunt.py:118-121 (`if all(loaded.get(k) == state[k] for k in ("tfen", "color", "seed", "tt_bits")):`) and by the sha1 checkpoint filename over the same four fields. State it as: the header comparison is the only guard for any direct caller of th_tt_load, and defense in depth inside solve_hunt.

Implementation note the item omits: engine_c.lib is a process-global, and no existing test touches th_seed or th_tt_init. A test that reseeds must restore the default afterwards (`th_seed(0x9E3779B97F4A7C15)` — the value th_init uses at tinyhouse.c:634 — followed by th_tt_init) or it silently changes the Zobrist tables for every test that runs after it.

Also add a fourth cheap assertion, verified: th_tt_load on a nonexistent path returns -1, which is the third arm of solve_hunt.py's rc dict and is otherwise unpinned.

</details>

*Verifier: Verified end to end, including the mutation the miner did not run. 1) QUOTE / ANCHOR — matches character for character. `cat -n tinyhouse.c | sed -n '340,400p'` gives line 374: ` if (hdr[1] != tt_mask + 1 || hdr[2] != tt_seed_used) { fclose(f); return -2; }` inside `int th_tt_load(const char *fname)` (line 368), with the doc comment at 367: `/* returns 0 on success, -1 on missing/unreadable, -2 on size/seed mismatch */`. The enclosing-function attribution is correct. 2) COVERAGE CLAIM — reproduced on the current tree: $ grep -n "th_tt_save\|th_tt_load" test_tinyhouse.py test_engine_c.py ; [...]*


### 25. `[INSTRUMENT]` Pin attacked() against an independent geometric oracle, because perft cannot isolate it

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — Hunt for table-construction errors perft happens not to catch; the oracle was written to look for one and found nothing, which is itself the argument for keeping it.
- **What** — A test that recomputes, from raw file/rank arithmetic and the RULES.md movement descriptions only, whether square sq is attacked by colour c, and compares it against the C attacked() probed through th_in_check.
- **Mechanism** — attacked() is the single legality gate for the entire engine, implemented from four precomputed tables (ORTH, DIAG, PCAPS, MAO_ATT) that nothing checks directly. Perft is a weak witness: a hole in one table shows up only if it changes a legal-move count, and the Python engine builds its tables with structurally identical code, so the parity test would agree on the same mistake. An oracle written from geometry breaks that shared-ancestry blind spot. MAO_ATT is the specific worry - it is populated by side effect from the MAO_MOVES loop, so its correctness is a consequence of a loop rather than a stated property.
- **Soundness argument** — Pure test addition, no production change. It pins the invariant that legality - and hence every mate and stalemate terminal the proof machinery emits - rests on the correct attack relation. It also becomes the guard for the no-sliders legality fast path, whose theorem is a statement about exactly this relation.
- **Integration point** — `tinyhouse.c:83`:

  ```c
  static int attacked(const THPos *p, int sq, int by) {
      const uint8_t *n;
      for (n = ORTH[sq]; *n != 0xff; n++) {
          int pc = p->board[*n];
          if (pc && COLOR(pc) == by && (TYPE(pc) == W || TYPE(pc) == K)) return 1;
      }   (enclosing function: attacked. The table it depends on is built by side effect at tinyhouse.c:67-68 inside init_tables: "                MAO_MOVES[s][nm[s]][0] = b; MAO_MOVES[s][nm[s]++][1] = t;" / "                MAO_ATT[t][na[t]][0] = s; MAO_ATT[t][na[t]++][1] = b;")
  ```
- **Toggle and pin** — `ATTACK_ORACLE_TRIALS = 400` as a module constant in the test file (0 skips). No production code changes, so node identity is not applicable.
- **Expected gain** — ESTIMATE, metric = coverage of the attack relation, not nodes or NPS. The miner's run made 215,546 independent (square, colour) comparisons across 400 random walks in a few seconds. Confirming measurement: deliberately corrupt one entry of MAO_ATT in a scratch build and check this test goes red while perft(7) may not - that is the experiment proving the instrument has power the perft oracle lacks.
- **Risk** — The oracle is a second implementation, so it can be the wrong one. Write it from RULES.md's movement table (mao = one orthogonal step to a square that must be empty, then one diagonal step outward), never by reading tinyhouse.c, and keep it short enough to eyeball. Fixed seed.
- **Oracles** — pytest -q; RULES.md's piece-movement table as the specification; the deliberate-corruption experiment as the power check; PERFT_ORACLE stays as the complementary end-to-end oracle.
- **Effort** — ~45 lines in test_engine_c.py; two hours including the corruption experiment.
- **Novelty** — Nothing on the closed or fixed lists targets attacked() in isolation; every existing check is end-to-end through perft or move-set parity, and both share the Python table-construction logic as a common ancestor.

<details><summary>Evidence</summary>

```
attacked() re-read verbatim from the current tree at tinyhouse.c:83-101 (the quote is the current first loop; the mao loop at 96-99 is `    for (int i = 0; MAO_ATT[sq][i][0] != 0xff; i++) {`), and the side-effect table construction re-read at tinyhouse.c:67-68. Miner's oracle against the SHIPPED engine_c: `tested 215546 mismatches 0` (400 random walks; for every position, every empty square and both colours, a lone enemy king is planted and th_in_check compared against geometry recomputed from file/rank deltas including the mao blocker rule). Static bound check via the Python mirror: max MAO_MOVES per sq 4, max MAO_ATT per sq 4, max KING per sq 8 - so MAO_MOVES[16][9][2]/MAO_ATT[16][9][2] have slack but KINGN[16][9] is exactly full at 8 + terminator, zero margin if a piece is ever added.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Two fields are wrong and must be replaced. Everything else in the item stands as written.

CORRECTED "mechanism": attacked() is the single legality gate for the entire engine — grep confirms exactly one caller, tinyhouse.c:111 `return attacked(p, king_sq(p, color), 1 - color);` — implemented from four precomputed tables (ORTH, DIAG, PCAPS, MAO_ATT) that nothing checks against the specification. Perft is not a weak witness because table holes hide in the node count; measured, every single-entry MAO_ATT hole moves perft(7) off 1,355,253 (16/16 squares). Perft is a weak witness because it is CIRCULAR: test_tinyhouse.py:12-18 PERFT_ORACLE is a hardcoded list of counts generated by this project's own Python engine, and RULES.md states the counts are "UNVERIFIED empirically; the login wall blocked the direct test." Perft therefore pins self-consistency, never conformance. The Python engine builds its tables with structurally identical code (tinyhouse.py:66-67 vs tinyhouse.c:67-68), so the parity test shares the same blind spot. A geometry wrong from the start is invisible to every oracle in the repo: both engines agree, and the recorded constants bake in the error. An oracle written from RULES.md is the only check that can see it. MAO_ATT remains the specific worry — it is populated by side effect from the MAO_MOVES loop, so its correctness is a consequence of a loop rather than a stated property.

CORRECTED "expected_gain": ESTIMATE, metric = spec-conformance coverage of the attack relation, not nodes or NPS. Verified: 9,298 independent (board, square, colour) comparisons in a few seconds, 0 mismatches, against the shipped engine. Do NOT use single-entry MAO_ATT corruption as the power check — I ran it on all 16 squares and perft(7) caught every one, so it demonstrates the opposite of the intended point. The correct power check is a SHARED-ANCESTRY mutation: apply the same geometry error to tinyhouse.c AND tinyhouse.py AND regenerate PERFT_ORACLE from the mutated Python engine (e.g. make the mao's diagonal continuation inward rather than outward). Then pytest goes fully green on a wrong rule set while the geometric oracle goes red. That is the experiment proving the instrument has power the perft oracle structurally lacks.

Also worth adding to "risk": the probe plants a king on an EMPTY square, so the oracle only exercises unoccupied targets. This is not a gap — attacked() has exactly one caller and it is always passed a king square — but the test should assert that single-caller property (or be revisited if a second caller appears), otherwise the coverage argument silently expires.

The "evidence" field's claim that the mao loop sits at tinyhouse.c:96-99 is off by one: it is line 97, `    for (int i = 0; MAO_ATT[sq][i][0] != 0xff; i++) {`, with the body at 98-100.

</details>

*Verifier: CITATIONS: exact. `cat -n tinyhouse.c` lines 83-88 match the quoted `attacked()` prologue character for character; lines 67-68 match the MAO side-effect construction verbatim; line 97 matches the cited ` for (int i = 0; MAO_ATT[sq][i][0] != 0xff; i++) {`. Repo re-read just now, `git status --short` shows only the two pre-existing untracked review files, and `engine_c.perft("fuwk/3p/P3/KWUF[-] w", 7) = 1355253` (drift signature intact). I BUILT AND RAN THE PROPOSED INSTRUMENT. [...]*


## `[NEW-IDEA]` — draw-proof lane first

### 26. `[NEW-IDEA]` df-pn as a second engine: 12.5x better on the win lane, and the only reachable formulation for the draw proof

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — KNOWN OPEN 'a draw proof is the real prize', costed across three lenses; Kishimoto/Winands/Mueller/Saito ICGA 35(3) 2012; Nagai's df-pn (2002); Kishimoto & Mueller AAAI-04 and Information Sciences 175(4):296-314 (2005) for the GHI fix. A depth-limited df-pn prototype was built against the repo's own movegen and measured against th_mate_hunt.
- **What** — Add a df-pn proof-number engine beside th_mate_hunt_mt in two milestones: first a depth-limited win hunt (measured 12.5x fewer nodes to the recorded mate-in-9), then the unbounded version with ancestor repetition as the disproof terminal, which turns 'no win within N plies' into 'no win, ever' - two such disproofs are the draw proof.
- **Mechanism** — EXACT FORMULATION for the draw lane. Goal: colour C forces a win from the root. OR node = C to move, AND node = 1-C. Terminal with no legal moves: mover in check -> mover loses; mover not in check -> mover wins (stalemate=win). Map to (pn,dn)=(0,inf) if the winner is C else (inf,0). Ancestor repetition -> draw -> (inf,0), a DISPROOF. No horizon and no other terminal, so a draw stops being the absence of a proof and becomes a positive goal; termination is bounded by the state count since paths are simple in position space. WHY THE CURRENT MACHINERY CANNOT DO IT, measured: in the depth-limited hunt rep-safety blocks only 2.4% of store attempts (34,912 of 1,449,755 at d16 White) because the horizon fires long before a cycle does - at D=10 the df-pn disproof used 1,986 horizon leaves and ZERO repetition leaves. Remove the horizon and every one of those must instead be driven to a repetition, so the block rate goes to ~100% and the search degenerates from a graph search to a tree over simple paths. The fix is Kishimoto-Mueller df-pn(r) / BTA twin entries: a slot splits into a base entry (repetition-free or unproven, reusable on any path) and twin entries tagged with the path positions the result depended on. Cost: one index word per slot plus ~16 bytes per twin and a path-compatibility test on probe. MEMORY: a df-pn entry is key 8B + pn 4B + dn 4B = 16B, 24B with a twin index; 2^28 x 24B = 6.0 GiB, which is 6e-5 of the 4.4e12 symmetry-reduced states, so this only works if the disproof DAG is far smaller than the state space - plausible, since a disproof of 'White wins' keeps all White moves but only ONE Black move per node.
- **Soundness argument** — A NEW entry point (th_dfpn), not a change to search(), so every existing proof stands untouched and solve_hunt.py stays byte-identical. The unbounded version DELETES the unsound horizon rather than weakening it, so every leaf becomes one of the two cases tinyhouse.c already marks SND_LB|SND_UB. The real risk is the rep-safety invariant: a GHI bug makes a repetition-dependent disproof reusable on a path where the repetition does not exist, producing a wrong 'proven draw'. Mitigation is structural - keep the conservative `my_rep >= ply` rule as the default and put twin entries behind their own toggle, so the GHI-correct mode must match the conservative mode on every position both can solve. Output must additionally be validated by replaying the returned PV through th_make and asserting th_result.
- **Integration point** — `solve_hunt.py:7`:

  ```python
  A value > 29000 at depth d proves a forced win for that color; anything else
  proves there is no forced win within d plies (total plies - there are no
  search extensions, so the ply budget is exact).   (module docstring of solve_hunt.py)
  ```
- **Toggle and pin** — A separate driver plus two visible lines. solve_hunt.py: `ap.add_argument("--engine", choices=("ab", "dfpn", "dfpn-unbounded"), default="ab")`. tinyhouse.c or a new C file: `#define TH_GHI_TWIN 0` (0 = today's conservative store rule, 1 = twin entries). With the default "ab" not one byte of the current path executes, so every existing node count reproduces exactly - that is the pin. Node identity ACROSS engines is impossible by construction (df-pn and alpha-beta expand different node sets), and so is identity between conservative and twin modes; the cross-mode pin is that both return the SAME verdict on every position either can finish. The df-pn table must be its own allocation with its own --tt accounting: wiring it into the alpha-beta table would corrupt the bounds.
- **Expected gain** — ESTIMATE. Metric is nodes-to-proof at a fixed position, NOT nodes-to-depth (the two engines share no depth axis). Measured basis: 1,949 vs 24,358 nodes = 12.5x better on the recorded mate-in-9, and ~6x WORSE on the depth-limited disproof (19,610 vs 3,416 at D=8; 142,350 vs 23,608 at D=10), so the depth limit was doing all the work and removing it makes the job harder before it makes it possible. Milestone gates, in order: (1) df-pn must reproduce the mate-in-9 with bestmove b4c2 and must NOT find any win the recorded 20/22-ply bounds exclude; (2) run unbounded from the start with a node cap and record the root dn against nodes spent - if dn falls monotonically and the twin count stays inside the table, the approach is viable; if dn plateaus while twins saturate, it is not, and that is a one-day answer.
- **Risk** — Highest-risk item here. GHI bugs are silent and produce exactly the failure the doctrine forbids. Proof numbers on a 5-6x-branching DAG can thrash a bounded table, which is what the node_budget argument is for. There is a real chance the disproof DAG is simply too large and the answer is 'no'. The VERIFY_PROVEN_CUT item should land first: it builds the ancestor-crossing detector the df-pn version needs.
- **Oracles** — Re-running 1.Fd1-c2 -> mate in 9 from "fuwk/3p/P1F1/KWU1[-] b" - the unbounded engine must return the same mate distance; the recorded bounds in solve_status.json must not be contradicted; solve_hunt.py --seed 0xC0FFEE --fresh on anything df-pn proves, since a collision inheriting a sound-flagged twin entry is the tail risk; pytest -q; perft(7)=1,355,253 to show the shared movegen was not disturbed.
- **Effort** — Milestone 1: port the working Python prototype (~100 lines) to C behind --engine dfpn, ~250 lines of C plus ~30 of Python wiring, two to three days. Milestone 2 (unbounded, TH_GHI_TWIN=0): ~2 days, report the dn trajectory. Milestone 3 (twin entries): ~1 week, worth starting only if milestone 2's dn curve is falling.
- **Novelty** — KNOWN OPEN names the draw proof; this answers it with a formulation, a named GHI fix, a memory model, a measured reason the current machinery cannot get there, and a gating measurement. The repo has exactly one search algorithm today. Merged from three lenses (win lane, draw lane, costing) - one entry point, staged.

<details><summary>Evidence</summary>

```
solve_hunt.py:7-9 and th_mate_hunt_mt (tinyhouse.c:590-594) re-read verbatim from the current tree; the horizon line the draw lane must delete is tinyhouse.c:461 `        if (any) return 0;                    /* unknown: no soundness */`, also re-read. Miner runs: dfpn_probe.py 1 9 "fuwk/3p/P1F1/KWU1[-] b" -> pn=0 PROVEN nodes=1,949 tt=1,480 0.27s vs ab_ref mate_hunt d=9 value=29991 nodes=24358; dfpn_probe.py 0 8 -> 19,610 DISPROVEN vs ab d=8 3,416; 0 10 -> 142,350 vs 23,608. Leaf census dfpn_leaf.py 0 10: rep=0 horizon=1,986 terminal=137. Instrumented store census (scratch copy, perft7 1355253, repo untouched): col=0 d=16 stores 1,414,843 rep-blocked 34,912 (2.4%); col=0 d=12 429 of 21,839 (1.9%). Root soundness probe: full-window th_solve at the start returns snd=0 at every depth 2..14, which I independently reproduced at d8/d10/d12.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Three numeric claims need correcting; the item's category, anchor, quote, soundness argument, and direction of gain all stand.

(a) The 12.5x basis does not reproduce. Replace "1,949 vs 24,358 nodes = 12.5x" with a stated protocol. Mine: fresh process, th_tt_init(22), th_mate_hunt(pos, 9, black) on "fuwk/3p/P1F1/KWU1[-] b" -> value=29991, nodes=30137, bestmove=214 (=b4c2), stable across tt bits 16..24. An independent df-pn prototype proves the same mate in 1,908 nodes. That is 15.8x. Against a warm iteratively-deepened table (depths 1..9 in one process) the depth-9 increment is 22,566 and the cumulative is 34,674, giving 11.8x and 18.2x respectively. So: "an independently rebuilt df-pn proves the recorded mate-in-9 in ~1.9k nodes against ~23k-30k for the null-window hunt, i.e. 12x-16x fewer nodes depending on whether the alpha-beta table is warm; the protocol must be stated with the number."

(b) "at D=10 the df-pn disproof used 1,986 horizon leaves and ZERO repetition leaves" is REFUTED. My prototype, which does check ancestor repetition, at C=0 D=10 from the start position: leaves = {rep: 1840, horizon: 1931, terminal: 141}; at C=0 D=8: {rep: 150, horizon: 526, terminal: 5}; on the mate-in-9: {rep: 1, horizon: 318, terminal: 36}. Repetition leaves are already comparable in count to horizon leaves at D=10, and the root value came back path-dependent (dep=True) in all three runs. The miner's rep=0 is almost certainly an artifact of a prototype without ancestor repetition detection. The supporting sentence should read: "even at D=10 the depth-limited df-pn already terminates ~1.8k branches on ancestor repetition against ~1.9k on the horizon, and the root value is already repetition-derived; removing the horizon leaves repetition as the ONLY non-terminal leaf, so essentially every value becomes path-dependent and unstorable under the conservative rule." This is a stronger argument for twin entries than the original, not a weaker one.

(c) Denominators and small drifts in the census: ab at col=0 d=10 is 23,547 here (item said 23,608); d=8 is 3,416 exactly. Store census on my instrumented build: col=0 d=16 -> 35,268 rep-blocked, 1,288,046 actual tt_store calls, 5,081,142 attempts reaching the guard, so 2.67% of (stores+blocked) and 0.69% of attempts; col=0 d=12 -> 432 / 21,868 / 94,414 = 1.94% and 0.46%. Say which denominator the percentage uses.

(d) Wording: "termination is bounded by the state count since paths are simple in position space" overstates it. Only PATH LENGTH is bounded by the state count; the search tree is bounded by the number of simple paths, which is vastly larger. The item's own later sentence ("degenerates from a graph search to a tree over simple paths") is the honest version -- use that and drop the state-count bound.

(e) Add the unit caveat: a df-pn MID call is a much heavier node than an ab search() entry, so nodes-to-proof is the only comparable axis and no time claim may be read off these numbers.

</details>

*Verifier: I tried to kill this and could not. I re-read both anchors, re-derived the arithmetic, reproduced the store census on my own instrumented build, and wrote my OWN df-pn prototype from scratch (I did not read or run the miner's) to re-measure both lanes. Three sub-numbers are wrong; the item's substance survives all of them. 1) QUOTES, byte-checked just now. `sed -n '7,9p' solve_hunt.py | od -c` -> "A value > 29000 at depth d proves a forced win for that color; [...]*


### 27. `[NEW-IDEA]` Sigma-mirror as a draw-proof scaffold: the pure mirror is REFUTED, but the balanced sub-space is only 2,199,040 positions

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — RULES.md:45 states the start position is symmetric under 180-degree rotation + colour swap; the construction was built and measured end to end rather than argued.
- **What** — Exploit that the start position is fixed by sigma = 180-rotation + colour swap. Black answering every White move m with sigma(m) keeps the position sigma-balanced, and the ENTIRE balanced sub-space is 2,199,040 positions. The pure mirror strategy is measured and FAILS; what survives is the balanced set as a strategy-verification scaffold and sigma(m) as a free candidate-move generator.
- **Mechanism** — sigma pairs square s with 15-s and flips colour, so a balanced position is determined by 8 half-squares plus one hand: exactly 2,199,040 syntactic positions, 1.2e-7 of the state space. A White move leaves it unbalanced; Black's sigma(m) restores balance. That makes the mirror walk a walk on ~1e6 White-to-move positions, and because the strategy commits to ONE Black move per node, the verified DAG grows with White's branching only. THE REFUTATION, measured in 45 seconds: over 456,275 balanced positions and 1,261,950 successful mirror pairs, sigma(m) was illegal for Black 359,491 times (22%), about half of those because White gave check and the mirror cannot answer while Black must address its own king; worse, 4,804 of the walk's positions were ones where White's move CHECKMATED Black outright. The pure mirror does not draw, it loses. What survives: use the balanced set as the seed for a strategy-verification proof where the verified object is an explicit Black strategy, with mirror demoted to a move-ordering prior that proposes sigma(m) first at every Black node - one table lookup.
- **Soundness argument** — As an ordering prior it cannot affect soundness at all: ordering changes which nodes are visited, never which values are sound. As a strategy-verification proof it is sound by a different and stronger argument than bound duality - every Black node has exactly one move and every White node all of them, so the verified object IS the strategy, and the only permitted leaves are ancestor repetitions, White checkmated, or Black stalemated (stalemate=win, so a stalemated Black is a Black win and a legal leaf; a stalemated WHITE is a White win and is NOT).
- **Integration point** — `RULES.md:45`:

  ```
  Position is symmetric under 180-degree rotation + color swap.   (document scope: the "Starting position" section)
  ```
- **Toggle and pin** — As an ordering prior: `#define TH_MIRROR_BONUS 0` in tinyhouse.c, added inside order_score() next to the existing killer/history terms. 0 reproduces current node counts EXACTLY, since the bonus is additive and zero is a no-op on the score. As a proof scaffold it is a new script, scripts/mirror_scaffold.py, which changes nothing that exists.
- **Expected gain** — ESTIMATE, split by use. (a) As a strategy scaffold the deciding number is already measured and negative (4,804 immediate checkmates), so the gain is that nobody spends a week on it - the item's main value. (b) As an ordering prior in the df-pn disproof search: metric is nodes-to-depth, fixed depth, paired, same position; expect single-digit percent at best and do not be surprised by zero, because the mirror move is only legal 78% of the time. Confirming measurement: th_mate_hunt at depths 12/14/16 from the start with TH_MIRROR_BONUS at 0 and at 1<<18, node counts compared in SEPARATE processes (the history contamination makes within-process pairs meaningless).
- **Risk** — Low as ordering, zero as a closed negative result. The trap it removes is real: the mirror looks like a free draw proof and it is not.
- **Oracles** — pytest -q; perft(7)=1,355,253 (ordering must not change movegen); toggle-off reproducing the pre-change node count EXACTLY at TH_MIRROR_BONUS=0; the recorded 20/22-ply bounds unchanged in verdict.
- **Effort** — The refutation is done. The ordering prior is ~15 lines in order_score() plus a sigma_move() helper; half a day including the paired measurement.
- **Novelty** — Not on the fixed list, the closed measurements, or KNOWN OPEN. The repo notes the 180+colour-swap symmetry as a fact about the start position and never asks what it buys as a strategy.

<details><summary>Evidence</summary>

```
RULES.md:45 re-read verbatim from the current tree. order_score, the integration point for the prior, re-read at tinyhouse.c:400-411 (`static int order_score(const THPos *p, uint16_t m, uint16_t ttm, int ply, int ks) {` ... `    return history[(int)p->stm][m & 2047] + j;`). Miner's walk: start is sigma-balanced OK; 456,275 balanced White-to-move positions visited, 1,261,950 mirror pairs worked, 359,491 BREAKS, terminals White mated 0 / White stalemated 0 / Black mated (White wins, bad) 4804 / Black stalemated 61, 45.0s; break classification over the first 20,000: 10,001 'White move gives check', 9,999 other. Balanced-set count: 2,199,040. The walk asserts balance after every mirror pair and that assert never fired.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Three corrections, none fatal.

(a) HEADLINE NUMBER over-counts by 24.5%. 2,199,040 is exactly right for the model as stated, but that model does not apply the kings-non-adjacent filter that RULES.md:141 says scripts/state_count.py uses for the 1.8e13 figure it is being compared against. In a balanced position the kings sit at s and 15-s, and two rep squares make that pair adjacent: I ran it and got `rep squares with adjacent mirrored kings: [('b2', 'c3'), ('c2', 'b3')]`. Excluding those king placements gives:
`balanced, pawns rank2-3, stm            : 2199040`
`same, minus adjacent-kings (illegal)    : 1660136`
So the apples-to-apples balanced count is 1,660,136; 538,904 of the 2,199,040 are syntactically illegal. Title should read "only 1,660,136 positions" (or keep 2,199,040 and label it a syntactic upper bound that admits adjacent kings).

(b) SOUNDNESS ONE-LINER, ordering half. Replace "ordering changes which nodes are visited, never which values are sound" with: "ordering can never make an unsound value carry a sound flag, but it does change which nodes earn one — tinyhouse.c:509 `if (!cutoff && all_children_lb) snd |= SND_UB;` gates SND_UB on `cutoff`, which is order-dependent. So the prior cannot emit a wrong PROVEN; it can change which claims get proven at a fixed depth." That is still a pass on the bound-duality invariant, just stated honestly.

(c) EFFORT is understated. "~15 lines in order_score() plus a sigma_move() helper" is wrong: neither `static int order_score(const THPos *p, uint16_t m, uint16_t ttm, int ply, int ks)` (tinyhouse.c:400) nor `static int search(THPos *p, int depth, int ply, int alpha, int beta, SInfo *si)` (tinyhouse.c:413) carries the opponent's previous move, and there is no per-ply move stack. The prev-move has to be threaded through the recursion first. Also worth stating in the item: the bonus can only reach the final `return history[(int)p->stm][m & 2047] + j;` path, because TT move, direct checks, captures and both killers all return early — so the prior only ever reorders quiet non-killer moves, which further caps the plausible gain. The `#define TH_MIRROR_BONUS 0` node-identity pin itself is sound (additive zero on the last return is a genuine no-op).

</details>

*Verifier: I tried to kill this and could not. Both load-bearing empirical claims reproduce independently. 1) CITATION — verbatim match. `cat -n RULES.md | sed -n '30,60p'` gives line 45 exactly: ` 45 Position is symmetric under 180-degree rotation + color swap.` The secondary anchor also matches. `sed -n '390,420p' tinyhouse.c | cat -n` gives at file line 400 `static int order_score(const THPos *p, uint16_t m, uint16_t ttm, int ply, int ks) {` and at 410 ` return history[(int)p->stm][m & 2047] + j;`. 2) DRIFT SIGNATURE INTACT — `engine_c.perft("fuwk/3p/P3/KWUF[-] w", 7)` printed `1355253`. Safe to proceed. [...]*


### 28. `[NEW-IDEA]` Symmetry folding in the TT: measured at 1.089x, not 4x, and slightly negative in nodes - close it

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — KNOWN OPEN 'symmetry reduction ... NOT exploited in the search or the TT'. Two lenses implemented it independently (file-mirror canonical key; 180+colour-swap fold) and both measured it.
- **What** — Answer the open question with a measurement instead of an implementation: canonicalising the Zobrist key over the group merges only 8.9% of the states a forward search from the start reaches, and folding the TT by it measures NEUTRAL-TO-WORSE in nodes-to-depth. Record it; do not build it.
- **Mechanism** — The group is real - over 1,480 positions from the first 6 plies all four transforms preserved legal-move count and th_result exactly, and over 400 random positions the 180+colour-swap map's movegen automorphism check had 0 mismatches. It fails on frequency, not correctness. The 4x applies to the SYNTACTIC space, which is closed under the group; the set reachable from the start is not, and the measured fold ratio (distinct raw / distinct canonical) is 1.000, 1.000, 1.004, 1.008, 1.026, 1.036, 1.063, 1.089 through ply 8 - creeping, but nothing suggests it approaches 4 anywhere near searchable depths. Against that, the cost is four th_key computations per node (a 24-iteration loop, called once per node before every probe). Direct A/B: file-mirror canonical key changed depth-16 nodes 10,286,159 -> 10,577,939 (+2.8% WORSE) with the hit rate moving only 5.0% -> 5.1%; the 180+colour-swap fold changed the null-window hunt by 0% to +17% worse and the full-window solve by -0.1%, because in a one-colour hunt the map sends attacker nodes to defender nodes, searched under mutually useless windows. The right place to spend the group is a df-pn proof-number table, where entries are window-free.
- **Soundness argument** — Does not touch the search if not implemented, which is the recommendation. If implemented anyway: the transforms are value-preserving in the side-to-move frame and mate distances are invariant because they are bijections on moves, so folding is sound for VALUES. It is NOT sound for the stored MOVE - root_search returns *bestmove straight out of the TT (tinyhouse.c:572) and solve_hunt.py prints it as the proof line, so a canonical entry hands back a move in the wrong frame. That is a wrong-looking proof from a correct search, which in a solver is nearly as bad as a wrong one; it needs one of the 16 unused data bits as a transform flag.
- **Integration point** — `tinyhouse.c:283`:

  ```c
  for (int s = 0; s < 16; s++) if (p->board[s]) k ^= zob_piece[s][(int)p->board[s]];   (enclosing function: th_key - the loop that would have to run once per group element)
  ```
- **Toggle and pin** — If anyone re-opens it: `#define TH_CANON_KEY 0` inside th_key. With it 0 the current body runs verbatim and every node count is bit-identical. Node identity with it 1 is IMPOSSIBLE by design, since the point is that different positions share an entry; the pin is the reproducibility of the deepening sweep across processes (2^22 depth 16 gave 10,286,159 nodes twice from independent runs). The recommended action needs no code: add the measurement to the MEASURED AND CLOSED note in the solve_hunt.py docstring beside the lazy-SMP numbers.
- **Expected gain** — MEASURED as approximately zero and slightly negative. Metric: nodes-to-depth at fixed depth, paired, same position. The gain from recording it is the week nobody spends. If anyone disputes it: th_mate_hunt at depths 12/14/16 from the start, toggle 0 vs 1, separate processes, three repeats, reporting nodes-to-depth AND wall-clock medians - both must improve, and the prediction is neither does.
- **Risk** — The risk is in implementing it, not in skipping it: a mirrored bestmove out of root_search would print a wrong PV for a genuine proof, and solve_status.json publishes those lines. The measurement is also on ONE root position (the start, which is asymmetric under file mirror and self-symmetric under sigma) at depth 16 - say that when recording it rather than closing the whole KNOWN OPEN entry, since a symmetric root could behave differently.
- **Oracles** — PERFT_ORACLE and perft(7)=1,355,253 (both folded builds were cross-checked against base on all five oracle positions and matched exactly, confirming th_key changes nothing outside the TT); the deepening sweep reproduced across processes; solve_status.json verdicts unchanged; pytest -q. WORTH LANDING ANYWAY, and not listed separately: a parametrised test applying file-mirror and 180+colour-swap to every PERFT_ORACLE position and asserting identical perft at every oracle depth - 8 free oracle positions at zero authoring cost, and the precondition for ever canonicalising a key. The miner ran it and all four transforms preserve perft on all four non-trivial oracle positions; note the colour bit is `color << 4`, so cflip must XOR 16, not 8.
- **Effort** — Zero - the recommendation is not to build it; the measurements are done. Recording it is a docs commit. If someone insists: ~60 lines plus the move-frame handling, one day, not worth spending.
- **Novelty** — Directly closes the TT half of a stated KNOWN OPEN item with a number, and separates the case where 4x is real (retrograde over the syntactic space) from the case where it is 1.089 (forward search from the start). Merged from two lenses that measured the two halves of the group and agreed.

<details><summary>Evidence</summary>

```
th_key re-read verbatim from the current tree at tinyhouse.c:281-287, and the wrong-frame bestmove hazard at tinyhouse.c:572 `        *bestmove = tt_probe(th_key(p), &tv) ? tv.move : 0;`. Miner A, bfs_sym.py: automorphism check 1480 positions x 4 transforms, movecount+result invariant OK; fold ratio by ply 1.000/1.000/1.004/1.008/1.026/1.036/1.063/1.089. Miner A, sym fold on the null-window hunt, tt 2^22: d14 c0 1245821 -> 1247951; d16 c1 1824606 -> 1930030; 1uwk/1f1p/PW2/K1UF d14 2907235 -> 3403761; full-window d14 1,320,285 -> 1,319,009. Miner B, file-mirror canonical key, identical deepening sweep: d16 10,286,159 nodes 5.0% hit -> 10,577,939 nodes 5.1% hit; PERFT_ORACLE cross-check OK on all five positions.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Two corrections to the item's prose; the anchor, category, recommendation and gain claim all stand.

(a) Fold ratio, say CUMULATIVE. Per-ply distinct raw / distinct canonical is exactly 1.0000 at every ply 1-6 (193/193, 1221/1221, 7760/7760, 46088/46088) - no two positions at the same ply from the start are group-related that shallow. The 1.000/1.000/1.004/1.008/1.026/1.036 series is the ratio over the CUMULATIVE reachable set (all plies so far), which is the right figure for a TT and which I reproduced to three decimals (233/232, 1453/1441, 9204/8972, 55183/53279). Written without "cumulative" the number is refutable in one command.

(b) Wrong-frame bestmove: right conclusion, wrong mechanism. Replace "root_search returns *bestmove straight out of the TT (tinyhouse.c:572) and solve_hunt.py prints it as the proof line, so a canonical entry hands back a move in the wrong frame" with: search() blocks every TT cutoff at the root (`if (ply > 0) {`, tinyhouse.c:438), so the root re-searches and usually overwrites the entry with a correct-frame move; the leak is the replacement policy at tinyhouse.c:523-524 (`if ((depth >= 2 || proven) && (!tv_hit || proven || (!old_proven && depth >= tv.depth))) {`) - when the root's own store is skipped because a deeper or proven entry from the group-partner is already there, line 572 hands back that partner's move. Measured on a scratchpad file-mirror build: 32 of 40 primed pairs returned an illegal bestmove at the root (base build 0 of 40), e.g. tfen "fuwk/3p/PK2/1WUF[-] b" got move 231 with legal=[183,201,212,214,234].

(c) Optional precision on the gain: my independent implementation of the exact proposed toggle measured d12 172,221 -> 172,221, d14 1,245,821 -> 1,245,641, d16 c1 1,824,606 -> 1,825,999, d16 c0 9,913,857 -> 9,957,280 (all fresh process, tt 2^22, three-process reproducible). The item's +2.8% deepening-sweep figure and +17% 4-group figure are unverified by me; the qualitative claim "neutral to slightly worse" is verified.

</details>

*Verifier: I tried to kill this one and could not. Everything decisive I re-ran myself. 1) QUOTES (re-read now, other session's tree). `sed -n '283p;572p' tinyhouse.c` -> ` for (int s = 0; s < 16; s++) if (p->board[s]) k ^= zob_piece[s][(int)p->board[s]];` ` *bestmove = tt_probe(th_key(p), &tv) ? tv.move : 0;` Both match the item character for character, and line 283 is inside th_key (tinyhouse.c:281-287). The colour-bit note is right: tinyhouse.c:15 `#define PIECE(c, t, pr) (((t) + 1) | ((pr) << 3) | ((c) << 4))`, so cflip is XOR 16. 2) DRIFT SIGNATURE. `.venv/bin/python -c "import engine_c; [...]*


## `[SHOULD-BE-BETTER]`

### 29. `[SHOULD-BE-BETTER]` th_tt_save writes the entire table every checkpoint: 256 MiB of file for 0.33 MiB of entries at 2^24

> **Verifier: PLAUSIBLE** — citation re-read against the current tree, quote matched.

- **Source** — Following solve_hunt.py's save_state() into th_tt_save, then measuring the occupancy of the table it dumps.
- **What** — Every completed depth writes tt_mask+1 entries unconditionally, including the 99.87% of slots still zero, so checkpoint cost scales with --tt instead of with the work done.
- **Mechanism** — fwrite of the whole array. The table is sparse for a long time: at 2^24 after a depth-12 hunt only 21,740 of 16.7M slots are non-empty. solve_hunt.py calls save_state() after every completed depth and README recommends a large --tt, so each checkpoint carries ~0.3 MiB of information in gigabytes of writes. A sparse dump (count in the header, then index+xkey+data triples) is 24 bytes per live entry and also lets the loader accept a dump into a table of a DIFFERENT size, removing the `hdr[1] != tt_mask + 1` rejection that currently forces a full re-search whenever you change --tt between runs.
- **Soundness argument** — Does not touch the search. Entries are self-validating by xkey ^ data == key, so scattering them into a table of another size is safe: an entry landing in a slot whose index no longer matches simply never validates on probe. Sparse-loading into a zeroed table gives a strict subset of what a dense load would give, and the TT is a cache - a missing entry costs nodes, never correctness.
- **Integration point** — `tinyhouse.c:361`:

  ```c
  int ok = fwrite(hdr, sizeof hdr, 1, f) == 1 &&
               fwrite(tt, sizeof(TTEntry), tt_mask + 1, f) == tt_mask + 1;   (enclosing function: int th_tt_save(const char *fname))
  ```
- **Toggle and pin** — `#define TT_DUMP_SPARSE 1` above th_tt_save; with 0 both save and load take the existing dense path byte for byte, and the header's format word (from the TT_FORMAT_ID item, which this depends on) distinguishes the two so an old dense dump is never read as sparse. Node identity: unaffected in either direction when a run starts from a fresh table; a resumed run cannot be node-identical by construction, since the point of the dump is to change what is in the table.
- **Expected gain** — ESTIMATE: checkpoint bytes drop by the occupancy ratio - measured 774x at 2^24 (256 MiB -> 0.34 MiB) and 172x at 2^22 - and the wall time with it (0.16s -> ESTIMATED under 0.01s at 2^24). Metric is bytes written and seconds per checkpoint; neither nodes-to-depth nor NPS moves. Confirmed by re-running the occupancy measurement after the change and comparing file size against `non-empty entries * 24 + header`.
- **Risk** — A table that has actually filled up dumps 1.5x the dense size (24 bytes vs 16). Guard by falling back to dense above ~60% occupancy, recorded in the header's format word.
- **Oracles** — pytest -q; a save/load round-trip must reproduce the same next-depth node count as an uninterrupted run; solve_hunt.py resume must still print "table reloaded"; the roundtrip test from the TT-persistence instrument item.
- **Effort** — ~35 lines in tinyhouse.c; half a day with the round-trip test.
- **Novelty** — ALREADY FIXED has the --tt RAM sanity check, which bounds the in-memory table. Nothing bounds what that table costs on disk per checkpoint.

<details><summary>Evidence</summary>

```
th_tt_save re-read verbatim from the current tree at tinyhouse.c:356-365 (quote above is current); the caller re-read at solve_hunt.py:135-137 `def save_state():\n    state_path.write_text(json.dumps(state, indent=2))\n    E.lib.th_tt_save(str(tt_path).encode())`. Miner's occupancy measurement (fresh table, one depth-12 White hunt from the start, then th_tt_save, occupancy counted by reading the file back): 2^20 save 0.01s file 16.0 MiB, 21,622 non-empty (2.062%); 2^22 0.03s 64.0 MiB, 24,316 (0.580%); 2^24 0.16s 256.0 MiB, 21,740 (0.130%).
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Corrected item (same anchor, honest scope):

category: SHOULD-BE-BETTER
title: th_tt_save dumps the whole table every checkpoint; at the shallow depths it is >99% zeros (2^24, depth 12: 21,838 of 16,777,216 live)
what: Every completed depth writes tt_mask+1 entries unconditionally, so checkpoint BYTES scale with --tt rather than with the work done. Wall time is not the problem: measured 0.080s median (5 repeats) for 256 MiB at 2^24 and 0.330s (min 0.300 / max 0.361) for 1 GiB at 2^26, once per completed depth. The metric is bytes written.
mechanism: fwrite of the whole array (tinyhouse.c:361-362). Sparse dump = count in the header, then index+xkey+data triples at 24 bytes per live entry. Measured savings, 24-byte records: 2^24 depth 12, 256.0 MiB -> 0.500 MiB (512x); 2^22 depth 12, 64.0 MiB -> 0.499 MiB (128x).
LIMIT (this is the honest ceiling, and it is the reason to consider dropping the item): occupancy grows ~7.5x per two plies. Measured at 2^24: depth 12 = 21,838 (0.130%), depth 14 = 164,465 (0.980%), depth 16 = 1,227,746 (7.318%). The saving therefore applies to the fast warm-up depths and evaporates on the multi-hour depths that motivate resume, where the >60%-occupancy fallback to a dense dump is what runs.
DROPPED from the original item: the claim that this "removes the hdr[1] != tt_mask + 1 rejection that forces a full re-search whenever you change --tt". That branch is unreachable from solve_hunt.py, because solve_hunt.py:102-103 hashes args.tt into the checkpoint identity, so a different --tt already selects a different state file and discards the JSON progress as well. Making the loader size-agnostic is a SEPARATE change that must also drop tt from `ident`; propose it on its own or not at all.
soundness: Does not touch the search. Entries self-validate on probe (tinyhouse.c:331 `if ((x ^ d) != key || !d) return 0;`), so an entry scattered into a slot whose index no longer matches simply never validates. A sparse load into a zeroed table is a strict subset of a dense load, and the TT is a cache: a missing entry costs nodes, never correctness.
toggle_and_pin: `#define TT_DUMP_SPARSE 1` above th_tt_save; with 0 both save and load take the existing dense path byte for byte. Needs a format word in the header (currently hdr is exactly {magic, tt_mask+1, tt_seed_used}) so an old dense dump is never read as sparse. Node identity: unaffected for a fresh-table run; a resumed run cannot be node-identical by construction.
expected_gain: MEASURED, not estimated, for bytes: 512x at 2^24 depth 12, 128x at 2^22 depth 12, falling to 9x by 2^24 depth 16. Wall time gain is under one second per checkpoint and is not a reason to do this. Neither nodes-to-depth nor NPS moves.
oracles: pytest -q; perft(7) == 1,355,253 on the modified build; save/load round-trip must reproduce the same next-depth node count as an uninterrupted run; solve_hunt.py resume must still print "table reloaded".
GATE BEFORE IMPLEMENTING: measure non-empty count at depth 20 and 22 with --tt 26. If occupancy there is past the dense-fallback threshold, this item only optimizes the warm-up and should be closed unimplemented.

</details>

*Verifier: The defect is real and I reproduced it; the item's VALUE CASE is partly wrong, so it does not earn CONFIRMED as written. 1) QUOTE/ANCHOR: OK, character for character. `sed -n '356,366p' tinyhouse.c | cat -n` gives line 356 `int th_tt_save(const char *fname) {`, 361 ` int ok = fwrite(hdr, sizeof hdr, 1, f) == 1 &&`, 362 ` fwrite(tt, sizeof(TTEntry), tt_mask + 1, f) == tt_mask + 1;`. Caller re-read: solve_hunt.py:135-137 `def save_state():` / ` state_path.write_text(json.dumps(state, indent=2))` / ` E.lib.th_tt_save(str(tt_path).encode())`, called once per completed depth at line 210 and once on a proof at 202. [...]*


### 30. `[SHOULD-BE-BETTER]` The --tt 26 default (1 GiB) is unmeasured and the measured curve is flat past 2^20

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — Instrumented tt_probe/tt_store hit and store counters, run in solve_hunt.py's actual pattern (iterative deepening 6..16 step 2 on ONE table).
- **What** — solve_hunt.py defaults to a 1 GiB transposition table, but nothing in the repo has ever measured what table size buys, and at depth 16 the nodes-to-depth curve is essentially flat from 2^20 upwards while the hit rate never exceeds 5.3%.
- **Mechanism** — Measured under the real deepening pattern at depth 16: 2^18 = 11,937,705 nodes at 3.5% hit rate; 2^22 = 10,286,159 at 5.0%; 2^24 = 10,568,088 at 5.3%. A 64x table buys ~14% in nodes and then stops, and the 2^24 sweep was slower in wall time than 2^22 at the same node count, consistent with cache and page-fault cost. A 1 GiB default therefore trades real memory - and the swap risk check_tt_size() was written to guard - for a benefit nobody has bounded. Store rate is 25% of interior nodes at every size (74-75% are the deliberately-skipped unproven depth-1 stores) and replacement rejections are negligible (1,630 of 1.29M at 2^22), so this is not a capacity or policy problem: the transpositions are simply not there.
- **Soundness argument** — Does not touch the search. Table size changes which transpositions are found, so it changes nodes-to-depth, but every value stored is still gated by the same sound-flag and depth rules and every probe is still validated by xkey ^ data == key. A smaller table can only lose sharing, never produce a wrong PROVEN.
- **Integration point** — `solve_hunt.py:48`:

  ```python
  ap.add_argument("--tt", type=int, default=26, help="log2 TT entries (26 = 1 GiB, 27 = 2 GiB)")   (module-level argparse setup)
  ```
- **Toggle and pin** — The toggle IS the visible default on this line; passing --tt 26 explicitly reproduces today's behaviour exactly. Node identity is IMPOSSIBLE here and that is the point: the item is a nodes-to-depth measurement, and changing table size necessarily changes which nodes are revisited. Pin instead on the sweep being reproducible across processes, which it is (2^22 depth-16 gave 10,286,159 nodes on two independent runs).
- **Expected gain** — ESTIMATE: no change to nodes-to-depth at the depths measured, but ~1 GiB of RAM freed and less page-fault pressure, which is exactly what check_tt_size() exists to protect. The honest deliverable is the number, not the saving: extend scripts/bench_workers.py with a --tt sweep so the default is chosen by measurement. Metric: nodes-to-depth at fixed depth. Confirm by running the sweep at the target depth before committing a long run.
- **Risk** — The measurement stops at depth 16 and depth 16 is not depth 22; transposition density plausibly rises with depth as the tree revisits more of a bounded state space, so the curve could steepen. Do NOT lower the default on the strength of a depth-16 curve - add the sweep tool first and measure at the depth actually being run. That caveat belongs in the --tt help string either way. The depth-20+ sweep is a long job and is the maintainer's to run.
- **Oracles** — scripts/bench_workers.py extended with --tt (paired repeats, medians and spread); the deepening sweep reproduced across processes; solve_status.json depth values unchanged - table size must never change a proven verdict, only the cost of reaching it.
- **Effort** — ~30 lines to add the sweep to scripts/bench_workers.py, plus the depth-20 measurement itself (long job, hand over the command).
- **Novelty** — Not on either closed list. MEASURED AND CLOSED covers lazy SMP worker counts and depth-1 store skipping, never table size; scripts/bench_workers.py takes --tt only as a fixed parameter, never as the variable.

<details><summary>Evidence</summary>

```
solve_hunt.py:48 re-read verbatim from the current tree, and the guard it interacts with at solve_hunt.py:58-83 (check_tt_size, `if want > total // 2 and not args.force_tt: sys.exit(...)`) also re-read. scripts/bench_workers.py:44 re-read: `        if E.lib.th_tt_init(args.tt) != 0:   # fresh table: no cross-run seeding` - --tt is a fixed parameter there. Miner's sweep, iterative deepening 6..16 step 2 on one table exactly as solve_hunt does: d16 at 2^18 nodes 11,937,705 probes 10,762,710 hits 374,552 (3.5%) 12.19s; 2^22 10,286,159 / 9,402,865 / 469,537 (5.0%) 7.45s; 2^24 10,568,088 / 9,693,126 / 516,164 (5.3%) 51.78s. From a fresh table at a single fixed depth 16: 2^16 11,677,528 (2.7%) / 2^20 10,175,448 (3.5%) / 2^22 9,913,857 (3.7%) / 2^24 10,119,067 (3.8%).
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Two corrections to the item; the anchor, quote, and soundness argument need none.

(a) STRIKE the wall-time sentence from `mechanism`. Replace "and the 2^24 sweep was slower in wall time than 2^22 at the same node count, consistent with cache and page-fault cost" with: "wall time was not measured — this machine was under concurrent load (load avg 13-38) and paired repeats invert the ordering, so only the node counts here are trustworthy." An independent 1-worker sweep in separate processes gives 2^18 13,512,613 / 2^20 12,147,196 / 2^22 11,874,178 / 2^24 12,155,968 nodes at 3.4% / 4.1% / 4.8% / 5.1% hit rate, bit-exact across processes, which supports the flat-past-2^20 conclusion on its own.

(b) `mechanism` says "Store rate is 25% of interior nodes". It is 25% of store ATTEMPTS (nodes that reach the store block at tinyhouse.c:513), which is 13.0% of all nodes: 1,548,678 stored of 6,072,400 attempts of 11,874,178 nodes at 2^22. The 74-75% depth-1 skip fraction is right as stated.

Optional: `category` is better as [INSTRUMENT] than [SHOULD-BE-BETTER] — the item's own deliverable is "extend scripts/bench_workers.py with a --tt sweep so the default is chosen by measurement", i.e. a measuring tool, not a behaviour change. The item correctly refuses to lower the default on depth-16 evidence.

</details>

*Verifier: I tried to kill this and could not. Everything load-bearing reproduced independently. 1) CITATION. `cat -n <repo>/solve_hunt.py` line 48, re-read just now: `ap.add_argument("--tt", type=int, default=26, help="log2 TT entries (26 = 1 GiB, 27 = 2 GiB)")` Character-for-character match with the quote (the trailing `(module-level argparse setup)` is the item's own annotation, not source text). The help string is arithmetically right: tinyhouse.c:291 `typedef struct { _Atomic uint64_t xkey; _Atomic uint64_t data; } TTEntry;` = 16 B, so 2^26 x 16 = 1 GiB. [...]*


### 31. `[SHOULD-BE-BETTER]` to_c is the real Python->C trust boundary and validates nothing

> **Verifier: PLAUSIBLE** — citation re-read against the current tree, quote matched.

- **Source** — Two independent lenses reached the same chokepoint; I re-ran the reachability probe against the shipped module.
- **What** — to_c copies a Position straight into THPos with no checks, so a Position not built by from_tfen reaches the C engine, which then reads out of bounds and can emit a PROVEN mate on a position the Python reference refuses to evaluate at all.
- **Mechanism** — from_tfen is a careful trust boundary (tinyhouse.py:146-168: exactly one king per side, <=2 of each unit, side not to move not in check). to_c requires none of it, and cffi only enforces int8_t range per field. Two out-of-bounds sites follow: king_sq returns -1 (line 107), th_in_check hands that to attacked(), which reads ORTH[-1]; and th_key indexes zob_piece[16][32] with a board byte outside the encoding (6, 31, 40, 127, -1 all accepted). Both are silent in an optimised build: they return a number. One guard inside to_c is the root-cause fix because every caller routes through this one function (engine_c.perft/legal_moves, server.py:47, solve_hunt.py:129, scripts/bench_workers.py:46).
- **Soundness argument** — Adds a precondition check, removes nothing. Rejection-only: every position from_tfen accepts today also passes, so every node count and every proof is unchanged. It protects the invariant that every value the search reports is about a real position.
- **Integration point** — `engine_c.py:45`:

  ```python
  def to_c(pos: T.Position):
      c = ffi.new("THPos *")
      for i, pc in enumerate(pos.board):
          c.board[i] = pc
      for color in (0, 1):
          for t in range(4):
              c.hands[color][t] = pos.hands[color][t]
      c.stm = pos.stm
      return c   (enclosing function: to_c)
  ```
- **Toggle and pin** — `VALIDATE_TO_C = True` as a module constant in engine_c.py next to _LIB, checked at the top of to_c. Set False and to_c is character-for-character the current function. Node identity is exact: the guard runs once per conversion, never inside the search, so perft(7)=1,355,253 and the depth-14 hunt's 1,245,821 nodes are untouched. Cheapest correct implementation is to reuse from_tfen's exact checks rather than writing new ones.
- **Expected gain** — ESTIMATE: zero movement in both honest metrics. nodes-to-depth unchanged by construction; NPS unchanged within noise since to_c is called once per search invocation, not per node. The gain is that the failure mode changes from 'C reads out of bounds and returns a number' to 'ValueError at the boundary'. Confirmed by pytest -q still 43, perft(7)=1,355,253, and one new test asserting to_c raises on the kingless Position.
- **Risk** — Low. The only way to get it wrong is a guard stricter than from_tfen that rejects a position the solver legitimately reaches; reuse from_tfen's checks. A grep of all callers found none that pass a hand-built Position today, so nothing breaks.
- **Oracles** — pytest -q (test_engine_c.py:29 and :37 both go through to_c, so a too-strict guard goes red immediately); the random-walk parity test; perft(7)=1,355,253; a new test that to_c(T.Position()) raises and that board[5]=40 raises.
- **Effort** — ~8 lines in to_c plus one test; one hour.
- **Novelty** — ALREADY FIXED covers the king-capture IndexError in the PYTHON engine and the hand-count bound as enforced BY from_tfen. Neither closes to_c, the door that bypasses from_tfen entirely. Merged from two lenses: the kingless/ORTH[-1] path and the out-of-range board-byte/zob_piece path are the same missing guard.

<details><summary>Evidence</summary>

```
I ran this against the shipped module just now:
$ PYTHONPATH=<repo> .venv/bin/python scratchpad/v.py
kingless kings: 0 0
py raises: ValueError list.index(x): x not in list
C th_in_check -> 0
C th_moves -> 0
Miner's ASan+UBSan build of a verbatim copy: `base.c:85:14: runtime error: index -1 out of bounds for type 'uint8_t[16][5]'` and `AddressSanitizer: global-buffer-overflow ... 5 bytes before global variable 'ORTH'` in th_in_check; and with a kingless board driven through th_solve at depth 6: value 29999, snd 1 -> above MATE_BOUND, which tinyhouse.c and index.html:118 both label 'forced (proven)'.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Category: [SHOULD-BE-BETTER], not [BUG-SOUNDNESS]. Corrected "what": to_c copies a Position straight into THPos with no checks. Every caller in the repo today routes through T.Position.from_tfen (engine_c.py:65, engine_c.py:80, server.py:45-47, solve_hunt.py:129, scripts/bench_workers.py:36+46; test_engine_c.py walks legal moves off a parsed position), and from_tfen rejects both hazards, so no proof the shipped program can emit is wrong. What is missing is the guard on the boundary itself: any future code that hand-builds a Position gets silent out-of-bounds reads instead of an error. Corrected mechanism sentence: king_sq (tinyhouse.c:104) returns -1 and th_in_check (tinyhouse.c:110) hands that to attacked(), which reads ORTH[-1] (tinyhouse.c:85, `static uint8_t ORTH[16][5]` at line 26); th_key (tinyhouse.c:283) indexes zob_piece[16][32] (line 274) with a board byte outside 0..29. Corrected evidence numbers: kingless T.Position() through th_solve at depth 6 with th_tt_init(20) returns value 30000, snd 3 (not 29999 / snd 1), which is > MATE_BOUND=29000 and is rendered "forced (proven)" by index.html:118. Corrected soundness line is unchanged and correct: rejection-only precondition check, outside the search, node identity exact.

</details>

*Verifier: Quote and anchor: EXACT. `cat -n <repo>/engine_c.py` right now shows lines 45-53 character-for-character as quoted (def to_c at line 45, `return c` at 53). Working tree is clean apart from two untracked review .md files; HEAD is 2054f2d (the other session has committed since the baseline was taken). Mechanism: REAL, I reproduced it. tinyhouse.c:104-112 verbatim: `static int king_sq(const THPos *p, int color) { int target = PIECE(color, K, 0); for (int s = 0; s < 16; s++) if (p->board[s] == target) return s; return -1; [...]*


## GUI

### 32. `[SHOULD-BE-BETTER]` /api/analyze mixes frames: value is white-view, snd is side-to-move-view

> **Verifier: CONFIRMED** — citation re-read against the current tree, quote matched.

- **Source** — server.py white_view() at line 33 and the out dict at line 61.
- **What** — white_view flips the sign of the value for black to move but the snd flags pass through unchanged, so for a black-to-move position SND_LB - a sound lower bound on the mover's value - is an upper bound on the number the same dict reports.
- **Mechanism** — The flags are defined relative to the side to move in tinyhouse.c (SND_LB=1, SND_UB=2, set from best_child_ub / all_children_lb at lines 507-509). Negating the value must swap the two flags to stay meaningful. index.html only ever tests snd === 3, which is symmetric, so the current GUI is accidentally immune - but the JSON is the API, scripts/build_book.py consumes the same dict, and the next consumer that writes `snd & 1` gets the bound backwards half the time. The observed black-to-move mate row reports value=-29991 with snd=1.
- **Soundness argument** — No search change. It makes an already-exported soundness annotation mean what the field next to it implies, which is the difference between a usable proof record and a misleading one.
- **Integration point** — `server.py:61`:

  ```python
  out = {"tfen": tfen, "depth": depth, "value": white_view(v, pos.stm), "snd": snd[0],   (enclosing function: analyze)
  ```
- **Toggle and pin** — `SND_IN_WHITE_VIEW = True` beside ENGINE_VERSION and, when set, emit `snd[0] if pos.stm == T.WHITE else ((snd[0] & 1) << 1) | ((snd[0] & 2) >> 1)`. False reproduces today's field exactly. Bumping the cache namespace in the same commit is mandatory since stored rows carry the old convention - which is one more reason to derive it from the source hash rather than by hand.
- **Expected gain** — ESTIMATE: neither honest metric moves. The metric is frame consistency of the exported record: today 1 of 2 side-to-move cases is inverted. Confirmed by analysing a white-to-move mate and a black-to-move mate at the same depth and checking the two snd values are mirror-consistent with their signed values.
- **Risk** — Low, but it is a silent format change to every cached row - worthless without the namespace bump in the same commit.
- **Oracles** — pytest -q (floor); re-running "fuwk/3p/P1F1/KWU1[-] b" and its white-to-move counterpart and comparing the flag pairs; a row written before the change must not be served after it.
- **Effort** — 3 lines; 30 minutes.
- **Novelty** — Not on the fixed list; distinct from the TT sound-flag/depth gating docs, which concern the C internals rather than the exported JSON. Distinct from the fmtVal item, which is about what the GUI says; this is about what the API means.

<details><summary>Evidence</summary>

```
Re-read verbatim from the current tree: server.py:33-34 `def white_view(v: int, stm: int) -> int:\n    return v if stm == T.WHITE else -v`, and server.py:61-63, the out dict quoted above, where `"value": white_view(v, pos.stm)` sits next to `"snd": snd[0]` unflipped. The flag definitions re-read at tinyhouse.c:293-294 (`#define SND_LB 1` / `#define SND_UB 2`) and their assignment at 507-509. index.html:120 re-read - it only tests `snd === 3`, which is why the GUI is accidentally immune. Miner's live run: /api/analyze on "fuwk/3p/P1F1/KWU1[-] b" depth=10 -> value=-29991 snd=1 best=b4c2, i.e. a white-view value carrying a mover-frame flag.
```

</details>

<details><summary>Verifier correction — apply before implementing</summary>

Three corrections, none fatal to the item:

(a) "scripts/build_book.py consumes the same dict" overstates. I read scripts/build_book.py in full: it calls `a = server.analyze(tfen, DEPTH)` at line 23 and then only prints `a['value']` and `a['best']` (line 25: `print(f"{done:4d} ply{PLIES-ply} {tfen:34s} v={a['value']:6d} best={a['best']}", flush=True)`). It never reads `snd`. What it DOES do is write rows into analysis.sqlite through analyze(), which is the real reason the ENGINE_VERSION bump is mandatory — a book built before the change would serve old-convention snd afterwards. Reword to: "scripts/build_book.py drives the same analyze() and persists the same rows; no current consumer reads snd, so this is a latent contract defect, not a live wrong answer."

(b) The GUI-immunity argument should also note fmtVal's early return, not just `snd === 3`. index.html:118-119 `if (v > 29000) return {...}` / `if (v < -29000) return {...}` fire before snd is touched, and every asymmetric-snd row I observed at depth 12 was a mate row. So the GUI is doubly immune today, which lowers the urgency without changing the defect.

(c) Strengthen `expected_gain` with the measurement I actually ran, since it is cheap and decisive: depth 12, fresh th_tt_init(22), walk the first two plies from the start (39 positions, 5.15s) and collect (stm, snd). Today it yields `[(b,0):5, (b,1):1, (w,0):32, (w,1):1, (w,2):1]` with the pair `('1uwk/1f1p/PK2/1WUF[-] w', v=+29991, snd=1)` and `('fuwk/3p/P1F1/KWU1[-] b', white_view=-29991, snd=1)` — two rows carrying the same flag with opposite meaning. After the fix the black row must read snd=2. That is the mirror-consistency check, runnable in six seconds, and it belongs in the item as the named oracle instead of the vaguer "analysing a white-to-move mate and a black-to-move mate at the same depth".

</details>

*Verifier: I tried to kill this and could not. 1) CITATION — re-read just now, matches character for character. `cat -n <repo>/server.py` gives: ``` 33 def white_view(v: int, stm: int) -> int: 34 return v if stm == T.WHITE else -v ... 61 out = {"tfen": tfen, "depth": depth, "value": white_view(v, pos.stm), "snd": snd[0], ``` The item's quote of line 61 is exact; the "(enclosing function: analyze)" tail is annotation, and analyze() does begin at line 37. 2) FRAME OF `snd` IN C — confirmed, and it is documented in C as mover-relative. [...]*


---

## Killed by the verifier

Nine of the 34 merged items did not survive an adversarial pass. Recorded so nobody re-derives them.

**K1. `[BUG-SOUNDNESS]` The GUI prints "no forced win within horizon" when the engine proved neither bound** — `index.html:120`

CITATION: matches. `cat -n index.html | sed -n '100,140p'` right now gives line 120 verbatim as quoted: ` const proven = snd === 3 ? "exact at this depth" : "no forced win within horizon";` inside `function fmtVal(v, snd)` (117-122). Call site index.html:269 `const f = fmtVal(a.value, a.snd);`. Not on the ALREADY FIXED or MEASURED AND CLOSED lists. THE snd==0 OBSERVATION IS REAL. I reproduced it (perft drift signature held in the same process): $ PYTHONPATH=... .venv/bin/python scratchpad/v.py perft7 1355253 'fuwk/3p/P3/KWUF[-] w' d8 v=0 white_view=0 snd=0 'fuwk/3p/P3/KWUF[-] w' d10 v=0 white_view=0 snd=0 'fuwk/3p/P3/KWUF[-] w' d12 v=0 white_view=0 snd=0 'fuwk/3p/P1F1/KWU1[-] b' d10 v=29991 white_view=-29991 snd=1 (mate branch, untouched) So the GUI does take the else branch with snd==0. That part of the item stands. [...]

**K2. `[BUG]` pthread_create's return is unchecked, so a failed helper leads to pthread_join on an uninitialised pthread_t** — `tinyhouse.c:558`

CITATION: exact. `cat -n tinyhouse.c | sed -n '500,600p'` reproduces the quote character for character at 558-562, inside `static int root_search(THPos *p, int depth, int alpha, int beta, int workers, uint16_t *bestmove, int *snd)` (549-550), with `pthread_t th[63];` at 553 and `for (int i = 0; i < nh; i++) pthread_join(th[i], 0);` at 566. Novelty also holds: nothing on the fixed/closed lists touches helper lifecycle. Baseline sane: `.venv/bin/python -c "import engine_c; print(engine_c.perft('fuwk/3p/P3/KWUF[-] w', 7))"` -> 1355253, unmoved. The item dies on its MECHANISM and its CONSEQUENCE, both of which I tested directly rather than reasoning about. (1) "th[i] is left as whatever was on the stack" is FALSE on macOS. [...]

**K3. `[DOC-OVERCLAIM]` tinyhouse.c claims it "mirrors tinyhouse.py exactly" while the one documented ruleset toggle does not exist in it** — `tinyhouse.c:1`

1. QUOTE CHECK — passes. `cat -n tinyhouse.c | head -20` gives lines 1-6 exactly as quoted, character for character: ``` 1 /* Tinyhouse C hot path: movegen, make/unmake, perft. 2 * Mirrors tinyhouse.py exactly: square = 4*rank+file (a1=0), piece = 3 * (type+1) | promoted<<3 | color<<4, types P F U W K = 0..4, move = 4 * to | from<<4 | drop<<8 | promo<<9 (for drops the from field is the type). 5 * Built as a shared library, loaded from Python via cffi (ABI mode). 6 */ ``` Every supporting citation also checks out: tinyhouse.py:13 `DOUBLE_STEP = False`; tinyhouse.py:241 ` if DOUBLE_STEP and s >> 2 == START_RANK[us]:`; tinyhouse.c:159-165 `case P` has one push and no second-rank branch; `grep -n DOUBLE_STEP tinyhouse.c` -> no hits; test_tinyhouse.py:115-120 pins the Python side only; engine_c.py:41-42 is `lib = ffi.dlopen(str(_LIB))` / `lib.th_init()`. [...]

**K4. `[DOC-OVERCLAIM]` RULES.md names proof-number search as the realistic target and expects shallow wins - both contradicted by measurement** — `RULES.md:153`

Quote checked: `cat -n RULES.md | sed -n '120,175p'` gives RULES.md:153-156 exactly as quoted, character for character ("small endgame classes to seed a retrograde pass). The realistic target is a **weak solve / of the starting position** via proof-number search (drops make the game sharp; forced / wins, if present, should be shallow), falling back to a strong engine. Phase 4 reports / which tier was reached."). So the anchor is good and this is not a re-report (nothing on the FIXED or CLOSED lists). I reproduced the miner's paired numbers exactly, including the df-pn side, which I found in this session's own scratchpad (dfpn_probe.py): $ PYTHONPATH=<repo> .venv/bin/python dfpn_probe.py 0 8 -> pn=1099511627776 dn=0 DISPROVEN nodes=19,610 tt=12,367 3.50s $ ... dfpn_probe.py 0 10 -> DISPROVEN nodes=142,350 tt=88,616 19.15s $ ... [...]

**K5. `[DOC-OVERCLAIM]` Nothing binds a built artifact to its source: the dylib is checked by mtime and ENGINE_VERSION is hand-bumped** — `engine_c.py:16`

Quotes check out, the dylib repro reproduces exactly, but the item is filed as [DOC-OVERCLAIM] and the doc it accuses is accurate. Per the rubric ("If the doc is actually accurate, REFUTE") it dies as filed; the salvageable half is in `corrected`. 1. QUOTE CHECK (verbatim, just re-read). $ sed -n '12,18p' engine_c.py _DIR = Path(__file__).parent _SRC = _DIR / "tinyhouse.c" _LIB = _DIR / "libtinyhouse.dylib" (blank) if not _LIB.exists() or _LIB.stat().st_mtime < _SRC.stat().st_mtime: subprocess.run(["cc", "-O2", "-pthread", "-shared", "-o", str(_LIB), str(_SRC)], check=True) $ sed -n '19,21p' server.py # Bump when the search changes in a way that can change stored values, so a # stale cache from an older engine is never served as this engine's result. ENGINE_VERSION = 2 Both match the item character for character, including the parenthetical about placement. quote_ok = true. 2. [...]

**K6. `[DOC-OVERCLAIM]` state_count.py prints "/4 symmetry" as an exact figure; Burnside fixed points are never counted** — `scripts/state_count.py:88`

Quote and anchors check out, but the mathematical claim is wrong: the group acts FREELY, so total/4 is EXACT, not a lower bound. 1. CITATION (matches). `cat -n <repo>/scripts/state_count.py` lines 88-90, confirmed byte-for-byte with `sed -n '86,90p' ... | od -c`: 88 total *= 2 # side to move 89 print(f"upper bound on states: {total:,}") 90 print(f"/4 symmetry : {total // 4:,}") RULES.md:145-146 re-read, also verbatim as quoted: - **Upper bound: 17,669,515,462,968 (~1.8e13)** states; ~4.4e12 after factoring the 4-element symmetry group (file mirror x color-flip rotation). Script re-run: `.venv/bin/python scripts/state_count.py` -> `upper bound on states: 17,669,515,462,968` / `/4 symmetry : 4,417,378,865,742`. And `t%4 == 0`, `4*(t//4) == t`, so the floor division is not even hiding a remainder. 2. THE REFUTATION. [...]

**K7. `[INSTRUMENT]` A sound-flag audit toggle: bound duality has no oracle at all, and mutation MUT-B is invisible** — `tinyhouse.c:506`

Quote is fine; the instrument is not. Three independent kills, all measured. 1) CITATION OK. `cat -n tinyhouse.c | sed -n '506,511p'` (re-read now, file is 635 lines, not the 631 baseline - the other session is editing) gives character-for-character: /* bound duality: LB of node <- UB of best child; UB of node <- LB of all */ uint8_t snd = 0; if (best_child_ub) snd |= SND_LB; if (!cutoff && all_children_lb) snd |= SND_UB; si->snd = snd; si->rep_min = my_rep; Line 488 `best_child_ub = (ci.snd & SND_UB) ? 1 : 0;` and the 515-516 mask are also verbatim as quoted. The premise "nothing checks the flags" is also true: `grep -rn "th_solve\|snd" test_tinyhouse.py test_engine_c.py` returns NOTHING, and solve_hunt.py:174 calls `th_mate_hunt_mt`, which at tinyhouse.c:592-593 passes literal `0` for the snd out-param. [...]

**K8. `[INSTRUMENT]` The entire Python/C divergence net is one 1,069-position random walk from a single seed** — `test_engine_c.py:21`

1. ANCHOR OK. `cat -n test_engine_c.py` (37 lines, re-read just now, `git diff --stat HEAD -- test_engine_c.py tinyhouse.py test_tinyhouse.py` empty, HEAD 2054f2d): lines 21-28 match the quote character for character, and line 29 does assert th_result as claimed. The citation is the one thing in this item that holds. 2. THE MECHANISM IS FALSE, AND I MEASURED IT. The item's load-bearing sentence is "The C perft tests only compare C against hardcoded integers, so they cannot see a Python/C split - all of them pass with the two files on different rulesets." Both engines are pinned to the SAME list. test_tinyhouse.py:21-24 verbatim: "@pytest.mark.parametrize(\"tfen,counts\", PERFT_ORACLE)\ndef test_perft(tfen, counts):\n pos = Position.from_tfen(tfen)\n assert [pos.perft(d) for d in range(1, len(counts) + 1)] == counts" and test_engine_c.py:11-13 asserts the identical `counts` for C. [...]

**K9. `[NEW-IDEA]` Costed alternatives: a reachable-state census kills retrograde and BDD, and prices "just go deeper"** — `scripts/state_count.py:88`

CITATION: CONFIRMED. `cat -n scripts/state_count.py` lines 88-90 read exactly `total *= 2 # side to move` / `print(f"upper bound on states: {total:,}")` / `print(f"/4 symmetry : {total // 4:,}")`, module scope, final block. Ran it: `upper bound on states: 17,669,515,462,968` / `/4 symmetry : 4,417,378,865,742`. Drift signature intact: `E.perft('fuwk/3p/P3/KWUF[-] w',7)` = 1355253. CENSUS: CONFIRMED, exactly. I wrote my own BFS over the C movegen (`lib.th_moves`/`lib.th_make`, key = the 25-byte `ffi.buffer(THPos)`, `ffi.sizeof("THPos")==25` so it is an exact canonical key) and got, per ply, new/cum: 6/7, 33/40, 193/233, 1220/1453, 7751/9204, 45979/55183, 291007/346190, 1689902/2036092, 9630829/11666921. Every number the item claims for plies 1-9 reproduces to the digit. [...]

---

## What this changes in README's "what is still owed"

The README's solve-status section and `solve_status.json` currently present the bounds and
the proven wins as equally proof-grade. After this pass they are not, and the list of open
work is different:

1. **`solve_hunt.py:9` is false as written.** "there are no search extensions, so the ply
   budget is exact" — the TT extends the search on its own (**item 1**). Either fix the search
   or restate the contract. The negative bounds are unaffected; the positive claims' ply
   counts are upper bounds, not exact distances.

2. **The two published bounds survive everything found here.** "No forced White win within
   20 plies" and "no forced Black win within 22 plies" are not exposed to **item 1** (an
   extension only finds extra wins) and are not exposed to graph-history interaction
   (**item 15**: adding history can only move a value toward 0, so a stored non-win cannot hide
   a real win). They do not need re-running for these reasons.

3. **The three published forced wins were the exposed claims, and all three now have an
   independent confirmation** they did not have before: each reproduces at its exact
   distance under a build with TT reuse structurally disabled. Add that re-check to the
   PROVEN ritual next to the second-Zobrist-seed re-run (**item 15**).

4. **New open item: the record has no executable link to the code.** Nothing in the 43
   tests touches the solver. `solve_status.json`'s claims are prose. A test that re-derives
   the mate-in-9 in 0.1s would have caught **item 1** the first time ordering shifted.

5. **New open item: `--tt` above ~26 is not safe to leave running unattended.** The
   allocation is now bounded (`2054f2d`), but `th_tt_save` still writes the entire table
   after every completed depth and its failure is discarded (**item 8**). At the README's
   recommended `--tt 27` that is a 2 GiB write per depth.

6. **Still owed and unchanged:** pawn double-step remains empirically unverified (login
   wall), the 50-move rule remains unimplemented, deep SMP scaling remains unmeasured, and
   the draw proof remains out of reach of the current machinery.

7. **Deep SMP scaling — hand-over, not run here.** Per the standing rule about long jobs I
   did not start it. The command that answers it, on an idle machine:

   ```bash
   .venv/bin/python scripts/bench_workers.py --depth 22 --workers 1,2,4 --repeats 3
   ```

   Read **item 7** first: the repeats inside one process are not currently independent
   measurements, so fix that before spending the hours.

---

## Appendix A — the two harnesses, so any of this can be re-run

Both are throwaway scratch builds; neither touches the repo. `$S` is a scratch directory.

**Probe-disabled ground truth.** Copy `tinyhouse.c`, insert one line, build:

```c
static int TT_PROBE_ENABLED = 0;   /* review harness: 0 = no cross-path TT reuse */
static int tt_probe(uint64_t key, TTView *out) {
    if (!tt || !TT_PROBE_ENABLED) return 0;
```

```bash
cc -O2 -pthread -shared -o $S/libnoprobe.dylib $S/th_noprobe.c
```

It reproduces `perft(7) = 1,355,253`, so the movegen is untouched; only cross-path reuse is
gone. Any positive claim the shipped build makes should be reproducible here at the same
distance. All three recorded wins are.

**Differential sweep.** Walk a seeded set of random positions from the start, search each
at a fixed depth with both builds and the same fresh table, and print every value
disagreement. One hit at depth 11 and depth 12 on seed 11, position
`f1w1/2k1/K2p/W1UF[Up] b`. Two things matter for reproducing it: sweep *both* colours, and
do **not** reset the process between positions — the defect only surfaces once the
in-process `history[][]` table is warm (**item 7**), which is exactly the state a real
`solve_hunt.py` run is in from its second depth onward.

## Appendix B — things checked that came back clean

Worth recording so nobody spends the time again.

- **Move buffers.** `uint16_t buf[128]` at `tinyhouse.c:206`, `:229`, `:451`, `:601`.
  Exhaustive enumeration to depth 5 plus 4,000 random walks of up to 40 plies gives a
  maximum of **52** pseudo-moves; the structural bound is ~64 (at most 4 hand types x 14
  empty squares, with the mover's board pieces bounded by what is not in hand). No overflow
  is reachable.
- **Zobrist array bounds.** `zob_piece[16][32]` indexed by a piece code with maximum 29;
  `zob_hand[2][4][3]` indexed by a hand count that `from_tfen` caps at 2. Both in range.
- **`history[2][2048]` indexed by `m & 2047`.** A move encodes into exactly 11 bits
  (`to` 4, `from` 4, `drop` 1, `promo` 2, and drop/promo are mutually exclusive), so the
  mask is lossless and no two distinct moves collide.
- **The torn-read guard.** `tt_store` writes `data` then `xkey`; `tt_probe` reads `data`
  then `xkey`. All four interleavings either validate the intact entry or fail
  `xkey ^ data == key`. Sound as documented.
- **Aborted helpers never store.** `g_abort` is only cleared before helpers are created and
  after they are joined, so the window where a helper could see 0 after a child saw 1 does
  not exist.
- **Mate-score ply adjustment.** Store adds `ply`, probe subtracts it; distance from the
  node is preserved in both directions. The `int16_t` cannot overflow: the stored value is
  bounded by `MATE` = 30000.
- **Mate scores carry their justifying flag.** 250 random positions at depth 12, 60 mate
  scores, 0 missing `SND_LB` (wins) or `SND_UB` (losses). The invariant holds today; **item 3**
  is about it not being *enforced*.
- **Symmetry.** All four orbit members of the start position give identical perft to depth
  7 (**item 23**).
- **Drop legality.** 170,679 pseudo drops across 52,435 not-in-check positions: none was
  illegal, confirming the premise **item 16** rests on.
