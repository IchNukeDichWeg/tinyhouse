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

/* TH-12: the mover's king square is loop-invariant across a legality scan
 * except for the one move that moves the king, so king_sq()'s 16-square scan
 * does not need repeating per move.
 *
 * The drop test MUST come first. For a drop, M_FROM(m) is the piece TYPE (0-3),
 * which aliases square indices 0-3, so a bare `M_FROM(m) == ks` false-positives
 * whenever the mover's own king stands on rank 1. */
#define KING_SQ_HOIST 1
#define KS_AFTER(m, ks) ((!M_IS_DROP(m) && M_FROM(m) == (ks)) ? M_TO(m) : (ks))

/* TH-11: this game has NO SLIDERS, so nothing can be pinned in the classical
 * sense and most moves cannot expose the mover's own king at all. The only
 * ways one can are: the king itself moving; the mover already being in check;
 * or a piece vacating the LEG square of an enemy mao whose destination is the
 * king. A capture cannot open a line, because the captured square stays
 * occupied by the capturer. A drop only ever fills a square.
 *
 * Trap A, and it is not a nicety: "a drop can never expose the own king" is
 * true but insufficient, because a mover who IS in check must BLOCK. Gating
 * drops as unconditionally legal before the in-check test gives
 * perft(6) = 3,226,861 against the true 139,141, so the whole shortcut is
 * gated on not being in check.
 *
 * Trap B: the mao-origin test is TYPE(pc) == U, NOT
 * board[origin] == PIECE(them, U, 0). attacked() ignores the promoted bit and
 * a pawn can promote to U; the buggy form gives perft(7) = 892,492,429 against
 * 196,868,543 on a promoted-mao position.
 *
 * Split into two toggles because the backlog measures this as a large win for
 * perft and neutral-to-negative inside search(), and those are separate claims
 * that deserve separate measurements. */
#define FAST_LEGALITY 1
#define FAST_LEGALITY_IN_SEARCH 0

static int attacked(const THPos *p, int sq, int by);

static int cannot_expose_king(const THPos *p, uint16_t m, int ks) {
    if (M_IS_DROP(m)) return 1;
    int frm = M_FROM(m);
    if (frm == ks) return 0;
    int them = 1 - p->stm;
    for (int i = 0; MAO_ATT[ks][i][0] != 0xff; i++) {
        if (MAO_ATT[ks][i][1] != frm) continue;
        int pc = p->board[MAO_ATT[ks][i][0]];
        if (pc && COLOR(pc) == them && TYPE(pc) == U) return 0;
    }
    return 1;
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

/* 0 = pre-change behaviour, the node-identity pin; 1 = shipped (see TH-09
 * below, at the drop loop) */
#define DROP_EMPTY_MASK 1

/* TH-16: TH-11's trap A, used constructively. When the mover is in check a
 * drop cannot capture, so it can only help by BLOCKING - and in this game only
 * a mao check has anything to block, since every other attacker is adjacent to
 * the king. So under check, either exactly one mao attacks and its leg square
 * is the single droppable square, or no drop is legal at all and the whole
 * drop section can be skipped. Perft is unchanged by construction: every
 * pruned drop was illegal anyway, and the surviving moves keep their order.
 *
 * The caller has to say whether the mover is in check, because pseudo_moves
 * does not know and computing it here would charge every node for a fact most
 * of them already have. -1 means "unknown", which generates everything. */
#define DROP_CHECK_PRUNE 1
#define DROP_CHECK_PRUNE_IN_SEARCH 1

/* 0, or 1 with *sq set to the only square a drop may answer the check on */
static int check_block_square(const THPos *p, int ks, int *sq) {
    int them = 1 - p->stm, attackers = 0, leg = -1;
    const uint8_t *n;
    for (n = ORTH[ks]; *n != 0xff; n++) {
        int pc = p->board[*n];
        if (pc && COLOR(pc) == them && (TYPE(pc) == W || TYPE(pc) == K)) attackers++;
    }
    for (n = DIAG[ks]; *n != 0xff; n++) {
        int pc = p->board[*n];
        if (pc && COLOR(pc) == them && (TYPE(pc) == F || TYPE(pc) == K)) attackers++;
    }
    for (n = PCAPS[1 - them][ks]; *n != 0xff; n++) {
        int pc = p->board[*n];
        if (pc && COLOR(pc) == them && TYPE(pc) == P) attackers++;
    }
    if (attackers) return 0;              /* adjacent attacker: nothing to block */
    for (int i = 0; MAO_ATT[ks][i][0] != 0xff; i++) {
        int pc = p->board[MAO_ATT[ks][i][0]];
        if (pc && COLOR(pc) == them && TYPE(pc) == U && !p->board[MAO_ATT[ks][i][1]]) {
            /* A double mao check is blockable iff both attackers run THROUGH
             * THE SAME LEG - one drop then blocks both. The first version
             * declared every double check unblockable and pruned four legal
             * blocking drops on 1U~2/2U1/k1K1/4[FWpfuw] b, which perft never
             * caught: the acceptance positions had no same-leg double check,
             * and neither did 74,702 randomly walked positions. Found by the
             * bitboard perft cross-check. */
            if (attackers && MAO_ATT[ks][i][1] != leg) return 0;
            attackers++;
            leg = MAO_ATT[ks][i][1];
        }
    }
    if (!attackers) return 0;
    *sq = leg;
    return 1;
}

static int pseudo_moves(const THPos *p, uint16_t *out, int in_check) {
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
    /* TH-09: with anything in hand the empty-square scan ran once per piece
     * TYPE, up to four times over the same 16 squares. Collect them once.
     * Ascending square order is preserved deliberately: emission order is what
     * move ordering sees, and changing it would break node identity, which is
     * this change's whole acceptance test.
     *
     * The mask is built in its OWN gated loop and NOT accumulated inside the
     * piece loop above, which already walks all 16 squares and looks like the
     * better place for it. That version measured 6.5% SLOWER. */
#if DROP_CHECK_PRUNE
    if (in_check == 1) {
        int blk, ks = king_sq(p, us);
        if (!check_block_square(p, ks, &blk)) return n;
        if (!p->board[blk]) {
            for (int t = 0; t < 4; t++) {
                if (!p->hands[us][t]) continue;
                if (t == P && ((blk >> 2) == 0 || (blk >> 2) == 3)) continue;
                out[n++] = MV_DROP(t, blk);
            }
        }
        return n;
    }
#else
    (void)in_check;
#endif
#if DROP_EMPTY_MASK
    if (p->hands[us][0] | p->hands[us][1] | p->hands[us][2] | p->hands[us][3]) {
        uint8_t empt[16];
        int ne = 0;
        for (int s = 0; s < 16; s++) if (!b[s]) empt[ne++] = s;
        for (int t = 0; t < 4; t++) {
            if (!p->hands[us][t]) continue;
            for (int i = 0; i < ne; i++) {
                int s = empt[i];
                if (t == P && ((s >> 2) == 0 || (s >> 2) == 3)) continue;
                out[n++] = MV_DROP(t, s);
            }
        }
    }
#else
    for (int t = 0; t < 4; t++) {
        if (!p->hands[us][t]) continue;
        for (int s = 0; s < 16; s++) {
            if (b[s]) continue;
            if (t == P && ((s >> 2) == 0 || (s >> 2) == 3)) continue;
            out[n++] = MV_DROP(t, s);
        }
    }
#endif
    return n;
}

/* legal moves; returns count. out may be NULL to just count. */
int th_moves(THPos *p, uint16_t *out) {
    uint16_t buf[128];
    Undo u;
    int ks = king_sq(p, p->stm);
    int in_chk = attacked(p, ks, 1 - p->stm);
    int n = pseudo_moves(p, buf, in_chk), nl = 0;
    for (int i = 0; i < n; i++) {
#if FAST_LEGALITY
        if (!in_chk && cannot_expose_king(p, buf[i], ks)) {
            if (out) out[nl] = buf[i];
            nl++;
            continue;
        }
#endif
#if KING_SQ_HOIST
        int myks = KS_AFTER(buf[i], ks);
        make(p, buf[i], &u);
        if (!attacked(p, myks, p->stm)) {
#else
        make(p, buf[i], &u);
        if (!th_in_check(p, 1 - p->stm)) {
#endif
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

uint64_t th_perft_mailbox(THPos *p, int depth) {
    uint16_t buf[128];
    Undo u;
    if (depth == 0) return 1;
    int ks = king_sq(p, p->stm);
    int in_chk = attacked(p, ks, 1 - p->stm);
    int n = pseudo_moves(p, buf, in_chk);
    uint64_t total = 0;
    for (int i = 0; i < n; i++) {
#if FAST_LEGALITY
        if (!in_chk && cannot_expose_king(p, buf[i], ks)) {
            if (depth == 1) { total += 1; continue; }
            make(p, buf[i], &u);
            total += th_perft_mailbox(p, depth - 1);
            unmake(p, &u);
            continue;
        }
#endif
#if KING_SQ_HOIST
        int myks = KS_AFTER(buf[i], ks);
        make(p, buf[i], &u);
        if (!attacked(p, myks, p->stm))
#else
        make(p, buf[i], &u);
        if (!th_in_check(p, 1 - p->stm))
#endif
            total += depth == 1 ? 1 : th_perft_mailbox(p, depth - 1);
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

/* TH-10: the key for a child node, computed from the parent's key and the move
 * instead of rescanning 16 squares and 8 hand counts.
 *
 * Deliberately NOT done inside make()/unmake(). The obvious placement makes
 * perft and th_moves pay for a key they never read - the backlog measured
 * perft(8) at 0.955x, a 4.7% LOSS - and avoiding that needs two make()
 * variants. Threading the key through search() as a parameter costs those
 * callers nothing at all, and it also disposes of the reported SMP trap by
 * construction: there is no shared "current key" to go stale, because every
 * root (main thread and every helper) computes its own with th_key().
 *
 * A hand count needs TWO xors, not one: th_key xors zob_hand for every count
 * including 0, so moving from c to c-1 must remove c and add c-1. */
#define MDP_SYMMETRIC_SND 1
#define INCREMENTAL_KEY 1
#define KEY_PARANOIA 0        /* 1 = assert the incremental key at every node */

static uint64_t key_after(const THPos *p, uint16_t m, uint64_t key) {
    int us = p->stm, to = M_TO(m);
    key ^= zob_stm;
    if (M_IS_DROP(m)) {
        int t = M_FROM(m), c = p->hands[us][t];
        key ^= zob_piece[to][PIECE(us, t, 0)];
        key ^= zob_hand[us][t][c] ^ zob_hand[us][t][c - 1];
        return key;
    }
    int frm = M_FROM(m), cap = p->board[to], pc = p->board[frm];
    key ^= zob_piece[frm][pc];
    if (cap) {
        int ct = PROMOTED(cap) ? P : TYPE(cap), c = p->hands[us][ct];
        key ^= zob_piece[to][cap];
        key ^= zob_hand[us][ct][c] ^ zob_hand[us][ct][c + 1];
    }
    key ^= zob_piece[to][M_PROMO(m) ? PIECE(us, M_PROMO(m), 1) : pc];
    return key;
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

/* TH-19: `history` is thread-local and nothing ever resets it, so repeats of
 * the same search in one process are NOT independent samples. Measured, five
 * repeats of an identical depth-13 hunt with a fresh table before each:
 * 757,431 / 839,298 / 845,107 / 1,345,672 / 795,066 in one process, against
 * 757,431 five times in five separate processes. A scratch build with the one
 * memset below made the in-process repeats identical, so history is the sole
 * carrier.
 *
 * Two separate questions, deliberately answered separately. MEASUREMENT wants
 * the table cleared between repeats, and that is th_clear_history(), an
 * explicit call for benchmark harnesses that changes no search behaviour at
 * all. SEARCH STRENGTH is the open question - carry-over across successive
 * iterative-deepening depths may well be worth keeping - so the toggle below
 * stays OFF until someone measures that, which is a different experiment from
 * repeats at one depth. */
#define CLEAR_HISTORY_AT_ROOT 0

void th_clear_history(void) { memset(history, 0, sizeof history); }

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

/* Occupancy of the table, for sizing decisions (TH-39). Counting is O(entries)
 * and only meaningful between searches, so it is a tool call and nothing in the
 * search reads it. */
uint64_t th_tt_fill(void) {
    if (!tt) return 0;
    uint64_t used = 0;
    for (uint64_t i = 0; i <= tt_mask; i++)
        if (atomic_load_explicit(&tt[i].data, memory_order_relaxed)) used++;
    return used;
}

static void nodes_flush(void) {
    if (tl_pending) { atomic_fetch_add_explicit(&g_nodes, tl_pending, memory_order_relaxed); tl_pending = 0; }
}
/* TH-31: this counter is CUMULATIVE for the life of the process. Nothing
 * resets it - not th_tt_init, not th_seed - so a caller wanting the cost of
 * one search must difference it around the call, which all three shipped
 * callers do. No reset entry point is provided on purpose: differencing is
 * correct under concurrency and a reset is not.
 * It also does NOT count perft. th_perft recurses without touching g_nodes, so
 * differencing around a perft yields zero; th_perft's own return value is the
 * leaf count and is what a perft benchmark should read. */
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

/* TH-08: the horizon asks one yes/no question - "is there a legal move" - and
 * used to build the entire pseudo-move list to answer it, then walk it until
 * the first legal move. Two things make that cheap instead.
 *
 * A drop can never expose the mover's own king, so if the mover is NOT in
 * check and holds any piece with a legal empty target, a legal move exists and
 * nothing needs generating. The in-check gate is not optional: being in check
 * is exactly the case where a drop must BLOCK. Gating drops as unconditionally
 * legal without it gives perft(6) = 3,226,861 against the true 139,141.
 *
 * Otherwise it falls back to generate-and-test, which is what the old code did
 * unconditionally. Node counts cannot change: the horizon never recurses, so
 * only the yes/no answer escapes this function.
 *   0 = pre-change behaviour, the node-identity pin for a toggle-off run
 *   1 = shipped */
#define HORIZON_FAST_PATH 1

static int horizon_has_move(THPos *p, int in_check) {
#if HORIZON_FAST_PATH
    if (!in_check) {
        int us = p->stm;
        for (int t = 0; t < 4; t++) {
            if (!p->hands[us][t]) continue;
            for (int s = 0; s < 16; s++) {
                if (p->board[s]) continue;
                if (t == P && ((s >> 2) == 0 || (s >> 2) == 3)) continue;
                return 1;
            }
        }
    }
#else
    (void)in_check;
#endif
    uint16_t buf[128];
    int n = pseudo_moves(p, buf, in_check);
    Undo u;
#if KING_SQ_HOIST
    int ks = king_sq(p, p->stm);
#endif
    for (int i = 0; i < n; i++) {
#if KING_SQ_HOIST
        int myks = KS_AFTER(buf[i], ks);
        make(p, buf[i], &u);
        int ok = !attacked(p, myks, p->stm);
#else
        make(p, buf[i], &u);
        int ok = !th_in_check(p, 1 - p->stm);
#endif
        unmake(p, &u);
        if (ok) return 1;
    }
    return 0;
}

static int search(THPos *p, int depth, int ply, int alpha, int beta, SInfo *si, uint64_t key) {
    si->rep_min = MAXPLY;
    si->snd = 0;
    si->best = 0;
    if (g_abort) return 0;
    if (++tl_pending >= 4096) nodes_flush();

    /* mate distance pruning: value here is within [-(MATE-ply), MATE-ply] */
    if (alpha < -(MATE - ply)) alpha = -(MATE - ply);
    if (beta > MATE - ply) beta = MATE - ply;
    /* TH-13: credit BOTH ends of the clamp, not just the top. If alpha sits at
     * the largest value reachable from this ply the true value is at most that,
     * so the return is a sound upper bound; if it sits at the smallest, the true
     * value is at least that, so it is a sound lower bound. Only the first half
     * was credited. Flag tightness only - it cannot change a value, since the
     * return is the same either way. */
    if (alpha >= beta) {
#if MDP_SYMMETRIC_SND
        si->snd = (alpha == MATE - ply ? SND_UB : 0) | (alpha == -(MATE - ply) ? SND_LB : 0);
#else
        si->snd = alpha == MATE - ply ? SND_UB : 0;
#endif
        return alpha;
    }

#if !INCREMENTAL_KEY
    key = th_key(p);
#elif KEY_PARANOIA
    if (key != th_key(p)) { fprintf(stderr, "incremental key mismatch at ply %d\n", ply); abort(); }
#endif
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

    Undo u;
    int any = 0;
    if (depth <= 0) {
        int in_chk = th_in_check(p, p->stm);
        if (horizon_has_move(p, in_chk)) return 0;   /* unknown: no soundness */
        si->snd = SND_LB | SND_UB;
        return in_chk ? -(MATE - ply) : (MATE - ply);
    }

    uint16_t buf[128];
#if DROP_CHECK_PRUNE_IN_SEARCH
    /* TH-16, class B. Pruning drops that cannot answer a check removes only
     * ILLEGAL moves, but it is NOT node-identical: order_score produces ties
     * (equal history, usually 0) and the selection sort takes the first index
     * holding the maximum, so shortening the list changes which tied legal move
     * is searched first. Nodes-to-depth is the metric here, not time. */
    int n = pseudo_moves(p, buf, attacked(p, king_sq(p, p->stm), 1 - p->stm));
#else
    int n = pseudo_moves(p, buf, -1);
#endif
    int scores[128];
    int enemy_ks = king_sq(p, 1 - p->stm);
#if KING_SQ_HOIST
    int my_ks = king_sq(p, p->stm);
#endif
#if FAST_LEGALITY_IN_SEARCH
    int in_chk_root = attacked(p, my_ks, 1 - p->stm);
#endif
    for (int i = 0; i < n; i++) scores[i] = order_score(p, buf[i], ttm, ply, enemy_ks);

    int best = -MATE, alpha0 = alpha;
    uint16_t bestm = 0;
    int my_rep = MAXPLY;
    uint8_t best_child_ub = 0, all_children_lb = 1, cutoff = 0;
    for (int i = 0; i < n; i++) {
        int bi = i;
        for (int j = i + 1; j < n; j++) if (scores[j] > scores[bi]) bi = j;
        uint16_t m = buf[bi]; buf[bi] = buf[i]; scores[bi] = scores[i]; buf[i] = m;
        uint64_t ckey = key_after(p, m, key);      /* before make: reads the pre-move board */
#if FAST_LEGALITY_IN_SEARCH
        if (!in_chk_root && cannot_expose_king(p, m, my_ks)) {
            make(p, m, &u);
            goto legal;
        }
#endif
#if KING_SQ_HOIST
        int myks = KS_AFTER(m, my_ks);
        make(p, m, &u);
        if (attacked(p, myks, p->stm)) { unmake(p, &u); continue; }
#else
        make(p, m, &u);
        if (th_in_check(p, 1 - p->stm)) { unmake(p, &u); continue; }
#endif
#if FAST_LEGALITY_IN_SEARCH
    legal:
#endif
        any = 1;
        SInfo ci;
        int v = -search(p, depth - 1, ply + 1, -beta, -alpha, &ci, ckey);
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
    search(&a->pos, a->depth, 0, a->alpha, a->beta, &si, th_key(&a->pos));
    nodes_flush();
    return 0;
}

/* Root search with lazy-SMP helpers. Returns value from side-to-move's
 * perspective; *snd gets the soundness flags of the MAIN thread's result. */
static int root_search(THPos *p, int depth, int alpha, int beta, int workers,
                       uint16_t *bestmove, int *snd) {
    memset(killers, 0, sizeof killers);
#if CLEAR_HISTORY_AT_ROOT
    memset(history, 0, sizeof history);
#endif
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
    int v = search(p, depth, 0, alpha, beta, &si, th_key(p));
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
/* TH-34: *snd carries the main thread's soundness flags out, in COLOR's frame.
 * They were discarded (a literal 0 was passed through), which made the one
 * self-consistency check available here impossible to run: a root fail-high
 * above MATE_BOUND should always carry SND_LB. It is a check and not a missing
 * proof step - with no static eval, a mate score can only come from a real
 * terminal, so a fail-high above MATE_BOUND is already a proof - but a check
 * nobody can run is worth nothing. Only meaningful on the WIN branch: the
 * negative branch is flag-free by design and the root flags are empty at every
 * depth of a real hunt. */
int th_mate_hunt_mt(THPos *p, int depth, int color, int workers, uint16_t *bestmove, int *snd) {
    if (p->stm == color)
        return root_search(p, depth, MATE_BOUND, MATE, workers, bestmove, snd);
    int v = -root_search(p, depth, -MATE, -MATE_BOUND, workers, bestmove, snd);
    /* the value was negated into color's frame, and SND_LB/SND_UB are duals of
     * the value they describe, so the bits swap with it */
    if (snd)
        *snd = ((*snd & SND_LB) ? SND_UB : 0) | ((*snd & SND_UB) ? SND_LB : 0);
    return v;
}
int th_mate_hunt(THPos *p, int depth, int color, uint16_t *bestmove) {
    return th_mate_hunt_mt(p, depth, color, 1, bestmove, 0);
}

/* Per-root-move values at fixed depth (root side's perspective).
 * TH-35: out_snd (may be NULL) carries each move's soundness flags, in the
 * frame of the value beside it. The child value is NEGATED on the way out and
 * SND_LB/SND_UB are duals of the value they describe, so the bits must be
 * SWAPPED - a badge reading the raw child flag prints "upper bound" for a
 * lower bound. Note the obvious acceptance test, "badge proven only when
 * snd == 3", is insensitive to exactly this, since 3 is invariant under the
 * swap; that is how the sign error would ship. What is actually carried here
 * is mate-row soundness: proven DRAWS are close to unreachable at GUI depths
 * (2,301 of 2,302 quiet root moves at depth 10 had no flags at all). */
int th_root_moves(THPos *p, int depth, uint16_t *out_moves, int *out_values, int *out_snd) {
    uint16_t buf[128];
    int n = th_moves(p, buf);
    Undo u;
    uint64_t rootkey = th_key(p);
    for (int i = 0; i < n; i++) {
        path[0] = rootkey;
        uint64_t ckey = key_after(p, buf[i], rootkey);
        make(p, buf[i], &u);
        SInfo si;
        int v = -search(p, depth - 1, 1, -MATE, MATE, &si, ckey);
        unmake(p, &u);
        out_moves[i] = buf[i]; out_values[i] = v;
        if (out_snd)
            out_snd[i] = ((si.snd & SND_LB) ? SND_UB : 0) | ((si.snd & SND_UB) ? SND_LB : 0);
    }
    nodes_flush();
    return n;
}

/* ------------------------------------------------------------------- df-pn
 * A second engine, because the first one structurally cannot prove a draw: its
 * horizon returns an unsound 0, so "not a win" is the absence of a proof rather
 * than a positive result. df-pn has no horizon - every leaf is a terminal or a
 * repetition - so a disproof is something it can produce directly.
 *
 * Formulation: phi/delta (Nagai), uniform across OR and AND nodes.
 *   phi(n) = min over children of delta(c)
 *   delta(n) = sum over children of phi(c)
 * An OR node is the attacker to move, an AND node the defender.
 *
 * KISHIMOTO-MULLER TWIN ENTRIES, which is what this file is really for.
 * A value that used a repetition is path-dependent: it is only valid on paths
 * that still contain the ancestor that was repeated. The conservative rule -
 * the one tinyhouse.c uses on its own store side - throws every such value
 * away, and the Python prototype measured that at 39% of everything computed.
 * A twin entry instead STORES the value together with the ancestors it is
 * conditioned on, and reuses it whenever those ancestors are on the current
 * path. Two conditioning slots, because the dependency-set size was measured
 * before this was written: 90.0% of withheld values depend on exactly one
 * ancestor, 9.9% on two, 0.08% on three. Two slots therefore recover 99.9% of
 * them; three or more are still withheld.
 *
 * A dependency on the node ITSELF never escapes it: a descendant that repeats
 * this node depends on this node being an ancestor, which it always is
 * whenever this node is being evaluated. So the node's own key is dropped from
 * the set on the way out.
 *
 * SOUNDNESS, stated exactly, because this is the part that rests on
 * measurement rather than on proof. A twin is reused when its conditioning
 * ancestors are PRESENT on the current path. That does not account for a
 * different path carrying EXTRA ancestors, which would create repetitions the
 * stored value never saw. No counterexample was found -- 3,960 agreements with
 * th_mate_hunt over 400 positions at five depths, 90 with the Python reference
 * in scripts/dfpn.py, and 114 unbounded twins-on against twins-off differentials,
 * with zero disagreements anywhere -- but absence of a counterexample is not a
 * proof, and twins-off is the arm that is sound by construction. th_dfpn takes
 * use_twins explicitly for that reason: there is no hidden default, and any
 * claim that matters should be re-run with it off.
 *
 * AND THE MEASURED VERDICT: twins work and do not help. Widening DF_DEPS_MAX
 * from 1 to 8 drives the withheld fraction from 13.9% to exactly 0.0% at 12M
 * nodes from the start -- the GHI store problem disappears completely -- while
 * the root disproof number gets WORSE, 8,397 to 10,700. At 96M nodes the start
 * position still resolves 1 of its 6 root moves and the disproof numbers rise.
 * The bottleneck is the size of the search, not the transposition table, so the
 * backlog's expectation that twins were the missing piece is refuted.
 *
 * The per-ply child cache below is not an optimisation. df-pn advances by
 * re-reading a child after searching it, so a child whose value went nowhere
 * reads back as the (1,1) initial estimate, gets selected again, and the search
 * never terminates. With twins most values now reach the table, but a withheld
 * one still needs somewhere to live for the duration of its parent's loop. */

#define DF_INF 0xFFFFFFFFu
#define DFPN_MAXPLY 256
#define DFPN_MAXMOVES 128
#define DFPATH_SLOTS 2048

/* How many conditioning ancestors a twin entry can carry. Measured before
 * choosing it: on a 200k-node sample from the start, 90.0% of path-dependent
 * values depended on exactly one ancestor, 9.9% on two and 0.08% on three --
 * but that shallow sample does NOT extrapolate, and at 48M nodes 29% of values
 * exceed two. Widening is one constant, so it is measurable rather than
 * argued. */
#define DF_DEPS_MAX 2

typedef struct { uint32_t phi, delta; } PD;
typedef struct { uint64_t key, c[DF_DEPS_MAX]; uint32_t phi, delta; } DFEntry;
/* n > DF_DEPS_MAX means "more dependencies than a twin can hold": withheld */
typedef struct { uint64_t k[DF_DEPS_MAX]; int n; } Deps;

static DFEntry *dftt = 0;
static uint64_t dftt_mask = 0;
static uint64_t zob_dfrem[DFPN_MAXPLY + 1];

static _Thread_local uint64_t df_pathset[DFPATH_SLOTS];
static _Thread_local uint32_t df_cphi[DFPN_MAXPLY][DFPN_MAXMOVES];
static _Thread_local uint32_t df_cdel[DFPN_MAXPLY][DFPN_MAXMOVES];
static _Thread_local uint8_t df_chave[DFPN_MAXPLY][DFPN_MAXMOVES];

static int df_attacker, df_use_twins, df_depth_limit, df_abort;
static uint64_t df_nodes, df_cap;
static uint64_t df_st_rep, df_st_withheld, df_st_twin_store, df_st_twin_hit,
                df_st_plain_store, df_st_plycap;

/* -- path membership, O(1). Linear probing with backward-shift deletion; keys
 * on a path are distinct by construction, since a duplicate IS a repetition and
 * is detected before the push. */
static void pathset_add(uint64_t k) {
    if (!k) k = 1;
    uint64_t i = k & (DFPATH_SLOTS - 1);
    while (df_pathset[i]) i = (i + 1) & (DFPATH_SLOTS - 1);
    df_pathset[i] = k;
}
static int pathset_has(uint64_t k) {
    if (!k) k = 1;
    uint64_t i = k & (DFPATH_SLOTS - 1);
    while (df_pathset[i]) {
        if (df_pathset[i] == k) return 1;
        i = (i + 1) & (DFPATH_SLOTS - 1);
    }
    return 0;
}
static void pathset_del(uint64_t k) {
    if (!k) k = 1;
    uint64_t i = k & (DFPATH_SLOTS - 1);
    while (df_pathset[i] != k) i = (i + 1) & (DFPATH_SLOTS - 1);
    uint64_t j = i;
    for (;;) {
        df_pathset[i] = 0;
        for (;;) {
            j = (j + 1) & (DFPATH_SLOTS - 1);
            if (!df_pathset[j]) return;
            uint64_t home = df_pathset[j] & (DFPATH_SLOTS - 1);
            if (i <= j ? (home <= i || home > j) : (home <= i && home > j)) break;
        }
        df_pathset[i] = df_pathset[j];
        i = j;
    }
}

static void dep_add(Deps *d, uint64_t k) {
    if (d->n > DF_DEPS_MAX) return;
    for (int i = 0; i < d->n; i++) if (d->k[i] == k) return;
    if (d->n == DF_DEPS_MAX) { d->n = DF_DEPS_MAX + 1; return; }
    d->k[d->n++] = k;
}
static void dep_merge(Deps *d, const Deps *s) {
    if (s->n == 0) return;
    if (s->n > DF_DEPS_MAX) { d->n = DF_DEPS_MAX + 1; return; }
    for (int i = 0; i < s->n; i++) dep_add(d, s->k[i]);
}
static void dep_drop(Deps *d, uint64_t k) {          /* the node's own key */
    if (d->n > DF_DEPS_MAX) return;
    for (int i = 0; i < d->n; i++)
        if (d->k[i] == k) { d->k[i] = d->k[d->n - 1]; d->n--; return; }
}

static uint32_t sat_add(uint32_t a, uint32_t b) {
    uint32_t s = a + b;
    return s < a ? DF_INF : s;
}

int th_dfpn_init(int log2_entries) {
    if (dftt) free(dftt);
    uint64_t n = 1ULL << log2_entries;
    dftt = calloc(n * 2, sizeof(DFEntry));       /* slot 0 plain, slot 1 twin */
    dftt_mask = n - 1;
    return dftt ? 0 : -1;
}

static int df_probe(uint64_t key, PD *out) {
    if (!dftt) return 0;
    DFEntry *e = &dftt[(key & dftt_mask) * 2];
    if (e[0].key == key) { out->phi = e[0].phi; out->delta = e[0].delta; return 1; }
    if (df_use_twins && e[1].key == key) {
        for (int i = 0; i < DF_DEPS_MAX; i++)
            if (e[1].c[i] && !pathset_has(e[1].c[i])) return 0;
        df_st_twin_hit++;
        out->phi = e[1].phi; out->delta = e[1].delta;
        return 1;
    }
    return 0;
}

static void df_store(uint64_t key, PD v, const Deps *d) {
    if (!dftt) return;
    DFEntry *e = &dftt[(key & dftt_mask) * 2];
    if (d->n == 0) {
        df_st_plain_store++;
        e[0].key = key;
        for (int i = 0; i < DF_DEPS_MAX; i++) e[0].c[i] = 0;
        e[0].phi = v.phi; e[0].delta = v.delta;
    } else if (d->n <= DF_DEPS_MAX && df_use_twins) {
        df_st_twin_store++;
        e[1].key = key;
        for (int i = 0; i < DF_DEPS_MAX; i++) e[1].c[i] = i < d->n ? d->k[i] : 0;
        e[1].phi = v.phi; e[1].delta = v.delta;
    } else {
        df_st_withheld++;
    }
}

static PD df_mid(THPos *p, uint32_t phi_th, uint32_t delta_th, int ply,
                 uint64_t key, Deps *deps) {
    PD r;
    deps->n = 0;
    if (++df_nodes > df_cap) { df_abort = 1; r.phi = 1; r.delta = 1; return r; }

    int is_or = (p->stm == df_attacker);
    uint16_t buf[DFPN_MAXMOVES];
    int n = th_moves(p, buf);

    /* A terminal is a terminal at the depth limit too: a mate reached exactly
     * at the limit is a proof, not a failure. */
    if (!n) {
        int proved = ((th_in_check(p, p->stm) ? 1 - p->stm : p->stm) == df_attacker);
        if (proved == is_or) { r.phi = 0; r.delta = DF_INF; }
        else { r.phi = DF_INF; r.delta = 0; }
        /* a terminal is path- and depth-independent, so it is stored under the
         * plain key and is valid for every remaining-depth budget */
        Deps none = {{0}, 0};
        df_store(key, r, &none);
        return r;
    }
    if (pathset_has(key)) {                       /* ancestor repetition: a draw */
        df_st_rep++;
        deps->k[0] = key; deps->n = 1;
        if (is_or) { r.phi = DF_INF; r.delta = 0; } else { r.phi = 0; r.delta = DF_INF; }
        return r;
    }
    if (df_depth_limit >= 0 && ply >= df_depth_limit) {
        /* the attacker ran out of budget. Sound to store, because the TT key
         * carries the REMAINING depth below - see tkey. */
        if (is_or) { r.phi = DF_INF; r.delta = 0; } else { r.phi = 0; r.delta = DF_INF; }
        return r;
    }
    if (ply >= DFPN_MAXPLY - 1) {
        /* Absolute recursion cap. Unlike the depth limit this is a function of
         * the PATH, not of anything in the key, so nothing derived from it may
         * be stored: n = 3 is the "too many dependencies" state, which withholds.
         * If df_st_plycap comes back 0 the cap never bound and no result was
         * affected by it. */
        df_st_plycap++;
        deps->n = DF_DEPS_MAX + 1;
        if (is_or) { r.phi = DF_INF; r.delta = 0; } else { r.phi = 0; r.delta = DF_INF; }
        return r;
    }

    /* TT key. Under a depth limit the value of a node depends on how much
     * budget is left, so the remaining depth is mixed in -- otherwise a value
     * cut short at ply 9 would be reused at ply 3, where it is simply wrong.
     * Unbounded (the mode the draw claim needs) this is the plain key. */
    uint64_t tkey = df_depth_limit >= 0
                  ? key ^ zob_dfrem[df_depth_limit - ply] : key;

    pathset_add(key);
    uint32_t *cphi = df_cphi[ply], *cdel = df_cdel[ply];
    uint8_t *chave = df_chave[ply];
    memset(chave, 0, (size_t)n);

    uint32_t phi = DF_INF, delta = 0;
    for (;;) {
        int best = -1;
        uint32_t best_cd = DF_INF, second_cd = DF_INF, best_cp = DF_INF;
        uint64_t best_key = 0;
        phi = DF_INF; delta = 0;
        Deps round = {{0}, 0};
        for (int i = 0; i < n; i++) {
            uint64_t ck = key_after(p, buf[i], key);
            uint32_t q, d;
            if (pathset_has(ck)) {
                /* a child repeating an ancestor is a draw on THIS path, checked
                 * before the caches so the dependency is never lost */
                Undo u; make(p, buf[i], &u);
                int cor = (p->stm == df_attacker);
                unmake(p, &u);
                if (cor) { q = DF_INF; d = 0; } else { q = 0; d = DF_INF; }
                dep_add(&round, ck);
                df_st_rep++;      /* counted here: a repeating child is resolved
                                   * in the scan and df_mid is never entered on it */
            } else if (chave[i]) {
                q = cphi[i]; d = cdel[i];
            } else {
                PD hit;
                uint64_t ctk = df_depth_limit >= 0
                             ? ck ^ zob_dfrem[df_depth_limit - ply - 1] : ck;
                if (df_probe(ctk, &hit)) { q = hit.phi; d = hit.delta; }
                else { q = 1; d = 1; }
            }
            if (d < phi) phi = d;
            delta = sat_add(delta, q);
            if (d < best_cd) { second_cd = best_cd; best_cd = d; best_cp = q; best = i; best_key = ck; }
            else if (d < second_cd) second_cd = d;
        }
        dep_merge(deps, &round);
        if (phi >= phi_th || delta >= delta_th || df_abort) break;

        uint32_t c_phi_th = delta_th >= DF_INF ? DF_INF
                          : (delta_th > delta - best_cp ? delta_th - (delta - best_cp) : 0);
        uint32_t c_del_th = phi_th;
        if (second_cd != DF_INF && second_cd + 1 < c_del_th) c_del_th = second_cd + 1;

        Undo u;
        make(p, buf[best], &u);
        Deps cd = {{0}, 0};
        PD cv = df_mid(p, c_phi_th, c_del_th, ply + 1, best_key, &cd);
        unmake(p, &u);
        cphi[best] = cv.phi; cdel[best] = cv.delta; chave[best] = 1;
        dep_merge(deps, &cd);
    }
    pathset_del(key);

    r.phi = phi; r.delta = delta;
    dep_drop(deps, key);                 /* a self-dependency does not escape */
    if (!df_abort) df_store(tkey, r, deps);
    return r;
}

/* Returns 1 proved, -1 disproved, 0 unresolved. stats[] (12 slots) gets
 * nodes, root pn, root dn, repetition leaves, twin stores, twin hits, plain
 * stores, withheld, ply-cap hits, and the table's occupied entry count. */
int th_dfpn(THPos *p, int attacker, uint64_t node_cap, int depth_limit,
            int use_twins, uint64_t *stats) {
    df_attacker = attacker;
    df_cap = node_cap;
    df_depth_limit = depth_limit;
    df_use_twins = use_twins;
    df_nodes = df_abort = 0;
    df_st_rep = df_st_withheld = df_st_twin_store = df_st_twin_hit = 0;
    df_st_plain_store = df_st_plycap = 0;
    memset(df_pathset, 0, sizeof df_pathset);

    Deps d = {{0}, 0};
    uint64_t key = th_key(p);
    PD r = df_mid(p, DF_INF, DF_INF, 0, key, &d);
    int is_or = (p->stm == attacker);
    uint32_t pn = is_or ? r.phi : r.delta, dn = is_or ? r.delta : r.phi;

    if (stats) {
        uint64_t used = 0;
        if (dftt)
            for (uint64_t i = 0; i <= dftt_mask; i++)
                used += (dftt[i * 2].key != 0) + (dftt[i * 2 + 1].key != 0);
        stats[0] = df_nodes; stats[1] = pn; stats[2] = dn;
        stats[3] = df_st_rep; stats[4] = df_st_twin_store; stats[5] = df_st_twin_hit;
        stats[6] = df_st_plain_store; stats[7] = df_st_withheld;
        stats[8] = df_st_plycap; stats[9] = used;
    }
    return pn == 0 ? 1 : (dn == 0 ? -1 : 0);
}

/* ---------------------------------------------------------- bitboard perft
 * A 4x4 board fits in one uint16_t, so the whole position is eleven 16-bit
 * masks plus the hand counts (~30 bytes): a child node is a struct COPY plus a
 * few XORs - no mailbox, no make/unmake, no undo. Types are mask membership
 * (king = wk & fk, wazir = wk & ~fk, ferz = fk & ~wk), and a promoted mask
 * tracks which pieces revert to pawns when captured. Legality reuses the
 * no-sliders theorem from TH-11: only king moves and enemy-mao-leg vacations
 * can expose the mover's king, so a per-node risky mask marks the origins that
 * need a real test and everything else is counted with popcount. Promotion
 * legality does not depend on the piece chosen, so a promoting move is tested
 * once and counted three times.
 *
 * Measured (M2 Pro, interleaved medians, spread under 2%): 113 Mnps on the
 * start position, 170 with hands in play, 297 drop-heavy - x2.10 / x2.20 /
 * x2.54 over the mailbox walk. Perft only: the search keeps the mailbox
 * generator, whose cost profile is TT-dominated and where the cheap
 * representation change measured as a loss (TH-14).
 *
 * The mailbox path below is kept compiled as th_perft_mailbox: it is the
 * toggle-off pin, and the differential test in test_solver.py runs both over
 * random walks forever. That differential is not decoration - writing this
 * engine found a real pruning bug in check_block_square that 74,702 walked
 * positions and every perft acceptance number had missed. Two independent
 * movegens that must agree are the instrument that catches the third bug.
 *   0 = mailbox perft, 1 = bitboard perft (counts identical either way) */
#define BITBOARD_PERFT 1


static uint16_t BB_ORTH[16], BB_DIAG[16], BB_KING[16], BB_PCAP[2][16], BB_MAOORIG[16];
#define BB_BACKRANKS 0xF00Fu
static int bb_ready = 0;

static void bb_init(void) {
    if (bb_ready) return;
    for (int s = 0; s < 16; s++) {
        for (const uint8_t *n = ORTH[s]; *n != 0xff; n++) BB_ORTH[s] |= 1u << *n;
        for (const uint8_t *n = DIAG[s]; *n != 0xff; n++) BB_DIAG[s] |= 1u << *n;
        BB_KING[s] = BB_ORTH[s] | BB_DIAG[s];
        for (int c = 0; c < 2; c++)
            for (const uint8_t *n = PCAPS[c][s]; *n != 0xff; n++) BB_PCAP[c][s] |= 1u << *n;
        for (int i = 0; MAO_ATT[s][i][0] != 0xff; i++) BB_MAOORIG[s] |= 1u << MAO_ATT[s][i][0];
    }
    bb_ready = 1;
}

typedef struct {
    uint16_t occ, by[2], pawns[2], maos[2], wk[2], fk[2], prom[2];
    uint8_t hands[2][4];
} BState;

static void bst_from(const THPos *p, BState *b) {
    memset(b, 0, sizeof *b);
    for (int s = 0; s < 16; s++) {
        int pc = p->board[s];
        if (!pc) continue;
        int c = COLOR(pc);
        uint16_t m = 1u << s;
        b->occ |= m; b->by[c] |= m;
        if (PROMOTED(pc)) b->prom[c] |= m;
        switch (TYPE(pc)) {
        case P: b->pawns[c] |= m; break;
        case U: b->maos[c] |= m; break;
        case W: b->wk[c] |= m; break;
        case F: b->fk[c] |= m; break;
        default: b->wk[c] |= m; b->fk[c] |= m;
        }
    }
    for (int c = 0; c < 2; c++)
        for (int t = 0; t < 4; t++) b->hands[c][t] = (uint8_t)p->hands[c][t];
}

static int bst_attacked(const BState *b, int sq, int by) {
    if (BB_ORTH[sq] & b->wk[by]) return 1;
    if (BB_DIAG[sq] & b->fk[by]) return 1;
    if (BB_PCAP[1 - by][sq] & b->pawns[by]) return 1;
    if (BB_MAOORIG[sq] & b->maos[by])
        for (int i = 0; MAO_ATT[sq][i][0] != 0xff; i++)
            if (((b->maos[by] >> MAO_ATT[sq][i][0]) & 1) && !((b->occ >> MAO_ATT[sq][i][1]) & 1))
                return 1;
    return 0;
}

/* child = parent + move. promo is 0 or F/U/W. */
static void bst_move(BState *b, int us, int s, int to, int promo) {
    uint16_t fm = 1u << s, tm = 1u << to;
    int them = 1 - us;
    if (b->by[them] & tm) {                          /* capture: to hand as raw type */
        int ct = (b->prom[them] & tm) ? P
               : (b->pawns[them] & tm) ? P
               : (b->maos[them] & tm) ? U
               : (b->wk[them] & tm) ? W : F;
        b->hands[us][ct]++;
        b->by[them] &= (uint16_t)~tm;
        b->pawns[them] &= (uint16_t)~tm; b->maos[them] &= (uint16_t)~tm;
        b->wk[them] &= (uint16_t)~tm; b->fk[them] &= (uint16_t)~tm;
        b->prom[them] &= (uint16_t)~tm;
    }
    b->occ = (uint16_t)((b->occ & ~fm) | tm);
    b->by[us] = (uint16_t)((b->by[us] & ~fm) | tm);
    if (b->prom[us] & fm) { b->prom[us] = (uint16_t)((b->prom[us] & ~fm) | tm); }
    if (b->pawns[us] & fm) {
        b->pawns[us] &= (uint16_t)~fm;
        if (promo == U) { b->maos[us] |= tm; b->prom[us] |= tm; }
        else if (promo == W) { b->wk[us] |= tm; b->prom[us] |= tm; }
        else if (promo == F) { b->fk[us] |= tm; b->prom[us] |= tm; }
        else b->pawns[us] |= tm;
    } else if (b->maos[us] & fm) {
        b->maos[us] &= (uint16_t)~fm; b->maos[us] |= tm;
    } else {
        if (b->wk[us] & fm) { b->wk[us] &= (uint16_t)~fm; b->wk[us] |= tm; }
        if (b->fk[us] & fm) { b->fk[us] &= (uint16_t)~fm; b->fk[us] |= tm; }
    }
}

static uint16_t bst_targets(const BState *b, int us, int s) {
    uint16_t own = b->by[us], fm = 1u << s;
    if (b->pawns[us] & fm) {
        uint16_t t = BB_PCAP[us][s] & b->by[1 - us];
        int to = s + PUSH[us];
        if (to >= 0 && to < 16 && !((b->occ >> to) & 1)) t |= 1u << to;
        return t;
    }
    if (b->maos[us] & fm) {
        uint16_t t = 0;
        for (int i = 0; MAO_MOVES[s][i][0] != 0xff; i++)
            if (!((b->occ >> MAO_MOVES[s][i][0]) & 1) && !((own >> MAO_MOVES[s][i][1]) & 1))
                t |= 1u << MAO_MOVES[s][i][1];
        return t;
    }
    uint16_t wkb = b->wk[us] & fm, fkb = b->fk[us] & fm;
    if (wkb && fkb) return BB_KING[s] & (uint16_t)~own;
    if (wkb) return BB_ORTH[s] & (uint16_t)~own;
    return BB_DIAG[s] & (uint16_t)~own;
}

static uint64_t bst_perft(const BState *b, int us, int depth) {
    int them = 1 - us;
    uint16_t kingm = b->wk[us] & b->fk[us];
    int ks = __builtin_ctz(kingm);
    int in_chk = bst_attacked(b, ks, them);
    uint16_t promo_rank = (uint16_t)(0xFu << (PROMO_RANK[us] * 4));
    uint64_t total = 0;

    if (in_chk) {                        /* rare: test every child */
        uint16_t movers = b->by[us];
        while (movers) {
            int s = __builtin_ctz(movers); movers &= movers - 1;
            uint16_t tg = bst_targets(b, us, s);
            int is_p = (b->pawns[us] >> s) & 1;
            while (tg) {
                int to = __builtin_ctz(tg); tg &= tg - 1;
                int promo = is_p && ((promo_rank >> to) & 1);
                int myks = s == ks ? to : ks;
                if (depth == 1) {
                    BState c = *b; bst_move(&c, us, s, to, promo ? F : 0);
                    if (!bst_attacked(&c, myks, them)) total += promo ? 3 : 1;
                } else if (promo) {
                    for (int pc = F; pc <= W; pc++) {
                        BState c = *b; bst_move(&c, us, s, to, pc);
                        if (!bst_attacked(&c, myks, them)) total += bst_perft(&c, them, depth - 1);
                    }
                } else {
                    BState c = *b; bst_move(&c, us, s, to, 0);
                    if (!bst_attacked(&c, myks, them)) total += bst_perft(&c, them, depth - 1);
                }
            }
        }
        uint16_t empt = (uint16_t)~b->occ;
        for (int t = 0; t < 4; t++) {
            if (!b->hands[us][t]) continue;
            uint16_t e = t == P ? (uint16_t)(empt & ~BB_BACKRANKS) : empt;
            while (e) {
                int to = __builtin_ctz(e); e &= e - 1;
                BState c = *b;
                c.occ |= 1u << to; c.by[us] |= 1u << to;
                if (t == P) c.pawns[us] |= 1u << to;
                else if (t == U) c.maos[us] |= 1u << to;
                else if (t == W) c.wk[us] |= 1u << to;
                else c.fk[us] |= 1u << to;
                c.hands[us][t]--;
                if (!bst_attacked(&c, ks, them))
                    total += depth == 1 ? 1 : bst_perft(&c, them, depth - 1);
            }
        }
        return total;
    }

    /* not in check: only king moves and mao-leg vacations can be illegal */
    uint16_t risky = kingm;
    if (BB_MAOORIG[ks] & b->maos[them])
        for (int i = 0; MAO_ATT[ks][i][0] != 0xff; i++)
            if (((b->maos[them] >> MAO_ATT[ks][i][0]) & 1) && ((b->occ >> MAO_ATT[ks][i][1]) & 1))
                risky |= 1u << MAO_ATT[ks][i][1];

    uint16_t movers = b->by[us];
    while (movers) {
        int s = __builtin_ctz(movers); movers &= movers - 1;
        uint16_t tg = bst_targets(b, us, s);
        if (!tg) continue;
        int is_p = (b->pawns[us] >> s) & 1;
        int is_risky = (risky >> s) & 1;
        if (depth == 1 && !is_risky) {
            if (is_p) {
                int pr = __builtin_popcount(tg & promo_rank);
                total += (uint64_t)(__builtin_popcount(tg) - pr) + (uint64_t)pr * 3;
            } else total += (uint64_t)__builtin_popcount(tg);
            continue;
        }
        while (tg) {
            int to = __builtin_ctz(tg); tg &= tg - 1;
            int promo = is_p && ((promo_rank >> to) & 1);
            int myks = s == ks ? to : ks;
            if (depth == 1) {            /* risky: one test, promo counts x3 */
                BState c = *b; bst_move(&c, us, s, to, promo ? F : 0);
                if (!bst_attacked(&c, myks, them)) total += promo ? 3 : 1;
            } else if (promo) {
                for (int pc = F; pc <= W; pc++) {
                    BState c = *b; bst_move(&c, us, s, to, pc);
                    if (!is_risky || !bst_attacked(&c, myks, them))
                        total += bst_perft(&c, them, depth - 1);
                }
            } else {
                BState c = *b; bst_move(&c, us, s, to, 0);
                if (!is_risky || !bst_attacked(&c, myks, them))
                    total += bst_perft(&c, them, depth - 1);
            }
        }
    }

    uint16_t empt = (uint16_t)~b->occ;
    int hp = b->hands[us][P] != 0;
    int ho = (b->hands[us][F] != 0) + (b->hands[us][U] != 0) + (b->hands[us][W] != 0);
    if (hp | ho) {
        if (depth == 1) {
            total += (uint64_t)ho * __builtin_popcount(empt)
                   + (uint64_t)hp * __builtin_popcount((uint16_t)(empt & ~BB_BACKRANKS));
        } else {
            for (int t = 0; t < 4; t++) {
                if (!b->hands[us][t]) continue;
                uint16_t e = t == P ? (uint16_t)(empt & ~BB_BACKRANKS) : empt;
                while (e) {
                    int to = __builtin_ctz(e); e &= e - 1;
                    BState c = *b;
                    c.occ |= 1u << to; c.by[us] |= 1u << to;
                    if (t == P) c.pawns[us] |= 1u << to;
                    else if (t == U) c.maos[us] |= 1u << to;
                    else if (t == W) c.wk[us] |= 1u << to;
                    else c.fk[us] |= 1u << to;
                    c.hands[us][t]--;
                    total += bst_perft(&c, them, depth - 1);
                }
            }
        }
    }
    return total;
}

uint64_t th_perft_bitboard(THPos *p, int depth) {
    if (depth == 0) return 1;
    bb_init();
    BState b;
    bst_from(p, &b);
    return bst_perft(&b, p->stm, depth);
}

uint64_t th_perft(THPos *p, int depth) {
#if BITBOARD_PERFT
    return th_perft_bitboard(p, depth);
#else
    return th_perft_mailbox(p, depth);
#endif
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
    for (int i = 0; i <= DFPN_MAXPLY; i++) zob_dfrem[i] = rng64();
}

void th_init(void) {
    init_tables();
    th_seed(0x9E3779B97F4A7C15ULL);
}
