"""C engine parity: identical perft numbers and identical legal move sets."""
import random

import pytest

import engine_c
import tinyhouse as T
from test_tinyhouse import PERFT_ORACLE


@pytest.mark.parametrize("tfen,counts", PERFT_ORACLE)
def test_perft_c_matches_oracle(tfen, counts):
    assert [engine_c.perft(tfen, d) for d in range(1, len(counts) + 1)] == counts


def test_perft_c_deep_start():
    assert engine_c.perft("fuwk/3p/P3/KWUF[-] w", 6) == 139141
    assert engine_c.perft("fuwk/3p/P3/KWUF[-] w", 7) == 1355253


def test_move_sets_match_on_random_walks():
    random.seed(7)
    for _ in range(20):
        pos = T.Position.start()
        for _ply in range(60):
            py_moves = sorted(pos.legal_moves())
            c_moves = sorted(engine_c.legal_moves(pos))
            assert py_moves == c_moves, pos.tfen()
            assert engine_c.lib.th_result(engine_c.to_c(pos)) == (pos.result() or 0)
            if not py_moves:
                break
            pos.make(random.choice(py_moves))


def test_c_roundtrip():
    pos = T.Position.from_tfen("1uwk/P3/3p/K2F[UWf] w")
    assert engine_c.to_py(engine_c.to_c(pos)).tfen() == pos.tfen()


def test_to_c_rejects_an_unvalidated_position():
    """THB-05: to_c is the real Python->C trust boundary.

    Every rule used to live in from_tfen, which a hand-built Position bypasses.
    A kingless one reached th_solve and came back value=30000 snd=3 -- the
    code's own encoding of an exact, PROVEN game value -- computed off
    out-of-bounds reads, since king_sq returns -1 and attacked() then indexes
    ORTH[-1]. An over-full hand is the same class of hole: th_key indexes
    zob_hand[c][t][n] and that dimension is 3.
    """
    with pytest.raises(ValueError):
        engine_c.to_c(T.Position())                     # no kings at all

    lone = T.Position()
    lone.board[0] = T.piece(T.WHITE, T.K)
    with pytest.raises(ValueError):
        engine_c.to_c(lone)                             # no black king

    overfull = T.Position.from_tfen("3k/4/4/K3[-] w")
    overfull.hands[T.WHITE][T.P] = 9
    with pytest.raises(ValueError):
        engine_c.to_c(overfull)
