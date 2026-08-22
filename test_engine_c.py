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


@pytest.mark.parametrize("root", [t for t, _ in PERFT_ORACLE])
def test_move_sets_match_on_random_walks(root):
    """TH-24: the walk started only from the start position, and random play
    from there reaches promotion and full hands vanishingly rarely -- exactly
    the states where Python and C are most likely to disagree. Parametrised
    over the oracle roots, which between them start with eight pieces in hand,
    a promotion one push away, and a mao check with a single blocking drop.
    """
    random.seed(7)
    for _ in range(20):
        pos = T.Position.from_tfen(root)
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


def test_the_loaded_library_was_built_from_this_source_and_these_flags():
    """THB-14: the rebuild trigger was `dylib.mtime < source.mtime`.

    A flags-only edit changed nothing it could see -- the dylib hash was
    measured unchanged across an -O2 -> -O0 change -- and mtime is the wrong
    signal in the other direction too, since `git checkout` of an OLDER
    tinyhouse.c also silently rebuilds backwards. The stamp is the identity of
    what was actually built, so this fails whenever the loaded library is stale.

    The cdef half of the item is a category error and is not guarded here: a
    ffi.cdef edit is Python-side and needs no rebuild by construction. What it
    does need is signature coverage, which is TH-22.
    """
    import hashlib

    expect = int.from_bytes(hashlib.sha1(
        engine_c._SRC.read_bytes() + " ".join(engine_c._CFLAGS).encode()).digest()[:8], "little")
    assert engine_c.lib.th_build_id() == expect
    assert engine_c._STAMP.read_text().strip() == str(expect)


# -- attacked() against an oracle written from RULES.md prose (TH-23) --------

def _spec_attacks(pos):
    """Does any piece of colour `by` attack `sq`? Derived from RULES.md in the
    OPPOSITE direction to the shipped code.

    tinyhouse.attacked() asks, for a target square, which neighbours could be
    holding an attacker -- it reads reverse tables. This walks the board, and
    for every piece asks where that piece attacks, straight from the prose:

      King  1 step any direction
      Ferz  1 step diagonally
      Wazir 1 step orthogonally
      Horse 1 step orthogonal then 1 step diagonally outward, blocked if the
            orthogonal step square is occupied, and it does not attack the
            blocking square itself
      Pawn  captures 1 step diagonally forward

    Shares no table and no loop with the engine, so agreement is evidence.
    """
    out = {0: set(), 1: set()}
    for s in range(16):
        pc = pos.board[s]
        if not pc:
            continue
        f, r = s % 4, s // 4
        t, c = T.ptype(pc), T.pcolor(pc)
        steps = []
        if t == T.K:
            steps = [(df, dr) for df in (-1, 0, 1) for dr in (-1, 0, 1) if (df, dr) != (0, 0)]
        elif t == T.F:
            steps = [(df, dr) for df in (-1, 1) for dr in (-1, 1)]
        elif t == T.W:
            steps = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        elif t == T.P:
            dr = 1 if c == T.WHITE else -1
            steps = [(-1, dr), (1, dr)]
        for df, dr in steps:
            nf, nr = f + df, r + dr
            if 0 <= nf < 4 and 0 <= nr < 4:
                out[c].add(nr * 4 + nf)
        if t == T.U:
            for of, orr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                bf, br = f + of, r + orr
                if not (0 <= bf < 4 and 0 <= br < 4):
                    continue
                if pos.board[br * 4 + bf]:          # orthogonal step square occupied
                    continue
                dests = (((bf + of, br + 1), (bf + of, br - 1)) if of
                         else ((bf + 1, br + orr), (bf - 1, br + orr)))
                for tf, tr in dests:
                    if 0 <= tf < 4 and 0 <= tr < 4:
                        out[c].add(tr * 4 + tf)
    return out


def test_attacked_matches_a_spec_oracle():
    """TH-23: coverage, not a suspected defect. attacked() is consumed by every
    legality decision in both engines and nothing checked it against the rules
    text -- only against itself, via perft.

    Scope, stated: this covers the ATTACK direction only. ORTH/DIAG/PCAPS are
    also consumed by pseudo_moves alongside KINGN and MAO_MOVES, and that
    direction is still verified by nothing but perft.
    """
    random.seed(11)
    compared = 0
    for root, _ in PERFT_ORACLE:
        for _ in range(30):
            pos = T.Position.from_tfen(root)
            for _ply in range(25):
                spec = _spec_attacks(pos)
                for sq in range(16):
                    for by in (T.WHITE, T.BLACK):
                        assert pos.attacked(sq, by) == (sq in spec[by]), \
                            f"{pos.tfen()} sq={T.sq_name(sq)} by={by}"
                        compared += 1
                moves = pos.legal_moves()
                if not moves:
                    break
                pos.make(random.choice(moves))
    assert compared > 50_000, compared
    print(f"\n  attacked() agreed with the spec oracle over {compared:,} comparisons")
