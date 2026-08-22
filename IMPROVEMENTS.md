# Tinyhouse — improvement backlog

Merged 2026-08-22 at commit `2054f2d`, from three independent v1 review passes
(archived in `Reviews/`). This file is the live backlog. IDs are permanent:
never renumbered, never reused, and a killed item keeps its ID in the kill list.

## Baseline verified before adjudicating anything

| Fact | Value |
|---|---|
| Test suite | 43 passed |
| Config-drift signature | `perft(7)` from start = **1,355,253** |
| Line counts | `tinyhouse.py` 372 · `tinyhouse.c` 635 · `engine_c.py` 85 · `server.py` 137 · `index.html` 410 · `solve_hunt.py` 211 |
| Commits | 11, HEAD `2054f2d` |
| Proven bound (White) | no forced White win within **20 plies** |
| Proven bound (Black) | no forced Black win within **22 plies** |
| Published forced wins | 3, all re-verified within budget by this merge |

## Reconciliation

```
raw items in  98  =  minted 59  +  folded 35  +  killed 4  +  deferred 0
plus 3 items originated by the merge itself (TH-05, TH-22, TH-44)
total minted 62
```

Contributions: `review_opus-4-8_v1.md` 32 · `review_opus47_v1.md` 34 ·
`review_opus-5_v1.md` 32. All three were complete and followed the required item
format; none was truncated. Each had already self-killed items before submitting
(2, 4 and 9 respectively); those 15 are not counted in the 98 and are not
re-litigated here.

49 clustered claims went to 11 adversarial verifiers whose default verdict was
REFUTED. **Nothing was promoted for being reported more than once.** Three items
were raised by a single report and verified — THB-04, THB-09, THB-11 — and they
rank above several unanimous ones. Twelve claims were materially corrected or
partly refuted by verification; see the kill list and the per-item Verdict lines.

## Doctrine

Carried forward unchanged. These are the rules the project runs on.

1. **Soundness outranks speed.** The entire output of this program is proof
   claims. A change that can emit one wrong PROVEN is rejected regardless of what
   it buys.
2. **Two honest metrics: nodes-to-depth and time-per-node.** Nothing else counts.
   Node counts are load-independent and are the primary metric wherever both are
   available.
3. **There is no Elo instrument in this project** — no opponent, no match harness.
   An item quoting Elo is malformed.
4. **No hidden switches.** Every toggle is a visible in-file constant or `#define`,
   never an environment variable.
5. **Every item names an oracle that fails if it is wrong.** An item with no oracle
   is not ready to implement.
6. **Node identity is the strongest pin available.** Where a change claims to be
   node-identical, that claim is itself the test.
7. **A measurement on one machine at one depth is not a measurement anywhere else.**
   Say the machine, the depth, the repeat count and the load.

---

# P0 — soundness

## THB-01 · [BUG-SOUNDNESS] A TT cutoff at a horizon node breaks the ply-budget contract: a depth-N hunt can report a win of distance > N

- **Verdict**: **CONFIRMED — reproduced by the merge directly**, not taken from a report.
- **Raised by**: `opus-5` only (item 1). A single-report finding that verified; the
  other two passes missed it entirely.
- **Mechanism**: the TT cutoff block at `tinyhouse.c:438-448` executes *before* the
  horizon branch at `tinyhouse.c:455`. The cutoffs are gated on
  `tv.depth >= depth`, and `tv.depth` is a `uint8_t`, so once `depth <= 0` that
  comparison is unconditionally true. Any stored mate score is therefore handed
  back at a node with zero remaining budget, and the ply adjustment faithfully
  re-bases its distance — producing a mate distance attached to a depth that does
  not contain it.
- **Reproduction** (each depth in its own fresh process, `th_tt_init(22)`,
  1 worker, position `f1w1/2k1/K2p/W1UF[Up] b`, hunting Black):

  | depth | returned | meaning |
  |---|---|---|
  | 11 | 0 | no win within 11 |
  | **12** | **29985** | **"mate in 15" — from a 12-ply budget** |
  | 13 | 29987 | mate in 13 (the true distance) |

  Depth 11 finds nothing and depth 13 finds 13, so the true distance is 13 and the
  honest depth-12 answer is "no win within 12". The engine reports mate in 15:
  **wrong verdict and wrong distance.**
- **Correction to the source report**: `opus-5` states this "surfaces only when the
  in-process `history[][]` table is warm". The opposite holds. A cold process fires
  it; running depth 11 first in the same process makes depth 12 return 0 correctly.
  This matters: `solve_hunt.py` deepens iteratively in one process, so the
  published-bounds path is the warm one. The bounds escaped by luck, not design.
- **Impact on the record — checked, not assumed**: the defect is directional. A TT
  cutoff is gated on `tv.depth >= depth || tv.sound & ...`, so a reused value is
  either from a search at least as deep or is a genuinely sound bound. It can only
  make the search *better* informed, so it can add wins and never conceal one.
  Therefore:
  - **Both negative bounds stand unqualified.** No forced White win within 20
    plies, no forced Black win within 22 plies.
  - **All three published forced wins are within budget** — re-verified by this
    merge: mate in 9 first proven at depth 9, and both mate-in-13 claims first
    proven at depth 13.
- **Soundness audit**: the fix only ever *removes* cutoffs, so it cannot introduce a
  value the plain search would not produce. Horizon unsoundness, bound duality, the
  rep-safety store gate, the ply adjustment and `xkey ^ data == key` are all
  untouched.
- **Integration point**: `tinyhouse.c:438`, `if (ply > 0) {`.
- **Toggle and pin**: two one-line forms, both reported as built and measured:
  **H** `if (ply > 0 && depth > 0) {` refuses every horizon cutoff; **M** additionally
  refuses an interior cutoff whose mate distance exceeds the remaining depth. Both
  are a single added conjunct, so toggling off is exactly node-identical.
- **Expected gain**: not a speed change. Reported node cost is within ±5% with an
  unstable sign; **UNMEASURED by this merge**.
- **Oracles**: `pytest -q` (43); `perft(7) = 1,355,253`; all three recorded wins
  must still prove at their exact distances; the depth-12 repro above must return 0.
- **Effort**: one line plus the doc edits it forces (TH-01, TH-02).

---

# [BUG]

## THB-02 · from_tfen accepts a promoted KING, smuggling a second king past both count guards

- **Verdict**: CONFIRMED (parse and solver output both reproduced).
- **Raised by**: `opus-4-8` (S1), `opus47` (001).
- **Mechanism**: `tinyhouse.py:130` applies the `~` marker to any piece type. The
  king-count guard counts `piece(color, K)` with `promoted=False`, and the
  unit-count loop skips `ptype(pc) == K`, so a `K~` (board value 13) is invisible to
  **both**. `KK~2/4/4/3k[-] w` parses with two white kings and round-trips unchanged.
- **Evidence**: `th_solve` returns `v=29995, snd=1` at depths 6/8/10 — above
  `MATE_BOUND`, with the flag the code treats as a proof. An independent pure-Python
  negamax agrees, so the search is not misevaluating; the parser is admitting a
  position outside the game. Reachable through `server.py` from raw HTTP.
- **Correction — the promoted-PAWN half of the source claims is REFUTED**:
  `tinyhouse.py:155` buckets a promoted piece under `P`, so `P~` *is* counted
  correctly and is not invisible. Only the promoted king evades. A *lone* promoted
  king is also correctly rejected ("needs exactly one white king"), so the
  `king_sq == -1` path is not reachable this way.
- **Second-order**: capturing a promoted king pushes a hand count to 3, which
  `th_key` reads at `zob_hand[c][0][3]`, one past the declared dimension. Verified
  *not* to produce a key collision (the aliased entries cancel), so this is a latent
  out-of-dimension read, not a demonstrated wrong result.
- **Fix**: reject `~` on any type outside `(F, U, W)` at `tinyhouse.py:130`.
- **Oracles**: `pytest -q` plus new rejection cases; `perft(7)` unchanged (the guard
  never fires on a legal input).
- **Effort**: 2 lines.

## THB-03 · from_tfen accepts a pawn on rank 1 or rank 4, either colour

- **Verdict**: CONFIRMED, and **wider than any single report claimed**.
- **Raised by**: `opus-4-8` (B1, own-promotion-rank only), `opus-5` (11, plus
  promoted pawn). Neither covered all four cases.
- **Mechanism**: the parse loop checks file overflow, characters and file coverage;
  the post-loop block checks unit counts, king counts and side-not-to-move-in-check.
  Pawn placement is never checked. The only pawn-rank rule in the codebase is the
  *drop* restriction at `tinyhouse.py:273` and its C mirror.
- **Evidence** — all four accepted and round-tripping:
  `P3/4/4/K2k[-] w`, `3k/4/4/K2p[-] b`, `3p/4/4/K2k[-] b`, `3k/4/4/P2K[-] w`.
- **Correction**: the two families are illegal for *different* reasons, and only one
  is immobile. On its own promotion rank the pawn is completely stuck (`pawn_moves=[]`)
  because promotion is forced; on the mirror rank it plays on normally (`d4d3`). A
  report describing all four as immobile would be wrong.
- **Fix**: mirror the drop predicate — reject `ptype(pc) == P and (sq >> 2) in (0, 3)`,
  plus `ppromoted(pc)` for a "promoted pawn".
- **Oracles**: `pytest -q` plus three new rejection cases; all five `PERFT_ORACLE`
  round-trips green; `perft(7)` unchanged.
- **Effort**: ~4 lines.

## THB-04 · make()/unmake() write `hands[us][4]` on a king capture, and no sanitizer can see it

- **Verdict**: CONFIRMED. **Single-report finding (`opus-5` 5) that verified.**
- **Mechanism**: `tinyhouse.c:127` does `p->hands[us][TYPE(cap)]++` and `TYPE(K)==4`,
  but `hands` is `int8_t[2][4]` inside
  `{ int8_t board[16]; int8_t hands[2][4]; int8_t stm; }`. Measured layout:
  `&hands[0][4] == &hands[1][0]` and `&hands[1][4] == &stm`, with no padding — so the
  aliasing is deterministic. Because it is an *intra-object* overwrite, ASan tracks
  object boundaries and stays silent.
- **Evidence**: with Black to move and able to capture the white king, `th_moves`
  alone returns having left the caller's `stm` flipped from 1 to 0 — `unmake` restores
  `stm` at `:136` and *then* decrements the alias at `:146`. Paired perft on a
  white-capturer position: buggy `perft(2)=13` vs guarded `perft(2)=5`, the 8 extra
  nodes being phantom black pawn drops off the aliased slot. Both builds give
  `perft(7)=1,355,253` on the start position, so the guard is a no-op on legal input.
- **Correction**: "enumerating moves corrupts the caller's THPos" is true only for the
  **black**-capturer direction; for white the struct is byte-identical on return but
  the fabricated hand count is live *inside* the make/unmake window, so the recursion
  sees it. Cite `:146` alongside `:127` — `:146` is the half that survives the call.
- **Fix**: `if (cap && TYPE(cap) != K)` at `:127` **and** the mirror at `:146`, in the
  same commit.
- **Oracles**: `perft(7) = 1,355,253`; `PERFT_ORACLE`; a C driver asserting the hand
  array is unchanged after `th_moves` on a king-capturable position.
- **Effort**: 2 lines plus a driver test.

## THB-05 · `to_c` is the real Python→C trust boundary and validates nothing

- **Verdict**: CONFIRMED. Single-report finding (`opus-5` 31) that verified.
- **Mechanism**: `engine_c.py:45` copies a `Position` straight into `THPos`. Every
  guard lives in `from_tfen`; a hand-built `Position` bypasses all of them.
- **Evidence**: a kingless hand-built position reaches `th_solve` and returns
  `value=-29998, snd=3` at depths 2-6. `snd=3` is `SND_LB|SND_UB` — the code's own
  definition of an **exact, proven** game value. So the engine emits a fabricated
  mate proof computed off out-of-bounds reads. Sanitizers *do* fire here (unlike
  THB-04): `tinyhouse.c:85` reads `ORTH[-1]`.
- **Correction**: state it as `|v| >= MATE_BOUND`, not "above MATE_BOUND" — the
  headline case is a claimed forced *loss* (-29998); a positive +29999 occurs on the
  black-kingless variant. The read at `:85` is only the entry point: the values read
  are then used as board indices, so the blast radius is build- and
  stack-layout-dependent, not a stable constant.
- **Reachability**: **latent trap only.** Every current caller routes through
  `from_tfen`. This is the root-cause fix location for THB-04 and THB-06.
- **Fix**: reuse `from_tfen`'s checks behind a visible `VALIDATE_TO_C = True`.
- **Oracles**: `pytest -q`; `perft(7)`; a new test that `to_c(T.Position())` raises.

## THB-06 · `str_move('K@a1')` fabricates a king drop that corrupts `THPos`

- **Verdict**: CONFIRMED. Single-report finding (`opus-5` 6) that verified.
- **Mechanism**: `TYPE_CHARS.index('K')` yields drop type 4 with no range check; C
  `make` does `p->hands[us][M_FROM(m)]--` with `M_FROM == 4`, hitting the same alias
  as THB-04.
- **Evidence**: from the start position, `hands` goes
  `[[0,0,0,0],[0,0,0,0]] → [[0,0,0,0],[-1,0,0,0]]`, and a **second white king**
  materialises on the target square. `th_key` then reads `zob_hand[...][-1]`,
  poisoning TT keys. The corruption is invisible to a `tfen()` round-trip because
  `"P" * -1 == ""`.
- **Correction**: the `'a1b2=K'` half is **not** a memory bug — `M_PROMO` masks with
  `& 3`, so promo 4 silently becomes 0 and the move degrades to a plain `a1b2`. That
  is a silent-downgrade parsing defect, a different and much lower severity. Do not
  bucket the two together. Corruption also only occurs with White to move; for Black
  the aliased write lands on `stm` and is clobbered one line later.
- **Reachability**: latent trap. No shipped caller passes untrusted strings to
  `str_move`; only the test suite uses it, with well-formed input.

## THB-07 · A `.tt` dump carries no identity of the code that produced it

- **Verdict**: CONFIRMED. Single-report finding (`opus-5` 2) that verified.
- **Mechanism**: the header at `tinyhouse.c:361` is `{magic, entry count, Zobrist
  seed}`. Nothing identifies the rules, the flag semantics or the bit layout, and
  `th_key` depends only on (board, hands, stm, seed) — all of which survive a rules
  change unchanged.
- **Evidence**: a scratch build with a genuinely different rule (`case F:` iterating
  `KINGN`, so a ferz moves like a king — `perft(1..4) = 7/43/362/3408` vs stock
  `6/33/241/1855`) wrote a dump that the **stock** build loaded with `rc = 0`,
  installing 3,659 foreign-rule entries silently.
- **Correction — the hole is wider than the report says**: the format authenticates
  nothing at all, so a hand-written file is accepted and can produce a false proof.
  The header does not even identify the position, colour or search parameters; only
  `solve_hunt.py`'s filename hash ties a dump to a run, and that lives *outside* the
  file, so a renamed or copied `.tt` is accepted.
- **Credit where due**: after a win, `solve_hunt.py:204-207` prints a second-seed
  re-verification command with `--fresh`, which discards the table — a run that
  follows that advice cannot be fooled.
- **Fix**: a build fingerprint as `hdr[3]`, derived from the source (hash
  `tinyhouse.c` at build time), mirrored into `solve_hunt.py`'s checkpoint identity.
  A hand-maintained `TT_FORMAT_ID` constant is **not** sufficient — nobody bumps a
  format id when editing `pseudo_moves`.
- **Also fix the comment** at `tinyhouse.c:350-353`: entries are self-validating
  against *corruption*, which says nothing about *provenance*.

## THB-08 · `save_state()` discards `th_tt_save`'s return, and the save destroys the previous checkpoint on open

- **Verdict**: CONFIRMED, with a **more damaging failure mode found during
  verification** than the report described.
- **Raised by**: `opus-5` (8).
- **Evidence**: with a directory placed at the `.tt` path, `solve_hunt.py` printed
  `=> no forced WHITE win within 6 plies (proven, checkpointed)` and exited 0 with
  nothing written. The docstring promises "an interrupted run costs at most the depth
  it died in" and the SIGINT handler prints "checkpoint is current", neither of which
  consults the return value.
- **New (merge-verified)**: `th_tt_save` opens the **live** checkpoint with
  `fopen(fname, "wb")` at `tinyhouse.c:358`, truncating it before a byte is written,
  and nothing restores it on failure. Demonstrated: a 268 MB dump overwritten by a
  2^18 table became 4 MB, and reloading at 2^24 returned `-2` — the previous good
  dump is unrecoverable from the moment the new save starts.
- **Fix**: write to `fname + ".tmp"` then `rename`. One line, and it closes both this
  and the truncated-file arm of THB-09's sibling behaviour.
- **Also**: the code never `fsync`s, so a crash right after a "checkpointed" line can
  still lose the dump.

## THB-09 · The sqlite cache row is a function of live TT state, not of its key

- **Verdict**: CONFIRMED. Single-report finding (`opus-5` 9) that verified.
- **Mechanism**: `analyze()` keys rows on `(tfen, depth, ENGINE_VERSION)`, but
  `th_solve` probes a table earlier requests filled, and the probe cuts on a proven
  entry regardless of depth.
- **Evidence** (real `server.py` on a scratch port, fresh DB each time): depth 14
  first → `value=-29991, snd=1, nodes=6060143`. Then depth 6 on the same server →
  `value=-29991, snd=1, **nodes=15**`. Fifteen nodes cannot prove a mate at distance
  9. The depth-6 row is permanently stored with the depth-14 answer, and a later
  honest cold depth-6 request can never be served for that key again.
- **Correction**: the served value is **not wrong** — the entry is a genuine proof.
  The defect is the label and the pinning, plus the fact that the API is
  history-dependent: the same request returns different answers depending on what
  preceded it, and that nondeterminism is then frozen into the cache.
- **Fix**: `CACHE_ONLY_PROVEN = True` guarding the INSERT, and/or stop storing
  `nodes`/`time`/`depth` provenance that describes a search that did not happen.
  Name the cost in the comment: unproven positions then recompute every request, so
  `scripts/build_book.py` only stays useful for proven positions.

## THB-10 · `/api/analyze` clamps depth above but not below

- **Verdict**: CONFIRMED. Raised by all three (`opus-4-8` B4, `opus47` 005,
  `opus-5` 12) — noted, but promoted on the reproduction, not the count.
- **Mechanism**: `server.py:123` is `min(int(q.get("depth", 12)), 22)` with no floor.
- **Evidence**: cold server, `depth=0` → `best: None`, every move 0, `nodes: 8`.
  After a depth-14 request on the same position, `depth=0` → `best: "b4c2"` and the
  moves array carries `-29991`, all under `"depth": 0`. `depth=-5` behaves the same,
  so negative depths reach the engine.
- **Correction to `opus-5`**: it claims the top-level `value` shows a mate score. It
  does not — the root skips the TT cutoff (`ply > 0` at `:438`), so the headline
  value stays 0. The mate appears only inside `moves`. The result is arguably worse
  than claimed: the payload is **self-contradictory**, a headline "0.00 / no forced
  win within horizon" sitting directly above a move listed as "Black wins in 9".
- **Fix**: `max(1, min(..., 22))`, plus a `DELETE` of any existing `depth < 1` rows.

## THB-11 · One abandoned `/api/analyze` request pins `ENGINE_LOCK`

- **Verdict**: CONFIRMED. Single-report finding (`opus-5` 13) that verified.
- **Evidence**: idle baseline for a trivial `depth=2` request is 0.13s. After a
  `depth=14` request abandoned at 2s by the client, the next trivial request took
  **11.36s**, and an independent run gave **87.72s**. The abandoned handler runs to
  completion and only then dies on `BrokenPipeError`.
- **Correction**: it does **not** block "every later request". `/api/position`,
  `/api/status`, `/` and `/pieces/` never touch the lock (measured 0.09s while a
  depth-14 search held it), and cache *hits* return before the lock. Only
  `/api/analyze` cache misses block.
- **Additionally (merge-verified)**: the abandoned search still writes its row and
  pollutes the TT, and `index.html:395` wires `$("depth").onchange = analyze`, so
  dragging the depth selector queues one full search per intermediate value —
  `analyzeSeq` discards the stale *response* but never stops the *work*.
- **Fix**: a visible `MAX_GUI_DEPTH`, plus `ENGINE_LOCK.acquire(timeout=...)`
  returning 503.

## THB-12 · GUI history is corrupted by a second click before `load()` resolves

- **Verdict**: CONFIRMED. Single-report finding (`opus47` 003) that verified, against
  code that was patched *after* the report was written.
- **Evidence**: the verifier sliced `index.html:239-247` and `:284-301` verbatim and
  ran them against a live server. Clicking `a2a3` then `d1c2` without awaiting gives
  `hist[2]` derived from the **pre-first-click** position, with the wrong side to
  move, recording a move that is not even legal after `a2a3`.
- **Correction — the existing guards do not close it**: the `if (!next) return;`
  guard at `index.html:241` checks the move against the *stale* map, i.e. against the
  wrong position, so it only rejects strings absent from the pre-click position. The
  `loadSeq` guard fixes a real but *different* bug (it keeps the displayed board
  matching `hist[histAt]`). Net: the corrupt entry is plainly visible in the history
  strip — "only masks it" is too generous.
- **Also under-reported**: the same move clicked twice corrupts too, and the trigger
  is not only board clicks — the moves table keeps live onclick handlers.
- **Soundness**: client-side only. The search always runs on the TFEN the server
  received; no proof is affected.

## THB-13 · Setup mode silently strips the promoted flag, changing which game is analysed

- **Verdict**: CONFIRMED, and **elevated from the reporter's "GUI-only" framing**.
- **Raised by**: `opus47` (034), filed as `[SHOULD-BE-BETTER]`.
- **Why it is a bug, not a nicety**: a captured promoted piece returns to hand as a
  **pawn**. Verified end to end: from `K3/4/2k1/2F~1[-] b`, `c2c1` yields
  `...[p] w`; from `K3/4/2k1/2F1[-] b` the same move yields `...[f] w`. Different
  position, different game tree, measurably different node counts.
- **Mechanism**: `setupPlace` writes `promoted=false` unconditionally, so clicking an
  existing promoted square with any palette piece silently discards the flag with no
  visual warning.
- **Correction**: setup mode *does* preserve an existing promoted piece (entry never
  resets `state.board`, and `buildTfen` re-emits the `~`). "Cannot represent" would
  be overstated; "cannot add one, and silently destroys one" is exact.

## THB-14 · The dylib rebuild trigger ignores the compile flags

- **Verdict**: CONFIRMED for the flags half; **the cdef half is REFUTED as filed.**
- **Raised by**: `opus-4-8` (B2), `opus47` (031).
- **Correction**: a `ffi.cdef` edit is Python-side and needs no rebuild *by
  construction*, so "editing the cdef does not trigger a rebuild" is a category
  error, not a defect. These are two independent issues and only the flags half is a
  staleness bug in `engine_c.py:16`. Measured: the dylib hash was unchanged across a
  `touch engine_c.py` **and** across an `-O2 → -O0 -DTH_POISON` flag edit.
- **Where the real exposure is (merge-verified)**: a struct-layout cdef error *is*
  caught today by the existing perft tests, but a wrong **signature** is not. With a
  deliberately swapped `th_mate_hunt` cdef, the suite stayed **43 green** while the
  function returned 0 instead of 29985. See TH-22.
- **Scope note**: the dylib is gitignored, so this is per-developer-machine only.

## THB-15 · `DOUBLE_STEP` has no C counterpart, and `server.py` drives both engines at once

- **Verdict**: CONFIRMED as a divergence; **the "silent" characterisation is REFUTED**.
- **Raised by**: `opus-4-8` (B3), `opus47` (002).
- **Evidence**: Python with the flag on gives `[6, 36, 274, 2181, 19317]`; C gives
  `[6, 33, 241, 1855, 16021]` — diverging at depth 2.
- **Correction**: "no test can catch a flip" is **false**. The constant is
  module-level, so flipping it is global at import and the suite goes **4-red**
  (39 passed, 4 failed). The desync is loud. Downgrade severity accordingly.
- **The sharper hazard, found in verification and in none of the reports**:
  `server.py` drives **both** engines in one process — `position_info` enumerates the
  GUI's legal move list from the **Python** generator, while `analyze` evaluates with
  the **C** engine. With the flag flipped the GUI would offer `a2a4=W` and then get
  an evaluation from an engine whose ruleset has no such move.
- **Fix**: an import-time assert in `engine_c.py`, and a note that the mixed-ruleset
  server path is the reason it matters.

---

# [DOC-OVERCLAIM]

## TH-01 · `solve_hunt.py:9` "there are no search extensions, so the ply budget is exact" is false

- **Verdict**: CONFIRMED. Follows directly from THB-01.
- **Correction to apply**: the negative half survives — a TT cutoff is gated on
  `tv.depth >= depth || tv.sound`, so reuse is only ever better-informed and cannot
  manufacture a false negative. And the mate itself is **still a proof**. Only the
  *distance bound* fails. Correct wording: "anything else proves there is no forced
  win within d plies; a reported mate distance, however, may exceed d, because a TT
  cutoff can return a value proven by a deeper search before the horizon check is
  reached."
- **Effort**: two sentences, or free if THB-01 lands first.

## TH-02 · Three documents sell one proof grade for two claim strengths

- **Verdict**: CONFIRMED. Raised by `opus-5` (15) and `opus-4-8` (D1).
- **Sites, all verified verbatim at these lines**: `README.md:54-57`;
  `solve_status.json:16`; and under-counted by the reports — `tinyhouse.c:587-589`
  and `index.html:118-119` restate the same undistinguished grade, and
  `solve_status.json` uses the single word "proven" as the key name for **both**
  categories (`proven_bounds`, `proven_wins_found`).
- **Correction to both directions**: "exposed to the TT-extension defect" overstates
  the positive side — the defect makes "within N plies" false, not the proof false.
  And the negative bounds are **not literally unconditional**: they are immune to
  horizon unsoundness, to the TT extension and to store-side GHI, but they carry the
  Zobrist-collision residual (TH-06).
- **Effort**: ~15 lines across four files.

## TH-03 · `tinyhouse.c:256` claims rep-safety "keeps the graph-history interaction problem out"

- **Verdict**: CONFIRMED overclaim. Raised by `opus-4-8` (D1/S3) and `opus-5` (4).
- **Why it matters**: `README.md:57` points readers at this block as the authority.
- **Audit result**: rep-safety governs the **store** side — it prevents a
  path-dependent value from entering the table. The **reuse** side is unguarded: the
  probe at `:432-448` applies no path condition, and nothing in `TTView` records
  which path an entry came from. Accurate phrasing: "rep-safety keeps path-dependent
  values *out of the table*".
- **Two mitigations the reports do not credit**: the path-repetition scan at
  `:425-426` runs **before** the probe at `:432`, so a node that itself repeats a
  current-path ancestor can never take a stored decisive value — the most direct GHI
  case is already closed. And the residual is one-directional, landing on the
  **positive** side (a possible over-claimed win), never a fabricated "no win".
- **Also worth stating**: the immunity is relative to the engine's own model. Under
  real threefold rules a winning strategy may legally pass through a once-repeated
  position; the engine scores that as a draw, so its negative results are
  *conservative* with respect to threefold, not identical to it.
- **Cheap mitigation**: replay each published proof PV from the root and check it is
  repetition-free. Not more search.

## TH-04 · The `PERFT_ORACLE` docstring overclaims its provenance

- **Verdict**: CONFIRMED, and **the merge concurs from first-hand knowledge** — this
  docstring was written in the authoring session and the enumeration it describes did
  not happen.
- **Raised by**: `opus47` (007) only.
- **Three distinct defects**, not one: (a) "all 33 nodes enumerated manually" — no
  artifact, test or comment anywhere enumerates them; `test_start_moves` pins only
  the six depth-1 moves. (b) "three independent implementations" — the repo contains
  two, and `tinyhouse.c:2` declares itself a mirror of `tinyhouse.py`; the three
  from-spec implementations were real but were three models of one family working
  from one document, and none is in the tree. (c) Scope: the provenance sentence
  reads as covering the whole oracle, but `perft(6)` and `perft(7)` in
  `test_engine_c.py` have no stated provenance at all.
- **Not wrong**: every oracle number itself.

## TH-05 · `solve_status.json` records "single thread" but the tool defaults to 2 workers and the README omits `--workers 1`

- **Verdict**: CONFIRMED. **Originated by this merge** (found by the docs verifier's
  open-ended audit; in none of the three reports).
- **Mechanism**: `solve_status.json` records `"method": "null-window mate hunt,
  single thread"` and `"machine": "... single thread"`, but `solve_hunt.py:46`
  defaults `--workers` to 2, and `README.md:65,68` give the reproduction commands
  with no `--workers 1`. Confirmed by git order: the `default=2` commit (`7b3b902`)
  predates the file that records "single thread" (`2125a70`).
- **Why this is the doc item that matters**: together with the missing deepening
  schedule, it means **the two headline bounds cannot be re-derived, or even re-run,
  under the same conditions from what the repo records** — and the one condition it
  does record contradicts the command it tells you to use.
- **Fix**: put `--workers 1` in the README commands, or correct the recorded method;
  and record the deepening schedule, since a cold single-depth run gives a different
  node count than the iteratively-deepened slice (a re-run reported +3.4%).

## TH-06 · The negative bounds need the second-seed re-verification too

- **Verdict**: CONFIRMED — the collision argument is sound and is **not** covered by
  the other two immunity arguments.
- **Raised by**: `opus47` (006) only.
- **Why it survives**: the horizon-unsoundness and TT-extension arguments are both
  *directional*. A 64-bit key collision has **no** directional structure: it
  substitutes an unrelated position's value. In the hunt window a colliding
  `TT_UPPER` entry with `v <= alpha` satisfies `:445`, pruning a subtree that may
  contain a real mate and yielding a false negative.
- **Risk is higher for negatives than positives**, on two counts: the negative runs
  are the high-node-count ones, and *any* low-valued colliding entry suffices,
  whereas a false positive needs a collision that happens to hold a mate score.
- **Caveat to carry**: the verifier's truncated-key demonstration proves the
  *mechanism*, not the probability — it forces collisions far above the real rate.
  The published bounds are likely fine; the residual is unquantified.
- **Fix**: `solve_hunt.py:204` offers the second-seed prompt only inside
  `if v > 29000:`. Extend it to the negative branch at `:211`.

## TH-07 · The `from_tfen` comment says each unit "exists exactly twice"; the code only rejects counts above 2

- **Verdict**: PLAUSIBLE — real mismatch, but the **doc** is what should change.
- **Raised by**: `opus-4-8` (D2). Citation drifted: the phrase is at
  `tinyhouse.py:147`, not `:146`.
- **Measured**: of the TFEN literals in the repo, 6 are full and **10 are under-full**,
  including most of the rules suite. Enforcing `n != 2` would reject them.
- **Fix**: soften the comment to "at most twice".

---

# [EFFICIENCY] — nodes-to-depth

## TH-13 · Credit the symmetric `SND_LB` in mate-distance pruning

- **Verdict**: CONFIRMED sound, and **measured to be nearly worthless**.
- **Raised by**: `opus-4-8` (E1), `opus47` (028).
- **Correction to both framings**: the reports ask whether the branch can ever fire.
  It fires constantly — and the item is still marginal. Paired over 200 positions at
  depth 8 with fresh TT and identical seeds: **3,136,715 nodes on both builds**,
  **2 of 200** root flags upgraded, **0** value changes.
- **Why so small**: the upgrade only reaches nodes that already found a mate-in-1
  whose pruned siblings blocked `all_children_lb`. A mate-in-1 already reuses via the
  `TT_LOWER` path at `:442`.
- **Verdict for the roadmap**: a one-line commit for flag tightness. Not a soundness
  narrative.
- **Integration point**: `tinyhouse.c:422`.

## TH-17 · Enemy-king-proximity bonus for quiet drops in move ordering

- **Verdict**: PLAUSIBLE. **UNMEASURED.**
- **Raised by**: `opus-4-8` (E2) only.
- **Settling command**: paired single-thread `th_mate_hunt` at fixed depth on the
  `1.Fd1-c2` line, weight 0 vs tuned, **separate processes** (see TH-19).

---

# [NPS] — time per node

All four measured items below are **node-identical**; that identity is the pin.
Machine for every figure: Apple M2 Pro (10 cores, 16 GiB, Darwin 25.5.0) under
variable load; child-process CPU-time medians over interleaved A/B repeats.

**The reports' ranking was wrong and is corrected here.** `opus-5` claims its
incremental-key item is "the ONLY NPS item measured to help the actual proof
search". Verification refutes that: on the same node-pinned depth-12 mate hunt,
the horizon fast path gives **1.104x** and the drop-mask gives **1.087x**, both
beating the incremental key's 1.033-1.074x.

| ID | Change | perft | real search | node-identical |
|---|---|---|---|---|
| TH-08 | horizon fast path | — | **1.104x** hunt d12 · **1.124x** solve d14 · **1.210x** drop-heavy | yes |
| TH-09 | drop empty-square mask | 1.071x | **1.087x** hunt d12 · 1.063x solve d14 | yes |
| TH-10 | incremental Zobrist key | **0.955x** (slower) | 1.033-1.074x hunt d12 · 1.051x solve d14 | yes |
| TH-11 | fast legality (no sliders) | **1.391x** start · **2.193x** drop-heavy | 0.985-0.999x (neutral/slight loss) | yes |
| TH-12 | king_sq hoist | 1.05-1.09x · 1.144x at perft(8) | unmeasured | yes |

## TH-08 · Answer the horizon's one yes/no question without building the full move list

- **Verdict**: CONFIRMED. **Largest search win of the four.** Raised by `opus-5` (17)
  and `opus47` (014).
- **Mechanism**: `pseudo_moves` runs at `tinyhouse.c:452`, *before* the `depth <= 0`
  branch at `:455`, so the horizon pays for the whole list and then walks it until
  the first legal move. A drop can never expose the mover's own king, so when the
  mover is not in check and holds any piece with a legal empty target, a legal move
  exists.
- **Correction**: "cuts pseudo_moves **calls** by 14-59%" is **wrong**. Call count is
  not reduced at all — every horizon node still calls a generator, just one that
  exits early. What is cut is generated-move **volume**: 38.4-76.0% of all moves
  generated (39.4% on the real hunt). The horizon fraction is 33.7-43.2% of search
  entries (76.7% drop-heavy), not the reported 37-42%.
- **Oracles**: `perft(7) = 1,355,253`; toggle-off node identity at d14/d16; `pytest -q`.

## TH-09 · Generate drops from a precomputed empty-square set

- **Verdict**: CONFIRMED. Raised by all three (`opus-4-8` N6, `opus47` 015,
  `opus-5` 19).
- **Correction**: the range given (1.05-1.07x) is right for perft but
  **under-inclusive for search** — measured 1.063x and 1.087x on the two real search
  workloads. The reported "keep the empty-hand early exit" trap is **refuted as a
  performance concern**: removing it measured 1.003x, no measurable cost.
- **A real trap found in verification and named by no report**: the intuitively
  better version — accumulating the mask inside the piece loop, which already reads
  all 16 squares — is **6.5% slower** (0.935x). Build the mask in its own gated loop.
- **Emission order must be preserved** or node identity breaks.

## TH-10 · Maintain the Zobrist key incrementally in make/unmake

- **Verdict**: CONFIRMED, with a **cost the reports omit**.
- **Raised by**: all three (`opus-4-8` N3, `opus47` 013, `opus-5` 18).
- **Measured**: 1.033-1.074x on the hunt, 1.051x on solve d14 — i.e. 3.2-6.9%,
  slightly *below* the claimed 4.4-7.2% band.
- **Omitted downside**: perft and `th_moves` pay for a key they never read, because
  make/unmake maintain it unconditionally. **perft(8) measures 0.955x — 4.7%
  slower.** Avoiding that needs two `make()` variants, which no report budgeted for.
- **Both reported traps are real and reproducible**: `root_search` must set the key
  *before* the helper copy, or every SMP helper searches with a stale key and writes
  SND-flagged entries under wrong keys — a wrong-PROVEN that 1-worker node identity
  would not catch. And a hand-count change needs **two** XORs, because `th_key` XORs
  `zob_hand` for every count including 0.
- **Risk**: the soundness kind. Ship with the paranoia assert.

## TH-11 · Skip the legality test for moves that provably cannot expose the king

- **Verdict**: CONFIRMED for perft; **do not apply it inside `search()`**.
- **Raised by**: `opus-4-8` (N1, N2), `opus47` (009), `opus-5` (16).
- **Correction**: the claimed search-side regression of 3-6% is **overstated** —
  measured 0.1% on the mate hunt and 1.5-2.1% on solve d14. Direction survives, cost
  does not. Drop-heavy perft is 2.193x, not 2.3x, and is strongly position-dependent
  (1.64x on a second drop-heavy position).
- **Two implementation traps, both reproduced as real failures, named by no report**:
  - **Trap A**: "a drop can never expose the own king" is true but *insufficient* —
    when the side **is** in check a drop must **block**. Gating drops as
    unconditionally legal before the in-check test gives `perft(6) = 3,226,861`
    instead of 139,141.
  - **Trap B**: the mao-origin test must be `TYPE(pc) == U`, **not**
    `board[origin] == PIECE(them, U, 0)` — `attacked()` ignores the promoted bit and
    a pawn can promote to U. The buggy variant gives `perft(7) = 892,492,429` instead
    of 196,868,543 on a promoted-mao position.
- **Ship**: the perft/`th_moves`/`th_result`/`th_root_moves` half only.

## TH-12 · Hoist `king_sq` out of the per-move legality loop

- **Verdict**: PLAUSIBLE — measured, but **not reproducible as a single number**.
- **Raised by**: `opus-4-8` (N4), `opus47` (011, 012).
- **Measured**: 1.092x at low load, 1.059x under contention, 1.144x at perft(8). The
  "1.10x" figure sits at the top of the range and only reproduces on an idle machine.
- **Trap named by no report**: the drop test must come **first**. For a drop,
  `M_FROM(m)` is the piece *type* (0-3), which aliases square indices 0-3, so a bare
  `M_FROM(m) == ks` false-positives whenever the own king stands on rank 1.
- Search-side effect **UNMEASURED**.

## TH-14 · Bitboard movegen and `attacked()`

- **Verdict**: PLAUSIBLE. **UNMEASURED**, high effort, **not node-identical**
  (bit-iteration changes within-piece move order).
- **Raised by**: `opus-4-8` (N7), `opus47` (010).
- Do TH-08/09/10/12 first; they are node-identical and cheaper.

## TH-15 · Staged movegen: try the TT move before generating the full list

- **Verdict**: PLAUSIBLE. **UNMEASURED.** Raised by `opus-4-8` (N5, NI5).
- The node-identical subset (TT move first) and the fuller reordering (lazy drop
  materialisation, **not** node-identical) are one integration point; stage them as
  separate toggles or the gain cannot be attributed.

## TH-16 · Prune drops that cannot resolve a check

- **Verdict**: PLAUSIBLE. **UNMEASURED.** Raised by `opus47` (008).
- Overlaps TH-11's Trap A: it is the same theorem, used constructively. Perft must be
  identical, because every pruned drop was illegal anyway.

---

# [INSTRUMENT]

**The single largest gap in the repo: zero of the 43 tests touch the solver.**
Verified by grep — nothing exercises `th_solve`, `th_solve_mt`, `th_search`,
`th_mate_hunt`, `th_mate_hunt_mt`, `th_root_moves`, `th_key`, `th_nodes`,
`th_seed`, `th_tt_init`, `th_tt_save` or `th_tt_load`. THB-01 would have been
caught the first time move ordering shifted if TH-18 existed.

## TH-18 · Pin the recorded proofs

- **Verdict**: CONFIRMED, and **the pin is stronger than reported**.
- **Raised by**: all three (`opus-4-8` I1, `opus47` 016, `opus-5` 21).
- **Verified**: `th_root_moves(start, depth 10)` returns `d1c2 = -29990` with all five
  other root moves 0 — identical across 3 separate processes, depths 10/11/12, five
  Zobrist seeds, TT sizes 2^0 through 2^24, and with `th_tt_init` never called.
- **Assert the value, never the node count.** The node count is not merely drifty:
  with a TT held across repeats it collapses from 95,857 to **6**, which would make a
  node pin look catastrophically broken. It *is* reproducible across processes with a
  fresh TT (95,857 three for three), so a node assertion is possible only with a
  documented fresh-process precondition.
- **Effort**: ~12 lines. **Highest-value instrument in the backlog.**

## TH-19 · Clear `history` at the root, or fork per measurement

- **Verdict**: CONFIRMED with **causation proven**, not argued.
- **Raised by**: all three (`opus-4-8` I2, `opus47` 030, `opus-5` 7).
- **Reproduced exactly**: depth 13, `tt 2^22`, 1 worker, fresh `th_tt_init` before
  every repeat. Five repeats **in one process**: 757,928 → 845,801 → 834,551 →
  844,615 → 851,481. Five **separate processes**: 757,928 every time. A scratch build
  adding one `memset(history, ...)` after the killers memset at `tinyhouse.c:552`
  gives 757,928 on all five in-process repeats — `history` is the sole carrier.
- **Correction**: "warm up" implies faster. The repeats get **slower** — +11.5% nodes,
  and it does not converge back.
- **The damaging consequence is between arms, not within them**:
  `scripts/bench_workers.py` loops worker counts in the outer position, so the
  **first** worker count is the only arm that ever contains a cold-history sample.
  The arms are not drawn from the same distribution — a bias in the exact comparison
  the script exists to make. Helper threads are always cold, so the contamination is
  asymmetric between the `workers=1` and `workers>1` arms.
- **Do not default it on in `solve_hunt` without measuring**: the carry-over across
  successive iterative-deepening depths is a different and genuinely unmeasured
  question from repeats at one depth.
- **Piggyback**: `scripts/bench_workers.py` formats nodes as `{...ction/1e6:8.0f}M`,
  printing "1M" for everything from 500k to 1.5M — the clean metric is unreadable at
  exactly these depths.

## TH-20 · Paired nodes-to-depth + solver-digest regression harness

- **Verdict**: CONFIRMED. Raised by `opus47` (020), `opus-5` (20).
- **Correction**: a single-process harness **is** valid — the carry-over is
  deterministic when the sequence is fixed (byte-identical output from three
  processes). The real constraint is that the position list and depth pair must be
  frozen in the committed baseline. So TH-19 is a nice-to-have here, not a
  prerequisite; the harness is ~48 lines, not the ~70 costed.
- **Depth choice is load-bearing**: at depths 6/8 a path-dependent-store mutation
  shows as a **one-node** difference (luck); at 10/12 it shows as -1.3% (signal).
  Record the baseline at the deeper pair. One of the three planted mutations stays
  invisible on both fields at both depths — this is a regression detector, not a
  soundness proof, and the baseline file must say so.

## TH-21 · Pin the TT save/load round trip and the seed/size refusals

- **Verdict**: CONFIRMED. Raised by all three (`opus-4-8` I3, `opus47` 017,
  `opus-5` 24).
- **All codes verified on the shipped build**: save 0 · load same seed 0 · different
  size -2 · different seed -2 · missing -1 · bad magic -1 · truncated -1 · save or
  load with no table allocated -1.
- **Also pin content, not just codes**: after `th_seed(12345)` made the load fail -2,
  restoring the original seed made the same file load 0 — showing the check is keyed
  to `tt_seed_used` and not something incidental.
- **Must land before THB-07**, or the header widening cannot be verified.
- **Housekeeping**: a test that reseeds must restore the default
  (`th_seed(0x9E3779B97F4A7C15)`) or it silently changes the Zobrist tables for every
  later test in the process.

## TH-22 · The search API has zero cffi signature coverage

- **Verdict**: CONFIRMED. **Originated by this merge** (surfaced while verifying
  THB-14).
- **Evidence**: with a deliberately swapped `th_mate_hunt` cdef, `pytest -q` stayed
  **43 green** while the function returned 0 instead of 29985 on the THB-01 repro.
  `test_engine_c.py` only touches `th_perft`, `th_moves` and `th_result`.
- This is the genuinely silent half of the build-identity problem: a struct-layout
  error is caught by the existing perft tests; a signature error is not.

## TH-23 · Pin `attacked()` against an independent geometric oracle

- **Verdict**: CONFIRMED as **missing coverage**, not as a suspected defect.
- **Raised by**: `opus-5` (25) only.
- **Result**: an oracle written from `RULES.md` prose alone, deliberately derived in
  the opposite direction from the shipped code, agreed over **321,440 comparisons,
  0 mismatches**. The blind spot is real; nothing is hiding in it. Price it as
  coverage, not as a bug.
- **Scope note**: the oracle covers the *attack* direction only. `ORTH`/`DIAG`/`PCAPS`
  are also consumed by `pseudo_moves` alongside `KINGN` and `MAO_MOVES`, and that
  direction is still unverified against the spec by anything but perft.

## TH-24 · Extend the Python/C parity walk beyond the start position

- **Verdict**: CONFIRMED. Raised by `opus-4-8` (I5), `opus47` (032).
- Random play from the start reaches promotion and full hands vanishingly rarely.
  Parametrise the walk root over the `PERFT_ORACLE` positions.

## TH-25 · Assert published perft counts on the symmetry orbit — as cheap breadth, not as a new instrument

- **Verdict**: CONFIRMED factually; **the value proposition is REFUTED.**
- **Raised by**: `opus-5` (23).
- **Measured**: 5 oracle positions × 4 orbit members, 0 mismatches in both engines.
  But on eight injected engine bugs the orbit caught **6 of 8** while the existing
  identity-position perft caught **8 of 8**, adding **zero** detections. It is
  structurally blind to any error symmetric under the group — which is every uniform
  geometry error.
- **If merged**: assert the *published counts* on orbit members, never orbit
  self-consistency alone.

## TH-26 · Test the `solve_hunt` resume/checkpoint round trip
`opus-4-8` (I4). Subprocess test at `--tt 20`, shallow `--maxdepth`, scratch `--state`.

## TH-27 · Assert the SMP hunt returns the same proof as single-threaded
`opus47` (018). Fixed depth on the mate-in-9 line, workers 1 vs 2.

## TH-28 · Pin the horizon "non-terminal is UNSOUND" invariant
`opus47` (019). `th_solve` at depth 1 on a non-terminal root must return `snd == 0`.
This is invariant #1 and nothing guards it.

## TH-29 · Pin a draw-by-repetition proof
`opus47` (022). **Note the difficulty**: 3,613 random low-material positions
(including 1,853 bare-kings searched to depth 14) produced **zero** proven draws —
the horizon's unsound 0 swallows them. `snd == 3` *is* reachable (4 proven
wins/losses appeared), so the machinery works; a hand-crafted position where no line
reaches the horizon is required.

## TH-30 · Test the Zobrist reseed contract
`opus47` (023). **Heed `opus-4-8`'s kill of its own version**: asserting the value is
*equal* under two seeds passes even if reseeding is a no-op. Assert that the **keys
differ**.

## TH-31 · `th_nodes()` has no reset, and does not count perft
`opus-4-8` (I6). Verified: neither `th_tt_init` nor `th_seed` resets it. **Correction**:
`th_perft` does **not** feed the counter at all, so differencing around a perft gives
zero. All three current callers difference correctly.

## TH-32 · A paired NPS bench for the C search
`opus47` (021). `bench_workers.py` is an SMP scaling tool, not a paired A/B harness.

## TH-33 · Cross-check `state_count.py` and delete its dead stub
`opus-4-8` (I7). The headline 1.77e13 figure has nothing verifying the arithmetic; the
`placements()` stub is never called. Note `opus-5`'s kill of the related "Burnside"
claim: the group acts freely here, so `total/4` is **exact**, not a lower bound.

## TH-34 · Expose `snd` from `th_mate_hunt_mt`

- **Verdict**: CONFIRMED as an unenforced invariant; **the framing is corrected.**
- **Raised by**: `opus47` (029), `opus-5` (3).
- **Correction**: the PROVEN verdict does **not** rest on the discarded flags alone.
  With no static eval, mate scores can only come from real terminals, so a fail-soft
  root fail-high above `MATE_BOUND` is already a proof of a forced mate. The flags are
  load-bearing only for cross-depth TT reuse. This is a cheap self-consistency
  assertion, not a missing proof step — on 201 sampled root mate proofs, **0** were
  missing `SND_LB`.
- **Trap for the fix**: gate the assert on the `v > 29000` branch **only**. The
  negative branch runs flag-free by design — on the real start hunt the root flags are
  empty at every depth, so asserting `SND_UB` there would fire every time.

## TH-35 · Expose `snd` from `th_root_moves`

- **Verdict**: CONFIRMED, with the **payoff corrected**.
- **Raised by**: `opus-5` (10) only.
- **Correction**: the "proven draw vs unknown" payoff is close to unreachable at GUI
  depths — 2,301 of 2,302 quiet root moves at depth 10 had `child_snd == 0`, and not
  one was a proven draw. What is actually discarded is **mate-row** soundness. Note
  `index.html:118-119` already ignores `snd` entirely for `|v| > 29000`.
- **The reported sign correction is right and load-bearing**: the child value is
  negated, and `SND_LB`/`SND_UB` are duals of the value they describe, so the bits
  must be **swapped**. A badge reading the raw flag prints "upper bound" for a lower
  bound. The obvious acceptance test (`badge proven only when snd == 3`) is
  insensitive to exactly this — which is how it would ship the bug.

---

# [NEW-IDEA] — draw-proof lane first

## TH-36 · df-pn as a second engine

- **Verdict**: CONFIRMED as the principled route. Raised by all three
  (`opus-4-8` NI1/NI2, `opus47` 024/025/027, `opus-5` 26).
- **Why alpha-beta cannot get there**: the horizon returns unsound 0 at
  `tinyhouse.c:461`, so a draw is the *absence* of a proof rather than a positive
  goal. **Correction**: "cannot prove a draw at any depth" is not a theorem of this
  code — the path-repetition return at `:425-426` and both terminal returns set
  `SND_LB|SND_UB`, so a tree in which no line reaches the horizon would return
  `v=0, snd=3`. The accurate wording is "cannot prove a draw at any depth at which any
  line still reaches the horizon", which empirically is every depth on every position
  tried (0 proven draws in 3,613).
- **Measured advantage on the win lane**: ~1,949 df-pn nodes (two independent
  prototypes got 1,949 and 1,908) against 30,137 cold / 22,566 warm-increment /
  34,674 warm-cumulative alpha-beta nodes for the recorded mate-in-9 — i.e.
  **11.6x-17.8x**, and the bare "12.5x" is unreproducible without stating the
  protocol. **A df-pn node is a much heavier unit than an alpha-beta node**, so
  nodes-to-proof is the only comparable axis and no time claim follows.
- **The hard part**: removing the horizon makes repetition the only non-terminal
  leaf, so essentially every value becomes path-dependent and unstorable under the
  conservative rule. Measured at D=10 the depth-limited prototype already terminates
  ~1,840 branches on ancestor repetition against ~1,931 on the horizon — which
  **refutes** `opus-5`'s "ZERO repetition leaves" claim and is a *stronger* argument
  for Kishimoto-Müller twin entries, not a weaker one.
- **Gating milestone**: run unbounded from the start with a node cap and record root
  `dn` against nodes spent. Falling `dn` with twins inside the table means viable;
  plateauing `dn` with saturating twins means no. That is a one-day answer.

## TH-37 · The reachable-position census is the number this lane actually needs

- **Verdict**: CONFIRMED exactly. **Originated by `opus-5` (22)**; independently
  reproduced by exact 128-bit packed keys (no collision tail at all).
- **Per ply, new / cumulative**: 6/7 · 33/40 · 193/233 · 1220/1453 · 7751/9204 ·
  45979/55183 · 291007/346190 · 1689902/2036092 · 9630829/11666921 ·
  49003553/60670474. Plies 1-2 equal perft 1-2, as they must.
- **Correction**: the attached performance claim ("12 seconds, 1.8 GB") did **not**
  reproduce — 185s wall / 3.06 GB RSS at hashbits 27 with 16-byte keys, most of it
  first-touch page faulting. Quote the key width, hashbits and machine with any timing.
- **Why it matters**: it converts "a strong solve is infeasible" from an argument into
  a measurement, and prices df-pn honestly. Growth is bending (6.4 → 5.1).

## TH-38 · Bounded retrograde terminal shell
`opus-4-8` (NI3), `opus47` (026). A bounded-`k` retrograde can only label WIN/LOSS,
never DRAW, so it is sound as an exact leaf evaluator but cannot close the draw claim
alone. Depends on TH-37 for costing.

---

# [SHOULD-BE-BETTER]

## TH-39 · The `--tt 26` default is unmeasured, and the table — not the dump format — is what to size

- **Verdict**: CONFIRMED. Raised by `opus-5` (30), reinforced by verification of the
  sparse-dump item that was killed (K-02).
- **Measured**: at depth 16 the nodes-to-depth curve is flat past 2^20 and the hit
  rate never exceeds ~5.3%. But the sizing measurement taken while killing K-02 is
  the sharper one: at depth 18, `tt 2^22` is **91.7% full and took 216.6s**, against
  **100.3s** for `2^24` on the same work.
- **Do not lower the default on a depth-16 curve.** Add a `--tt` sweep to
  `bench_workers.py` and measure at the depth actually being run. The depth-20 sweep
  is a long job and is Sam's to run.

## TH-40 · `/api/analyze` mixes frames: `value` is white-view, `snd` is mover-view
`opus-5` (32). Verified with a colour-mirrored pair: both return `snd=1`, but for
White that is a lower bound on the published number and for Black an upper bound.
**Latent**: `index.html:120` tests only `snd === 3`, which is invariant under the
flip, and `fmtVal` short-circuits on `|v| > 29000` before consulting `snd` at all.
Fix as an API contract bug. Requires a cache-namespace bump in the same commit.

## TH-41 · Cache hits replay the first computation's `nodes`, `time` **and `depth`**
`opus-4-8` (G1). **Correction**: it is not only `nodes`/`time` — `depth` and the whole
`moves` array are replayed too, which is what makes THB-09's mislabelling durable.
Mitigated for the user by the "· cached" marker at `index.html:272`. Cosmetic on its
own; load-bearing in combination with THB-09.

## TH-42 · Derive `ENGINE_VERSION` from the source instead of hand-bumping it
`opus-4-8` (S2). **Verified latent, not live**: reproduced end to end by editing
`#define MATE` in a scratch copy — the rebuild fired, the new engine returned 29993 at
depth 11 while the server kept serving the old 29991 at depth 10 under an unchanged
version key. Bounded by both artefacts being gitignored, so it is per-machine only.
Extra wrinkle: the trigger is mtime, not content, so `git checkout` of an *older*
`tinyhouse.c` also silently rebuilds backwards.

## TH-43 · `th_solve` at `depth <= 0` returns no best move
`opus-4-8` (B5). **Correction**: not depth 1 only — every `depth <= 0` root returns
`bestmove 0` via the horizon branch before any store. Reachable only through
`/api/analyze?depth=1` (THB-10), never from the GUI dropdown. Cosmetic: the value
itself is legitimately 0/`snd 0`.

## TH-44 · Error responses leak absolute filesystem paths
**Originated by this merge** (found while refuting the `/pieces/` traversal claim).
`GET /pieces/<subdir>` raises `IsADirectoryError`, which the blanket
`except Exception` at `server.py:129-130` turns into a 400 body echoing the absolute
path. Applies to **every** endpoint, mitigated only by the `127.0.0.1` bind.

---

# GUI

## TH-45 · History numbering is inverted for the entire game, not just the first move
`opus47` (004). **Correction**: the parity error does not stop at ply 0 — from a
black-to-move start, every white move loses its number and every black move carries
one. Also, no new state field is needed: `state.hist[0].split(' ').pop()` recovers the
starting side to move, which is cheaper than the proposed `startStm` field (which
would need resetting in three places). Display-only.

## TH-46 · There is no check indicator of any kind
`opus47` (033). `in_check` is computed, serialised and never read — the string never
appears in `index.html`. **Under-inclusive as filed**: `move_str` never appends `+`
either, so the moves table and history carry no check annotation. The only
check-adjacent text fires once the game is already over.

## TH-47 · `/pieces/` hardcodes `image/svg+xml`
`opus-4-8` (G2). **Latent and near-zero severity**: the directory holds only the ten
`.svg` files, the route serves direct children only, and there is no upload path.
Hardcoding actually removes the sniffing risk a wrong guess would create. Tidiness.

---

# Kill list

The point of this section: it is what stops the next wave re-proposing the same
thing. Each entry keeps its ID permanently.

## Killed at this merge

| ID | Item | Why it died |
|---|---|---|
| **K-01** | Symmetry folding in the TT (`opus-4-8` NI4, `opus-5` 28) | **Measured dead.** Cumulative fold ratio is 1.089 by ply 8, not 4 — and *all* of it comes from sigma: the **file mirror merges exactly nothing** (ratio 1.000 at every ply 1-8) on the set reachable from this start. Direct A/B measured neutral-to-worse in nodes. Also hazardous: a group-partner entry hands back a bestmove in the wrong frame. |
| **K-02** | Sparse `.tt` dump (`opus-5` 29) | **Measured not worth it.** Saves 0.36s per checkpoint at the 1 GiB default, once per depth, against depths costing minutes to hours — and it saves least where it would matter, because occupancy rises with depth (0.98% → 41.7% at 2^24 over d14→d18; 3.9% → 91.7% at 2^22). At overnight depths a sparse format would be *larger*. The useful residue became TH-39. |
| **K-03** | Sigma-mirror as a draw strategy (`opus-5` 27) | **Refuted, and more strongly than published.** Exhaustive closed walk: mirror break rate 20.52% (not ~22%), and **13,736** positions where White's move checkmates Black outright — 2.9x the reported 4,804. The start *is* sigma-symmetric and the balance invariant holds (0 of 4,134,968 failures), but the strategy loses. |

## Killed during the campaign (see SCOREBOARD.md for the measurement)

| ID | Item | Why it died |
|---|---|---|
| **TH-25** | Assert published perft counts on the symmetry orbit | **Measured to add nothing, independently of the merge's own measurement.** All four orbit members of all five oracle positions match the published counts (0 mismatches), so the factual half stands. But against eight planted rules bugs -- ferz, wazir and king geometry, mao blocking, the pawn drop rule, pawn push distance, and both promotion lists -- the existing identity-position perft caught **8 of 8** and the orbit caught **0** that it did not. The merge measured 6/8 vs 8/8 and reached the same verdict; this is 8/8 vs 8/8, which is the same conclusion from the other side. Structurally blind to any error symmetric under the group, which is every uniform geometry error. The `sigma` mirror itself does earn its place elsewhere: `test_server.py` uses it to pin the TH-40 frame duality, where a colour-mirrored pair is exactly the right instrument. |
| **TH-16** (Class A form) | Prune drops that cannot resolve a check, in perft/`th_moves` | **Measured NULL-to-negative.** perft(7) +0.41% against a +0.67% control, and **-1.33%** on `3k/1U2/4/K3[f] b`, a mao check with exactly one blocking drop -- the position it targets. In-check nodes are a minority and `check_block_square` has to walk four attack tables to learn whether it may skip anything. The *search* form is a different animal: it is **not** node-identical (digest `811f304f1eef7998`, rows moving +7.28% and -5.63%) because removing list entries changes which index wins a tie in the selection sort. That form measured +7.91% with 1.7% fewer nodes and is reclassified to tier 5 rather than killed. |
| **TH-07** | "exists exactly twice" comment | **Moot, not killed on merit.** The comment moved into `Position.validate()` during THB-05's refactor and was rewritten as "at most twice", which is the change the item asks for. Re-measured: 8 of the repo's TFEN literals are full and 11 under-full, so softening the doc was the right direction and tightening the code would have been wrong. |

## Partial refutations folded into surviving items

- **Promoted-*pawn* half of THB-02** — `P~` is bucketed correctly under `P`; only the
  promoted **king** evades the guards.
- **"cdef edit does not trigger a rebuild" (THB-14)** — category error; a cdef edit is
  Python-side and needs no rebuild. Only the compile-flags half is a defect.
- **"No test can catch a `DOUBLE_STEP` flip" (THB-15)** — false; the suite goes 4-red.
- **`/pieces/` path traversal** — the guard is correct under every probe attempted
  (`..`, percent-encoded, `....//`, backslash, symlink to `/etc/hosts`, `//pieces/`).
  Only the Content-Type half survives, as TH-47.
- **"th_root_moves would reveal proven draws" (TH-35)** — none exist at GUI depths.
- **"alpha-beta cannot prove a draw at any depth" (TH-36)** — true only where some
  line still reaches the horizon.
- **"`=K` produces an out-of-encoding move" (THB-06)** — masked to 0; a silent
  downgrade, memory-safe.
- **"Symmetry orbit is a new instrument" (TH-25)** — strictly dominated by the
  existing perft assertions, 6/8 vs 8/8.

## Pre-existing closed measurements — do not re-propose

- **Unbounded check extensions.** Removed deliberately; they exploded the
  full-window search through perpetual drop-check subtrees.
- **"Just add more threads."** Lazy SMP measured at depth 18: 1/2/3/4 workers =
  27.8 / 28.4 / 51.7 / 49.7s. One and two tie within noise; three and beyond regress
  hard. Deeper scaling remains unmeasured — measure with `scripts/bench_workers.py`
  at the target depth, and read TH-19 first, because the repeats are currently biased.
- **Re-enabling depth-1 unproven TT stores.** They are ~74% of write traffic and
  near-worthless, and they thrash shared cache lines.
- **Elo of anything.** There is no opponent and no Elo instrument in this project.
- **`memchr` for the `king_sq` byte loop.** Measured a small loss (+2.1% CPU),
  node-identical.
- **Burnside correction to `state_count.py`'s `/4`.** The group acts freely; `total/4`
  is exact.

Additionally, the three reports self-killed 15 items before submitting (2, 4 and 9);
those reasons remain auditable in `Reviews/`.

---

# ROADMAP

Ordered by value, with the cheapest lane called out separately so the two are not
confused.

### Lane 1 — restore the contract (do this first)
The product is proof claims and one of them is currently unsound in its *budget*.
**First action**: apply THB-01 form **H** (`if (ply > 0 && depth > 0) {`), then
re-run the depth-12 repro and all three published wins. Immediately follow with
TH-01 and TH-02, because the fix decides which wording is correct. Then TH-05 —
the recorded method contradicts the documented command, so today the headline bounds
cannot be reproduced from the repo.

### Lane 2 — make the product testable (highest value per hour)
Nothing in CI touches the solver. **First action**: TH-18, ~12 lines, asserting
`th_root_moves(start, 10)` gives `d1c2 = -29990`, value only. Then TH-21 (TT round
trip), TH-28 (the horizon-UNSOUND invariant), TH-22 (cffi signature coverage). This
lane is what would have caught THB-01.

### Lane 3 — close the trust boundary (cheapest lane, ~10 lines total)
THB-02, THB-03 and THB-05 together, in one commit: two parse rules plus reusing them
in `to_c`. That one change closes THB-04 and THB-06 from the reachable direction and
makes the C library stop depending on a Python invariant for memory consistency.

### Lane 4 — resume integrity
THB-08 (temp-file-plus-rename, one line, closes the destroy-on-open window) and
THB-07 (build fingerprint in the `.tt` header). Both matter the moment an overnight
run is resumed, which is the documented workflow.

### Lane 5 — speed, in measured order
TH-08 → TH-09 → TH-10 → TH-11 (perft half only) → TH-12. Land TH-19 **first**, or the
measurements that justify each step are biased. Every one of these is node-identical;
that identity is the acceptance test.

### Lane 6 — the draw proof
TH-37 (census, already run) prices it; TH-36 (df-pn) is the only formulation that can
close it. Gate on the milestone: unbounded df-pn from the start with a node cap,
watching root `dn`. Falling means viable, plateauing means no. **A one-day answer to a
question the repo has been carrying since phase 4.**

**Highest value**: Lane 2 — the solver is the product and it has no automated
coverage at all. **Cheapest**: Lane 3, about ten lines for three confirmed bugs.
**What I would do first**: Lane 1, because a wrong budget claim on a published proof
is the one defect that damages the record rather than the code.
