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


def test_king_capture_does_not_write_past_the_hand_array():
    """THB-04: make()/unmake() indexed hands[us][TYPE(cap)] with TYPE(K) == 4,
    one past `int8_t hands[2][4]`.

    The struct is {board[16], hands[2][4], stm} with no padding, so
    &hands[1][4] is &stm and the aliasing is deterministic rather than
    undefined-in-practice. Being an intra-object overwrite, ASan tracks the
    object boundary and stays silent. unmake restores stm and *then* decrements
    the alias, so the corruption is what survives the call: th_moves alone
    returned with the caller's stm flipped from 1 to 0.

    THPos is built directly here on purpose. This is about the C library not
    depending on a Python-side invariant for memory consistency, and to_c now
    refuses to pass it an illegal position at all.
    """
    c = engine_c.ffi.new("THPos *")
    c.board[0] = 5       # white king a1
    c.board[4] = 20      # black wazir a2, attacking it
    c.board[15] = 21     # black king d4
    c.stm = 1            # black to move and able to capture the white king
    engine_c.lib.th_moves(c, engine_c.ffi.NULL)
    assert c.stm == 1
    assert [c.hands[0][t] for t in range(4)] == [0, 0, 0, 0]
    assert [c.hands[1][t] for t in range(4)] == [0, 0, 0, 0]

    # The other direction: hands[0][4] aliases hands[1][0], so White capturing
    # a black king fabricated a black PAWN in hand. Perft does not catch this
    # one -- the kingless side's king_sq returns -1 and attacked() reads
    # ORTH[-1], which reports "attacked" and filters every phantom drop back
    # out again. Two defects cancelling, so the hand array is the oracle.
    w = engine_c.ffi.new("THPos *")
    w.board[0] = 4       # white wazir a1
    w.board[1] = 21      # black king b1, en prise
    w.board[15] = 5      # white king d4
    w.stm = 0
    engine_c.lib.th_make(w, T.mv(0, 1))
    assert [w.hands[1][t] for t in range(4)] == [0, 0, 0, 0]


def test_importing_the_c_engine_refuses_a_double_step_ruleset():
    """THB-15: DOUBLE_STEP has no C counterpart, and C is what searches.

    The suite already goes red on a flip, since the constant is module level --
    the backlog's "no test can catch it" is false. What no test covered is that
    server.py drives both engines in one process: position_info enumerates the
    GUI's legal moves from the Python generator while analyze evaluates with C,
    so the GUI would offer a2a4=W and hand back an evaluation from an engine
    with no such move.
    """
    import subprocess
    import sys
    from pathlib import Path

    r = subprocess.run(
        [sys.executable, "-c", "import tinyhouse as T; T.DOUBLE_STEP = True; import engine_c"],
        cwd=Path(__file__).parent, capture_output=True, text=True)
    assert r.returncode != 0
    assert "DOUBLE_STEP" in r.stderr and "36 vs 33" in r.stderr
