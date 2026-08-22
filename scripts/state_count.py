"""Exact count of syntactically legal Tinyhouse states (upper bound on reachable).

Counts: board placements of 2 kings (ordered, non-adjacent) + distribution of the
8 non-king units over board/hands, times 2 for side to move. Constraints encoded:
pawns only on ranks 2-3 (8 squares), promoted pieces only from the 2 pawn-origin
units, hands hold raw types. Not counted: side-not-to-move-in-check exclusion,
reachability. So this is an upper bound.
"""
from collections import Counter
from itertools import combinations_with_replacement, product
from math import comb

SQ = [(f, r) for r in range(4) for f in range(4)]
MID = {(f, r) for (f, r) in SQ if r in (1, 2)}  # ranks 2-3

def adjacent(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1

# ordered king pairs, non-adjacent, grouped by how many mid squares they occupy
king_pairs = {}  # m -> count
for a in SQ:
    for b in SQ:
        if a != b and not adjacent(a, b):
            m = (a in MID) + (b in MID)
            king_pairs[m] = king_pairs.get(m, 0) + 1

# P-origin unit classes: 0 wp,1 bp (board pawns, mid only), 2-7 promoted board
# pieces (wF* wU* wW* bF* bU* bW*, any square), 8 white hand, 9 black hand.
# F/U/W-origin unit classes: 0 white board, 1 black board, 2 white hand, 3 black hand.
total = 0
P_CLASSES = list(range(10))
FUW_CLASSES = list(range(4))
for m, kp in king_pairs.items():
    mid_free0 = 8 - m
    free0 = 14
    for pu in combinations_with_replacement(P_CLASSES, 2):
        for fu in combinations_with_replacement(FUW_CLASSES, 2):
            for uu in combinations_with_replacement(FUW_CLASSES, 2):
                for wu in combinations_with_replacement(FUW_CLASSES, 2):
                    # count board pieces
                    pawns = {0: 0, 1: 0}
                    others = 0  # promoted + raw FUW on board (any square)
                    for c in pu:
                        if c in (0, 1):
                            pawns[c] += 1
                        elif c < 8:
                            others += 1
                    for grp in (fu, uu, wu):
                        for c in grp:
                            if c < 2:
                                others += 1
                    npw, npb = pawns[0], pawns[1]
                    # place pawns: white pawns choose from mid_free, then black
                    # pawns from what's left of mid; identical-class pairs are
                    # indistinct -> combinations
                    ways = 1
                    mid_free = mid_free0
                    for cnt in (npw, npb):
                        ways *= comb(mid_free, cnt)
                        mid_free -= cnt
                    # other board pieces: distinct classes except identical pairs
                    free = free0 - npw - npb
                    # group same-class board pieces to use comb
                    boardc = Counter()
                    for c in pu:
                        if 2 <= c < 8:
                            boardc[('p', c)] += 1
                    for name, grp in (('f', fu), ('u', uu), ('w', wu)):
                        for c in grp:
                            if c < 2:
                                boardc[(name, c)] += 1
                    for cnt in boardc.values():
                        ways *= comb(free, cnt)
                        free -= cnt
                    total += kp * ways
total *= 2  # side to move


# -- cross-check (TH-33) ----------------------------------------------------
# The headline figure cannot be enumerated -- that is the whole point of it --
# so what is checked is the METHOD, on a sub-problem small enough to count both
# ways: two kings plus the two W units and nothing else. The analytic side uses
# exactly the technique the full count uses (class multisets placed with comb);
# the brute-force side enumerates states one at a time and shares no line of
# code with it. Agreement validates the technique, not the arithmetic of the
# larger loops -- say so rather than implying more.
def sub_analytic():
    t = 0
    for m, kp in king_pairs.items():
        for grp in combinations_with_replacement(range(4), 2):   # 0 wb 1 bb 2 wh 3 bh
            free, ways = 14, 1
            counts = Counter(c for c in grp if c < 2)
            for cnt in counts.values():
                ways *= comb(free, cnt)
                free -= cnt
            t += kp * ways
    return t * 2


def sub_brute():
    """Enumerate the same states directly: place both kings, then distribute the
    two W units over (white board, black board, white hand, black hand)."""
    seen = set()
    for wk in range(16):
        for bk in range(16):
            a, b = (wk % 4, wk // 4), (bk % 4, bk // 4)
            if wk == bk or adjacent(a, b):
                continue
            free = [s for s in range(16) if s not in (wk, bk)]
            for placement in product(["wb", "bb", "wh", "bh"], repeat=2):
                boards = [i for i, p in enumerate(placement) if p.endswith("b")]
                for squares in product(free, repeat=len(boards)):
                    if len(set(squares)) != len(squares):
                        continue
                    board = {wk: "K", bk: "k"}
                    for i, sq in zip(boards, squares):
                        board[sq] = "W" if placement[i] == "wb" else "w"
                    hand = (sum(1 for i, p in enumerate(placement) if p == "wh"),
                            sum(1 for i, p in enumerate(placement) if p == "bh"))
                    for stm in (0, 1):
                        seen.add((tuple(sorted(board.items())), hand, stm))
    return len(seen)


# The symmetry group of order 4 (identity, file mirror, sigma, and their
# composition) acts FREELY here, so total/4 is exact rather than a lower bound:
# the file mirror fixes no square (a<->d, b<->c, no central file), so the white
# king can never map to itself; and sigma maps white pieces to black ones, so no
# state is fixed by it either. No Burnside correction is needed or correct.
if __name__ == "__main__":
    import sys

    if "--verify" in sys.argv:
        a, b = sub_analytic(), sub_brute()
        print(f"sub-problem (2 kings + 2 W units): analytic {a:,}  brute force {b:,}  "
              f"{'AGREE' if a == b else 'DISAGREE'}")
        sys.exit(0 if a == b else 1)
    print(f"upper bound on states: {total:,}")
    print(f"/4 symmetry          : {total // 4:,}")
