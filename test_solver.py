"""Solver contract tests. Nothing in the perft suite touches the C search, so
these are the only tests that exercise th_solve/th_mate_hunt/th_root_moves.

Several of them need a COLD process. Both the transposition table and the
thread-local `history` table carry over between in-process searches, and a warm
one can hide the very defect being pinned: THB-01 reproduces from a cold start
and disappears if a shallower depth ran first in the same process. `_cold()`
runs a snippet in a fresh interpreter for exactly that reason.
"""
import struct
import subprocess
import sys
from pathlib import Path

import pytest

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


# -- transposition table persistence ----------------------------------------

DEFAULT_SEED = 0x9E3779B97F4A7C15


@pytest.fixture
def tt():
    """A 2^12 table with a few real entries in it, default Zobrist seed.

    Restores the seed afterwards: reseeding rebuilds the Zobrist tables for the
    whole process, so a test that forgets silently changes every key for every
    later test.
    """
    import engine_c as E

    E.lib.th_seed(DEFAULT_SEED)
    E.lib.th_tt_init(12)
    bm, snd = E.ffi.new("uint16_t *"), E.ffi.new("int *")
    E.lib.th_solve(E.to_c(T.Position.start()), 6, bm, snd)
    yield E
    E.lib.th_seed(DEFAULT_SEED)


def test_tt_save_load_round_trip(tt, tmp_path):
    """TH-21: every documented return code of th_tt_save/th_tt_load.

    Content, not just codes: after a reseed makes the load fail, restoring the
    original seed makes the *same file* load again, which shows the refusal is
    keyed to tt_seed_used and not to something incidental about the file.
    """
    f = str(tmp_path / "a.tt").encode()
    assert tt.lib.th_tt_save(f) == 0
    assert tt.lib.th_tt_load(f) == 0                      # same table, same seed

    tt.lib.th_tt_init(13)
    assert tt.lib.th_tt_load(f) == -2                     # wrong entry count

    tt.lib.th_tt_init(12)
    tt.lib.th_seed(12345)
    assert tt.lib.th_tt_load(f) == -2                     # wrong Zobrist seed
    tt.lib.th_seed(DEFAULT_SEED)
    assert tt.lib.th_tt_load(f) == 0                      # ...and back again

    assert tt.lib.th_tt_load(str(tmp_path / "nope.tt").encode()) == -1
    assert tt.lib.th_tt_save(str(tmp_path).encode()) == -1          # a directory

    raw = (tmp_path / "a.tt").read_bytes()
    (tmp_path / "magic.tt").write_bytes(b"NOTMAGIC" + raw[8:])
    assert tt.lib.th_tt_load(str(tmp_path / "magic.tt").encode()) == -1
    (tmp_path / "short.tt").write_bytes(raw[: len(raw) // 2])
    assert tt.lib.th_tt_load(str(tmp_path / "short.tt").encode()) == -1


def test_tt_save_and_load_refuse_without_a_table():
    """Both return -1 before th_tt_init has ever run. Needs a cold process:
    once any test in the run allocates a table it stays allocated."""
    out = _cold("""
print(E.lib.th_tt_save(b"/dev/null"), E.lib.th_tt_load(b"/dev/null"))
""")
    assert out == "-1 -1"


def test_tt_dump_carries_the_build_that_wrote_it(tt, tmp_path):
    """THB-07: a dump used to carry no identity of the code that produced it.

    th_key depends only on (board, hands, stm, seed) and every one of those
    survives a rules change unchanged, so a build in which a ferz moved like a
    king -- perft(1..4) = 7/43/362/3171 against the stock 6/33/241/1855 --
    wrote a dump the stock build loaded with rc = 0. The xkey ^ data == key
    trick validates against corruption, not provenance.

    The header field is edited here rather than compiling a second engine: the
    end-to-end foreign-rule case is what motivated the field, this pins the
    mechanism that refuses it.
    """
    assert tt.lib.th_build_id() != 0, "built without -DTH_BUILD_ID"

    f = tmp_path / "a.tt"
    assert tt.lib.th_tt_save(str(f).encode()) == 0
    raw = bytearray(f.read_bytes())
    assert struct.unpack_from("<Q", raw, 24)[0] == tt.lib.th_build_id()

    struct.pack_into("<Q", raw, 24, 0xDEADBEEF)
    (tmp_path / "foreign.tt").write_bytes(raw)
    assert tt.lib.th_tt_load(str(tmp_path / "foreign.tt").encode()) == -3


def test_a_failed_tt_save_leaves_the_previous_dump_intact(tt, tmp_path):
    """THB-08: th_tt_save opened the live checkpoint with fopen(.., "wb"),
    truncating it before a byte was written, and nothing restored it on
    failure. A 268 MB dump overwritten by a smaller table became 4 MB and would
    not reload -- the previous good dump was unrecoverable from the moment the
    new save started. It now writes to <name>.tmp and renames.
    """
    f = tmp_path / "live.tt"
    assert tt.lib.th_tt_save(str(f).encode()) == 0
    good = f.read_bytes()

    # a path that cannot be written: the .tmp sibling is created and removed
    assert tt.lib.th_tt_save(str(tmp_path / "no" / "such" / "dir.tt").encode()) == -1
    assert not (tmp_path / "no").exists()

    # ...and a save onto a directory must not leave a stray .tmp behind either
    (tmp_path / "adir.tt").mkdir()
    assert tt.lib.th_tt_save(str(tmp_path / "adir.tt").encode()) == -1
    assert not (tmp_path / "adir.tt.tmp").exists()

    assert f.read_bytes() == good
    assert tt.lib.th_tt_load(str(f).encode()) == 0


# The recorded mate-in-9 line from solve_status.json, in engine notation.
MATE9_PV = ["b4c2", "b1b2", "F@a3", "b2c2", "d3c2", "U@b3", "d4d3", "b3d2", "W@b1"]


def test_the_recorded_proof_line_is_legal_and_repetition_free():
    """TH-03's cheap mitigation, run rather than described.

    Rep-safety keeps path-dependent values out of the table; the REUSE side is
    unguarded, and the residual lands on the positive side -- a possible
    over-claimed win. Replaying each published PV from the root and confirming
    it never repeats a position closes that for the proofs actually published,
    which is cheaper than more search.
    """
    pos = T.Position.from_tfen("fuwk/3p/P1F1/KWU1[-] b")
    seen = {pos.key()}
    for i, ms in enumerate(MATE9_PV):
        legal = {T.move_str(m): m for m in pos.legal_moves()}
        assert ms in legal, f"ply {i + 1}: {ms} illegal in {pos.tfen()}"
        pos.make(legal[ms])
        assert pos.key() not in seen, f"ply {i + 1} repeats a position: {pos.tfen()}"
        seen.add(pos.key())
    assert pos.result() == -1        # White, to move, is checkmated
    assert len(MATE9_PV) == 9
