# Tinyhouse v1 review — opus 4.7

## Baseline drift

No drift. All six claimed line counts match exactly (tinyhouse.py=372, tinyhouse.c=626, engine_c.py=85, server.py=137, index.html=410, solve_hunt.py=162). The 43-test suite passes clean in 6.73s. The perft(7) drift oracle returns 1,355,253 as claimed. All five recent commit SHAs are present at the top of the log in the stated order.

## Counts

raw: 39 | deduped: 38 | verifier killed: 4 | confirmed: 34

Per-category:
- BUG-SOUNDNESS: 1
- BUG: 4
- DOC-OVERCLAIM: 2
- EFFICIENCY: 2
- NPS: 6
- INSTRUMENT: 7
- NEW-IDEA: 4
- SHOULD-BE-BETTER: 8

## Findings

### 001. [BUG-SOUNDNESS] TFEN parser accepts `~` on K and P, admitting a phantom promoted king or pawn on the board
**Source:** LENS 3: tinyhouse.py + Python/C divergence
**Mechanism:** `from_tfen` sets `promoted=True` whenever the next character is `~` and stores `piece(color, t, promoted)` without checking `t in (F, U, W)`. The unit-count loop skips K entirely and buckets other promoted pieces under P, so a K~ contributes to no bucket and `pos.board.count(piece(color, K)) != 1` counts only value 5/21 (unpromoted K), never value 13/29 (K~). `K~K1k/4/4/4[-] w` parses: board holds two white kings; `ptype(13)&7-1 = K`, so pseudo_moves generates KING mobility for the phantom, `attacked()` treats it as an attacker, and the legality filter only asks whether king_sq(WHITE)=13 is attacked — so the phantom king moves without any restriction on itself. A solver run through server.py on such a position returns a PROVEN claim for a game whose rules Tinyhouse does not define.
**Soundness:** This IS the trust-boundary invariant. The fix (`if promoted and t not in (F, U, W): raise ValueError(...)`) between the current lines 130 and 133 tightens the parser without touching movegen, search, or the perft oracle, so every valid position parses unchanged and every existing test still passes.
**Integration:** tinyhouse.py:130 — from_tfen
```
                    promoted = j + 1 < len(rank) and rank[j + 1] == "~"
                    if promoted:
                        j += 1
                    pos.board[_sq(f, r)] = piece(color, t, promoted)
```
**Toggle / pin:** No runtime toggle — it is a parse-time reject. Reverting reproduces current behaviour byte-identically; perft numbers are node-identical because no valid start position parses through the new gate.
**Expected gain:** Closes one route to unsound solver output on user-supplied TFEN. Metric: number of malformed-TFEN classes rejected (K~, k~, P~, p~; currently 0 → 4 after fix). Confirm by adding reject cases to `test_from_tfen_rejects_malformed`.
**Risk:** Zero if the check is `t not in (F, U, W)`.
**Oracles:** pytest -q (43 tests, must stay green); new malformed-TFEN test cases for K~/k~/P~/p~; perft(7)=1,355,253 unchanged.
**Effort:** S — 2 lines in from_tfen plus 2 test cases.
**Novelty:** Not in ALREADY DONE. Commit e97ae52 tightened TFEN at the trust boundary (side-to-move, king count, in-check for wrong side, hand-count OOB) but did not restrict which types may carry a `~` marker.
**Verifier notes:** Confirmed live: `Position.from_tfen('K~K1k/4/4/4[-] w')` returns a Position with board index 12=13 (K~ white) and index 13=5 (K white). Fix `if promoted and t not in (F, U, W): raise ValueError(...)` between current lines 130 and 133 is minimal and does not touch any valid-position path.

### 002. [BUG] Python DOUBLE_STEP toggle has no C mirror and engine_c.py does not assert it is off — flipping it silently desynchronises the two engines on the solver path
**Source:** LENS 3: tinyhouse.py + Python/C divergence
**Mechanism:** tinyhouse.py:13 declares `DOUBLE_STEP = False`; lines 241-245 add three promotion moves per pawn on the relative 2nd rank when True. tinyhouse.c has no analogous branch — `case P:` only generates the single-square push. engine_c.py does `import tinyhouse as T` and never reads `T.DOUBLE_STEP`. Verified: with DOUBLE_STEP=True on `3k/4/P3/K3[-] w` Python generates {a2a4=F/U/W} moves that C never emits. solve_hunt.py, server.py, and the CLI drive the C engine directly and would happily proceed to prove `mate in N` on a game whose rules Python and C disagree about.
**Soundness:** Import-time `assert not T.DOUBLE_STEP, 'engine_c has no double-step; enable it in tinyhouse.c first'` in engine_c.py does not touch the search, adds no runtime overhead after import, and turns a silent parity break into a loud crash the first time the shared library is loaded.
**Integration:** engine_c.py:10 — module import
```
import tinyhouse as T
```
**Toggle / pin:** DOUBLE_STEP itself IS the visible in-file toggle at tinyhouse.py:13. Current setting is False, so the assert is node-identical.
**Expected gain:** Converts silent-divergence into an import-time crash. Metric: N-of-1 fail-fast at engine_c import.
**Risk:** Zero as long as the assert triggers only on `T.DOUBLE_STEP is True`.
**Oracles:** pytest -q; manually flip DOUBLE_STEP=True and confirm engine_c fails at import.
**Effort:** S — one line in engine_c.py at import site.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Include a mnemonic in the message pointing to the C-side edit needed (case P: in tinyhouse.c near line 159 plus regenerating libtinyhouse.dylib). Parity tests that monkeypatch DOUBLE_STEP=True at runtime remain unaffected because the assert fires at engine_c import.

### 003. [BUG] Rapid clicks before load() resolves corrupt state.hist in the GUI
**Source:** LENS 4
**Mechanism:** playMove mutates state.hist/state.histAt synchronously and only THEN awaits load(). state.info is not updated until load()'s promise resolves (line 290). If the user clicks a second legal move before that resolve, playMove re-reads OLD state.info.moves, appends a next TFEN derived from the pre-first-click position, and increments histAt. The loadSeq guard silences the stale response but does not repair state.hist; subsequent Undo jumps to a position the user never navigated to.
**Soundness:** Client-side history bookkeeping only. The search always runs on the TFEN the server received; no proof is ever wrong.
**Integration:** index.html:245 — playMove
```
  state.histAt++;
  return load(next);
```
**Toggle / pin:** Add a `state.pending` boolean set true at playMove entry and cleared in load()'s finally; reject playMove while pending. Removing the guard is byte-identical to today.
**Expected gain:** Eliminates a rare corrupted-history state; N-of-1 manual rapid-click test.
**Risk:** UI feels slightly less responsive under fast repeated input because inputs are dropped instead of queued.
**Oracles:** manual rapid-click test; pytest -q (still 43 green).
**Effort:** S — one boolean guard, ~5 lines.
**Novelty:** Not in ALREADY DONE — the fixed btnload race was validation vs. history clobber, a different one.
**Verifier notes:** Same window also affects the moves-table row onclick (line 278) and the history-span onclick at line 255 which calls load() directly — the guard should live in load() (or be checked by both entry points) so history-clicks are also debounced. The Play-best-line loop at line 313 already awaits playMove so it self-serializes.

### 004. [BUG] History move numbering assumes the initial position has white to move
**Source:** LENS 4
**Mechanism:** renderHistory uses `i % 2 === 0` on the history index alone, ignoring the initial state's stm. A game starting from a black-to-move setup labels the first black move as `1.<move>` instead of `1... <move>`, and every subsequent number is off.
**Soundness:** Display-only.
**Integration:** index.html:253 — renderHistory
```
    s.textContent = (i % 2 === 0 ? (i / 2 + 1) + "." : "") + m;
```
**Toggle / pin:** Store `state.startStm` at btnstart/btndone/btnload time (parse stm from TFEN, default `w`), then shift the parity/number accordingly. Character-identical for the default START.
**Expected gain:** Correct notation for black-to-move setup positions; N-of-1 spot check.
**Risk:** None.
**Oracles:** manual: load a black-to-move TFEN and verify the first move renders as `1... m`; pytest -q unchanged.
**Effort:** S — a couple of lines and one extra state field.
**Novelty:** Not in ALREADY DONE — the fixed setup label desync was btnsetup's stm button, not history rendering.
**Verifier notes:** Cleanest pin: `state.startStm` at start/setup/load time; in renderHistory shift so index 0 is `1... m` when startStm==='b', then odd i as `N.` and even i (>0) as continuation.

### 005. [BUG] /api/analyze clamps depth from above but not from below
**Source:** LENS 4
**Mechanism:** `min(int(q.get("depth", 12)), 22)` only enforces the ceiling; negative or zero ints pass through to `th_solve` whose behaviour at non-positive depth is unspecified. The GUI select never sends bad values, so this only bites direct API callers.
**Soundness:** Input validation at the trust boundary; existing search invariants unchanged.
**Integration:** server.py:123 — do_GET
```
                self.send_json(analyze(q["tfen"], min(int(q.get("depth", 12)), 22)))
```
**Toggle / pin:** Change to `max(1, min(int(q.get("depth", 12)), 22))`. For every depth the GUI actually sends (8..22) the result is byte-identical.
**Expected gain:** Robustness; no visible change for the GUI. Confirm with `curl /api/analyze?tfen=...&depth=0` before/after.
**Risk:** None.
**Oracles:** manual curl with depth=0 and depth=-5; pytest -q unchanged.
**Effort:** S — one edit.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Non-integer parses already caught by the outer try/except (returns 400), so `max(1, ...)` is sufficient — no need to reject explicitly.

### 006. [DOC-OVERCLAIM] solve_hunt.py labels the negative "no forced win within N plies" checkpoint as `(proven)` but only recommends seed re-verification for the positive-mate case
**Source:** LENS-2-tinyhouse.c-TT-SMP-soundness
**Mechanism:** A Zobrist collision at a shared TT slot returns another position's stored value; if that value is 0 (unproven or non-mate) with stored_depth >= probe depth, it shortcuts search of a subtree that actually contains a terminal mate. Alpha-beta then does not propagate the mate, root returns v <= MATE_BOUND, and the "no forced win within N plies" claim is falsely emitted. Symmetric with the mate-faking direction that IS re-verified.
**Soundness:** Does not change any invariant in tinyhouse.c; only adds a verification step for the negative claim. The seed-reseeding mechanism (th_seed + --seed + --fresh) was built for exactly this.
**Integration:** solve_hunt.py:211 — `<module>`
```
    print(f"  => no forced {name} win within {d} plies (proven, checkpointed)", flush=True)
```
**Toggle / pin:** Add the same `if not args.seed: print(re-verify command)` branch that lives at line 204-207 (positive-mate case) to the negative case at line 211. Print-only, node-identical.
**Expected gain:** Adds one honest verification step for the currently-quoted negative bounds in solve_status.json (depth 20 White, depth 22 Black). Confirmed by rerunning `solve_hunt.py 0 --maxdepth 20 --seed 0xC0FFEE --fresh` and `1 --maxdepth 22 --seed 0xC0FFEE --fresh` and checking that both return v <= 29000 at the same depths.
**Risk:** None to search correctness; only more noise on the console.
**Oracles:** solve_hunt.py --seed 0xC0FFEE --fresh at depth 20 (White) and depth 22 (Black) returning v <= 29000.
**Effort:** S — one print block copy.
**Novelty:** New; the ALREADY DONE list covers only the collision-mitigation code (th_seed / --seed).
**Verifier notes:** Fix is a copy of the 204-207 block guarded by `if not args.seed:`, inserted after line 211. Print-only, node-identical, no soundness change to tinyhouse.c.

### 007. [DOC-OVERCLAIM] PERFT_ORACLE docstring claims deeper counts were "hand-verified" and "cross-checked by three independent implementations" — only start-position depth 1-2 was hand-enumerated
**Source:** LENS 5
**Mechanism:** The docstring invites the reader to trust every listed count as hand-verified; in fact the ~50k-node counts in position 3 and the 16021-node depth-5 in position 1 are self-cross-checked by two implementations of the same author's rules (Python and C) but not against an external reference. Rewriting the docstring to state exactly what was hand-verified vs a cross-implementation drift oracle protects future readers.
**Soundness:** Docstring-only edit. Does not change any test value.
**Integration:** test_tinyhouse.py:3 — (module docstring)
```
"""Tinyhouse engine tests. Perft oracle: values hand-verified at depth 1-2 from
the start position (all 33 nodes enumerated manually) and cross-checked by three
independent implementations written from RULES.md alone."""
```
**Toggle / pin:** Docstring edit only. Reverting reproduces prior text; all tests still pass byte-identically.
**Expected gain:** Reader no longer mistakes the deeper perft counts for hand-verified ground truth.
**Risk:** None.
**Oracles:** pytest -q.
**Effort:** S — 3-line docstring rewrite.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Rewrite to distinguish hand-verified (start position, depth 1-2, 33 nodes) from cross-implementation drift oracle (deeper counts between Python and C implementations of the same author's rules).

### 008. [EFFICIENCY] Prune drops that cannot resolve check
**Source:** LENS 7
**Mechanism:** `pseudo_moves` emits all 4*empties drops unconditionally, then `search()`'s legality filter runs `make + th_in_check + unmake` for each. When the side to move is in check, none of those drops except the ~0-1 mao-blocker squares can be legal (no sliders exist on a 4x4 leaper board; only U-check is blockable and only at exactly one square per attacker). Detecting the check kind once at node entry and restricting drop targets collapses the drop iteration from ~40 to 0-1 per check node.
**Soundness:** Drops never remove pieces; they cannot resolve leaper (P/F/W/K) check except by blocking — impossible for 1-square leapers — or by capturing — impossible for drops. For a mao (U) check, only the exact mao-blocker square between attacker and king can resolve. Pruning others changes only which moves the search sees as filtered-illegal, not the legal-move set.
**Integration:** tinyhouse.c:193 — pseudo_moves
```
    for (int t = 0; t < 4; t++) {
        if (!p->hands[us][t]) continue;
        for (int s = 0; s < 16; s++) {
            if (b[s]) continue;
            if (t == P && ((s >> 2) == 0 || (s >> 2) == 3)) continue;
            out[n++] = MV_DROP(t, s);
        }
    }
```
**Toggle / pin:** `#define PRUNE_CHECK_DROPS 0` at top; when 1, if `th_in_check(p, us)` compute allowed drop-target mask (empty if leaper check, {blocker} if single mao check, empty if double check) and emit drops only for squares in that mask. Node-identical when off. When on, perft is IDENTICAL because pruned drops were all illegal.
**Expected gain:** Estimate 10-25% NPS on the mate hunt. Paired median of 5 runs on M2 Pro; report NPS deltas and total wall time for a fixed-node budget on 1.Fd1-c2.
**Risk:** Misclassifying the attacker set (esp. discovered/double check from enemy's last move) could drop a legal check-blocker; guard with an assert under -UNDEBUG that any pruned drop, when actually made, would leave the mover in check.
**Oracles:** pytest -q; perft(7)==1,355,253; test_engine_c parity; 1.Fd1-c2 mate-in-9 reproduces; toggle-off reproduces pre-change node count exactly.
**Effort:** M — one classify-check helper + a masked drop emit branch.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** More accurately NPS than EFFICIENCY — nodes-to-depth unchanged; saving is fewer make/th_in_check/unmake calls per check node. Double-mao-check: allowed mask is intersection of the two blocker singletons (usually empty).

### 009. [NPS] Skip make/unmake legality filter for moves that cannot expose our king
**Source:** LENS 7
**Mechanism:** `search()` at line 474-475 does `make + th_in_check + unmake` for every pseudo move. Because no piece is a slider (P/F/W/K are 1-square leapers, U is a blockable mao), the only way a non-king move can expose our king is by vacating a square that was blocking an enemy mao ray. Compute `mao_pin_bb` once per node (walk enemy U bitboard, look up MAO_MOVES entries whose target is our king, mark blocker as pinned iff it holds one of our pieces). Then king moves and moves from a pinned square get make+in_check; every other piece move and every drop skip the filter.
**Soundness:** Proof by exhaustion of enemy attackers: after moving a non-king, non-mao-pinned piece from F to T, king K is unchanged and each enemy attacker A of K is either (a) same as before with same blocker state, or (b) newly attacking because F was on its ray/adjacency. Leapers P/F/W/K adjacency to K is fixed; moving from F does not change whether any leaper at X (X!=F) attacks K. For U, unblocking requires F on the (A,K) mao-blocker line — exactly the pinned-mask condition. Drops add to empty squares, cannot expose. Filtered set equals legal-move set exactly.
**Integration:** tinyhouse.c:474 — search
```
        make(p, m, &u);
        if (th_in_check(p, 1 - p->stm)) { unmake(p, &u); continue; }
```
**Toggle / pin:** `#define SKIP_LEGALITY_NONPINNED 0`; when 1, compute `mao_pin_bb` and `in_check_now` at node entry, then skip th_in_check when `!in_check_now && !M_IS_DROP(m) && M_FROM(m) != king && !((mao_pin_bb >> M_FROM(m)) & 1)`. Node-identical when off; perft IDENTICAL when on.
**Expected gain:** Estimate 20-40% NPS on search and perft. Pair perft(8) and mate-hunt depth-N times, medians of 5.
**Risk:** A missing pin case would let an illegal move through and immediately break perft; assert under -UNDEBUG that every skipped move, when applied, does not leave us in check.
**Oracles:** pytest -q; perft(7)==1,355,253; test_engine_c parity; 1.Fd1-c2 M9; toggle-off reproduces node count exactly.
**Effort:** M — one pin-mask helper, a two-line skip guard in search and th_moves, plus a debug cross-check.
**Novelty:** Not in ALREADY DONE; complements the bitboard-attacked finding but is independent.
**Verifier notes:** Quote at lines 478-479 (finding cites 474-475). Pin_bb from MAO_MOVES[e][*] where e is an enemy U square and target equals king_sq(us); mark blocker only when it holds one of our pieces. Magnitude estimate is aggressive but direction plausible since th_in_check is a hot path.

### 010. [NPS] Bitboard-based attacked() replaces per-neighbor board reads with u16 masked tests
**Source:** LENS 7
**Mechanism:** 16 squares fit in u16, so `piece_bb[color][type]` (10 u16 words) captures the whole layout. `attacked(sq, by)` becomes `(piece_bb[by][W]|piece_bb[by][K]) & ORTH_MASK[sq]`, then diag, then `piece_bb[by][P] & PCAP_MASK[1-by][sq]`, then mao attackers filtered by `MAO_ATT_MASK[sq]` with per-(attacker,target) blocker bit tested against `occ`. Current code chases pointer arrays and does `p->board[*n]` cache-missing loads for every neighbor.
**Soundness:** Pure rewrite of attacked() over the same representation with new bitboards maintained as pure functions of the board. Invariants asserted under -UNDEBUG. Perft node-identity holds.
**Integration:** tinyhouse.c:83 — attacked
```
static int attacked(const THPos *p, int sq, int by) {
    const uint8_t *n;
    for (n = ORTH[sq]; *n != 0xff; n++) {
        int pc = p->board[*n];
        if (pc && COLOR(pc) == by && (TYPE(pc) == W || TYPE(pc) == K)) return 1;
    }
```
**Toggle / pin:** `#define TH_BB_ATTACKED 0`; when 1 make/unmake update bitboards and `attacked()` uses masks. `th_prime()` computes bitboards from the board at the Python entry points. Node-identical when off. -UNDEBUG cross-check compares to old function on every call.
**Expected gain:** Estimate 15-30% NPS on search. Medians of 5 paired runs on M2 Pro. attacked() fires from every legality test plus every quiescence probe in horizon.
**Risk:** Mao blocker logic must handle blocker on either color; a wrong mask for a specific (attacker, target) pair would misregister attackers. Mitigate with -UNDEBUG cross-check plus perft oracle.
**Oracles:** pytest -q; perft(7)==1,355,253; test_engine_c parity; 1.Fd1-c2 M9; toggle-off reproduces node count exactly.
**Effort:** M — 10 bitboards, occ, four bitmask tables, incremental updates, prime function; ~120 LOC.
**Novelty:** Not addressed by any prior commit.
**Verifier notes:** Mao mask must encode BOTH attacker and specific blocker per (from,to) — use the existing MAO_ATT[sq][i][0/1] pair table, AND attacker-set against piece_bb[by][U] and test `occ & (1 << blocker) == 0`. Add cross-check inside attacked() itself. Prime bitboards in th_prime() AND any Python-facing entry point that mutates the board without going through make/unmake.

### 011. [NPS] Cache the two king squares on THPos and maintain incrementally
**Source:** LENS 7
**Mechanism:** `th_in_check` calls `king_sq` which does a 16-element `p->board[s] == target` scan; fires once per pseudo move in the legality filter (line 475) and again in `attacked` walk when checking neighbors. On perft(7)=1,355,253 the scan runs millions of times; replacing with a byte read from `p->king_sq[color]` is unconditionally faster.
**Soundness:** Invariant: after every make/unmake, `p->king_sq[c]` equals index of PIECE(c,K,0) (updated on K moves; drops can never be K, promotions can never produce K). Perft node-identity by construction.
**Integration:** tinyhouse.c:104 — king_sq
```
static int king_sq(const THPos *p, int color) {
    int target = PIECE(color, K, 0);
    for (int s = 0; s < 16; s++) if (p->board[s] == target) return s;
    return -1;
}
```
**Toggle / pin:** `#define TH_CACHE_KING 0`; when 1, `king_sq()` returns `p->king_sq[color]`, make/unmake update on king moves, and Python-facing entries call `th_prime(p)` at trust boundary. Node-identical when off.
**Expected gain:** Estimate 5-12% NPS across perft and search. Paired median of 5 runs of perft(8) on start and 1.Fd1-c2 mate-hunt.
**Risk:** Missed update path desyncs cache; guard with `#ifndef NDEBUG` re-scan-and-assert.
**Oracles:** pytest -q; perft(7)==1,355,253; test_engine_c parity; 1.Fd1-c2 M9; toggle-off reproduces node count exactly.
**Effort:** S — one struct field, one prime helper, four update sites (make/unmake king move).
**Novelty:** Not addressed by any prior commit.
**Verifier notes:** Enemy-king capture mid-make can leave captured-side cache stale, but no live query reads it (every post-make th_in_check checks 1-p->stm = original mover, still on board), and unmake restores the board before any deeper query fires. Prime helper must also run inside th_load_tfen if it exists C-side.

### 012. [NPS] Cache the mover's king square across the pseudo-move legality filter
**Source:** LENS 1: tinyhouse.c movegen and make/unmake
**Mechanism:** `th_in_check(p, 1-p->stm)` is invoked once per pseudo-move in th_moves, th_perft, and search. Each call runs king_sq (linear scan over 16 board cells) before attacked() even starts. Since only a king move changes the mover's king square, caching it at the top of the loop and updating to M_TO(m) iff the move started at the cached king square (and is not a drop) eliminates that scan from every non-king-move filter — typically 40+ moves per node.
**Soundness:** Pure representation change: `king_sq(p, 1-p->stm)` after make() is identical to `(M_IS_DROP(m) || M_FROM(m) != us_ks) ? us_ks : M_TO(m)`. make() only changes the moving piece's location (never the enemy king; kings never in hand). attacked() sees the same square as before.
**Integration:** tinyhouse.c:211 — th_moves / th_perft / search
```
        if (!th_in_check(p, 1 - p->stm)) {
            if (out) out[nl] = buf[i];
            nl++;
        }
```
**Toggle / pin:** `#define KING_CACHE 1` at top; #if KING_CACHE compute us_ks once and use `attacked(p, ks_after, 1-p->stm)`, #else keep current th_in_check call. Off is node-identical.
**Expected gain:** Estimate 8-15% NPS on perft(7). Confirm by paired median over 5 runs with toggle flipped.
**Risk:** Off-by-one on which move actually moved the king (drop vs board move); tests catch via perft mismatch.
**Oracles:** pytest -q; python engine_c.py 7 -> perft(7)==1355253; random walk parity; toggle-off reproduces perft(7) time within noise.
**Effort:** S — ~20 lines across three call sites.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Apply cache in three call sites: th_moves (line 205), th_perft (line 228), and the two loops in search (horizon at line 456 and main at line 474). At each entry compute `us_ks = king_sq(p, p->stm)`; after make(m), `ks_after = (M_IS_DROP(m) || M_FROM(m) != us_ks) ? us_ks : M_TO(m)`; call `attacked(p, ks_after, 1 - p->stm)`. Do NOT cache across recursion — recompute at each function entry.

### 013. [NPS] Incremental Zobrist key maintenance in make/unmake
**Source:** LENS 1: tinyhouse.c movegen and make/unmake
**Mechanism:** Every search() call runs th_key(p) once for TT probe, and inside root_search/th_root_moves it is called again for best-move lookup. Cost per key is 24 XORs plus 16 zero-checks. Incremental: store key in THPos, XOR out old codes in make(), XOR in new codes; unmake() reverses. Reduces to a handful of ops per move.
**Soundness:** Invariant `stored_key == th_key(p)` after every make/unmake. Provable by tracing branches: drop = XOR-out one hand code + XOR-in one piece code + STM flip; move = XOR-out mover from frm, XOR-in mover (or promoted) at to, XOR-out captured piece at to if any + XOR-out old hand slot + XOR-in new hand slot for capturer, STM flip. Zobrist tables unchanged, so TT keys and persistence loader stay compatible.
**Integration:** tinyhouse.c:281 — th_key
```
uint64_t th_key(const THPos *p) {
    uint64_t k = p->stm ? zob_stm : 0;
    for (int s = 0; s < 16; s++) if (p->board[s]) k ^= zob_piece[s][(int)p->board[s]];
    for (int c = 0; c < 2; c++) for (int t = 0; t < 4; t++)
        k ^= zob_hand[c][t][(int)p->hands[c][t]];
    return k;
}
```
**Toggle / pin:** `#define INCREMENTAL_KEY 1`; on: extend THPos with `uint64_t key` field maintained by make/unmake, let th_key(p) return p->key. Off keeps linear recompute. Debug builds assert `p->key == th_key_recompute(p)` per make/unmake.
**Expected gain:** Estimate 5-15% NPS in the mate hunt.
**Risk:** HIGH — one missed XOR corrupts TT keys and silently returns wrong stored values. Requires debug-only assert per make/unmake and re-verification against recorded 1.Fd1-c2 mate-in-9 under multiple seeds before trusting.
**Oracles:** pytest -q; perft(7)==1,355,253; test_engine_c parity; solve_hunt.py --seed 0xC0FFEE --fresh matches recorded M9; cross-seed rerun (--seed 0xDEADBEEF); debug build asserts.
**Effort:** M — ~40 lines across make, unmake, header, plus debug-only assert.
**Novelty:** Not in ALREADY DONE; complementary to SMP or persistence work.
**Verifier notes:** Verified th_key is the per-node key source at search() line 424. Compile-time toggle with debug-only assert at every make/unmake is the correct gate; oracles must include perft(7)=1,355,253 and test_engine_c random-walk parity under an assertion build, plus a fresh --seed 0xC0FFEE mate-in-9 rerun before the toggle is trusted with asserts off.

### 014. [NPS] Sound one-legal-move short-circuit in the horizon
**Source:** LENS 7
**Mechanism:** Horizon path at line 451-460 iterates all pseudo moves and does full make/in_check/unmake per candidate until one legal is found. Under Finding 009, drops are proven legal when not in check, so if `hands[us]` has any piece and the board has any legal drop square, set `any=1` without a single make/unmake. Even without pin optimization, iterating drops before piece moves shortens the loop.
**Soundness:** Horizon returns 0 (no soundness) for non-terminal and ±(MATE-ply) with SND_LB|SND_UB for terminal. Short-circuit only sets `any=1` when a legal move genuinely exists.
**Integration:** tinyhouse.c:451 — search
```
    if (depth <= 0) {
        for (int i = 0; i < n && !any; i++) {
            make(p, buf[i], &u);
            if (!th_in_check(p, 1 - p->stm)) any = 1;
            unmake(p, &u);
        }
```
**Toggle / pin:** `#define HORIZON_DROP_SHORTCUT 0`; when 1, before loop: if `!th_in_check(p, us)` and any hand slot non-zero and some legal drop square exists (empties respecting pawn rank rule), set any=1. Otherwise fall through. Node-identical when off.
**Expected gain:** Estimate 3-8% NPS on the mate hunt. Independent gain source from other search optimizations.
**Risk:** Miscounting hand parity or pawn-rank restriction could short-circuit when no legal drop exists; guard with an assert naming a concrete drop move that would pass the legality filter.
**Oracles:** pytest -q; perft(7)==1,355,253; test_engine_c parity; 1.Fd1-c2 M9; toggle-off reproduces node count exactly.
**Effort:** S — one guarded early-exit at the top of the horizon branch.
**Novelty:** Not in ALREADY DONE; distinct from check-drop pruning.
**Verifier notes:** Simplest implementation: when not th_in_check(p, us), test buf[n-1] (drops are appended after piece moves in pseudo_moves, so a drop lands last when hands are non-empty and a legal drop square exists; pawn rank filter already applied at generation). A single M_IS_DROP(buf[n-1]) test avoids the make/in_check/unmake for the common case.

### 015. [NPS] Precompute empties list once in pseudo_moves, iterate per hand type
**Source:** LENS 1: tinyhouse.c movegen and make/unmake
**Mechanism:** Current inner loop is `for (int t = 0; t < 4; t++) if (hands[us][t]) for (int s = 0; s < 16; s++) { if (b[s]) continue; ... }`. If mover has 3 hand types, that is 48 board-cell reads plus branches. An up-front sweep `int emp[16], ne = 0; for (int s = 0; s < 16; s++) if (!b[s]) emp[ne++] = s;` shrinks the inner cost to ne (typically 6-10) per type and preserves the pawn back-rank filter.
**Soundness:** Textual refactor: same drops emitted in same order. Perft is the oracle.
**Integration:** tinyhouse.c:193 — pseudo_moves
```
    for (int t = 0; t < 4; t++) {
        if (!p->hands[us][t]) continue;
        for (int s = 0; s < 16; s++) {
            if (b[s]) continue;
            if (t == P && ((s >> 2) == 0 || (s >> 2) == 3)) continue;
            out[n++] = MV_DROP(t, s);
        }
    }
```
**Toggle / pin:** `#define EMPTIES_ONCE 1`; #if EMPTIES_ONCE precomputed-list variant, #else current double loop. Off is node-identical.
**Expected gain:** Estimate 2-5% NPS on perft(7) start (drops rare), higher (5-10%) on hands-heavy TFENs.
**Risk:** Very low.
**Oracles:** pytest -q; engine_c.perft on all PERFT_ORACLE tfens; python engine_c.py 7 -> 1355253.
**Effort:** S — ~6 lines.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Expected gain optimistic: current inner test is a well-predicted branch and 16 board reads are L1-hot; realistic NPS lift on M2 Pro likely under 2% except on hands-heavy TFENs. Confirm with paired perft timing. Ensure empties list is scoped inside pseudo_moves (not file-static) to keep the function reentrant for future SMP work.

### 016. [INSTRUMENT] No test pins the search's output on ANY known mate
**Source:** LENS 5
**Mechanism:** 43 tests cover perft, rules, TFEN, and the C engine's move set, but not one exercises th_solve, th_mate_hunt, or th_root_moves. A regression that changes alpha-beta bounds, mate-distance encoding, ply adjustment, sound-flag propagation, or null-window hunt sign trips no test — the solver is the product, and it has zero automated coverage. Add tests that run th_solve on `k3/W1F1/1K2/4[p] b` (mate in 1) asserting value==-(MATE-1) and snd==(SND_LB|SND_UB), plus th_mate_hunt on the recorded 1.Fd1-c2 line proving Black mate in 9 (value 30000-9=29991).
**Soundness:** Instrument only.
**Integration:** test_engine_c.py:38 — (new test at end of file)
```
def test_c_roundtrip():
    pos = T.Position.from_tfen("1uwk/P3/3p/K2F[UWf] w")
    assert engine_c.to_py(engine_c.to_c(pos)).tfen() == pos.tfen()
```
**Toggle / pin:** New tests only. Pinned values: th_solve on `k3/W1F1/1K2/4[p] b` at depth 2 returns -29999, snd==3; th_mate_hunt on `fuwk/3p/P1F1/KWU1[-] b` color=1 depth 10 returns 29991; best move matches PV 'b4c2'.
**Expected gain:** Catches any soundness break in search/tt_probe/tt_store/root_search that changes a proven value. 0 → 3+ pinned contracts.
**Risk:** None to correctness; mate-in-9 test adds a few hundred ms to CI.
**Oracles:** pytest -q; re-run 1.Fd1-c2 -> mate in 9.
**Effort:** S — three parametrized cases, ~30 lines.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Cited line 38 is past current EOF; anchor after test_c_roundtrip (35-37). Verify pin values by running th_solve once on the target positions before locking them into asserts — do not hand-derive.

### 017. [INSTRUMENT] No round-trip test of th_tt_save/th_tt_load
**Source:** LENS 5
**Mechanism:** th_tt_save writes hdr = {magic, tt_mask+1, tt_seed_used} then the raw TTEntry array; th_tt_load refuses on magic/size/seed mismatch. If the loader's return-code contract (-1 missing/unreadable, -2 size/seed mismatch, 0 ok) drifts, solve_hunt.py's resume banner prints the wrong message and either re-searches or imports a table under the wrong Zobrist seed (silent unsoundness). Test: (a) solve to depth 8 and save, (b) re-init TT, load, re-solve at depth 8, assert value+best-move identical, (c) re-init and mutate th_seed then assert th_tt_load returns -2.
**Soundness:** Test-only; verifies persistence preserves proof values and seed-mismatch rejection actually rejects — directly load-bearing for multi-hour resumed runs.
**Integration:** test_engine_c.py:38 — (new test at end of file)
```
def test_c_roundtrip():
    pos = T.Position.from_tfen("1uwk/P3/3p/K2F[UWf] w")
    assert engine_c.to_py(engine_c.to_c(pos)).tfen() == pos.tfen()
```
**Toggle / pin:** New test only; scratch file under tmp_path fixture.
**Expected gain:** Catches header format drift, size-mismatch mishandling, seed-mismatch mis-detection. 0 → 3 branches pinned.
**Risk:** Small file write; sub-second.
**Oracles:** pytest -q.
**Effort:** S — one test, ~25 lines.
**Novelty:** TT persistence landed in 09a18fd; no round-trip test committed with it.
**Verifier notes:** Test needs to expose th_tt_save/th_tt_load via engine_c (currently only declared in the header block inside engine_c.py); use engine_c.lib directly with encoded bytes. Seed-mismatch branch requires calling `engine_c.lib.th_seed(new_seed)` between save and load — verify that call also re-inits so tt_seed_used actually updates; if seeding does not touch tt_seed_used, the -2 path will not trigger.

### 018. [INSTRUMENT] No test asserts lazy-SMP hunt returns same proof as single-threaded
**Source:** LENS 5
**Mechanism:** root_search spawns workers-1 helpers into shared TT with per-thread state. If tt_store's memory ordering, the sound-flag OR, or the xkey^data validation subtly breaks under contention, workers=2 can converge on a value workers=1 never produces. A test that fixes the mate-in-9 line and asserts `th_mate_hunt_mt(color=1, depth=10, workers=1) == th_mate_hunt_mt(color=1, depth=10, workers=2)` exercises the whole helper path.
**Soundness:** Test-only. Assertion is that SMP does not change proof values; if it does, the assertion fires.
**Integration:** test_engine_c.py:38 — (new test at end of file)
```
def test_c_roundtrip():
    pos = T.Position.from_tfen("1uwk/P3/3p/K2F[UWf] w")
    assert engine_c.to_py(engine_c.to_c(pos)).tfen() == pos.tfen()
```
**Toggle / pin:** New test. Between the two calls invoke E.lib.th_tt_init(20); teardown restores suite's tt state.
**Expected gain:** Catches SMP soundness breaks that change a proven value. 0 → 1 pinned.
**Risk:** Non-deterministic test if a real race exists — but that is exactly the signal wanted. Fixed-depth 10 keeps runtime under 2s per config.
**Oracles:** pytest -q; scripts/bench_workers.py.
**Effort:** S — one test, ~20 lines.
**Novelty:** Lazy SMP landed in 09a18fd; no automated soundness gate.
**Verifier notes:** Exact-equality assertion is defensible (null-window fully explores; max over siblings invariant), but if flakiness surfaces from TT-order effects weaken to `(v1 >= MATE_BOUND) == (v2 >= MATE_BOUND)` plus `abs(v1 - v2) <= 2`. Use known M9 root (`fuwk/3p/P1F1/KWU1[-] b`, best `b4c2`) at depth 10; both configs must return 29991.

### 019. [INSTRUMENT] No test pins the horizon "non-terminal is UNSOUND" invariant
**Source:** LENS 5
**Mechanism:** search() at depth<=0 with non-terminal moves returns 0 with si->snd unset. If someone "fixes" this to set the flag, an unproven horizon-0 draw would be stored with sound=(SND_LB|SND_UB), propagate as PROVEN, and search emits fake draw proofs. Test: construct a position with more than horizon depth to any terminal, call th_solve at depth 1, assert snd==0.
**Soundness:** Test-only. Pins invariant #1 (horizon is UNSOUND).
**Integration:** test_engine_c.py:38 — (new test at end of file)
```
def test_c_roundtrip():
    pos = T.Position.from_tfen("1uwk/P3/3p/K2F[UWf] w")
    assert engine_c.to_py(engine_c.to_c(pos)).tfen() == pos.tfen()
```
**Toggle / pin:** New test; th_solve at depth 1 with SInfo pointer, assert snd==0.
**Expected gain:** Catches accidental promotion of horizon-0 to sound.
**Risk:** None.
**Oracles:** pytest -q.
**Effort:** S — one test, ~10 lines.
**Novelty:** Not currently pinned.
**Verifier notes:** Use ffi.new("int*") for the out-arg. Toggle-verify by flipping `if (any) return 0` branch in tinyhouse.c to also set si->snd = SND_LB|SND_UB; test must fail.

### 020. [INSTRUMENT] No nodes-to-depth harness pins a search count
**Source:** LENS 5
**Mechanism:** C engine exposes th_nodes(); a fixed position + fixed depth + fresh TT + single thread produces a deterministic count. A test asserting `th_solve(start, depth=6, workers=1)` with fresh 2^18 TT visits exactly N nodes flips red on any silent ordering change (killer table format, history decay, gives_direct_check false positives). Same technique that perft(7)=1,355,253 pins movegen — but for SEARCH.
**Soundness:** Instrument-only.
**Integration:** test_engine_c.py:38 — (new test at end of file)
```
def test_c_roundtrip():
    pos = T.Position.from_tfen("1uwk/P3/3p/K2F[UWf] w")
    assert engine_c.to_py(engine_c.to_c(pos)).tfen() == pos.tfen()
```
**Toggle / pin:** New test. Fresh TT (th_tt_init) and workers=1 for determinism; recorded value must be measured on developer's machine and committed as baseline (annotate machine).
**Expected gain:** Any ordering/killer/history change moving count >0.1% flags itself. 0 → 1.
**Risk:** Machine-dependent counts possible if any code path is unstable; single-threaded search here is deterministic. If count varies across machines that itself is a soundness signal.
**Oracles:** pytest -q; toggle-off reproduces pre-change node count exactly.
**Effort:** S — one test + one measured constant.
**Novelty:** No search-side drift oracle exists; only perft(7) protects movegen.
**Verifier notes:** Pin must call th_tt_init(18) fresh before each measurement — TT state from prior tests would poison the count.

### 021. [INSTRUMENT] No paired NPS bench for the C search
**Source:** LENS 5
**Mechanism:** engine_c.py __main__ measures perft NPS but nothing benches raw search speed. scripts/bench_workers.py is a scaling comparison across worker counts, not a paired A vs B on single-threaded search. A scripts/bench_search_nps.py that runs th_solve at fixed depth on N=3 anchor positions with fresh TT, times each with statistics.median across R repeats, and prints nodes/seconds/nps would let an NPS finding be measured before/after.
**Soundness:** Bench script only.
**Integration:** scripts/bench_workers.py:60 — (new sibling script)
```
print(f"\nbest at depth {args.depth}: --workers {best[0]} ({best[1]:.1f}s median)")
print("re-measure if you move to a materially deeper target depth.")
```
**Toggle / pin:** New file scripts/bench_search_nps.py; existing bench unaffected.
**Expected gain:** Makes NPS findings measurable. Paired NPS medians across R repeats per anchor. Confirm by running before/after -O2 → -O3.
**Risk:** None.
**Oracles:** scripts/bench_workers.py (reference); pytest -q.
**Effort:** S — ~50 lines mirroring bench_workers.py.
**Novelty:** Only perft NPS is measurable today.
**Verifier notes:** bench_workers.py does record nodes and times per run so NPS is computable, but it's a single-position SMP scaling tool, not a paired NPS harness across multiple anchor TFENs.

### 022. [INSTRUMENT] No test pins a draw-by-repetition proof
**Source:** LENS 5
**Mechanism:** search() sets si->rep_min and si->snd = SND_LB|SND_UB when path[j] == key at some same-side ancestor — what lets the solver return proven draws by loop-forcing. A test that constructs a small position where the only defense is to loop (bare-king endgame where attacker cannot progress within N plies) and asserts th_solve returns 0 with snd==3 pins the mechanism. Without it, a refactor of the repetition scan can silently downgrade draw claims from PROVEN to unknown, or worse promote a non-repetition path to sound-flag 3.
**Soundness:** Test-only.
**Integration:** test_engine_c.py:38 — (new test at end of file)
```
def test_c_roundtrip():
    pos = T.Position.from_tfen("1uwk/P3/3p/K2F[UWf] w")
    assert engine_c.to_py(engine_c.to_c(pos)).tfen() == pos.tfen()
```
**Toggle / pin:** New test; construct position (bare kings + one non-progressable piece each) where forced-draw status is hand-verifiable.
**Expected gain:** Catches changes to path-repetition loop that alter when SND_LB|SND_UB gets set. 0 → 1 pinned.
**Risk:** Requires hand-crafting a small position with trivially-verifiable draw at depth D — one hour of work up front, permanent coverage.
**Oracles:** pytest -q.
**Effort:** M — needs a hand-crafted position.
**Novelty:** Not covered; 43 tests never call any solver.
**Verifier notes:** Cited line drifts: SND_LB|SND_UB set at tinyhouse.c:426 (loop header on 425), not 422. engine_c already declares `int th_solve(THPos *p, int depth, uint16_t *bestmove, int *snd)`. Pick a position with only same-side-repeating king shuffles available so any legal sequence reaches an ancestor same-side key within the depth budget.

### 023. [INSTRUMENT] No test exercises the Zobrist reseed contract
**Source:** LENS 5
**Mechanism:** th_seed rebuilds zob_piece/zob_hand/zob_stm from a splittable-mix64 seeded xorshift; the entire seed-agreement workflow (solve under seed A, reset TT, solve under seed B, compare) has zero coverage. If th_seed's iteration order, table dimensions, or tt_seed_used stamping breaks, the two seeds still "agree" on the wrong number.
**Soundness:** Test-only; runs the solver at fixed depth twice and compares.
**Integration:** test_engine_c.py:38 — (new test at end of file)
```
def test_c_roundtrip():
    pos = T.Position.from_tfen("1uwk/P3/3p/K2F[UWf] w")
    assert engine_c.to_py(engine_c.to_c(pos)).tfen() == pos.tfen()
```
**Toggle / pin:** New test only. Teardown: call E.lib.th_seed(0x9E3779B97F4A7C15) and E.lib.th_tt_init(current bits) so subsequent tests see default tables.
**Expected gain:** Catches breakage of th_seed table dimensions, tt_seed_used stamping, or reseed determinism. 0 → 1 pinned.
**Risk:** Two extra depth-10 solves in CI (~1 s).
**Oracles:** pytest -q; solve_hunt.py --seed 0xC0FFEE --fresh.
**Effort:** S — one test, ~15 lines.
**Novelty:** Reseed feature landed in 09a18fd but was never exercised automatically.
**Verifier notes:** Verify runtime — a mate-in-9 solve twice may exceed ~1s depending on TT bits; keep to small tt_bits (e.g. 16) or shallower mate line if depth-10 pair blows past ~2s.

### 024. [NEW-IDEA] Depth-first proof-number search (df-pn) to close the draw claim
**Source:** draw-proof research (lens 6)
**Mechanism:** Alpha-beta with depth cap can only report "no win within N plies"; it cannot prove a draw. PN search expands the leaf most likely to prove or disprove the root and terminates when the root's proof or disproof number reaches infinity. In games with sharp forced lines and short refutation trees (drops make Tinyhouse sharp), PN typically visits far fewer nodes than alpha-beta, and unlike alpha-beta it CLOSES a draw claim. df-pn (Nagai's two-threshold variant) keeps the stack shallow and lets a TT store pn/dn per node cheaply. Repetitions handled as in current path[]/rep_min: an OR-node whose path-ancestor equals current is disproven for the attacker (defender loops forever = draw). Terminals use same mate/stalemate values.
**Soundness:** Reuses two invariants: (a) terminal values from th_result are sound; (b) rep-safety — values that depended on a path-ancestor repetition are NEVER shared to another path via TT (df-pn+ style, mirroring my_rep >= ply guard at line 513). A root disproof under sound leaf classifiers is a strong proof that no forced win exists from the root WITHOUT any depth cap.
**Integration:** tinyhouse.c:590 — th_mate_hunt_mt
```
int th_mate_hunt_mt(THPos *p, int depth, int color, int workers, uint16_t *bestmove) {
```
**Toggle / pin:** New C entry point th_dfpn_hunt(THPos *p, int color, uint64_t node_budget, int *proven); new solve_dfpn.py driver. Nothing calls it by default.
**Expected gain:** NEW capability: potential strong draw proof of the start position (currently unreachable at any depth). Oracle is per-node-budget comparison at matched positions where both alpha-beta and df-pn terminate.
**Risk:** df-pn can stall on positions with many equal-value moves; pn/dn tables can grow large; GHI (graph-history-interaction) between transpositions and repetitions requires the same rep_min discipline.
**Oracles:** pytest -q (43 tests unchanged); perft(7)=1,355,253 drift signature; th_dfpn_hunt on 1.Fd1-c2 sub-position must return proof=White loses and value matches current M9; th_dfpn_hunt on hand-crafted trivially drawn K+piece endgame must return draw-proven while current alpha-beta at any bounded depth returns 0 without SND_LB|SND_UB; toggling off reproduces current solve_hunt node counts exactly.
**Effort:** L — df-pn state + expansion loop + rep integration + driver + tests; ~2-3 focused days.
**Novelty:** Fundamentally different proof method that can close the draw claim.
**Verifier notes:** Rep-safety invariant lives at tinyhouse.c:511-513 (`si->rep_min = my_rep; if (tt && my_rep >= ply ...)`). df-pn+ style: store pn/dn keyed by position only when no path-ancestor contributed to the verdict; otherwise return the value up the stack but skip the TT write. Concrete first oracle: run th_dfpn_hunt on K+piece drawn subposition and require draw-proven while current alpha-beta at any depth returns 0 with snd==0.

### 025. [NEW-IDEA] PN2 (two-level proof-number) layered on top of df-pn
**Source:** draw-proof research (lens 6)
**Mechanism:** Plain PN's memory scales with expanded-tree size; PN2 replaces most of that memory with a heuristic pn/dn computed by an inner PN using a fixed sub-budget (e.g. 10-100k nodes), so the outer tree only stores decision-critical nodes. In practice PN2 fits a 10-100x larger effective search in the same RAM as flat df-pn.
**Soundness:** Inner search's pn/dn are heuristic only; when the outer subsequently expands the same node its own bookkeeping overwrites them. PROVEN verdicts come only from outer expansion reaching terminal or repetition leaves, never from the inner heuristic. Soundness identical to df-pn; PN2 only affects ordering and memory.
**Integration:** tinyhouse.c:577 — th_solve_mt
```
int th_solve_mt(THPos *p, int depth, int workers, uint16_t *bestmove, int *snd) {
```
**Toggle / pin:** `--dfpn2-budget N` flag on solve_dfpn.py (0 = plain df-pn). Default 0. With 0 the search must be byte-identical to Finding 024.
**Expected gain:** Estimate: main-tree memory 10-100x smaller than flat df-pn at similar or slightly larger outer node count. Metric: max resident-set at a matched proof frontier.
**Risk:** Wrong inner-budget tuning wastes time re-searching the same subtree from outside.
**Oracles:** pytest -q; PN2 with budget=0 identical to df-pn; any budget converges to same verdict on M9 sub-position; peak RSS strictly lower than flat df-pn on a matched deeper proof.
**Effort:** M — small wrapper around df-pn expansion; ~1 day.
**Novelty:** Strictly follows Finding 024.
**Verifier notes:** Depends on Finding 024 landing first; --dfpn2-budget=0 must be byte-identical to plain df-pn (add as hard oracle). Inner search must NOT write TT entries as PROVEN unless it itself reaches terminal/repetition — safest: inner writes nothing to TT, only returns pn/dn to seed the outer node.

### 026. [NEW-IDEA] State-centric bounded-reachable retrograde
**Source:** draw-proof research (lens 6)
**Mechanism:** Enumerate every state reachable from start in <= N plies by forward BFS, then run backward value iteration (WIN if any successor is opponent-LOSS, LOSS if all successors are opponent-WIN, else UNKNOWN) over that closed subgraph. Alpha-beta re-solves each transposition-equivalent position separately along every path; a state-centric solver visits each unique reachable state exactly once. With canonical-key symmetry applied, unique reachable states at N=20 should sit well below the ~1e13 syntactic upper bound and likely within desktop RAM. Gives a STRONG solve of the reachable subgraph.
**Soundness:** Standard game-theoretic value iteration semantics; at fixed points WIN and LOSS labels are provably correct. Only unsoundness risk is missing a successor during enumeration, caught by reusing legal_moves. Repetitions become natural cycles; UNKNOWN states are the draw label.
**Integration:** tinyhouse.py:96 — Position.start
```
def start() -> "Position":
```
**Toggle / pin:** New standalone script solve_retro.py --plies N --out labels.db; not wired into any existing path.
**Expected gain:** NEW proof mode; per-state (not per-path) label. For N ~= 14-16 reachable set likely fits desktop RAM (~1e7-1e9 states, unmeasured). Measurement: run BFS to N=6,8,10,12 and count unique canonical-key states; extrapolate memory budget.
**Risk:** Reachable-set size may explode faster than measured; needs on-disk overflow (RocksDB or flat file + external sort) if RAM tight; BFS enumeration non-trivial to parallelize soundly.
**Oracles:** pytest -q; BFS successor count at depth 1=6=perft(1); depth 2=33=perft(2); depth 3=241=perft(3); labels agree with alpha-beta on 1.Fd1-c2 M9.
**Effort:** XL — bulk state store, forward BFS, backward value iteration, cross-check; ~1-2 weeks.
**Novelty:** Wholly different proof technology (state-centric vs tree-centric).
**Verifier notes:** "No forced win in N plies" follows only if BFS enumerates ALL states at depth <= N (not bounded/pruned frontier) and successor generation reuses Position.legal_moves verbatim. Boundary states at exact depth N stay UNKNOWN; WIN/LOSS in the interior correspond to a real forced mate reached entirely inside the enumerated subgraph. Canonical-key symmetry is separate — if not yet in place enumeration still works but loses the board-symmetry factor.

### 027. [NEW-IDEA] SCC-based cycle-resolution pass on top of df-pn
**Source:** draw-proof research (lens 6)
**Mechanism:** Naive PN storing pn/dn under only the position key can double-count repetition-blocked lines and never converge. When the current search's rep_min discipline forces a subtree to be non-stored, df-pn also cannot cache and stalls. Kishimoto's df-pn+ resolves this by expanding the local SCC on demand and running value iteration on that finite subgraph.
**Soundness:** SCC pass is a bounded strong-solve of a finite reachable subgraph, exactly Finding 026 restricted to the SCC. Output is game-theoretically correct. Values are marked as sound-under-repetition-with-this-frontier and are not shared to any parent path with a different frontier (same rep_min guard).
**Integration:** tinyhouse.c:513 — search
```
if (tt && my_rep >= ply && !g_abort) {
```
**Toggle / pin:** `--dfpn-ghi` flag on solve_dfpn.py, default False. When False df-pn behaves as in Finding 024 and any cycle-stalled subtree is dropped; when True invoke SCC pass. Off must reproduce Finding 024 on non-cyclic sub-positions.
**Expected gain:** NEW capability: enables df-pn to close drawn subgames that recur through short cycles — common in Crazyhouse-family games because dropped pieces can be captured and re-dropped. Without this, plain df-pn on start may never terminate.
**Risk:** SCC computation on a partially expanded graph is fiddly; bad SCC boundary detection could pull in unrelated subtrees and blow up memory.
**Oracles:** pytest -q; hand-crafted drawn position with obvious 3-cycle must be proven draw within small budget; same without flag times out; 1.Fd1-c2 M9 unaffected.
**Effort:** L — Tarjan SCC on expanded PN tree, value iteration, rep_min integration; ~3-4 days on top of df-pn.
**Novelty:** Complements Finding 024 for real games (cycles are the norm here).
**Verifier notes:** Depends on Finding 024. Recommend sequencing: land Finding 024, measure baseline on cycle-free positions (1.Fd1-c2 M9), then add --dfpn-ghi as follow-up commit.

### 028. [SHOULD-BE-BETTER] Mate-distance-pruning cutoff broadens to full clamp region
**Source:** LENS-2-tinyhouse.c-TT-SMP-soundness
**Mechanism:** True value is bounded above by MATE-ply for the entire clamp region alpha >= MATE-ply, and by -(MATE-ply) as a trivial SND_LB when alpha was clamped up. In Case B (alpha clamped up to -(MATE-ply), cutoff because beta_orig <= -(MATE-ply)), returned value -(MATE-ply) is a trivially-true lower bound on true value, so SND_LB is safe. In Case C (beta clamped down to MATE-ply, alpha_orig > MATE-ply, cutoff), returned alpha_orig is a valid upper bound because true <= MATE-ply < alpha_orig, so SND_UB is safe. Current code only claims SND_UB at exact-equality point.
**Soundness:** Broadening SND_UB from "== MATE-ply" to ">= MATE-ply" and adding SND_LB whenever alpha was clamped up preserves soundness (both bounds proven by MDP's own arithmetic); only adds flags, never removes them.
**Integration:** tinyhouse.c:418 — search
```
    if (alpha >= beta) { si->snd = alpha == MATE - ply ? SND_UB : 0; return alpha; }
```
**Toggle / pin:** Replace with `uint8_t s = 0; if (alpha >= MATE - ply) s |= SND_UB; if (alpha == -(MATE - ply)) s |= SND_LB; si->snd = s; return alpha;`. Toggle off by reverting.
**Expected gain:** Estimate: negligible in the mate-hunt regime measured so far (MDP does not fire within MAXPLY=400 for null-window depth <= 40), but frees SND_UB to propagate in wider-window searches near MAXPLY - MATE_BOUND.
**Risk:** Almost none.
**Oracles:** pytest -q; perft(7)==1,355,253; solve_hunt.py 0 --maxdepth 20 --seed 0xC0FFEE --fresh reproducing v<=29000.
**Effort:** S — one line.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Actual line is 422, not 418. MATE=30000 and MAXPLY=400, so MATE-ply and -(MATE-ply) can never coincide — the two added flag conditions are mutually exclusive. Impact is quality-only.

### 029. [SHOULD-BE-BETTER] Expose snd out of th_mate_hunt_mt
**Source:** LENS-2-tinyhouse.c-TT-SMP-soundness
**Mechanism:** root_search accepts int* snd for the main-thread SInfo, and th_solve/th_solve_mt plumb it through, but th_mate_hunt_mt hard-codes 0. solve_hunt.py only inspects returned value and treats any v<=MATE_BOUND as "proven no forced win", which is sound under alpha-beta completeness but leaves no in-band way to detect a partial search that happened to be <=MATE_BOUND.
**Soundness:** Pure interface addition; flag was already computed, just discarded.
**Integration:** tinyhouse.c:588 — th_mate_hunt_mt
```
    if (p->stm == color)
        return root_search(p, depth, MATE_BOUND, MATE, workers, bestmove, 0);
    return -root_search(p, depth, -MATE, -MATE_BOUND, workers, bestmove, 0);
```
**Toggle / pin:** Add `int *snd` to th_mate_hunt_mt/th_mate_hunt signatures, forward to root_search's snd argument, expose in engine_c.py cdef. Search node-identical.
**Expected gain:** No NPS or node change; enables solve_hunt.py to print "proven-no-mate via SND_UB" vs "no-mate found (heuristic horizon)".
**Risk:** cffi cdef must be updated; otherwise trivial.
**Oracles:** pytest -q; solve_hunt.py 0 --maxdepth 20 --seed 0 (v matches bounds, snd_out is SND_UB).
**Effort:** S — two signature edits + cdef.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Utility is modest — root_search has no time-abort path, so a completed C call will always yield SND_UB on fail-low; the added flag is mainly a paranoia cross-check, not a way to catch mid-run aborts (Python Ctrl-C cannot interrupt in-flight C call). Still a lazy one-line addition; solve_hunt.py should assert snd_out == SND_UB on fail-low as the oracle.

### 030. [SHOULD-BE-BETTER] root_search zeros killers but never clears the thread-local history table
**Source:** LENS 1: tinyhouse.c movegen and make/unmake
**Mechanism:** `history[2][2048]` accumulates depth*depth increments over lifetime of the main thread. A fresh position starts with move-index buckets pre-filled from an unrelated position's cutoffs. Since history is only used as an ordering tiebreaker in order_score, impact is limited but non-zero.
**Soundness:** Ordering-only; cannot change search result under alpha-beta with same TT contents.
**Integration:** tinyhouse.c:547 — root_search
```
    memset(killers, 0, sizeof killers);
```
**Toggle / pin:** `static const int RESET_HISTORY = 1;` before root_search; when set, `memset(history, 0, sizeof history);` alongside killer reset. Node-identical only on first solve after process start.
**Expected gain:** Negligible on a single solve, up to ~3% nodes-to-depth on SECOND consecutive solve of a materially different position.
**Risk:** None.
**Oracles:** pytest -q; solve_hunt.py --seed 0xC0FFEE --fresh unchanged; compare node totals of two consecutive solves of different tfens.
**Effort:** S — one line.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Actual line is 551, not 547. Gain likely negligible on cold start; only shows on back-to-back solves of unrelated positions on the same thread.

### 031. [SHOULD-BE-BETTER] Rebuild trigger checks only tinyhouse.c mtime, ignores compile flags and cdef edits
**Source:** LENS 3: tinyhouse.py + Python/C divergence
**Mechanism:** Line 16 compares only tinyhouse.c mtime against libtinyhouse.dylib mtime. Line 17 hardcodes `-O2 -pthread -shared` and the compile command lives in engine_c.py. If someone edits engine_c.py to add `-DDEBUG`, switch to `-O3`, or extend the ffi.cdef with a signature that does not match the still-installed .dylib, the file check passes and the old binary loads. cffi ABI mode does no signature verification at load time; a mismatched signature is only felt at the call site — crash, garbage return, silent wrong value.
**Soundness:** Rebuild trigger orthogonal to search logic; hashing (source + compile-command tuple + cdef string) fires only when intended bytes change.
**Integration:** engine_c.py:16 — `<module>`
```
if not _LIB.exists() or _LIB.stat().st_mtime < _SRC.stat().st_mtime:
```
**Toggle / pin:** Replace mtime check with `if not _LIB.exists() or _hash(_SRC, cdef_text, cmd) != stored_hash:` and write the hash into a sidecar file. Reverting reproduces current behaviour byte-identically.
**Expected gain:** Eliminates a class of debugging traps where the .dylib silently lags engine_c.py edits.
**Risk:** One hash computation at import (microseconds).
**Oracles:** pytest -q; edit ffi.cdef with unchanged tinyhouse.c and see rebuild fire.
**Effort:** S — 6-8 lines: hash three inputs, store sidecar.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Hash three things and store beside the .dylib: bytes of tinyhouse.c, the cdef string, and the compile-command tuple. Simplest: one sidecar `libtinyhouse.dylib.hash`, blake2b of the concatenation.

### 032. [SHOULD-BE-BETTER] Python/C parity test only walks from the start position
**Source:** LENS 3: tinyhouse.py + Python/C divergence
**Mechanism:** test_engine_c.py:21-32 walks 20 games x 60 plies from Position.start(). Pawn promotion requires four consecutive advances by the same pawn along its file — random play reaches this vanishingly rarely; hand rarely fills past one or two pieces. Perft oracle IS strong evidence of movegen agreement but only extends to depth 3-5 on hand-heavy/promoted-piece positions. A future edit that changed drop restriction at back rank in Python-only would slip through.
**Soundness:** Test-coverage strengthening only.
**Integration:** test_engine_c.py:21 — test_move_sets_match_on_random_walks
```
def test_move_sets_match_on_random_walks():
    random.seed(7)
    for _ in range(20):
        pos = T.Position.start()
        for _ply in range(60):
```
**Toggle / pin:** Add parametrized variant that seeds from each row of PERFT_ORACLE (particularly `1k2/4/2K1/4[PFUWpfuw] w` and `1uwk/P3/3p/K2F[UWf] w`).
**Expected gain:** Strengthens parity coverage on state classes least reached by random walk from start.
**Risk:** Test runtime increases ~5x per added seed (60 plies x 20 games). Still sub-second.
**Oracles:** pytest -q; instrument test to count unique (promoted?, hand-sum) signatures before/after.
**Effort:** S — add @pytest.mark.parametrize.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Parametrizing across all PERFT_ORACLE start_tfens is cheaper to write and gives strictly more coverage.

### 033. [SHOULD-BE-BETTER] `in_check` fetched from server but GUI never renders it
**Source:** LENS 4
**Mechanism:** renderBoard iterates squares/pieces but never consults `state.info.in_check`; no CSS class applied to the king's square. Player cannot see at a glance that their king is in check.
**Soundness:** GUI-only.
**Integration:** index.html:131 — renderBoard
```
function renderBoard() {
```
**Toggle / pin:** When `state.info.in_check` is true, find the STM king square and add a `.check` class (red glow). Remove class rule → appearance identical to today.
**Expected gain:** Better UX; no perf metric.
**Risk:** None.
**Oracles:** manual: load a position where STM king is in check and confirm the square is highlighted.
**Effort:** S — a few lines JS + one CSS rule.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Pure GUI/UX gap; no solver invariants involved.

### 034. [SHOULD-BE-BETTER] Setup mode cannot create promoted pieces
**Source:** LENS 4
**Mechanism:** PAL lists only base types; setupPlace writes `[type, color, false]` unconditionally. Building a test position with a promoted W (or F/U) via the GUI is impossible; user has to hand-edit TFEN.
**Soundness:** GUI-only.
**Integration:** index.html:346 — setupPlace
```
  else state.board[i] = [state.pal.toUpperCase(), state.pal === state.pal.toLowerCase() ? 1 : 0, false];
```
**Toggle / pin:** Add a shift-click on the palette (or a dedicated `~` chip) that flips pc[2] on the next place.
**Expected gain:** Enables building promoted-piece test positions from GUI.
**Risk:** None.
**Oracles:** manual: place a promoted W, save TFEN, reload — verify `~` round-trips.
**Effort:** S — one additional keyboard/click branch.
**Novelty:** Not in ALREADY DONE.
**Verifier notes:** Server parser already accepts `~`; buildTfen already emits it. GUI-only fix.

## Changes to the README "still owed" list

- **Add** (SOUNDNESS): TFEN `~` marker is not restricted by piece type — malformed positions with promoted K or P parse cleanly, and the solver can emit PROVEN claims on rulesets Tinyhouse does not define. Fix at tinyhouse.py:130 is 2 lines plus 2 test cases (Finding 001).
- **Add** (SOUNDNESS): No test in the 43-test suite exercises the solver — a wrong PROVEN value from search leaves CI green. Adding pinned mate-in-1 and mate-in-9 tests, an SMP=1-vs-2 agreement test, a horizon-UNSOUND invariant test, and a TT save/load round-trip test would each close a specific silent-failure route (Findings 016-019).
- **Qualify**: The docstring in test_tinyhouse.py claims deeper perft values were "hand-verified... cross-checked by three independent implementations", but only start-position depth 1-2 (33 nodes) was hand-enumerated. Rewrite to state exactly what was hand-verified vs cross-implementation drift (Finding 007).
- **Qualify** the "no forced win within N plies" wording in solve_status.json: the collision-mitigation recommendation currently attached only to the positive-mate case applies symmetrically to the negative-bound case. Extend the seed-reseed re-verification recommendation to the negative bounds at depth 20 White and depth 22 Black (Finding 006).
- **Add** (SILENT-DIVERGENCE): The Python DOUBLE_STEP toggle has no C mirror and no import-time guard in engine_c.py — flipping it silently desynchronises the two engines on the solver path (Finding 002).
- **Add** (draw-proof roadmap): The current alpha-beta hunt cannot prove a draw at any depth. df-pn (Finding 024), PN2 (025), state-centric retrograde (026), and SCC-cycle resolution (027) are the four candidate proof technologies capable of closing that gap.
