"""Exact count of syntactically legal Tinyhouse states (upper bound on reachable).

Counts: board placements of 2 kings (ordered, non-adjacent) + distribution of the
8 non-king units over board/hands, times 2 for side to move. Constraints encoded:
pawns only on ranks 2-3 (8 squares), promoted pieces only from the 2 pawn-origin
units, hands hold raw types. Not counted: side-not-to-move-in-check exclusion,
reachability. So this is an upper bound.
"""
from math import comb
from itertools import combinations_with_replacement

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
def placements(np_board, nother_board, mid_free, any_free):
    """Place np_board indistinct-per-class pawns and nother_board other pieces.
    Caller pre-multiplies per-class multiset factors; here classes are already
    distinct so it's ordered choice of squares: pawns from mid_free, others from
    remaining. Pawns of the two colors are distinct classes; handled by caller
    passing per-class counts. This helper handles only totals with same-domain."""
    raise NotImplementedError  # replaced by inline logic below

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
                    dup = 1  # same-class duplicates -> placements use comb not perm
                    for grp in (pu, fu, uu, wu):
                        if grp[0] == grp[1]:
                            dup *= 1  # multiset: identical units, one assignment
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
                    from collections import Counter
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
print(f"upper bound on states: {total:,}")
print(f"/4 symmetry          : {total // 4:,}")
