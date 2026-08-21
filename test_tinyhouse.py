"""Tinyhouse engine tests. Perft oracle: values hand-verified at depth 1-2 from
the start position (all 33 nodes enumerated manually) and cross-checked by three
independent implementations written from RULES.md alone."""
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
