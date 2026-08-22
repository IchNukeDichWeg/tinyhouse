"""Tinyhouse engine tests.

PERFT_ORACLE provenance, stated exactly (TH-04), because the previous wording
claimed more than was done:

- depth 1 from the start is pinned move by move in `test_start_moves`, and
  depth 2 is decomposed per root move in `test_start_perft_divide` below, so
  the 33 is auditable by hand rather than asserted. No such enumeration
  artifact existed when the docstring first claimed one.
- the deeper oracle values were cross-checked by three from-spec
  implementations written from RULES.md alone. That check was real, but it was
  three models of one family working from one document, and **none of the three
  is in this repo**: what the tree holds is `tinyhouse.py` and `tinyhouse.c`,
  and `tinyhouse.c` declares itself a mirror of `tinyhouse.py`. Treat their
  agreement as a transcription check, not as independent derivation.
- `perft(6)` and `perft(7)` in `test_engine_c.py` have no from-spec provenance
  at all. They are config-drift signatures: they pin that the engine has not
  changed, not that it was ever right.

Every oracle number itself is believed correct; only the strength of the
evidence behind it is restated here.
"""
import random

import pytest

import tinyhouse as T
from tinyhouse import Position, move_str, str_move

# (tfen, [perft(1), perft(2), ...])
PERFT_ORACLE = [
    ("fuwk/3p/P3/KWUF[-] w", [6, 33, 241, 1855, 16021]),
    ("1k2/4/2K1/4[PFUWpfuw] w", [55, 2274, 71482]),
    ("1uwk/P3/3p/K2F[UWf] w", [27, 328, 5768, 50971]),
    ("3k/1U2/4/K3[f] b", [4, 18, 231, 1240]),
    ("k3/W1F1/1K2/4[p] b", [0, 0]),
]


@pytest.mark.parametrize("tfen,counts", PERFT_ORACLE)
def test_perft(tfen, counts):
    pos = Position.from_tfen(tfen)
    assert [pos.perft(d) for d in range(1, len(counts) + 1)] == counts


# Depth-2 perft decomposed per root move: 6 replies summing to 33. Small enough
# to check against RULES.md by hand, which is what "hand-verified" should mean.
START_DIVIDE = {"a1b2": 5, "a2a3": 6, "b1b2": 6, "c1b3": 3, "c1d3": 6, "d1c2": 7}


def test_start_perft_divide():
    pos = Position.start()
    got = {}
    for m in pos.legal_moves():
        pos.make(m)
        got[move_str(m)] = len(pos.legal_moves())
        pos.unmake()
    assert got == START_DIVIDE
    assert sum(got.values()) == 33 == pos.perft(2)


def test_start_moves():
    pos = Position.start()
    got = sorted(move_str(m) for m in pos.legal_moves())
    assert got == sorted(["a2a3", "b1b2", "c1b3", "c1d3", "d1c2", "a1b2"])


@pytest.mark.parametrize("tfen", [t for t, _ in PERFT_ORACLE])
def test_tfen_roundtrip(tfen):
    assert Position.from_tfen(tfen).tfen() == tfen


def test_make_unmake_random_walk():
    random.seed(42)
    pos = Position.start()
    for _ in range(300):
        key = pos.key()
        moves = pos.legal_moves()
        if not moves:
            break
        m = random.choice(moves)
        pos.make(m)
        pos.unmake()
        assert pos.key() == key
        pos.make(m)
        # conservation: per raw type, board-unpromoted + hands == 2;
        # pawn-origin: pawns anywhere + promoted-on-board == 2
        counts = {t: 0 for t in range(4)}
        for pc in pos.board:
            if pc and T.ptype(pc) != T.K:
                counts[T.P if T.ppromoted(pc) else T.ptype(pc)] += 1
        for h in pos.hands:
            for t in range(4):
                counts[t] += h[t]
        assert counts == {T.P: 2, T.F: 2, T.U: 2, T.W: 2}, pos.tfen()


def test_promoted_capture_reverts_to_pawn():
    pos = Position.from_tfen("3k/2F~1/4/K3[-] b")
    pos.make(str_move("d4c3"))
    assert pos.hands[T.BLACK] == [1, 0, 0, 0]  # a pawn, not a ferz
    assert pos.tfen() == "4/2k1/4/K3[p] w"
    pos.unmake()
    assert pos.tfen() == "3k/2F~1/4/K3[-] b"


def test_promotion_is_forced_and_marked():
    pos = Position.from_tfen("4/kP1p/4/2K1[-] w")
    strs = [move_str(m) for m in pos.legal_moves() if m and T.m_from(m) == T.name_sq("b3")]
    assert sorted(s for s in strs if s.startswith("b3b4")) == ["b3b4=F", "b3b4=U", "b3b4=W"]
    assert "b3b4" not in strs  # no promotion-less push
    pos.make(str_move("b3b4=U"))
    assert pos.tfen() == "1U~2/k2p/4/2K1[-] b"


def test_mao_block_by_drop():
    # White U b3 checks the d4 king through the empty c3 square; the only legal
    # drop is on the blocking square.
    pos = Position.from_tfen("3k/1U2/4/K3[f] b")
    got = sorted(move_str(m) for m in pos.legal_moves())
    assert got == ["F@c3", "d4c3", "d4c4", "d4d3"]


def test_mao_blocked_cannot_move_or_check():
    # blocker on c3 shuts the b3 horse down toward d4/d2 (wazir on c3 does not
    # itself attack d4)
    pos = Position.from_tfen("3k/1UW1/4/K3[-] b")
    assert not pos.in_check(T.BLACK)


def test_checkmate_even_with_hand():
    pos = Position.from_tfen("k3/W1F1/1K2/4[p] b")
    assert pos.result() == -1  # adjacent wazir check: no block square, mate


def test_stalemate_is_win_for_stalemated():
    pos = Position.from_tfen("k3/2K1/W3/4[-] b")
    assert not pos.in_check(T.BLACK)
    assert pos.result() == 1  # black stalemated -> black wins


def test_no_pawn_drops_on_back_ranks():
    pos = Position.from_tfen("1k2/4/2K1/4[PFUWpfuw] w")
    drops = [move_str(m) for m in pos.legal_moves() if T.m_is_drop(m)]
    assert not any(s.startswith("P@") and s[3] in "14" for s in drops)
    assert any(s.startswith("P@") and s[3] in "23" for s in drops)
    assert any(s == "F@a1" for s in drops)  # non-pawns may drop on back ranks


def test_double_step_toggle(monkeypatch):
    pos = Position.from_tfen("3k/4/P3/K3[-] w")
    assert "a2a4=W" not in [move_str(m) for m in pos.legal_moves()]
    monkeypatch.setattr(T, "DOUBLE_STEP", True)
    strs = [move_str(m) for m in pos.legal_moves()]
    assert {"a2a3", "a2a4=F", "a2a4=U", "a2a4=W"} <= set(strs)


def test_drop_always_legal_when_not_in_check():
    # not in check + non-empty hand => never stalemate
    pos = Position.from_tfen("k3/2K1/W3/4[p] b")
    assert pos.result() is None
    assert all(T.m_is_drop(m) for m in pos.legal_moves())


# -- TFEN is a trust boundary (server.py feeds it raw HTTP input) ------------

@pytest.mark.parametrize("bad", [
    "fuwk/3p/P3/KWUF[-] W",          # capital W is not a side-to-move token
    "fuwk/3p/P3/KWUF[-] w 0 1",      # FEN-style counters must not parse as black
    "fuwk/3p/P3/KWUF[-]",            # missing side to move
    "fuwk/3p/P3/KWUF[-] x",          # garbage side to move
    "fuwk/3p/KWUF[-] w",             # 3 ranks
    "fuwk/3p/P3/KWUFF[-] w",         # rank overflows the board
    "fuwk/3p/P3/KWUF[-] w extra]",   # two hand sections
    "fuwk/3p/P3/KWUF[Z] w",          # bad hand piece
    "fuwk/3p/P3/KWUF[K] w",          # kings are never in hand
    "fuwk/3p/P3/KWUZ[-] w",          # bad board character
    "fuwk/3p/P3/KWUF[FF] w",         # 3 ferzes in the game
    "3k/4/4/4[-] w",                 # no white king
    "k3/K3/4/4[-] w",                # side not to move is in check
    "KK~2/4/4/3k[-] w",              # promoted king: invisible to both count guards
    "3k/2P~1/4/K3[-] b",             # promoted pawn: promotion is to F/U/W only
    "P3/4/4/K2k[-] w",               # white pawn on its own promotion rank
    "3k/4/4/K2p[-] b",               # black pawn on its own promotion rank
    "3p/4/4/K2k[-] b",               # black pawn on rank 4, unreachable
    "3k/4/4/P2K[-] w",               # white pawn on rank 1, unreachable
])
def test_from_tfen_rejects_malformed(bad):
    with pytest.raises(ValueError):
        Position.from_tfen(bad)


def test_from_tfen_accepts_black_to_move():
    assert Position.from_tfen("fuwk/3p/P3/KWUF[-] b").stm == T.BLACK


@pytest.mark.parametrize("bad", [
    "K@a1",        # kings are never in hand; drop type 4 decrements hands[us][4]
    "a1b2=K",      # M_PROMO masks with & 3, so =K silently became a plain a1b2
    "a1b2=P",      # ...and =P likewise, dropping a forced promotion
    "Z@a1",        # not a piece letter
    "a9b2",        # not a square
])
def test_str_move_rejects_unrepresentable_moves(bad):
    """THB-06: str_move produced moves no generator can emit.

    `K@a1` yields drop type 4; the C make() does hands[us][4]-- on the same
    alias THB-04 found, so a hand count goes negative and th_key then reads
    zob_hand[...][-1], poisoning every TT key derived from it. The corruption
    survives a tfen() round trip because "P" * -1 is "".
    """
    with pytest.raises(ValueError):
        str_move(bad)
