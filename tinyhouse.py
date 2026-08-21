"""Tinyhouse rules engine. Rules: see RULES.md.

Board: 16 ints, square = 4*rank + file, a1=0, d1=3, a4=12, d4=15.
Piece: 0 = empty, else (type+1) | promoted<<3 | color<<4.
Types: P=0, F=1, U=2, W=3, K=4.  Colors: white=0, black=1.
Move (int): to | from<<4 | drop<<8 | promo<<9, where for drops the from
field holds the dropped piece type and promo holds 1..3 (F/U/W) else 0.
"""

# Double-step for pawns on their relative 2nd rank. RULES.md: inferred absent
# on chess.com (PawnBaseRank defaults outside the embedded 4x4); toggle kept
# to quantify the alternative ruleset. En passant is dead either way.
DOUBLE_STEP = False

P, F, U, W, K = range(5)
WHITE, BLACK = 0, 1
TYPE_CHARS = "PFUWK"

def piece(color: int, ptype: int, promoted: bool = False) -> int:
    return (ptype + 1) | (promoted << 3) | (color << 4)

def ptype(pc: int) -> int: return (pc & 7) - 1
def pcolor(pc: int) -> int: return pc >> 4
def ppromoted(pc: int) -> bool: return bool(pc & 8)

# move helpers
def mv(frm: int, to: int, promo: int = 0) -> int: return to | frm << 4 | promo << 9
def mv_drop(dtype: int, to: int) -> int: return to | dtype << 4 | 1 << 8
def m_to(m: int) -> int: return m & 15
def m_from(m: int) -> int: return m >> 4 & 15
def m_is_drop(m: int) -> bool: return bool(m & 256)
def m_promo(m: int) -> int: return m >> 9 & 3

# precomputed neighbor tables ------------------------------------------------
def _sq(f, r): return 4 * r + f
def _on(f, r): return 0 <= f < 4 and 0 <= r < 4

ORTH = [[] for _ in range(16)]
DIAG = [[] for _ in range(16)]
KING = [[] for _ in range(16)]
# MAO_MOVES[sq] = [(blocker, dest), ...]; MAO_ATT[sq] = [(attacker_origin, blocker), ...]
MAO_MOVES = [[] for _ in range(16)]
MAO_ATT = [[] for _ in range(16)]
for f in range(4):
    for r in range(4):
        s = _sq(f, r)
        for df, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if _on(f + df, r + dr):
                ORTH[s].append(_sq(f + df, r + dr))
        for df, dr in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            if _on(f + df, r + dr):
                DIAG[s].append(_sq(f + df, r + dr))
        KING[s] = ORTH[s] + DIAG[s]
        for of, orr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            bf, br = f + of, r + orr
            if not _on(bf, br):
                continue
            b = _sq(bf, br)
            if of:  # horizontal step, diagonal continues horizontally +-1 rank
                dests = ((bf + of, br + 1), (bf + of, br - 1))
            else:   # vertical step
                dests = ((bf + 1, br + orr), (bf - 1, br + orr))
            for tf, tr in dests:
                if _on(tf, tr):
                    t = _sq(tf, tr)
                    MAO_MOVES[s].append((b, t))
                    MAO_ATT[t].append((s, b))

PAWN_PUSH = (4, -4)          # by color
PAWN_CAPS = ([], [])         # PAWN_CAPS[color][sq] = capture dests
for color in (WHITE, BLACK):
    caps = []
    dr = 1 if color == WHITE else -1
    for r in range(4):
        for f in range(4):
            row = []
            for df in (-1, 1):
                if _on(f + df, r + dr):
                    row.append(_sq(f + df, r + dr))
            caps.append(row)
    PAWN_CAPS[color].extend(caps)
PROMO_RANK = (3, 0)          # last rank by color
START_RANK = (1, 2)          # relative 2nd rank by color


class Position:
    __slots__ = ("board", "hands", "stm", "_undo")

    def __init__(self):
        self.board = [0] * 16
        self.hands = [[0, 0, 0, 0], [0, 0, 0, 0]]
        self.stm = WHITE
        self._undo = []

    @staticmethod
    def start() -> "Position":
        return Position.from_tfen("fuwk/3p/P3/KWUF[-] w")

    # -- serialization (TFEN): ranks 4->1, '~' suffix = promoted, hands in
    # [..] with uppercase = white, '-' if both empty, then side to move.
    @staticmethod
    def from_tfen(tfen: str) -> "Position":
        pos = Position()
        boardpart, rest = tfen.split("[")
        handpart, stmpart = rest.split("]")
        pos.stm = WHITE if stmpart.strip() == "w" else BLACK
        ranks = boardpart.strip().split("/")
        assert len(ranks) == 4, tfen
        for i, rank in enumerate(ranks):
            r, f = 3 - i, 0
            j = 0
            while j < len(rank):
                c = rank[j]
                if c.isdigit():
                    f += int(c)
                else:
                    color = WHITE if c.isupper() else BLACK
                    t = TYPE_CHARS.index(c.upper())
                    promoted = j + 1 < len(rank) and rank[j + 1] == "~"
                    if promoted:
                        j += 1
                    pos.board[_sq(f, r)] = piece(color, t, promoted)
                    f += 1
                j += 1
            assert f == 4, tfen
        if handpart != "-":
            for c in handpart:
                color = WHITE if c.isupper() else BLACK
                pos.hands[color][TYPE_CHARS.index(c.upper())] += 1
        return pos

    def tfen(self) -> str:
        out = []
        for r in range(3, -1, -1):
            row, run = "", 0
            for f in range(4):
                pc = self.board[_sq(f, r)]
                if not pc:
                    run += 1
                    continue
                if run:
                    row += str(run)
                    run = 0
                c = TYPE_CHARS[ptype(pc)]
                row += (c if pcolor(pc) == WHITE else c.lower()) + ("~" if ppromoted(pc) else "")
            if run:
                row += str(run)
            out.append(row)
        hand = "".join(TYPE_CHARS[t] * self.hands[WHITE][t] for t in range(4))
        hand += "".join(TYPE_CHARS[t].lower() * self.hands[BLACK][t] for t in range(4))
        return "/".join(out) + "[" + (hand or "-") + "] " + ("w" if self.stm == WHITE else "b")

    def key(self):
        return (tuple(self.board), tuple(self.hands[0]), tuple(self.hands[1]), self.stm)

    # -- attacks ------------------------------------------------------------
    def attacked(self, sq: int, by: int) -> bool:
        b = self.board
        for s in ORTH[sq]:
            pc = b[s]
            if pc and pcolor(pc) == by and ptype(pc) in (W, K):
                return True
        for s in DIAG[sq]:
            pc = b[s]
            if pc and pcolor(pc) == by and ptype(pc) in (F, K):
                return True
        # pawns: a pawn on s attacks sq if sq is in PAWN_CAPS[by][s];
        # equivalently s is a *reverse* capture square of sq
        for s in PAWN_CAPS[1 - by][sq]:
            pc = b[s]
            if pc and pcolor(pc) == by and ptype(pc) == P:
                return True
        for origin, blocker in MAO_ATT[sq]:
            pc = b[origin]
            if pc and pcolor(pc) == by and ptype(pc) == U and not b[blocker]:
                return True
        return False

    def king_sq(self, color: int) -> int:
        target = piece(color, K)
        return self.board.index(target)

    def in_check(self, color: int) -> bool:
        return self.attacked(self.king_sq(color), 1 - color)

    # -- movegen ------------------------------------------------------------
    def pseudo_moves(self):
        b, us = self.board, self.stm
        moves = []
        for s in range(16):
            pc = b[s]
            if not pc or pcolor(pc) != us:
                continue
            t = ptype(pc)
            if t == P:
                to = s + PAWN_PUSH[us]
                if 0 <= to < 16 and not b[to]:
                    if to >> 2 == PROMO_RANK[us]:
                        moves += [mv(s, to, F), mv(s, to, U), mv(s, to, W)]
                    else:
                        moves.append(mv(s, to))
                        if DOUBLE_STEP and s >> 2 == START_RANK[us]:
                            to2 = to + PAWN_PUSH[us]
                            if 0 <= to2 < 16 and not b[to2]:
                                # lands on promotion rank by construction
                                moves += [mv(s, to2, F), mv(s, to2, U), mv(s, to2, W)]
                for to in PAWN_CAPS[us][s]:
                    if b[to] and pcolor(b[to]) != us:
                        if to >> 2 == PROMO_RANK[us]:
                            moves += [mv(s, to, F), mv(s, to, U), mv(s, to, W)]
                        else:
                            moves.append(mv(s, to))
            elif t == F:
                for to in DIAG[s]:
                    if not b[to] or pcolor(b[to]) != us:
                        moves.append(mv(s, to))
            elif t == W:
                for to in ORTH[s]:
                    if not b[to] or pcolor(b[to]) != us:
                        moves.append(mv(s, to))
            elif t == K:
                for to in KING[s]:
                    if not b[to] or pcolor(b[to]) != us:
                        moves.append(mv(s, to))
            else:  # U
                for blocker, to in MAO_MOVES[s]:
                    if not b[blocker] and (not b[to] or pcolor(b[to]) != us):
                        moves.append(mv(s, to))
        hand = self.hands[us]
        empties = [s for s in range(16) if not b[s]]
        for t in range(4):
            if hand[t]:
                for s in empties:
                    if t == P and s >> 2 in (0, 3):
                        continue
                    moves.append(mv_drop(t, s))
        return moves

    def make(self, m: int) -> None:
        b, us = self.board, self.stm
        if m_is_drop(m):
            t, to = m_from(m), m_to(m)
            self._undo.append((m, 0))
            self.hands[us][t] -= 1
            b[to] = piece(us, t)
        else:
            frm, to = m_from(m), m_to(m)
            captured = b[to]
            self._undo.append((m, captured))
            if captured:
                self.hands[us][P if ppromoted(captured) else ptype(captured)] += 1
            pc = b[frm]
            if m_promo(m):
                pc = piece(us, m_promo(m), True)
            b[to], b[frm] = pc, 0
        self.stm = 1 - us

    def unmake(self) -> None:
        m, captured = self._undo.pop()
        us = self.stm = 1 - self.stm
        b = self.board
        if m_is_drop(m):
            t, to = m_from(m), m_to(m)
            b[to] = 0
            self.hands[us][t] += 1
        else:
            frm, to = m_from(m), m_to(m)
            pc = b[to]
            if m_promo(m):
                pc = piece(us, P)
            b[frm], b[to] = pc, captured
            if captured:
                self.hands[us][P if ppromoted(captured) else ptype(captured)] -= 1

    def legal_moves(self):
        out = []
        for m in self.pseudo_moves():
            self.make(m)
            if not self.in_check(1 - self.stm):
                out.append(m)
            self.unmake()
        return out

    def result(self):
        """None if not terminal, else +1 side to move wins (stalemate),
        -1 side to move loses (checkmate). Repetition handled by caller."""
        if self.legal_moves():
            return None
        return -1 if self.in_check(self.stm) else 1

    def perft(self, depth: int) -> int:
        if depth == 0:
            return 1
        n = 0
        for m in self.legal_moves():
            if depth == 1:
                n += 1
            else:
                self.make(m)
                n += self.perft(depth - 1)
                self.unmake()
        return n


# -- move <-> string ---------------------------------------------------------
def sq_name(s: int) -> str: return "abcd"[s & 3] + "1234"[s >> 2]
def name_sq(n: str) -> int: return _sq("abcd".index(n[0]), "1234".index(n[1]))

def move_str(m: int) -> str:
    if m_is_drop(m):
        return TYPE_CHARS[m_from(m)] + "@" + sq_name(m_to(m))
    s = sq_name(m_from(m)) + sq_name(m_to(m))
    if m_promo(m):
        s += "=" + TYPE_CHARS[m_promo(m)]
    return s

def str_move(s: str) -> int:
    if "@" in s:
        return mv_drop(TYPE_CHARS.index(s[0]), name_sq(s.split("@")[1]))
    promo = 0
    if "=" in s:
        s, p = s.split("=")
        promo = TYPE_CHARS.index(p)
    return mv(name_sq(s[:2]), name_sq(s[2:4]), promo)


if __name__ == "__main__":
    import sys
    pos = Position.from_tfen(sys.argv[2]) if len(sys.argv) > 2 else Position.start()
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    assert pos.tfen() == (sys.argv[2] if len(sys.argv) > 2 else "fuwk/3p/P3/KWUF[-] w")
    for d in range(1, depth + 1):
        print(d, pos.perft(d))
