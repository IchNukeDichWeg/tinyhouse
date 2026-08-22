# Tinyhouse v1 review — soundness, efficiency, NPS, new ideas

Reviewer: Claude Opus 4.8. Method: 7 parallel mining lenses → cross-miner dedup →
one adversarial verifier per item (job: refute), then main-thread re-verification of
every `file:line` against the live tree by `grep`, plus independent reruns of the top
items. 39 raw findings → 34 deduped → **32 survived, 2 killed**. 42 agents, ~2.2M
subagent tokens.

All `file:line` citations below are re-anchored to the **current** working tree by
`grep` (see the STEP 0 drift note — the repo advanced mid-review and several agents
cited a moving target).

---

## STEP 0 — baseline verification and DRIFT

At session start HEAD was `2125a70` and the facts matched: line counts as listed,
`git log` 10 commits, **perft(7) = 1,355,253**, **43 tests pass**, mate line
`1.Fd1-c2 → mate in 9` reproduces.

**DRIFT DETECTED (report-worthy): the repo advanced during the review.** HEAD moved
`2125a70 → 2054f2d` ("Bound the transposition table against physical RAM before
allocating"). Diff: `solve_hunt.py` +51 (a `check_tt_size` RAM guard + `free_bytes`
via `vm_stat`, `--force-tt` override), `tinyhouse.c` +9 (`th_tt_init` changed
`void → int`, returns −1 on alloc failure, with a calloc-overcommit warning comment),
`engine_c.py` cdef `void th_tt_init → int th_tt_init`, `bench_workers.py` now aborts if
`th_tt_init` fails. Current line counts: `solve_hunt.py` 211, `tinyhouse.c` 635.

**The config-drift oracle HELD on the current code: `perft(7) = 1,355,253`, 43 tests
pass.** So the rules/movegen are intact — this is a legitimate long-run-safety feature,
not a rules change. The new `check_tt_size` guard is correct (bounds the table to ≤ half
physical RAM before the overcommitting `calloc`, warns near free-memory, overridable);
it is *not* a finding and it partially pre-empts the memory concern in NEW-IDEA #26.
Consequence for this review: the `+9` in `tinyhouse.c` shifted later line numbers, so all
citations here are grepped against the live `2054f2d` tree.

Everything else in the STEP 0 fact list re-verified unchanged (perft oracle, 65× C/Python
speed ratio not re-timed under load, state-space counts).

---

## Counts

| Category | Count |
|---|---|
| BUG-SOUNDNESS | 2 (+1 potential/unproven, filed under DOC-OVERCLAIM) |
| BUG | 5 |
| DOC-OVERCLAIM | 2 |
| EFFICIENCY (nodes-to-depth) | 2 |
| NPS (time/node) | 7 |
| INSTRUMENT | 7 |
| NEW-IDEA | 5 |
| GUI | 2 |
| **Survived total** | **32** |
| Killed by verifier | 2 |

Independently reproduced by the reviewer (not taken on the agents' word): the
promoted-king hole (S1), the DOUBLE_STEP divergence (B3), the mate-in-9 oracle (I3), the
history-carryover non-determinism (I2), TT save/load + seed-mismatch (I4), and the
72–74% skippable-legality fraction backing N1/N2.

---

## [BUG-SOUNDNESS] — can emit a wrong PROVEN (ranked first)

### S1. `from_tfen` accepts a promoted king `K~`, smuggling a second king past the one-king guard; the solver then emits a sound-flagged win for an illegal position
- **Source**: python-divergence lens; reviewer-reproduced.
- **What**: `'~'` sets the promoted bit for *any* type, so `K~` builds `piece(color,K,True)` (value 13/29) and `P~` builds `piece(color,P,True)`. `KK~2/4/4/3k[-] w` is **accepted** with two white kings.
- **Mechanism**: the king-count guard tests `board.count(piece(color,K))` (promoted=False) and the unit-count guard does `if ptype(pc)==K: continue`, so a promoted king is invisible to **both** checks, yet `attacked()`/`pseudo_moves()` treat it as a king. **Reviewer-verified**: `KK~2/4/4/3k[-] w` parses, has 6 legal moves, and `th_solve(...,6)` returns **value 29995, snd=1 (SND_LB)** — a proof-flagged forced win for a structurally illegal position. This is the exact wrong-PROVEN the doctrine forbids, and it is user-reachable through the GUI TFEN box.
- **Soundness**: TFEN trust boundary only. Kings never promote and pawns promote *into* F/U/W, and `tfen()` only writes `~` on promoted F/U/W, so valid TFENs never contain `P~`/`K~`; rejecting them is node-identical on every legal input.
- **Integration point**: `tinyhouse.py:130` in `from_tfen` — `promoted = j + 1 < len(rank) and rank[j + 1] == "~"` then `pos.board[_sq(f, r)] = piece(color, t, promoted)` (`tinyhouse.py:133`).
- **Toggle & pin**: add module constant `PROMOTABLE = (F, U, W)` and, right after `promoted = ...`, `if promoted and t not in PROMOTABLE: raise ValueError(...)`. Removing the guard reproduces present behavior; on valid inputs it never fires (node-identical).
- **Expected gain**: wrong-proof prevention (no metric). Confirm: two negative tests asserting `from_tfen('KK~2/4/4/3k[-] w')` and `from_tfen('P~2k/4/4/K3[-] w')` raise (neither does today); pytest green; PERFT_ORACLE unchanged.
- **Risk**: nil (rejects only meaningless encodings).
- **Oracles**: pytest −q + 2 new negatives; perft(7)=1,355,253; the repro solving to 29995/snd=1.
- **Effort**: trivial (2 lines). **Novelty**: distinct from the fixed "no white king" / "king-capture IndexError" items — this manufactures an *extra* king invisible to the count guards.

### S2. Cache invalidation hinges on a hand-bumped `ENGINE_VERSION`; a value-changing rebuild silently serves stale "proven" rows (CONFIRMED, latent)
- **Source**: gui lens.
- **What**: `analysis.sqlite` keys on the literal `ENGINE_VERSION=2`, but `engine_c.py` auto-rebuilds the dylib on `tinyhouse.c` mtime. Editing the search so values/`snd` change *without* manually bumping the constant leaves old rows — including `snd===3` "exact" and mate "forced (proven)" — served verbatim by `analyze()`.
- **Mechanism**: `analyze()` does `SELECT ... WHERE version=ENGINE_VERSION` and returns the stored JSON untouched (only `cached=True` added); the stored `value`/`snd` are what `fmtVal` renders as proof labels. The dylib rebuild (mtime) and the cache version (manual constant) can disagree: new engine, old served proof. This is the only path by which the GUI shows a proof the current engine did not produce (the live path is sound).
- **Soundness**: touches the displayed proof label. Keying on the compiled artifact restores "displayed proof == current-engine proof."
- **Integration point**: `server.py:21` `ENGINE_VERSION = 2`; consumed `server.py:40`, stored `server.py:66`.
- **Toggle & pin**: `ENGINE_VERSION = int.from_bytes(hashlib.sha256((DIR/'libtinyhouse.dylib').read_bytes()).digest()[:6],'big')` (or hash `tinyhouse.c` source to avoid rebuild-only churn). Reverting to `= 2` is node-identical (only the cache partition key changes).
- **Expected gain**: correctness hardening, no node/NPS change.
- **Risk**: whole-cache invalidation on every rebuild (source-hash variant avoids no-op-recompile churn).
- **Oracles**: pytest unaffected; manual repro (edit a value-affecting line, don't bump, re-request same tfen+depth).
- **Effort**: S. **Severity**: **latent** — `ENGINE_VERSION=2` is consistent with the current dylib, so no live mislabel today; it fires only after a future forgotten bump. **Novelty**: distinct from the fixed "cache key missing engine version" (that *added* the field; this hardens it from a hand-int to an artifact-derived value).

### (See also S3 in DOC-OVERCLAIM — the GHI residual is a *potential* wrong-PROVEN and is ranked here in spirit.)

---

## [BUG]

### B1. `from_tfen` accepts a pawn on rank 1 or rank 4 (its own back rank / promotion rank), an unreachable position
- **Source**: python-divergence lens; reviewer-reproduced (`P2k/4/4/K3[-] w` and `3k/4/4/K2p[-] w` both accepted).
- **Mechanism**: the parser checks character/overflow/king-count/unit-count/not-in-check but never the pawn-rank invariant that mirrors the drop restriction `s>>2 in (0,3)`. A raw pawn can only ever legally sit on ranks 2–3 (drops barred from 1/4, reaching the last rank forces promotion away from `P`), so `piece(color,P,False)` never appears on ranks 1/4 in a legal game.
- **Soundness**: boundary only; guard fires solely on unreachable input, node-identical on legal boards.
- **Integration point**: `tinyhouse.py:133` `pos.board[_sq(f, r)] = piece(color, t, promoted)` (reached with `t = TYPE_CHARS.index(...)`, `r = 3 - i`).
- **Toggle & pin**: before the assignment, `if t == P and r in (0, 3): raise ValueError(...)`. Removing it reproduces current behavior.
- **Oracles**: pytest + 2 negatives; PERFT_ORACLE unchanged. **Effort**: trivial. **Severity**: validation completeness (the accepted pawn is stuck; less severe than S1, no snd-flagged win observed).

### B2. dylib staleness keys only on `tinyhouse.c` mtime, ignoring `engine_c.py`'s own cdef (ABI struct) and compile flags
- **Source**: python-divergence lens.
- **Mechanism**: the ffi `cdef` (THPos layout, signatures) and the exact `cc` command both live in `engine_c.py`. cffi ABI mode lays out `THPos` per the cdef and calls the prebuilt dylib. Edit the cdef (add/reorder a field, change a signature) or the `-O2/-pthread` flags **without** touching `tinyhouse.c` and no rebuild fires — Python then reads/writes the struct at offsets the binary disagrees with: **silent memory misinterpretation, not a crash.**
- **Soundness**: build freshness only. A rebuild triggered by an `engine_c.py` edit produces a binary matching the current cdef — strictly safer.
- **Integration point**: `engine_c.py:16` `if not _LIB.exists() or _LIB.stat().st_mtime < _SRC.stat().st_mtime:` / `:17` the `cc -O2 -pthread` `subprocess.run`.
- **Toggle & pin**: `max(_SRC.stat().st_mtime, Path(__file__).stat().st_mtime)`. Reverting is identical when only `tinyhouse.c` drives edits.
- **Oracles**: perft(7)=1,355,253 after a forced rebuild; test_engine_c parity. **Effort**: trivial. **Severity**: ~5 (needs the uncommon cdef-without-`.c` edit, but the failure class — silent struct corruption — is nasty).

### B3. DOUBLE_STEP divergence is unguarded at the C boundary and untested
- **Source**: python-divergence + instruments lenses; **reviewer-reproduced**.
- **What**: `DOUBLE_STEP` gates a two-square pawn push in `tinyhouse.py:13` (default False) with **no counterpart in `tinyhouse.c`**; `engine_c.py` imports `tinyhouse as T` but never reads `T.DOUBLE_STEP`.
- **Mechanism**: reviewer set `T.DOUBLE_STEP=True` and compared: Python perft `6,36,274,2181,19317` vs C `6,33,241,1855,16021` — **diverges at depth 2**. The C engine silently runs a different ruleset than the reference oracle, and `test_move_sets_match_on_random_walks` only runs at the default (False), so it can never catch a flip.
- **Soundness**: import-time assertion only; no-op at the committed False value.
- **Integration point**: `engine_c.py:10` `import tinyhouse as T` (no ruleset check anywhere); `tinyhouse.py:13` `DOUBLE_STEP = False`.
- **Toggle & pin**: after the dylib load, `assert not T.DOUBLE_STEP, "tinyhouse.c has no double-step; keep DOUBLE_STEP=False or implement it in C"`. Add a `monkeypatch`-scoped parity test asserting the **superset** relationship (C ⊂ Python with the flag on), not blind equality.
- **Risk**: none with the flag off; if double-step is later implemented in C, delete the guard in the same commit. **Effort**: trivial + S. **Severity**: low (flag committed off, documented as an unverified alternative). **Novelty**: known-open notes "python only"; the concrete gap is that *nothing* enforces it at the C boundary and *no test flips it*.

### B4. `/api/analyze` clamps depth from above (`min 22`) but has no lower bound, caching vacuous horizon-0 rows
- **Source**: gui lens.
- **Mechanism**: `min(int(...),22)` leaves 0/negative intact; `th_solve` then hits the `depth<=0` horizon branch returning unsound 0 (`snd=0`) for a non-terminal root, and `analyze()` writes that row. The GUI select is 8..22, so this is reachable only via crafted URLs — but the server is the trust boundary.
- **Soundness**: no wrong proof (`snd=0` blocks any proven/exact label); the concern is a nonsense cached row and an unvalidated int reaching the C boundary.
- **Integration point**: `server.py:123` `self.send_json(analyze(q["tfen"], min(int(q.get("depth", 12)), 22)))`; horizon branch `tinyhouse.c:455` `if (depth <= 0) {`.
- **Toggle & pin**: `max(1, min(int(q.get("depth", 12)), 22))`. Byte-identical for every depth the GUI sends (≥8).
- **Note**: default here is 12 while `index.html:394` defaults the select to 14 (minor inconsistency). **Effort**: S. **Severity**: low.

### B5. Depth-1 unproven solve returns `bestmove = 0` (no move)
- **Source**: solver lens; reviewer-reproduced (`th_solve(start, 1)` → bestmove 0; depth 2 → 41 = `c1b3`).
- **Mechanism**: the root store gate requires `depth >= 2 || proven`; at depth 1 on a non-mate root, `best` is an unproven bound so nothing is stored for the root, and `root_search` re-probes the root key and misses → bestmove 0. **Value and `snd` are correct** — only the reported move is missing.
- **Soundness**: does not touch value or any sound flag; purely an interface defect on a degenerate depth.
- **Integration point**: store gate `tinyhouse.c:523` `if ((depth >= 2 || proven) &&`; readback `tinyhouse.c:572` `*bestmove = tt_probe(th_key(p), &tv) ? tv.move : 0;`.
- **Toggle & pin**: on a probe miss, fall back to the **main thread's** own `bestm` (not a helper's, which may search `depth+1`); constant `ROOT_BESTMOVE_TT_ONLY = 1` preserves current behavior. Node-identical either way.
- **Oracles**: `th_solve(depth=1)` returns a legal move. **Effort**: small. **Severity**: low.

---

## [DOC-OVERCLAIM]

### S3 / D1. The rep-safety store gate does NOT fully eliminate graph-history interaction; the comment overclaims it (potential wrong PROVEN — **unproven**)
- **Source**: solver lens. Verifier verdict: **PLAUSIBLE**, ~medium. *Ranked at the top of this section because it touches the product's central claim and can, in principle, emit a wrong PROVEN.*
- **What**: the comment says the `my_rep >= ply` store gate "keeps the graph-history interaction problem out," but that gate is the known-*incomplete* "don't store rep-dependent values" heuristic. It prevents **storing** values that depended on an ancestor repetition; it does **not** guard **reuse** of a proven entry in a context where a position `Q` — a non-repeating winning descendant when `A` was stored — is instead an *ancestor* of `A` on the current path.
- **Mechanism**: `A` is stored EXACT-proven (its winning line ran through `Q`, which raised no rep flag, `rep_min=MAXPLY`). On a different move order `... → Q → ... → A`, reaching `A` returns its proven value by TT cutoff **without descending**; but `A`'s forced win runs back through the now-repeated ancestor `Q`, which the defender claims as a draw. The top-of-search rep loop (`tinyhouse.c:425`) catches `A` repeating, not `Q`. `th_seed` covers only Zobrist collisions, and cross-seed agreement is **necessary but not sufficient** (both seeds share the identical TT-reuse path).
- **Soundness**: invariant (c). **POTENTIAL, UNPROVEN** — no concrete Tinyhouse line emitting a wrong PROVEN was constructed. Impact if real: a wrong "proven mate in N" or "proven no forced win" on a transposition-heavy root.
- **Integration point**: comment `tinyhouse.c:256` `* is what keeps the graph-history interaction problem out).`; store gate `tinyhouse.c:513` `if (tt && my_rep >= ply && !g_abort) {`.
- **Toggle & pin**: primary fix is **comment-only** (soften to name the residual: closes the path-dependent subset, not the transposition-ancestor subset), node-identical. Optional hard fix: constant `TRUST_PROVEN_TT_ACROSS_PATHS = 1` (current) whose `0` refuses EXACT-proven TT cutoffs when an ancestor could transpose into the entry's subtree (loses most cutoffs; slow).
- **Oracles**: constructing the drop-transposition described would settle it; a df-pn / PN² cross-proof (NEW-IDEA #25) is the principled settlement. **Effort**: medium. **This qualifies the README/status "proof-grade" claim — see "What is still owed."**

### D2. `from_tfen` comment claims each non-king unit "exists exactly twice" but the code only rejects counts `> 2`
- **Source**: python-divergence lens.
- **Mechanism**: conservation makes exactly-two an invariant of every *reachable* position, but the enforcement is only `if n > 2: raise`, so an under-full board (e.g. a single wazir in the whole game) is silently accepted. The upper bound is the only safety-relevant check (it protects `th_key`'s 0–2 hand indexing), which the next comment sentence already states.
- **Soundness**: cosmetic; under-full counts index safely.
- **Integration point**: comment `tinyhouse.py:147`; check `tinyhouse.py:162` `if n > 2:`.
- **Toggle & pin**: soften the comment to "at most twice" (node-identical). A behavior variant `n != 2` would reject legitimate reduced-material analysis boards (`from_tfen` never enforces reachability) — so the doc softening is the safe fix. **Effort**: trivial. **Severity**: cosmetic.

---

## [EFFICIENCY] (nodes-to-depth)

### E1. Mate-distance early return drops the symmetric SND_LB flag on a fail-high lower bound
- **Source**: solver lens. Verdict: PLAUSIBLE.
- **Mechanism**: the node value is bounded in `[-(MATE-ply), MATE-ply]`. The branch credits `SND_UB` when `alpha==MATE-ply` (value ≤ ceiling), but by exact symmetry, when the window collapses with `alpha` clamped up to `-(MATE-ply)`, the returned `-(MATE-ply)` is always a valid **lower** bound (`SND_LB`). Crediting it lets bound-duality fire one ply earlier on forced-loss lines, so mate-loss proofs propagate sooner and cut more subtree.
- **Soundness**: invariant (b). The added flag asserts `value >= -(MATE-ply)`, which mate-distance pruning already guarantees unconditionally — the exact mirror of the trusted `SND_UB` case; it can never over-claim.
- **Integration point**: `tinyhouse.c:422` `if (alpha >= beta) { si->snd = alpha == MATE - ply ? SND_UB : 0; return alpha; }`.
- **Toggle & pin**: `MDP_SYMMETRIC_SND = 0` restores the current `? SND_UB : 0` (node-identical off; the point of "on" is fewer nodes).
- **Expected gain**: **ESTIMATE** small single-digit-% nodes-to-depth on forced-loss subtrees; ~0 elsewhere. Confirm: paired `th_mate_hunt` at fixed depth on the **losing** color of the 1.Fd1-c2 line, diff `th_nodes()` on/off.
- **Oracles**: pytest; 1.Fd1-c2 → mate in 9 (value/snd unchanged); toggle-off node-identity. **Effort**: trivial. **Risk**: very low.

### E2. Quiet drops get only history+jitter in ordering; no enemy-king-proximity term for mate hunts
- **Source**: solver lens. Verdict: PLAUSIBLE.
- **Mechanism**: in a null-window mate proof the attacker's winning move is usually a check (boosted `1<<21`) or a drop that constrains the king's escape squares. Direct-check drops are handled; mate-net drops one square off the king fall through to `history[stm][m&2047] + jitter`. `enemy_ks` is already computed per node, so a cheap proximity bonus for drops adjacent to the enemy king is nearly free.
- **Soundness**: `order_score` is ordering-only (reorders, never prunes); every legal move is still searched, no bound/flag changes.
- **Integration point**: fallthrough `tinyhouse.c:410` `return history[(int)p->stm][m & 2047] + j;` (`ks` == `enemy_ks` = `king_sq(p, 1-p->stm)`, `tinyhouse.c:467`).
- **Toggle & pin**: constant `DROP_KING_PROX_W = 0`; add it for `M_IS_DROP(m)` with no capture/check when `M_TO(m)` is a `KINGN` neighbor of `ks`. Weight 0 is node-identical.
- **Expected gain**: **ESTIMATE** mid-single-digit-% nodes-to-depth in attacker-side hunts; ~0 in drawish roots. Confirm: paired single-thread `th_mate_hunt` at fixed depth on 1.Fd1-c2, weight 0 vs tuned.
- **Oracles**: 1.Fd1-c2 → mate in 9; toggle-off node-identity; pytest. **Effort**: small.

---

## [NPS] (time per node)

### N1. Mao-aware fast legality: skip make/in_check/unmake for the moves that provably cannot expose the own king
- **Source**: movegen lens. Verdict: PLAUSIBLE (correctness airtight; magnitude unmeasured). **Reviewer measurement (deterministic): up to 72.0% of legality triples skippable on the start tree, 73.9% on a full-hand tree** — matching the "~71%" claim.
- **Mechanism**: this variant has **no sliders** (P/F/W step one, U leaps, K steps), so classic pins do not exist. Every attacker is single-step or a Mao leaper; a single-step attacker has no intervening square, so no quiet move creates a new adjacency check, and the **only** blockable geometry is the Mao's leg. Hence, when the mover is not in check, a non-king board move is legal without any make/in_check/unmake **unless** its from-square is the blocker-leg of an enemy Mao whose leap lands on the own king. Only king moves, those rare Mao-leg moves, and in-check nodes need the full filter.
- **Soundness**: legality filter only; legal set provably unchanged (the Mao-leg fallback still runs the full test for the only case that can differ, including capturing the Mao). perft is the oracle.
- **Integration point**: `th_moves` filter `tinyhouse.c:210-211` (`make(p, buf[i], &u);` / `if (!th_in_check(p, 1 - p->stm)) {`) and `search` filter `tinyhouse.c:457/479`; the Mao geometry is `MAO_ATT` (`tinyhouse.c:97`).
- **Toggle & pin**: `#define TH_FASTLEGAL 1`, fast path only when a per-node `th_in_check(p, us)` is false; `0` restores the unconditional loop (node-identical, perft(7)=1,355,253).
- **Expected gain**: **ESTIMATE** large (the finding says 40–70% NPS; make+in_check+unmake is the dominant per-move cost and ~72–74% of those triples are removable — reviewer-measured). Realized wall-clock needs a paired timed build. Confirm: paired perft(7) time-per-node medians on one idle machine (node count pinned) + a legality-call counter.
- **Oracles**: perft(7)=1,355,253; PERFT_ORACLE; pytest; test_engine_c parity; toggle-off node-identity. **Effort**: medium-high. **This is the top NPS item by gain×soundness.**

### N2. Drop moves are always legal when not in check: skip their legality filter (minimal, lowest-risk subset of N1)
- **Source**: movegen lens. Verdict: PLAUSIBLE. **Reviewer-measured: drops are 18.4% of legality triples on the start tree, 69.8% on a full-hand tree.**
- **Mechanism**: a drop only adds a friendly non-king piece to an empty square — it cannot become an attacker of the own king, cannot vacate a square (so cannot unblock a Mao), and is never the king. If the king was safe before, it is safe after. (RULES.md:80–82 documents exactly this invariant.)
- **Soundness**: strictly a provable subset of N1; safe to ship even if N1 is deferred.
- **Integration point**: drop generation `tinyhouse.c:193-199`; the filter loops in `th_moves`/`th_perft`/`search`.
- **Toggle & pin**: `#define TH_DROP_FASTLEGAL 1`, skip for `M_IS_DROP(m)` when `!th_in_check(p, us)`; `0` restores (node-identical).
- **Expected gain**: **ESTIMATE** 10–20% NPS on drop-heavy positions (near 0 at the empty-handed start). Confirm: paired `bench_workers.py` on a mid-game TFEN with non-empty hands; report saved legality tests/node.
- **Oracles**: perft(7)=1,355,253; PERFT_ORACLE; pytest; toggle-off node-identity. **Effort**: low.

### N3. Incremental Zobrist key in make/unmake instead of full recompute per node
- **Source**: movegen-opt lens. Verdict: PLAUSIBLE.
- **Mechanism**: `search` calls `th_key(p)` once per node (`tinyhouse.c:424`), XORing 16 board + 8 hand + stm lookups from scratch (~24 dependent reads on the hot struct). A move touches ≤2 board squares + 1 hand slot + stm, so an incremental update is ~4–8 XORs in make and the same in unmake.
- **Soundness**: node-identical — the key **value** must equal the full recompute (mandatory debug oracle: assert `incremental == th_key(p)` at every node during a solve); identical keys ⇒ identical TT probes/stores ⇒ byte-identical proofs.
- **Integration point**: `tinyhouse.c:424` `uint64_t key = th_key(p);` (fed by `th_key` at `tinyhouse.c:281`); XORs added in `make`/`unmake` (`tinyhouse.c:116/135`).
- **Toggle & pin**: `#define INCREMENTAL_KEY 1`; `0` falls back to `key = th_key(p)` (node-identical).
- **Expected gain**: **ESTIMATE** +5–12% NPS. Confirm: `bench_workers.py --depth 16 --workers 1 --repeats 5`, nodes byte-identical, medians compared. **Note:** run each repeat in a fresh process (see I2 — history carryover). **Effort**: medium.

### N4. Incremental king-square tracking to remove the 16-square linear scan in `king_sq`
- **Source**: movegen-opt lens. Verdict: PLAUSIBLE.
- **Mechanism**: `th_in_check` calls `king_sq` (a 16-square linear scan) once per pseudo-move in the legality filter, plus `enemy_ks` once per node for ordering. Only a king move changes a king square, so a cached `king[2]` updated O(1) in make/unmake turns `king_sq` into a table read.
- **Soundness**: returns the identical square ⇒ identical `in_check`. Debug oracle: `assert tracked == king_sq(...)` at every use.
- **Integration point**: `king_sq` `tinyhouse.c:104`; `th_in_check` `tinyhouse.c:110`; `enemy_ks` `tinyhouse.c:467`.
- **Toggle & pin**: `#define TH_INCR_KING 1`; requires `int8_t king[2]` in THPos (an ABI change to `to_c`) or threading `king[2]` as search locals; `0` keeps the scan (node-identical).
- **Expected gain**: **ESTIMATE** 5–20% standalone; smaller once N1 lands (fewer `in_check` calls remain). Confirm: paired `bench_workers.py --depth 16 --workers 1 --repeats 5`.
- **Risk**: the cache must be updated on both make and unmake and initialized in `to_c`; a missed path desyncs (caught by perft drift + parity). **Effort**: medium.

### N5. Staged movegen: try the TT move first without generating or scoring the full list
- **Source**: solver lens. Verdict: PLAUSIBLE.
- **Mechanism**: every node runs `pseudo_moves` then `order_score` over all moves before the loop, even when the TT move (ranked `1<<30`) causes an immediate cutoff. Searching the TT move first from a cheap pseudo-legality check skips one `pseudo_moves` pass + up to ~30 `order_score`/`enemy_ks`/`gives_direct_check` calls on TT-cutoff nodes.
- **Soundness**: node-identical — the TT move is already `order_score`'s top pick, so the searched order is unchanged and all bound/rep math is over the same moves.
- **Integration point**: `tinyhouse.c:452` `int n = pseudo_moves(p, buf);` and the score-all loop at `tinyhouse.c:466-468` (`int scores[128];` / `int enemy_ks = ...;` / `for (i) scores[i] = order_score(...)`); TT probe earlier in `search`.
- **Toggle & pin**: `#define STAGED_MOVEGEN 1`; `0` runs the full path (node-identical).
- **Expected gain**: **ESTIMATE** +5–15% NPS, concentrated on TT-cutoff nodes. Confirm: paired `bench_workers.py`, nodes byte-identical. **Effort**: medium.

### N6. Generate drops by iterating an empty-square mask instead of scanning all 16 squares per hand type
- **Source**: movegen lens. Verdict: PLAUSIBLE.
- **Mechanism**: the drop loop runs `for (s=0..15) if (b[s]) continue;` once per hand type — up to 64 square tests/node. Iterating the complement of an occupancy mask visits only empty squares (8 at start, fewer as material lands).
- **Soundness**: node-identical if empty squares are visited in ascending index order (matching the current scan).
- **Integration point**: `tinyhouse.c:193` `for (int t = 0; t < 4; t++) {`, `tinyhouse.c:195` `for (int s = 0; s < 16; s++) {`, `tinyhouse.c:196` `if (b[s]) continue;`.
- **Toggle & pin**: `#define DROP_MASK_ITER 1`; `0` keeps the scan (node-identical).
- **Expected gain**: **ESTIMATE** +2–6% NPS in drop-heavy nodes; ~0 empty-handed. Requires maintaining an occupancy mask in make/unmake (cost may offset on a 16-byte board — measure). **Effort**: low.

### N7. Bitboard movegen and attack detection over the 16-square board
- **Source**: movegen-opt lens. Verdict: PLAUSIBLE (high ceiling, high effort, **not node-identical**).
- **Mechanism**: the board is exactly 16 squares → occupancy fits a `uint16_t`. `attacked()` currently walks four `0xff`-terminated tables per query; with bitboards, "is sq attacked by type" becomes `(attackers & mask[sq])` tests, quiet moves `mask & ~occ`, captures `mask & enemy`, and Mao blocking a masked emptiness test on the leg square.
- **Soundness**: a faithful mirror must generate the identical pseudo-move set and `attacked()` verdicts; perft is the oracle. Mao semantics must be preserved bit-for-bit.
- **Integration point**: `attacked()` `tinyhouse.c:83-102`; `pseudo_moves()` `tinyhouse.c:150-201`; tables built in `init_tables`.
- **Toggle & pin**: `#define TH_BITBOARD 1`; `0` keeps the array path. **NOT node-identical**: bit-iteration emits moves in ascending-square order vs the current construction order, so within-piece ordering differs → different node counts. Pin via perft (count-invariant) + parity as move-*set* equality, and report nodes-to-depth as a separate paired metric.
- **Expected gain**: **ESTIMATE** +15–50% overall NPS (make/unmake and the filter remain), architecture-dependent (M2 Pro vs others — one-machine caveat). Confirm: paired perft(7) timing medians + `bench_workers.py`. **Effort**: high. Consider N1/N3/N4 first (node-identical, cheaper).

---

## [INSTRUMENT]

### I1. No test pins that the C solver finds the documented mate-in-9 — the whole product is unguarded
- **Source**: instruments lens. Verdict: CONFIRMED. **Reviewer-reproduced the exact oracle.**
- **What**: the suite covers only movegen/perft/parity; **nothing** exercises the search, mate-distance scoring, null-window bounds, or the PROVEN path. Add a test that `th_mate_hunt_mt` from `fuwk/3p/P1F1/KWU1[-] b` returns **0 at depths 7,8** and **29991 (=30000−9) with best `b4c2` at depths 9,10**.
- **Soundness**: read-only oracle over `th_mate_hunt_mt`; pins the soundness product itself (correct PROVEN + correct not-proven-below-horizon), which no current test does.
- **Integration point**: beside `test_engine_c.py:16` `def test_perft_c_deep_start():`. `th_tt_init(N)` fresh before each depth.
- **Reviewer measurement**: 0/0/29991/29991, best `b4c2`, deterministic across seeds 1/12345/999999, sub-second at `tt 2^22`. **Effort**: S. **Highest-value instrument.**

### I2. No nodes-to-depth regression harness — and it MUST fork one search per process because thread-local `history` is never reset
- **Source**: instruments lens. Verdict: CONFIRMED. **Reviewer-reproduced the carryover.**
- **What/Mechanism**: `bench_workers.py` measures wall time with SMP jitter, so it can't serve as an efficiency oracle; nodes-to-depth (load-independent) is the doctrine's metric and nothing records it. **Crucially**, `root_search` does `memset(killers, ...)` (`tinyhouse.c:551`) but never clears `_Thread_local history[2][2048]` (`tinyhouse.c:298`), so an in-process repeat is contaminated: **reviewer-measured** identical fresh-TT hunts return `30137 → 24080 → 24031 → 24032 → 24017` nodes as history warms, vs **30137 every time across fresh processes**. This means `bench_workers.py`'s `--repeats` in one process are **not independent** (repeat 1 cold, later ones warm, ~20% swing) — a real instrument defect that also biases its median and conflates worker effects with history warming. Also relevant to the review's own "toggle-off reproduces node count exactly" oracle: it needs a fresh process, not just a fresh TT.
- **Soundness**: history/killers are ordering-only; a node-count harness cannot change a proof. The persisted history is not itself a bug (it aids deepening) but forces the fresh-process harness design (and argues for an optional `th_history_clear()` so `bench_workers.py` repeats can be made independent).
- **Integration point**: new sibling script; `bench_workers.py` stays worker/time-focused. Anchors: `tinyhouse.c:551` (killers memset), `tinyhouse.c:298` (history decl).
- **Effort**: M.

### I3. No test pins TT save/load round-trip or the seed-mismatch rejection resume depends on
- **Source**: instruments lens. Verdict: CONFIRMED. **Reviewer-reproduced return codes: save=0, same-seed load=0, wrong-seed load=−2, missing=−1.**
- **Mechanism**: `solve_hunt`'s resume dumps and reloads the TT; a regression in the header logic (magic/size/`tt_seed_used`) would lose resumed work or import foreign-seed keys and flag another position's value as PROVEN. Pinning the three return codes locks the trust boundary — directly guards invariant (e).
- **Integration point**: beside `test_engine_c.py:35` `def test_c_roundtrip():`; write the dump to `tmp_path`. **Effort**: S.

### I4. `solve_hunt` resume/checkpoint round-trip is untested
- **Source**: instruments lens. Verdict: CONFIRMED.
- **Mechanism**: the resume path builds a sha1 identity over `tfen|color|seed|tt` and gates both JSON reuse and `th_tt_load`. A regression could silently restart an overnight run from zero or reuse a checkpoint whose meaning changed. A subprocess test: run to a shallow `--maxdepth`, re-run, assert "resumed … table reloaded" and restart at `proven_no_win_through+2`; a mismatched-identity checkpoint must print "starting fresh."
- **Integration point**: `solve_hunt.py:117` `if state_path.exists() and not args.fresh:` / `:119` the identity gate. Use `--tt 20`, low `--maxdepth`, scratch `--state`. **Effort**: M.

### I5. Python/C move-set and `th_result` parity are exercised only from the start position
- **Source**: instruments lens. Verdict: CONFIRMED.
- **Mechanism**: `test_move_sets_match_on_random_walks` seeds every walk from `Position.start()` (`test_engine_c.py:24`), so move-SET equality and `th_result` parity are never checked from the four non-start PERFT_ORACLE roots (full-hand 2274-node drop root, promoted-ferz root, terminal root). A count-preserving-but-which-move-diverging bug, or a `th_result` mismatch (stalemate-win vs loss) in a rich position, would pass unseen.
- **Toggle & pin**: parametrize the walk root over `[t for t,_ in PERFT_ORACLE]` (still green today). **Effort**: small.

### I6. `g_nodes` has no reset; `th_nodes()` is cumulative from process start
- **Source**: solver lens. Verdict: PLAUSIBLE (measurement fidelity).
- **Mechanism**: `g_nodes` is only incremented and read (grep confirms no reset), so every `th_nodes()` is cumulative — paired nodes-to-depth requires differencing, and any second in-process search pollutes it.
- **Integration point**: `tinyhouse.c:324` `th_nodes(void)`; decl `tinyhouse.c:302`.
- **Toggle & pin**: add `th_nodes_reset()` called at `root_search` entry, or a `NODES_AUTORESET = 0` flag keeping current cumulative behavior (byte-identical off). **Effort**: trivial. Pairs naturally with I2.

### I7. `state_count.py` has no independent cross-check and ships a dead `NotImplementedError` stub
- **Source**: instruments lens. Verdict: PLAUSIBLE (coverage add, not a bug).
- **Mechanism**: the headline 17,669,515,462,968 / 4,417,378,865,742 figures come from nested `combinations_with_replacement` + `comb()` over hardcoded domains with nothing verifying the arithmetic. Add a brute recount over a reduced inventory (2 kings + a couple of raw units, small enough to enumerate) cross-checked against the same generator restricted to that inventory. The `placements()` stub at `state_count.py:35` is dead (never called) and can be deleted.
- **Integration point**: `scripts/state_count.py:35` (stub), `:89-90` (prints). **Effort**: M. Note: README only *names* the script; it does not cite the figure, so severity is coverage, not overclaim.

---

## [NEW-IDEA] — draw-proof lane first

### NI1. df-pn WDL draw prover, GHI-safe by reusing the repo's rep-exclusion discipline
- **Source**: draw-proof research lens. Verdict: PLAUSIBLE. **This is the principled settlement of S3/D1 and the real prize.**
- **What**: add a depth-first proof-number (df-pn, Nagai 2002) solver that proves the start is a draw by **disproving** "White forces a win" and "Black forces a win," using `th_moves`/`th_result`/`th_key` as expansion/terminal primitives and treating first-path-repetition as a non-win (draw) leaf.
- **Mechanism**: df-pn is best-first over an AND/OR tree — OR (side whose win we test) wins if ANY child wins; AND (opponent) wins only if ALL do. Terminals come from `th_result` (checkmate = loss, stalemate = win per `Stalemate=win`); a first path-repetition **disproves** the win. Every infinite line is cut at its first repetition, so the disproof DAG is finite. Alpha-beta returns an unsound 0 at its horizon (`tinyhouse.c:455`, no flags) and thus can never emit a PROVEN draw at any depth — df-pn can.
- **Soundness**: invariant (c) and the first-rep=draw game-value equivalence (RULES.md:122; C comment 251–253). GHI safety must be handled explicitly — the standard fix is a Kishimoto–Müller GHI-safe scheme (or df-pn+ with ancestor-aware terminal marking), which also closes the S3/D1 residual by construction.
- **Integration point**: `tinyhouse.c:223` `th_result` reused verbatim as the terminal oracle; the rep-safety pattern at `tinyhouse.c:425` copied for cycle handling. New `int th_dfpn(THPos *p, int color, uint64_t max_entries, uint16_t *pv)` + a `solve_draw.py` driver. Alpha-beta untouched (all existing node counts/mate proofs identical).
- **Expected gain**: **CAPABILITY** (a PROVEN draw or forced win the alpha-beta engine cannot emit). Cost metric = proof-DAG size; honest extrapolation from the null-window hunts (728M nodes to depth 20 White, 302M Black) suggests a full draw proof is large but not obviously infeasible with a bounded table (see NI2).
- **Oracles**: must re-derive 1.Fd1-c2 → mate in 9 with the same ply; must agree with the alpha-beta bounds where they overlap. **Effort**: large. **Novelty**: no proof-number machinery exists in the repo.

### NI2. PN² + fixed-size df-pn table with re-search — the desktop-memory answer
- **Source**: draw-proof research lens. Verdict: PLAUSIBLE (depends on NI1 existing first).
- **Mechanism**: a full PN table over 4.4e12 folded states is >1 TB (RULES.md:150) and infeasible. df-pn stores only visited nodes and, when the table is full, re-derives evicted subtrees from a smaller cache (time-for-space, no correctness loss). PN² (Allis; Nagai–Imai) adds a second-level PN search at each first-level leaf whose small tree is discarded, ordering expansion within a chosen RAM budget. The existing `check_tt_size`/`th_tt_init` (`tinyhouse.c:313`) is the natural memory-budget knob.
- **Soundness**: pure caching/scheduling — re-search recomputes the same (pn,dn) from the same terminals; PN²'s second-level result only orders expansion, never concludes. The root proof still needs `dn=0` backed by real terminals.
- **Toggle & pin**: `static const int PN2_THRESHOLD = 0;` (0 = plain df-pn) and the existing `--tt BITS` sizing the PN table; PN2_THRESHOLD=0 reproduces plain df-pn.
- **Expected gain**: memory ceiling (the binding constraint) traded for re-search overhead (typically a small constant). **Oracle**: result must be table-size-invariant (same proof, same 1.Fd1-c2 mate). **Effort**: large. Precondition: NI1 must exist.

### NI3. Bounded retrograde terminal-shell WDL oracle as an exact leaf evaluator
- **Source**: draw-proof research lens. Verdict: PLAUSIBLE.
- **Mechanism**: although crazyhouse has no full material decomposition (RULES.md:150), the SHELL of positions within `k` plies of a terminal is finite and small for small `k`, and backward induction over it is exact. Seed from `th_result` terminals, generate predecessors (un-move/un-drop/un-capture/un-promote — inverses of make/unmake), label WIN/LOSS within `k`, and use it as an exact terminal oracle so search stops up to `k` plies early on any line entering the shell.
- **Soundness**: a bounded-`k` retrograde can only prove WIN/LOSS within `k` (a DRAW needs the whole graph), so the shell labels **only** win/loss and never a draw — as sound as `th_result` when predecessor generation is complete.
- **Integration point**: `tinyhouse.c:223` `th_result` (the terminal seed); predecessor generation is new code mirroring make/unmake (`tinyhouse.c:116/135`), keyed by `th_key`.
- **Toggle & pin**: CLI `--shell-plies K`; `K=0` disables (node-identical). **Expected gain**: nodes-to-depth (saves up to `k` plies on lines that reach the shell). **Oracle**: every shell entry must equal a forward `th_solve` to depth `k`; the mate-in-9 line must still resolve. **Effort**: large.

### NI4. Fold the 4-element symmetry group into the TT key (negamax-sound, up to 4×)
- **Source**: solver + movegen-opt lenses. Verdict: PLAUSIBLE (medium effort, **verify the automorphisms first**).
- **Mechanism**: `state_count.py` reduces 1.77e13 → ~4.4e12 via a 4-element group {identity, file-mirror, rot180+colorswap, vertical-mirror+colorswap}. If these are true game automorphisms, four game-theoretically identical positions occupy four TT slots today. Canonicalize the key (min over the orbit) at probe/store, while keeping **path-repetition detection on the unfolded physical key**.
- **Soundness**: touches `th_key` and transitively (c)/(d). **Sound only if the four maps are verified true automorphisms** — pawn push direction, `PROMO_RANK`, mao geometry, and the color-swapping element must map hands+stm consistently. The color-flip element negates value (swaps stm), so the fold must track sign. **Precondition oracle (run before folding): apply each transform to the start and confirm perft matches 1,355,253 at depths 1–7.**
- **Integration point**: wrap `th_key` (`tinyhouse.c:281`) with a `th_key_canon` (min over 4 transformed keys) used at probe/store call sites only; `path[]` keeps using `th_key`.
- **Toggle & pin**: `static const int FOLD_SYM = 1;`; `FOLD_SYM=0` is node-identical (fold affects only TT sharing). **Expected gain**: **ESTIMATE** 1.5–3× nodes-to-depth (below the 4× ideal — orbit stabilizers vary, reordering perturbs cutoffs, and each node computes up to 4 keys, an NPS cost). Confirm: paired single-thread nodes-to-depth on/off + the per-map perft oracle. **Effort**: medium. Directly attacks the known-open "symmetry not exploited."

### NI5. Lazy drop materialization / staged movegen in search
- **Source**: movegen-opt lens. Verdict: PLAUSIBLE (**not node-identical**).
- **Mechanism**: `pseudo_moves` always emits every drop (18%+ of moves, more with full hands) even at nodes that cut on the TT move/capture/killer. Generate TT move, captures, and killers first; materialize quiet drops only if no earlier move cuts.
- **Soundness**: legality/values unchanged, but ordering changes vs the current mixed `order_score` ranking → node count moves. **NOT node-identical** — measure as both nodes-to-depth and NPS. Keep `perft`/`th_moves` on the whole-list path.
- **Integration point**: `search` `tinyhouse.c:452` + the selection sort; drop loop `tinyhouse.c:193-200`.
- **Toggle & pin**: `#define TH_STAGED_MOVEGEN 1`; `0` = current path (node-identical off). **Oracle**: 1.Fd1-c2 → mate in 9 still proven; perft unchanged (unstaged path). **Effort**: medium. Overlaps N5 (N5 is the node-identical TT-move-first subset; NI5 is the fuller reordering).

---

## [GUI] (ranked last)

### G1. Cache hits serve the first computation's stale `nodes`/`time`
- **Source**: gui lens. Verdict: CONFIRMED.
- **Mechanism**: on a cache hit `analyze()` returns the stored dict with only `cached=True` added, so `nodes`/`time` describe the first run, not this near-zero one; `index.html:272` prints them next to "· cached". The "· cached" tag keeps it non-misleading, but the numbers are wrong. These fields are pure diagnostics — never inputs to any proof label.
- **Integration point**: `server.py:43` `out["cached"] = True`; `index.html:272`.
- **Toggle & pin**: on cache hit set `out["nodes"] = 0; out["time"] = 0.0`. Removing the two lines restores current behavior. **Effort**: S.

### G2. `/pieces/` serves any file in `pieces/` as `image/svg+xml` regardless of real type
- **Source**: gui lens. Verdict: CONFIRMED (latent; developer-controlled directory, all-SVG today).
- **Mechanism**: after the (correct) `parent==pieces/` traversal guard, `server.py:115` hardcodes `image/svg+xml`; a non-SVG asset added later would be mislabeled.
- **Toggle & pin**: `if f.suffix != ".svg": self.send_json({"error": "not found"}, 404)` before serving. **Effort**: S. **Severity**: trivial/latent.

---

## Killed by the adversarial verifier (2)

1. **[INSTRUMENT] "No test pins that reseeding changes the proof's independence check."** Self-defeating: it proposed asserting the proof value is *equal* under two seeds, but a silent no-op reseed also yields equal values — so the test passes whether reseed works or not. The instrument that actually pins it (assert *keys differ* between seeds) was not proposed. Killed.
2. **[NEW-IDEA] "Seed df-pn proof/disproof numbers from the alpha-beta bounds (df-pn+)."** Presupposes an existing df-pn prover to seed; none exists (the engine is pure fixed-depth alpha-beta). Nothing to seed, no toggleable layer, no metric to run. Killed. (The idea only makes sense *after* NI1.)

---

## What this changes in README's "what is still owed"

The README/`solve_status.json` "known limits" currently list: double-step unverified, 50-move
rule unimplemented, draw proof unreachable, deep SMP unmeasured, symmetry unexploited. This
review adds/qualifies:

1. **The "proof-grade" bounds carry a standard GHI caveat (S3/D1).** The `my_rep >= ply` store
   gate prevents *storing* rep-dependent values but does **not** guard *reuse* of a proven TT
   entry across a transposition where a former winning descendant becomes a repeated ancestor.
   No wrong PROVEN was demonstrated, but cross-seed agreement is **not** sufficient to rule it
   out. Honest wording: the bounds are proof-grade *modulo the standard alpha-beta GHI caveat on
   TT reuse across transpositions*; a definitive draw/bound proof needs df-pn with GHI-safe
   handling (NI1). The comment at `tinyhouse.c:256` should be softened to say so.
2. **The C solver is essentially untested (I1, I3, I4, I5).** No test exercises the search, the
   mate-in-9, TT persistence, resume, or non-start parity — the product's correctness rests on
   perft/movegen tests only. Add the mate-in-9 oracle (I1) at minimum.
3. **Two active trust-boundary holes in the shipped validator (S1, B1):** `from_tfen` accepts a
   promoted king (S1 — produces a snd-flagged wrong proof, user-reachable via the GUI) and a
   back-rank pawn (B1). Both are trivial fixes.
4. **No nodes-to-depth instrument, and `bench_workers.py` repeats are non-independent (I2)** —
   thread-local `history` warms in-process (reviewer-measured 30137→24080), so its median is
   biased and the doctrine's "toggle-off reproduces node count exactly" oracle needs a fresh
   process.

The double-step / 50-move / deep-SMP / symmetry items are unchanged; NI4 is a concrete plan for
the symmetry line and NI1–NI3 for the draw-proof line.

---

## Verification notes

- Every `file:line` above was re-grepped against the live `2054f2d` tree after the mid-review
  drift; the workflow's raw citations drifted ±4–9 lines (moving target) and several were
  corrected here (e.g. horizon branch is `tinyhouse.c:455`, `th_tt_init` is `:313`, the
  `solve_hunt` resume gate is `:117`).
- Reviewer-run oracles (independent of the agents): perft(7)=1,355,253 on current code; 43 tests
  pass; mate-in-9 = 0/0/29991/29991 best `b4c2`; DOUBLE_STEP divergence 6,36,274 vs 6,33,241;
  history carryover 30137→24080→24031→24032→24017 (same process) vs 30137×3 (fresh processes);
  TT save/load 0 / same-seed 0 / wrong-seed −2 / missing −1; promoted-king `KK~2/4/4/3k[-] w`
  accepted → v=29995 snd=1; skippable legality 72.0% (start) / 73.9% (full-hand).
- Verifier killed 2 of 34 (both presupposed nonexistent machinery or were self-defeating).
