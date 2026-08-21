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

void th_init(void) { init_tables(); }
