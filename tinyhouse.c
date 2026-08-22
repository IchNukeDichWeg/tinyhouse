/* Tinyhouse C hot path: movegen, make/unmake, perft.
 * Mirrors tinyhouse.py exactly: square = 4*rank+file (a1=0), piece =
 * (type+1) | promoted<<3 | color<<4, types P F U W K = 0..4, move =
 * to | from<<4 | drop<<8 | promo<<9 (for drops the from field is the type).
 * Built as a shared library, loaded from Python via cffi (ABI mode).
 */
#include <stdint.h>
#include <string.h>

typedef struct { int8_t board[16]; int8_t hands[2][4]; int8_t stm; } THPos;

#define TYPE(pc) (((pc) & 7) - 1)
#define COLOR(pc) ((pc) >> 4)
#define PROMOTED(pc) ((pc) & 8)
#define PIECE(c, t, pr) (((t) + 1) | ((pr) << 3) | ((c) << 4))
enum { P, F, U, W, K };

#define MV(f, t, pr) ((t) | (f) << 4 | (pr) << 9)
#define MV_DROP(dt, t) ((t) | (dt) << 4 | 1 << 8)
#define M_TO(m) ((m) & 15)
#define M_FROM(m) ((m) >> 4 & 15)
#define M_IS_DROP(m) ((m) & 256)
#define M_PROMO(m) ((m) >> 9 & 3)

/* neighbor tables, 0xff-terminated */
static uint8_t ORTH[16][5], DIAG[16][5], KINGN[16][9];
static uint8_t MAO_MOVES[16][9][2], MAO_ATT[16][9][2]; /* (blocker,dest) / (origin,blocker) */
static uint8_t PCAPS[2][16][3];
static const int PUSH[2] = {4, -4};
static const int PROMO_RANK[2] = {3, 0};
static int tables_ready = 0;

static void init_tables(void) {
    if (tables_ready) return;
    static const int OD[4][2] = {{1,0},{-1,0},{0,1},{0,-1}};
    static const int DD[4][2] = {{1,1},{1,-1},{-1,1},{-1,-1}};
    int no[16] = {0}, nd[16] = {0}, nk[16] = {0}, nm[16] = {0}, na[16] = {0};
    int npc[2][16] = {{0}};
    memset(ORTH, 0xff, sizeof ORTH); memset(DIAG, 0xff, sizeof DIAG);
    memset(KINGN, 0xff, sizeof KINGN);
    memset(MAO_MOVES, 0xff, sizeof MAO_MOVES); memset(MAO_ATT, 0xff, sizeof MAO_ATT);
    memset(PCAPS, 0xff, sizeof PCAPS);
    for (int f = 0; f < 4; f++) for (int r = 0; r < 4; r++) {
        int s = 4 * r + f;
        for (int i = 0; i < 4; i++) {
            int tf = f + OD[i][0], tr = r + OD[i][1];
            if (tf >= 0 && tf < 4 && tr >= 0 && tr < 4) {
                ORTH[s][no[s]++] = 4 * tr + tf; KINGN[s][nk[s]++] = 4 * tr + tf;
            }
        }
        for (int i = 0; i < 4; i++) {
            int tf = f + DD[i][0], tr = r + DD[i][1];
            if (tf >= 0 && tf < 4 && tr >= 0 && tr < 4) {
                DIAG[s][nd[s]++] = 4 * tr + tf; KINGN[s][nk[s]++] = 4 * tr + tf;
            }
        }
        for (int i = 0; i < 4; i++) {
            int bf = f + OD[i][0], br = r + OD[i][1];
            if (bf < 0 || bf > 3 || br < 0 || br > 3) continue;
            int b = 4 * br + bf;
            int df[2], dr[2];
            if (OD[i][0]) { df[0] = df[1] = bf + OD[i][0]; dr[0] = br + 1; dr[1] = br - 1; }
            else { dr[0] = dr[1] = br + OD[i][1]; df[0] = bf + 1; df[1] = bf - 1; }
            for (int j = 0; j < 2; j++) {
                if (df[j] < 0 || df[j] > 3 || dr[j] < 0 || dr[j] > 3) continue;
                int t = 4 * dr[j] + df[j];
                MAO_MOVES[s][nm[s]][0] = b; MAO_MOVES[s][nm[s]++][1] = t;
                MAO_ATT[t][na[t]][0] = s; MAO_ATT[t][na[t]++][1] = b;
            }
        }
        for (int c = 0; c < 2; c++) {
            int dr = c ? -1 : 1;
            for (int j = -1; j <= 1; j += 2) {
                int tf = f + j, tr = r + dr;
                if (tf >= 0 && tf < 4 && tr >= 0 && tr < 4)
                    PCAPS[c][s][npc[c][s]++] = 4 * tr + tf;
            }
        }
    }
    tables_ready = 1;
}

static int attacked(const THPos *p, int sq, int by) {
    const uint8_t *n;
    for (n = ORTH[sq]; *n != 0xff; n++) {
        int pc = p->board[*n];
        if (pc && COLOR(pc) == by && (TYPE(pc) == W || TYPE(pc) == K)) return 1;
    }
    for (n = DIAG[sq]; *n != 0xff; n++) {
        int pc = p->board[*n];
        if (pc && COLOR(pc) == by && (TYPE(pc) == F || TYPE(pc) == K)) return 1;
    }
    for (n = PCAPS[1 - by][sq]; *n != 0xff; n++) {
        int pc = p->board[*n];
        if (pc && COLOR(pc) == by && TYPE(pc) == P) return 1;
    }
    for (int i = 0; MAO_ATT[sq][i][0] != 0xff; i++) {
        int pc = p->board[MAO_ATT[sq][i][0]];
        if (pc && COLOR(pc) == by && TYPE(pc) == U && !p->board[MAO_ATT[sq][i][1]]) return 1;
    }
    return 0;
}

static int king_sq(const THPos *p, int color) {
    int target = PIECE(color, K, 0);
    for (int s = 0; s < 16; s++) if (p->board[s] == target) return s;
    return -1;
}

int th_in_check(const THPos *p, int color) {
    return attacked(p, king_sq(p, color), 1 - color);
}

typedef struct { uint16_t m; int8_t captured; } Undo;

static void make(THPos *p, uint16_t m, Undo *u) {
    int us = p->stm;
    u->m = m;
    if (M_IS_DROP(m)) {
        u->captured = 0;
        p->hands[us][M_FROM(m)]--;
        p->board[M_TO(m)] = PIECE(us, M_FROM(m), 0);
    } else {
        int frm = M_FROM(m), to = M_TO(m);
        int cap = p->board[to];
        u->captured = cap;
        /* THB-04: TYPE(K) is 4 and hands is int8_t[2][4], so a king capture
         * wrote one past the row. The struct has no padding, so &hands[1][4]
         * is &stm and the aliasing is deterministic - and being intra-object,
         * no sanitizer sees it. Kings are never in hand, so skipping the
         * increment is also the right rule, not just the safe one. */
        if (cap && TYPE(cap) != K) p->hands[us][PROMOTED(cap) ? P : TYPE(cap)]++;
        int pc = p->board[frm];
        if (M_PROMO(m)) pc = PIECE(us, M_PROMO(m), 1);
        p->board[to] = pc; p->board[frm] = 0;
    }
    p->stm = 1 - us;
}

static void unmake(THPos *p, const Undo *u) {
    int us = p->stm = 1 - p->stm;
    uint16_t m = u->m;
    if (M_IS_DROP(m)) {
        p->board[M_TO(m)] = 0;
        p->hands[us][M_FROM(m)]++;
    } else {
        int frm = M_FROM(m), to = M_TO(m);
        int pc = p->board[to];
        if (M_PROMO(m)) pc = PIECE(us, P, 0);
        p->board[frm] = pc; p->board[to] = u->captured;
        /* mirror of the guard in make(); this is the half that survives the
         * call, because stm is restored on the line above and then clobbered */
        if (u->captured && TYPE(u->captured) != K)
            p->hands[us][PROMOTED(u->captured) ? P : TYPE(u->captured)]--;
    }
}

static int pseudo_moves(const THPos *p, uint16_t *out) {
    int us = p->stm, n = 0;
    const int8_t *b = p->board;
    for (int s = 0; s < 16; s++) {
        int pc = b[s];
        if (!pc || COLOR(pc) != us) continue;
        int t = TYPE(pc);
        const uint8_t *nb;
        switch (t) {
        case P: {
            int to = s + PUSH[us];
            if (to >= 0 && to < 16 && !b[to]) {
                if (to >> 2 == PROMO_RANK[us]) {
                    out[n++] = MV(s, to, F); out[n++] = MV(s, to, U); out[n++] = MV(s, to, W);
                } else out[n++] = MV(s, to, 0);
            }
            for (nb = PCAPS[us][s]; *nb != 0xff; nb++) {
                if (b[*nb] && COLOR(b[*nb]) != us) {
                    if (*nb >> 2 == PROMO_RANK[us]) {
                        out[n++] = MV(s, *nb, F); out[n++] = MV(s, *nb, U); out[n++] = MV(s, *nb, W);
                    } else out[n++] = MV(s, *nb, 0);
                }
            }
            break; }
        case F:
            for (nb = DIAG[s]; *nb != 0xff; nb++)
                if (!b[*nb] || COLOR(b[*nb]) != us) out[n++] = MV(s, *nb, 0);
            break;
        case W:
            for (nb = ORTH[s]; *nb != 0xff; nb++)
                if (!b[*nb] || COLOR(b[*nb]) != us) out[n++] = MV(s, *nb, 0);
            break;
        case K:
            for (nb = KINGN[s]; *nb != 0xff; nb++)
                if (!b[*nb] || COLOR(b[*nb]) != us) out[n++] = MV(s, *nb, 0);
            break;
        default: /* U */
            for (int i = 0; MAO_MOVES[s][i][0] != 0xff; i++) {
                int blocker = MAO_MOVES[s][i][0], to = MAO_MOVES[s][i][1];
                if (!b[blocker] && (!b[to] || COLOR(b[to]) != us)) out[n++] = MV(s, to, 0);
            }
        }
    }
    for (int t = 0; t < 4; t++) {
        if (!p->hands[us][t]) continue;
        for (int s = 0; s < 16; s++) {
            if (b[s]) continue;
            if (t == P && ((s >> 2) == 0 || (s >> 2) == 3)) continue;
            out[n++] = MV_DROP(t, s);
        }
    }
    return n;
}

/* legal moves; returns count. out may be NULL to just count. */
int th_moves(THPos *p, uint16_t *out) {
    uint16_t buf[128];
    int n = pseudo_moves(p, buf), nl = 0;
    Undo u;
    for (int i = 0; i < n; i++) {
        make(p, buf[i], &u);
        if (!th_in_check(p, 1 - p->stm)) {
            if (out) out[nl] = buf[i];
            nl++;
        }
        unmake(p, &u);
    }
    return nl;
}

void th_make(THPos *p, uint16_t m) { Undo u; make(p, m, &u); }

/* -1 mover mated, +1 mover stalemated (wins), 0 non-terminal */
int th_result(THPos *p) {
    if (th_moves(p, 0)) return 0;
    return th_in_check(p, p->stm) ? -1 : 1;
}

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
}

/* ------------------------------------------------------------------ solver
 * Iterative-deepening alpha-beta over win/draw/loss with mate-distance
 * scores. Horizon (depth<=0, non-terminal) returns 0 UNSOUND; terminals and
 * path-repetitions return sound values. Soundness of a node value as a
 * lower/upper bound on the true game value is propagated by bound duality:
 * parent LB-sound needs the best child's UB; parent UB-sound needs every
 * child's LB (and no cutoff). A root result with both flags is the exact
 * game value: |v| >= MATE_BOUND a proven forced win/loss, v == 0 with both
 * flags a proven draw. First repetition of a path position counts as the
 * draw (equivalent to threefold for game values: a winning strategy never
 * needs to repeat, and the defender can force the claim by looping).
 * Results whose value depended on a repetition hitting an ANCESTOR of the
 * node are path-dependent and are never stored in the TT (rep-safety). That
 * keeps path-dependent values OUT OF THE TABLE; it does not close graph-history
 * interaction, because the REUSE side is unguarded - the probe below applies no
 * path condition and a TTView records nothing about which path an entry came
 * from. Two things bound the residual. The path-repetition scan runs BEFORE the
 * probe, so a node that itself repeats a current-path ancestor can never take a
 * stored decisive value, which is the most direct GHI case. And what is left is
 * one-directional: it lands on the positive side, a possible over-claimed win,
 * never a fabricated "no win". The published proofs are additionally checked by
 * replaying each PV from the root and confirming it is repetition-free
 * (test_solver.py), which is cheaper than more search.
 *
 * The immunity is also relative to this engine's own model: under real
 * threefold rules a winning strategy may legally pass through a once-repeated
 * position, and this scores that as a draw. Negative results are therefore
 * CONSERVATIVE with respect to threefold, not identical to it.
 *
 * Multithreading: lazy SMP. Helper threads search the same root (half of
 * them one ply deeper) sharing the TT; per-thread state (path, killers,
 * history) is thread-local. TT entries are two 64-bit words with the
 * key XOR data validation trick, so a torn read from a concurrent write
 * can never validate - a shared entry is either intact or ignored, which
 * keeps mate proofs sound. Aborted (g_abort) subtrees never store.
 */
#include <stdlib.h>
#include <stdio.h>
#include <pthread.h>
#include <stdatomic.h>
#include <unistd.h>

#define MATE 30000
#define MATE_BOUND 29000
#define MAXPLY 400

static uint64_t zob_piece[16][32], zob_hand[2][4][3], zob_stm;
static uint64_t rng_state = 0x9E3779B97F4A7C15ULL;
static uint64_t rng64(void) {
    rng_state ^= rng_state >> 12; rng_state ^= rng_state << 25; rng_state ^= rng_state >> 27;
    return rng_state * 0x2545F4914F6CDD1DULL;
}

uint64_t th_key(const THPos *p) {
    uint64_t k = p->stm ? zob_stm : 0;
    for (int s = 0; s < 16; s++) if (p->board[s]) k ^= zob_piece[s][(int)p->board[s]];
    for (int c = 0; c < 2; c++) for (int t = 0; t < 4; t++)
        k ^= zob_hand[c][t][(int)p->hands[c][t]];
    return k;
}

/* TT entry: data packs value(16) | move(16) | depth(8) | flag(4) | sound(4);
 * xkey = key ^ data. calloc zero-fill never validates against a real key. */
typedef struct { _Atomic uint64_t xkey; _Atomic uint64_t data; } TTEntry;
enum { TT_EMPTY, TT_EXACT, TT_LOWER, TT_UPPER };
#define SND_LB 1
#define SND_UB 2
static TTEntry *tt = 0;
static uint64_t tt_mask = 0;
static _Thread_local uint64_t path[MAXPLY];
static _Thread_local int16_t history[2][2048];
static _Thread_local uint16_t killers[MAXPLY][2];
static _Thread_local uint64_t tl_pending = 0;
static _Thread_local uint32_t tl_jitter = 0;   /* helper-thread ordering noise */
static _Atomic uint64_t g_nodes;
static volatile int g_abort = 0;

/* Returns 0 on success, -1 if the table could not be allocated.
 * NOTE: on an overcommitting OS (macOS, default Linux) calloc SUCCEEDS for a
 * request far larger than RAM and the process then balloons as the search
 * touches pages. So this return value is not a size check - callers must
 * bound log2_entries against physical memory before calling (solve_hunt.py
 * does). A genuinely failed allocation is survivable, since every tt access
 * is NULL-guarded, but the search would then run with no transposition table
 * at all, which is slow enough to look like a hang. */
int th_tt_init(int log2_entries) {
    if (tt) free(tt);
    uint64_t n = 1ULL << log2_entries;
    tt = calloc(n, sizeof(TTEntry));
    tt_mask = n - 1;
    return tt ? 0 : -1;
}

static void nodes_flush(void) {
    if (tl_pending) { atomic_fetch_add_explicit(&g_nodes, tl_pending, memory_order_relaxed); tl_pending = 0; }
}
uint64_t th_nodes(void) { nodes_flush(); return atomic_load_explicit(&g_nodes, memory_order_relaxed); }

typedef struct { int16_t value; uint16_t move; uint8_t depth, flag, sound; } TTView;

static int tt_probe(uint64_t key, TTView *out) {
    if (!tt) return 0;
    TTEntry *e = &tt[key & tt_mask];
    uint64_t d = atomic_load_explicit(&e->data, memory_order_relaxed);
    uint64_t x = atomic_load_explicit(&e->xkey, memory_order_relaxed);
    if ((x ^ d) != key || !d) return 0;
    out->value = (int16_t)(d & 0xffff);
    out->move = (uint16_t)(d >> 16 & 0xffff);
    out->depth = (uint8_t)(d >> 32 & 0xff);
    out->flag = (uint8_t)(d >> 40 & 0xf);
    out->sound = (uint8_t)(d >> 44 & 0xf);
    return 1;
}

static void tt_store(uint64_t key, int16_t value, uint16_t move, uint8_t depth, uint8_t flag, uint8_t sound) {
    TTEntry *e = &tt[key & tt_mask];
    uint64_t d = (uint64_t)(uint16_t)value | (uint64_t)move << 16 | (uint64_t)depth << 32
               | (uint64_t)flag << 40 | (uint64_t)sound << 44;
    atomic_store_explicit(&e->data, d, memory_order_relaxed);
    atomic_store_explicit(&e->xkey, key ^ d, memory_order_relaxed);
}

/* THB-01: a TT cutoff must never hand back a mate score whose distance
 * exceeds the budget remaining at this node. The cutoffs below are gated on
 * `tv.depth >= depth` and tv.depth is unsigned, so once depth has run out that
 * test is unconditionally true: any stored mate was handed back at a node with
 * no budget left and the ply re-basing dressed it up as a win found within the
 * horizon. Cold depth 12 on `f1w1/2k1/K2p/W1UF[Up] b` returned 29985 - "Black
 * wins in 15" - against a true distance of 13, so both the verdict and the
 * distance were wrong. The defect was directional (a cutoff is only ever taken
 * on a deeper or genuinely sound entry, so it can add wins and never conceal
 * one), which is why no recorded negative bound was ever at risk.
 *   0  pre-fix behaviour, kept as the node-identity pin for a toggle-off run
 *   1  form H: refuse every cutoff at a horizon node
 *   2  form M: refuse exactly the cutoffs that overrun the budget (shipped) */
#define TT_BUDGET_GUARD 2

static inline int tt_cut_ok(int v, int ply, int depth) {
#if TT_BUDGET_GUARD == 0
    (void)v; (void)ply; (void)depth; return 1;
#elif TT_BUDGET_GUARD == 1
    (void)v; (void)ply; return depth > 0;
#else
    int a = v < 0 ? -v : v;
    if (a <= MATE_BOUND) return 1;      /* carries no distance claim to overrun */
    return MATE - a - ply <= depth;     /* plies from HERE to the mate */
#endif
}

/* TT persistence: a multi-hour depth is worth resuming.
 *
 * The xkey ^ data == key trick makes an entry self-validating against
 * CORRUPTION, which says nothing about PROVENANCE: it holds just as well for
 * an entry a different engine wrote. Two things are therefore stamped in the
 * header. The Zobrist seed, because keys are meaningless under other tables.
 * And a build fingerprint (THB-07), because th_key depends only on (board,
 * hands, stm, seed) and every one of those survives a rules change unchanged -
 * a build in which a ferz moved like a king (perft(1..4) = 7/43/362/3171
 * against the stock 6/33/241/1855) wrote a dump that the stock build loaded
 * with rc = 0 and 3,659 foreign-rule entries. engine_c.py passes
 * -DTH_BUILD_ID=<hash of this file>, so ANY source edit invalidates every
 * dump; a hand-maintained format id would not, because nobody bumps one when
 * editing pseudo_moves. */
#ifndef TH_BUILD_ID
#define TH_BUILD_ID 0ULL     /* a build that did not pass -D: unidentified */
#endif
uint64_t th_build_id(void) { return (uint64_t)TH_BUILD_ID; }

static uint64_t tt_seed_used = 0;

/* THB-08: write to <fname>.tmp and rename. fopen(fname, "wb") truncated the
 * LIVE checkpoint before a byte was written and nothing restored it, so a save
 * that failed or was interrupted destroyed the previous good dump: a 268 MB
 * dump overwritten by a 2^18 table became 4 MB and would not reload. rename()
 * is atomic within a filesystem, so the old dump stands until the new one is
 * complete on disk - hence the fsync before it, since a crash right after a
 * "checkpointed" line would otherwise still lose the dump. */
int th_tt_save(const char *fname) {
    if (!tt) return -1;
    char tmp[4096];
    size_t n = strlen(fname);
    if (n + 5 > sizeof tmp) return -1;
    memcpy(tmp, fname, n);
    memcpy(tmp + n, ".tmp", 5);
    FILE *f = fopen(tmp, "wb");
    if (!f) return -1;
    uint64_t hdr[4] = {0x54494E59484F5553ULL, tt_mask + 1, tt_seed_used,
                       (uint64_t)TH_BUILD_ID};
    int ok = fwrite(hdr, sizeof hdr, 1, f) == 1 &&
             fwrite(tt, sizeof(TTEntry), tt_mask + 1, f) == tt_mask + 1 &&
             fflush(f) == 0 && fsync(fileno(f)) == 0;
    fclose(f);
    if (!ok || rename(tmp, fname) != 0) { remove(tmp); return -1; }
    return 0;
}

/* returns 0 on success, -1 on missing/unreadable, -2 on size/seed mismatch,
 * -3 when the dump came from a different build of tinyhouse.c */
int th_tt_load(const char *fname) {
    if (!tt) return -1;
    FILE *f = fopen(fname, "rb");
    if (!f) return -1;
    uint64_t hdr[4];
    if (fread(hdr, sizeof hdr, 1, f) != 1 || hdr[0] != 0x54494E59484F5553ULL) { fclose(f); return -1; }
    if (hdr[1] != tt_mask + 1 || hdr[2] != tt_seed_used) { fclose(f); return -2; }
    if (hdr[3] != (uint64_t)TH_BUILD_ID) { fclose(f); return -3; }
    int ok = fread(tt, sizeof(TTEntry), tt_mask + 1, f) == tt_mask + 1;
    fclose(f);
    return ok ? 0 : -1;
}

/* `best` (TH-43) is the searching thread's own best move. root_search used to
 * recover it by probing the TT, which returns nothing at depth 1: unproven
 * depth-1 stores are skipped on purpose, so /api/analyze?depth=1 answered with
 * best = null. The searcher already knows the move; it just was not handing it
 * back. Reporting it does not touch a single node. */
typedef struct { int rep_min; uint8_t snd; uint16_t best; } SInfo;

/* cheap direct-check detection for ordering only (ignores discovered and
 * unblocking effects; ordering need not be exact) */
static int gives_direct_check(const THPos *p, uint16_t m, int ks) {
    int to = M_TO(m), us = p->stm;
    int t = M_IS_DROP(m) ? M_FROM(m) : M_PROMO(m) ? M_PROMO(m) : TYPE(p->board[M_FROM(m)]);
    const uint8_t *nb;
    switch (t) {
    case P: for (nb = PCAPS[us][to]; *nb != 0xff; nb++) if (*nb == ks) return 1; return 0;
    case F: for (nb = DIAG[to]; *nb != 0xff; nb++) if (*nb == ks) return 1; return 0;
    case W: for (nb = ORTH[to]; *nb != 0xff; nb++) if (*nb == ks) return 1; return 0;
    case U:
        for (int i = 0; MAO_MOVES[to][i][0] != 0xff; i++)
            if (MAO_MOVES[to][i][1] == ks && !p->board[MAO_MOVES[to][i][0]]) return 1;
        return 0;
    }
    return 0;
}

static int order_score(const THPos *p, uint16_t m, uint16_t ttm, int ply, int ks) {
    if (m == ttm) return 1 << 30;
    int s = 0;
    if (gives_direct_check(p, m, ks)) s += 1 << 21;
    if (!M_IS_DROP(m) && p->board[M_TO(m)])
        return s + (1 << 20) + TYPE(p->board[M_TO(m)]) * 16 + M_PROMO(m);
    if (s) return s;
    if (m == killers[ply][0]) return (1 << 19);
    if (m == killers[ply][1]) return (1 << 19) - 1;
    int j = tl_jitter ? (int)(((m ^ tl_jitter) * 2654435761u) >> 27) : 0;
    return history[(int)p->stm][m & 2047] + j;
}

static int search(THPos *p, int depth, int ply, int alpha, int beta, SInfo *si) {
    si->rep_min = MAXPLY;
    si->snd = 0;
    si->best = 0;
    if (g_abort) return 0;
    if (++tl_pending >= 4096) nodes_flush();

    /* mate distance pruning: value here is within [-(MATE-ply), MATE-ply] */
    if (alpha < -(MATE - ply)) alpha = -(MATE - ply);
    if (beta > MATE - ply) beta = MATE - ply;
    if (alpha >= beta) { si->snd = alpha == MATE - ply ? SND_UB : 0; return alpha; }

    uint64_t key = th_key(p);
    for (int j = ply - 2; j >= 0; j -= 2)
        if (path[j] == key) { si->rep_min = j; si->snd = SND_LB | SND_UB; return 0; }
    if (ply >= MAXPLY - 2) return 0;
    path[ply] = key;

    uint16_t ttm = 0;
    TTView tv;
    int tv_hit = tt_probe(key, &tv);
    if (tv_hit) {
        ttm = tv.move;
        int v = tv.value;
        if (v > MATE_BOUND) v -= ply;
        else if (v < -MATE_BOUND) v += ply;
        if (ply > 0 && tt_cut_ok(v, ply, depth)) {
            if (tv.flag == TT_EXACT && (tv.depth >= depth || tv.sound == (SND_LB | SND_UB))) {
                si->snd = tv.sound; return v;
            }
            if (tv.flag == TT_LOWER && v >= beta && (tv.depth >= depth || (tv.sound & SND_LB))) {
                si->snd = tv.sound & SND_LB; return v;
            }
            if (tv.flag == TT_UPPER && v <= alpha && (tv.depth >= depth || (tv.sound & SND_UB))) {
                si->snd = tv.sound & SND_UB; return v;
            }
        }
    }

    uint16_t buf[128];
    int n = pseudo_moves(p, buf);
    Undo u;
    int any = 0;
    if (depth <= 0) {
        for (int i = 0; i < n && !any; i++) {
            make(p, buf[i], &u);
            if (!th_in_check(p, 1 - p->stm)) any = 1;
            unmake(p, &u);
        }
        if (any) return 0;                    /* unknown: no soundness */
        si->snd = SND_LB | SND_UB;
        return th_in_check(p, p->stm) ? -(MATE - ply) : (MATE - ply);
    }

    int scores[128];
    int enemy_ks = king_sq(p, 1 - p->stm);
    for (int i = 0; i < n; i++) scores[i] = order_score(p, buf[i], ttm, ply, enemy_ks);

    int best = -MATE, alpha0 = alpha;
    uint16_t bestm = 0;
    int my_rep = MAXPLY;
    uint8_t best_child_ub = 0, all_children_lb = 1, cutoff = 0;
    for (int i = 0; i < n; i++) {
        int bi = i;
        for (int j = i + 1; j < n; j++) if (scores[j] > scores[bi]) bi = j;
        uint16_t m = buf[bi]; buf[bi] = buf[i]; scores[bi] = scores[i]; buf[i] = m;
        make(p, m, &u);
        if (th_in_check(p, 1 - p->stm)) { unmake(p, &u); continue; }
        any = 1;
        SInfo ci;
        int v = -search(p, depth - 1, ply + 1, -beta, -alpha, &ci);
        unmake(p, &u);
        if (ci.rep_min < my_rep) my_rep = ci.rep_min;
        if (!(ci.snd & SND_LB)) all_children_lb = 0;
        if (v > best) {
            best = v; bestm = m;
            best_child_ub = (ci.snd & SND_UB) ? 1 : 0;
            if (v > alpha) alpha = v;
            if (alpha >= beta) {
                cutoff = 1;
                if (!M_IS_DROP(m) && !p->board[M_TO(m)]) {
                    int16_t *h = &history[(int)p->stm][m & 2047];
                    *h += depth * depth; if (*h > 16000) *h /= 2;
                    if (killers[ply][0] != m) { killers[ply][1] = killers[ply][0]; killers[ply][0] = m; }
                }
                break;
            }
        }
    }
    if (!any) {
        si->snd = SND_LB | SND_UB;
        return th_in_check(p, p->stm) ? -(MATE - ply) : (MATE - ply);
    }

    /* bound duality: LB of node <- UB of best child; UB of node <- LB of all */
    uint8_t snd = 0;
    if (best_child_ub) snd |= SND_LB;
    if (!cutoff && all_children_lb) snd |= SND_UB;
    si->snd = snd;
    si->rep_min = my_rep;
    si->best = bestm;

    if (tt && my_rep >= ply && !g_abort) {
        int flag = best <= alpha0 ? TT_UPPER : cutoff ? TT_LOWER : TT_EXACT;
        uint8_t ssnd = flag == TT_EXACT ? snd :
                       flag == TT_LOWER ? (snd & SND_LB) : (snd & SND_UB);
        int proven = (ssnd == (SND_LB | SND_UB) && flag == TT_EXACT) ||
                     best > MATE_BOUND || best < -MATE_BOUND;
        /* replacement decision reuses the entry probed at node entry; skip
         * unproven depth-1 stores entirely (they are most of the write
         * traffic and nearly worthless, and they thrash shared cache lines) */
        int old_proven = tv_hit && tv.sound == (SND_LB | SND_UB) && tv.flag == TT_EXACT;
        if ((depth >= 2 || proven) &&
            (!tv_hit || proven || (!old_proven && depth >= tv.depth))) {
            int sv = best;
            if (sv > MATE_BOUND) sv += ply;
            else if (sv < -MATE_BOUND) sv -= ply;
            tt_store(key, (int16_t)sv, bestm, (uint8_t)(depth < 0 ? 0 : depth), (uint8_t)flag, ssnd);
        }
    }
    return best;
}

typedef struct { THPos pos; int depth, alpha, beta; } HelperArg;

static _Atomic uint32_t g_tid;

static void *helper_main(void *v) {
    HelperArg *a = v;
    tl_jitter = 0x9E3779B9u * (atomic_fetch_add(&g_tid, 1) + 1);
    SInfo si;
    search(&a->pos, a->depth, 0, a->alpha, a->beta, &si);
    nodes_flush();
    return 0;
}

/* Root search with lazy-SMP helpers. Returns value from side-to-move's
 * perspective; *snd gets the soundness flags of the MAIN thread's result. */
static int root_search(THPos *p, int depth, int alpha, int beta, int workers,
                       uint16_t *bestmove, int *snd) {
    memset(killers, 0, sizeof killers);
    g_abort = 0;
    pthread_t th[63];
    HelperArg args[63];
    int nh = workers - 1;
    if (nh < 0) nh = 0;
    if (nh > 63) nh = 63;
    for (int i = 0; i < nh; i++) {
        args[i].pos = *p; args[i].depth = depth + (i & 1);
        args[i].alpha = alpha; args[i].beta = beta;
        pthread_create(&th[i], 0, helper_main, &args[i]);
    }
    SInfo si;
    int v = search(p, depth, 0, alpha, beta, &si);
    g_abort = 1;
    for (int i = 0; i < nh; i++) pthread_join(th[i], 0);
    g_abort = 0;
    nodes_flush();
    if (snd) *snd = si.snd;
    if (bestmove) {
        TTView tv;
        /* the searcher's own move first; the table is the fallback for the
         * depth <= 0 roots, where no search ran and there is nothing to give */
        *bestmove = si.best ? si.best : (tt_probe(th_key(p), &tv) ? tv.move : 0);
    }
    return v;
}

int th_solve_mt(THPos *p, int depth, int workers, uint16_t *bestmove, int *snd) {
    return root_search(p, depth, -MATE, MATE, workers, bestmove, snd);
}
int th_solve(THPos *p, int depth, uint16_t *bestmove, int *snd) {
    return th_solve_mt(p, depth, 1, bestmove, snd);
}
int th_search(THPos *p, int depth, uint16_t *bestmove) {
    return th_solve(p, depth, bestmove, 0);
}

/* Null-window mate hunt: proves/disproves "the given color forces a win within
 * depth plies". Returns the value from that color's perspective.
 * > MATE_BOUND is a proof of a forced win, and (since TT_BUDGET_GUARD) of the
 * distance it reports. A return of 0 is a proof of the negative: no forced win
 * exists within that many plies. Both are proofs relative to the Zobrist
 * keying - a 64-bit collision has no directional structure and could prune a
 * subtree holding a real mate, so a second seed is the check on both, not just
 * on the wins. */
int th_mate_hunt_mt(THPos *p, int depth, int color, int workers, uint16_t *bestmove) {
    if (p->stm == color)
        return root_search(p, depth, MATE_BOUND, MATE, workers, bestmove, 0);
    return -root_search(p, depth, -MATE, -MATE_BOUND, workers, bestmove, 0);
}
int th_mate_hunt(THPos *p, int depth, int color, uint16_t *bestmove) {
    return th_mate_hunt_mt(p, depth, color, 1, bestmove);
}

/* Per-root-move values at fixed depth (root side's perspective). */
int th_root_moves(THPos *p, int depth, uint16_t *out_moves, int *out_values) {
    uint16_t buf[128];
    int n = th_moves(p, buf);
    Undo u;
    uint64_t rootkey = th_key(p);
    for (int i = 0; i < n; i++) {
        path[0] = rootkey;
        make(p, buf[i], &u);
        SInfo si;
        int v = -search(p, depth - 1, 1, -MATE, MATE, &si);
        unmake(p, &u);
        out_moves[i] = buf[i]; out_values[i] = v;
    }
    nodes_flush();
    return n;
}

/* Reseed the Zobrist tables. A 64-bit key can collide, and a colliding
 * position inheriting a sound-flagged entry would return another position's
 * value flagged as PROVEN. Re-running a proof under a different seed makes
 * the two runs' collision sets independent, so agreement across seeds is the
 * cheap check against that tail risk. Callers must clear the TT after this
 * (th_tt_init), since existing entries are keyed under the old tables. */
void th_seed(uint64_t s) {
    rng_state = s ? s : 0x9E3779B97F4A7C15ULL;
    tt_seed_used = rng_state;
    for (int i = 0; i < 16; i++) for (int j = 0; j < 32; j++) zob_piece[i][j] = rng64();
    for (int c = 0; c < 2; c++) for (int t = 0; t < 4; t++)
        for (int i = 0; i < 3; i++) zob_hand[c][t][i] = rng64();
    zob_stm = rng64();
}

void th_init(void) {
    init_tables();
    th_seed(0x9E3779B97F4A7C15ULL);
}
