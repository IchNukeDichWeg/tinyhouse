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
        if (cap) p->hands[us][PROMOTED(cap) ? P : TYPE(cap)]++;
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
        if (u->captured) p->hands[us][PROMOTED(u->captured) ? P : TYPE(u->captured)]--;
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
 * node are path-dependent and are never stored in the TT (rep-safety; this
 * is what keeps the graph-history interaction problem out). Check moves
 * extend by one ply, so "depth" bounds quiet length, not total length.
 */
#include <stdlib.h>
#include <stdio.h>

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

typedef struct { uint64_t key; int16_t value; uint16_t move; uint8_t depth; uint8_t flag; uint8_t sound; } TTEntry;
enum { TT_EMPTY, TT_EXACT, TT_LOWER, TT_UPPER };
#define SND_LB 1
#define SND_UB 2
static TTEntry *tt = 0;
static uint64_t tt_mask = 0;
static uint64_t path[MAXPLY];
static uint64_t nodes = 0;
static int16_t history[2][2048];
static uint16_t killers[MAXPLY][2];

void th_tt_init(int log2_entries) {
    if (tt) free(tt);
    uint64_t n = 1ULL << log2_entries;
    tt = calloc(n, sizeof(TTEntry));
    tt_mask = n - 1;
}

typedef struct { int rep_min; uint8_t snd; } SInfo;

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
    return history[(int)p->stm][m & 2047];
}

static int search(THPos *p, int depth, int ply, int alpha, int beta, SInfo *si) {
    nodes++;
    si->rep_min = MAXPLY;
    si->snd = 0;

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
    TTEntry *e = tt ? &tt[key & tt_mask] : 0;
    if (e && e->key == key && e->flag != TT_EMPTY) {
        ttm = e->move;
        int v = e->value;
        if (v > MATE_BOUND) v -= ply;
        else if (v < -MATE_BOUND) v += ply;
        int sound = e->sound;
        int usable = e->depth >= depth || sound;
        if (usable && ply > 0) {
            if (e->flag == TT_EXACT && (e->depth >= depth || sound == (SND_LB | SND_UB))) {
                si->snd = sound; return v;
            }
            if (e->flag == TT_LOWER && v >= beta && (e->depth >= depth || (sound & SND_LB))) {
                si->snd = sound & SND_LB; return v;
            }
            if (e->flag == TT_UPPER && v <= alpha && (e->depth >= depth || (sound & SND_UB))) {
                si->snd = sound & SND_UB; return v;
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
        int ext = th_in_check(p, p->stm) ? 1 : 0;   /* check extension */
        SInfo ci;
        int v = -search(p, depth - 1 + ext, ply + 1, -beta, -alpha, &ci);
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

    if (e && my_rep >= ply) {
        int flag = best <= alpha0 ? TT_UPPER : cutoff ? TT_LOWER : TT_EXACT;
        uint8_t ssnd = flag == TT_EXACT ? snd :
                       flag == TT_LOWER ? (snd & SND_LB) : (snd & SND_UB);
        int proven = (ssnd == (SND_LB | SND_UB) && flag == TT_EXACT) ||
                     best > MATE_BOUND || best < -MATE_BOUND;
        int old_proven = e->sound == (SND_LB | SND_UB) && e->flag == TT_EXACT;
        if (e->flag == TT_EMPTY || proven || (!old_proven && depth >= e->depth)) {
            int sv = best;
            if (sv > MATE_BOUND) sv += ply;
            else if (sv < -MATE_BOUND) sv -= ply;
            e->key = key; e->value = sv; e->move = bestm;
            e->depth = depth < 0 ? 0 : depth; e->flag = flag; e->sound = ssnd;
        }
    }
    return best;
}

uint64_t th_nodes(void) { return nodes; }

/* Search at given depth, full window. Returns value; *snd gets soundness
 * flags (bit0: value is a proven lower bound, bit1: proven upper bound;
 * both = exact game value). |v| > 29000 means forced win/loss in MATE-|v|
 * plies and is proven whenever the corresponding bound flag is set. */
int th_solve(THPos *p, int depth, uint16_t *bestmove, int *snd) {
    SInfo si;
    memset(killers, 0, sizeof killers);
    int v = search(p, depth, 0, -MATE, MATE, &si);
    if (snd) *snd = si.snd;
    if (bestmove && tt) {
        TTEntry *e = &tt[th_key(p) & tt_mask];
        *bestmove = (e->key == th_key(p)) ? e->move : 0;
    }
    return v;
}

int th_search(THPos *p, int depth, uint16_t *bestmove) {
    return th_solve(p, depth, bestmove, 0);
}

/* Null-window mate hunt: proves/disproves "the given color forces a win
 * within `depth` quiet plies (checks extend)". Returns the mate value if
 * proven (>MATE_BOUND from that color's perspective) else the fail value. */
int th_mate_hunt(THPos *p, int depth, int color, uint16_t *bestmove) {
    SInfo si;
    memset(killers, 0, sizeof killers);
    int v;
    if (p->stm == color)
        v = search(p, depth, 0, MATE_BOUND, MATE, &si);
    else
        v = -search(p, depth, 0, -MATE, -MATE_BOUND, &si);
    if (bestmove && tt) {
        TTEntry *e = &tt[th_key(p) & tt_mask];
        *bestmove = (e->key == th_key(p)) ? e->move : 0;
    }
    return v; /* from `color`'s perspective */
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
    return n;
}

void th_init(void) {
    init_tables();
    for (int s = 0; s < 16; s++) for (int i = 0; i < 32; i++) zob_piece[s][i] = rng64();
    for (int c = 0; c < 2; c++) for (int t = 0; t < 4; t++)
        for (int i = 0; i < 3; i++) zob_hand[c][t][i] = rng64();
    zob_stm = rng64();
}
