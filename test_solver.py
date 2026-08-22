"""Solver contract tests. Nothing in the perft suite touches the C search, so
these are the only tests that exercise th_solve/th_mate_hunt/th_root_moves.

Several of them need a COLD process. Both the transposition table and the
thread-local `history` table carry over between in-process searches, and a warm
one can hide the very defect being pinned: THB-01 reproduces from a cold start
and disappears if a shallower depth ran first in the same process. `_cold()`
runs a snippet in a fresh interpreter for exactly that reason.
"""
import subprocess
import sys
from pathlib import Path

import tinyhouse as T

DIR = Path(__file__).parent


def _cold(body: str) -> str:
    """Run `body` in a fresh interpreter with the engine imported."""
    src = "import engine_c as E, tinyhouse as T\n" + body
    r = subprocess.run([sys.executable, "-c", src], cwd=DIR, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def hunt(tfen: str, depth: int, color: int, tt_bits: int = 22) -> int:
    """One cold mate hunt. Returns the value from `color`'s perspective."""
    return int(_cold(f"""
E.lib.th_tt_init({tt_bits})
pos = E.to_c(T.Position.from_tfen({tfen!r}))
bm = E.ffi.new("uint16_t *")
print(E.lib.th_mate_hunt(pos, {depth}, {color}, bm))
"""))


# Black mates in exactly 13 plies here, so depths 11 and 12 must find nothing.
BUDGET_TFEN = "f1w1/2k1/K2p/W1UF[Up] b"


def test_mate_hunt_respects_its_ply_budget():
    """THB-01: a depth-N hunt may never report a win of distance > N.

    The TT cutoff block ran before the `depth <= 0` branch, and its
    `tv.depth >= depth` guard is trivially true once depth has run out
    (tv.depth is unsigned). A stored mate score was therefore handed back at a
    node with no budget left, and the ply re-basing dressed it up as a mate
    found within the horizon. Cold depth 12 returned 29985 -- "Black wins in
    15" out of a 12-ply budget: wrong verdict and wrong distance.
    """
    got = {d: hunt(BUDGET_TFEN, d, T.BLACK) for d in (11, 12, 13)}
    # Not a vacuous test: the position really is a forced Black win, at 13.
    assert got[13] == 29987, got
    assert got[11] == 0, got
    assert got[12] == 0, f"depth 12 claimed a mate in {30000 - got[12]}: {got}"


def test_warm_table_hunt_respects_its_ply_budget():
    """THB-01, the arm that survives the obvious fix.

    Refusing cutoffs only at horizon nodes (`ply > 0 && depth > 0`) leaves the
    hole open one ply up: a full-window search stores exact, sound mate entries,
    and a later shallow hunt reuses one at an interior node that has far less
    budget than the mate distance it carries. Populate at depth 10, then ask for
    a win within 4 plies, and the pre-fix engine answers "mate in 9". The
    shipped guard tests the distance against the remaining depth, so it refuses
    exactly these and nothing else.

    This is the resume path, not a contrived one: `solve_hunt.py` reloads a
    dumped table and can then be asked for a shallower depth.
    """
    import engine_c as E

    mate9 = "fuwk/3p/P1F1/KWU1[-] b"     # Black mates in exactly 9
    E.lib.th_tt_init(20)
    c = E.to_c(T.Position.from_tfen(mate9))
    bm, snd = E.ffi.new("uint16_t *"), E.ffi.new("int *")
    assert E.lib.th_solve(c, 10, bm, snd) == 29991      # populate

    for d in (2, 4, 6, 8):
        v = E.lib.th_mate_hunt(E.to_c(T.Position.from_tfen(mate9)), d, T.BLACK, bm)
        assert v == 0, f"warm depth {d} claimed a mate in {30000 - v}"
    assert E.lib.th_mate_hunt(E.to_c(T.Position.from_tfen(mate9)), 10, T.BLACK, bm) == 29991


def test_recorded_proofs_reproduce():
    """The three published forced wins, at their exact recorded distances.

    Cold process each, so this also pins that the distances do not depend on
    table or history carry-over. `solve_status.json` is the record these back.
    """
    assert hunt("fuwk/3p/P1F1/KWU1[-] b", 9, T.BLACK) == 29991     # mate in 9
    assert hunt("fuwk/3p/P1F1/KWU1[-] b", 8, T.BLACK) == 0         # ...and not in 8
    assert hunt("1uwk/1f1p/PW2/K1UF[-] w", 13, T.WHITE) == 29987   # mate in 13
    assert hunt("1uwk/Pf1p/4/KWUF[-] w", 13, T.WHITE) == 29987     # mate in 13
