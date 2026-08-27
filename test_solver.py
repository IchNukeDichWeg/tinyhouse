"""Solver contract tests. Nothing in the perft suite touches the C search, so
these are the only tests that exercise th_solve/th_mate_hunt/th_root_moves.

Several of them need a COLD process. Both the transposition table and the
thread-local `history` table carry over between in-process searches, and a warm
one can hide the very defect being pinned: THB-01 reproduces from a cold start
and disappears if a shallower depth ran first in the same process. `_cold()`
runs a snippet in a fresh interpreter for exactly that reason.
"""
import struct
import json
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


def test_history_carry_over_is_under_the_callers_control():
    """TH-19: `history` is thread-local and nothing reset it, so repeats of the
    same search in one process were not independent samples.

    Measured, five repeats of an identical depth-13 hunt with a fresh table
    before each: 757,431 / 839,298 / 845,107 / 1,345,672 / 795,066 in one
    process, against 757,431 five times in five separate processes. This pins
    both halves at a cheap depth -- that the contamination is real, and that
    th_clear_history() removes it -- because a benchmark that cannot be
    reproduced is not a benchmark.
    """
    import engine_c as E

    def repeats(clear):
        out = []
        for _ in range(4):
            E.lib.th_tt_init(20)
            if clear:
                E.lib.th_clear_history()
            n0 = E.lib.th_nodes()
            E.lib.th_mate_hunt(E.to_c(T.Position.from_tfen("fuwk/3p/P3/KWUF[-] w")), 11, 0,
                               E.ffi.new("uint16_t *"))
            out.append(E.lib.th_nodes() - n0)
        return out

    E.lib.th_clear_history()
    dirty = repeats(False)
    assert len(set(dirty)) > 1, f"expected in-process drift, got {dirty}"

    clean = repeats(True)
    assert len(set(clean)) == 1, f"th_clear_history did not make repeats identical: {clean}"
    assert clean[0] == dirty[0], "the first repeat is the cold-history sample either way"


# The published headline line, from README.md and solve_status.json: 1.Fd1-c2
# loses by force. From the root that is a mate in 10 -- White's move, then
# Black's nine.
START_ROOT_VALUES = {"a1b2": 0, "a2a3": 0, "b1b2": 0, "c1b3": 0, "c1d3": 0, "d1c2": -29990}


@pytest.mark.parametrize("depth", [10, 11, 12])
def test_root_move_values_from_the_start_are_pinned(tt, depth):
    """TH-18: nothing in the suite touched the solver, so nothing would have
    noticed the day a published number moved.

    VALUES only, never the node count. The count for this search is not merely
    drifty: with a table held across repeats it collapses from 95,857 to 6,
    which would make a node assertion look catastrophically broken when nothing
    is wrong. It IS reproducible with a fresh table in a fresh process, so a
    node pin is possible -- but only with that precondition documented, and
    TH-20 is where it belongs.
    """
    got = _root_values(tt, depth)
    assert got == START_ROOT_VALUES


@pytest.mark.parametrize("seed", [0xC0FFEE, 1, 0xDEADBEEF])
def test_root_move_values_survive_a_reseed(tt, seed):
    """Under an independent Zobrist seed the two runs' collision sets are
    independent, so agreement is the cheap check against a key collision having
    faked the result. The fixture restores the default seed afterwards."""
    tt.lib.th_seed(seed)
    tt.lib.th_tt_init(22)
    assert _root_values(tt, 10) == START_ROOT_VALUES


@pytest.mark.parametrize("bits", [0, 8, 24])
def test_root_move_values_survive_any_table_size(tt, bits):
    """Including 2^0, which is one entry -- effectively no table at all."""
    tt.lib.th_tt_init(bits)
    assert _root_values(tt, 10) == START_ROOT_VALUES


def _root_values(E, depth):
    E.lib.th_clear_history()
    mvs, vals = E.ffi.new("uint16_t[128]"), E.ffi.new("int[128]")
    n = E.lib.th_root_moves(E.to_c(T.Position.start()), depth, mvs, vals, E.ffi.NULL)
    return {T.move_str(mvs[i]): vals[i] for i in range(n)}


def test_regression_harness_matches_its_baseline():
    """TH-20. The detector, as opposed to TH-18's record.

    Calibrated against five mutations planted in search(): this catches all
    five, the published-value pin catches none. Costs about 2s.
    """
    sys.path.insert(0, str(DIR / "scripts"))
    import json

    import engine_c as E
    import regress

    got = regress.measure(E)
    want = json.loads(regress.BASELINE.read_text())
    assert got["digest"] == want["digest"]
    assert [r["nodes"] for r in got["rows"]] == [r["nodes"] for r in want["rows"]]


# -- cffi signature coverage (TH-22) ----------------------------------------

def _cffi_symbols():
    import re

    cdef = (DIR / "engine_c.py").read_text().split('ffi.cdef("""')[1].split('""")')[0]
    return set(re.findall(r"\b(th_\w+)\s*\(", cdef))


def test_every_cffi_symbol_has_a_contract_check(tt):
    """TH-22: the search API had zero signature coverage.

    A struct-layout cdef error is caught today by the existing perft tests. A
    wrong SIGNATURE is not: with a deliberately swapped th_mate_hunt cdef the
    suite stayed green while the function returned 0 instead of a mate score.
    cffi ABI mode marshals by the declared types, so a wrong one mis-marshals
    silently.

    Every declared symbol is called below with an assertion about what it
    returns. The set comparison at the end is the part that matters over time:
    adding a cdef line without covering it fails this test.

    What this cannot catch, stated rather than implied: a 64-bit return
    declared as int is invisible while the real value stays under 2^31, so the
    th_nodes counter is only pinned as monotonic. th_key gets a genuine width
    check because its values are uniformly distributed over 64 bits.
    """
    import engine_c as E

    start = T.Position.start()
    mate9 = T.Position.from_tfen("fuwk/3p/P1F1/KWU1[-] b")
    checked = T.Position.from_tfen("3k/1U2/4/K3[f] b")      # mao gives check
    bm, snd = E.ffi.new("uint16_t *"), E.ffi.new("int *")
    covered = set()

    def cover(*names):
        covered.update(names)

    E.lib.th_init(); cover("th_init")                       # idempotent
    assert E.lib.th_perft(E.to_c(start), 4) == 1855; cover("th_perft")
    # both perft engines answer the same question; the differential walk test
    # is the real coverage, this pins the signatures
    assert E.lib.th_perft_mailbox(E.to_c(start), 4) == 1855; cover("th_perft_mailbox")
    assert E.lib.th_perft_bitboard(E.to_c(start), 4) == 1855; cover("th_perft_bitboard")
    assert E.lib.th_moves(E.to_c(start), E.ffi.NULL) == 6; cover("th_moves")
    assert E.lib.th_in_check(E.to_c(checked), T.BLACK) == 1
    assert E.lib.th_in_check(E.to_c(start), T.WHITE) == 0; cover("th_in_check")
    assert E.lib.th_result(E.to_c(start)) == 0
    assert E.lib.th_result(E.to_c(T.Position.from_tfen("k3/W1F1/1K2/4[p] b"))) == -1
    cover("th_result")

    moved = E.to_c(start)
    E.lib.th_make(moved, T.str_move("a2a3"))
    assert moved.board[T.name_sq("a3")] == T.piece(T.WHITE, T.P) and moved.stm == T.BLACK
    cover("th_make")

    k1, k2 = E.lib.th_key(E.to_c(start)), E.lib.th_key(E.to_c(mate9))
    assert k1 and k2 and k1 != k2 and k1 == E.lib.th_key(E.to_c(start))
    # > 0xFFFFFFFF, not `k1 >> 32`: a key truncated to a signed int comes back
    # negative, and in Python a negative >> 32 is -1, which is truthy. The
    # first version of this check passed against exactly that mutation.
    assert k1 > 0xFFFFFFFF, "th_key must be a full 64-bit value, not a truncated int"
    cover("th_key")

    E.lib.th_seed(0xC0FFEE)
    assert E.lib.th_key(E.to_c(start)) != k1, "reseeding must change the keys"
    E.lib.th_seed(DEFAULT_SEED)
    assert E.lib.th_key(E.to_c(start)) == k1
    cover("th_seed")

    assert E.lib.th_tt_init(18) == 0; cover("th_tt_init")
    assert E.lib.th_tt_grow(18) == 0; cover("th_tt_grow")   # never shrinks: no-op is 0
    assert E.lib.th_tt_fill() == 0                      # a fresh table is empty
    E.lib.th_solve(E.to_c(start), 6, bm, snd)
    assert 0 < E.lib.th_tt_fill() <= (1 << 18); cover("th_tt_fill")
    # TH-40: the 4-way bucket only costs one DRAM miss if it sits in ONE cache
    # line, which needs a 64-byte aligned base. Pinned here rather than assumed.
    assert E.lib.th_tt_bucket_aligned() == 1; cover("th_tt_bucket_aligned")
    E.lib.th_clear_history(); cover("th_clear_history")
    n0 = E.lib.th_nodes()
    E.lib.th_solve(E.to_c(start), 4, bm, snd)
    assert E.lib.th_nodes() > n0
    cover("th_nodes")

    assert E.lib.th_search(E.to_c(mate9), 9, bm) == 29991
    assert T.move_str(bm[0]) == "b4c2"; cover("th_search")
    assert E.lib.th_solve(E.to_c(mate9), 9, bm, snd) == 29991 and snd[0] & 1
    cover("th_solve")
    assert E.lib.th_solve_mt(E.to_c(mate9), 9, 1, bm, snd) == 29991; cover("th_solve_mt")
    assert E.lib.th_mate_hunt(E.to_c(mate9), 9, T.BLACK, bm) == 29991
    assert E.lib.th_mate_hunt(E.to_c(mate9), 8, T.BLACK, bm) == 0; cover("th_mate_hunt")
    assert E.lib.th_mate_hunt_mt(E.to_c(mate9), 9, T.BLACK, 2, bm, snd) == 29991
    assert snd[0] & 1, "a proven win must carry SND_LB in the winner's frame"
    cover("th_mate_hunt_mt")

    mvs, vals = E.ffi.new("uint16_t[128]"), E.ffi.new("int[128]")
    rsnd = E.ffi.new("int[128]")
    assert E.lib.th_root_moves(E.to_c(start), 4, mvs, vals, rsnd) == 6
    cover("th_root_moves")
    assert E.lib.th_build_id() >> 32; cover("th_build_id")

    assert E.lib.th_dfpn_init(16) == 0; cover("th_dfpn_init")
    dst = E.ffi.new("uint64_t[12]")
    assert E.lib.th_dfpn(E.to_c(mate9), T.BLACK, 200_000, -1, 1, dst) == 1
    assert 0 < dst[0] < 200_000 and dst[1] == 0        # nodes spent, pn == 0
    cover("th_dfpn")

    # a path under a directory that does not exist: both must refuse. Not a
    # directory path -- rename() onto a SYMLINK to a directory succeeds and
    # replaces the link, which is a portability trap rather than a contract.
    f = str(DIR / "no-such-dir" / "x.tt").encode()
    assert E.lib.th_tt_save(f) == -1; cover("th_tt_save")
    assert E.lib.th_tt_load(f) == -1; cover("th_tt_load")

    assert _cffi_symbols() - covered == set(), "cdef symbols with no contract check"


def test_a_non_terminal_horizon_node_is_unsound(tt):
    """TH-28, invariant #1 and nothing guarded it.

    The horizon returns 0 with NO soundness flags for a non-terminal node.
    That is the whole reason a mate score this engine reports is a proof: an
    unsound 0 can never propagate into one. A terminal reached at the horizon
    is the opposite case and does carry both flags, so both directions are
    pinned here -- if only the first were, setting SND_LB|SND_UB
    unconditionally at the horizon would pass.
    """
    bm, snd = tt.ffi.new("uint16_t *"), tt.ffi.new("int *")

    # depth 1: every child is a horizon node, and none of them is terminal
    v = tt.lib.th_solve(tt.to_c(T.Position.start()), 1, bm, snd)
    assert (v, snd[0]) == (0, 0)

    # depth 0 on a non-terminal root: the root itself is the horizon
    v = tt.lib.th_solve(tt.to_c(T.Position.start()), 0, bm, snd)
    assert (v, snd[0]) == (0, 0)

    # ...but a terminal AT the horizon is sound in both directions
    mated = T.Position.from_tfen("k3/W1F1/1K2/4[p] b")       # Black is checkmated
    v = tt.lib.th_solve(tt.to_c(mated), 0, bm, snd)
    assert v == -30000 and snd[0] == 3

    stalemated = T.Position.from_tfen("k3/2K1/W3/4[-] b")    # and stalemate WINS
    v = tt.lib.th_solve(tt.to_c(stalemated), 0, bm, snd)
    assert v == 30000 and snd[0] == 3


def test_reseeding_changes_the_keys_not_the_answers(tt):
    """TH-30, heeding the self-kill the source report attached to it.

    Asserting that a VALUE is equal under two seeds passes even if reseeding is
    a complete no-op, so that is not the contract to pin. The contract is that
    the keys differ -- otherwise the second-seed re-verification the whole
    proof story leans on would be checking nothing.
    """
    positions = [T.Position.start(),
                 T.Position.from_tfen("fuwk/3p/P1F1/KWU1[-] b"),
                 T.Position.from_tfen("1k2/4/2K1/4[PFUWpfuw] w")]
    before = [tt.lib.th_key(tt.to_c(p)) for p in positions]

    tt.lib.th_seed(0xC0FFEE)
    after = [tt.lib.th_key(tt.to_c(p)) for p in positions]
    assert all(a != b for a, b in zip(after, before)), "reseeding did not change the keys"
    assert len(set(after)) == len(after)

    tt.lib.th_seed(DEFAULT_SEED)
    assert [tt.lib.th_key(tt.to_c(p)) for p in positions] == before


def test_the_smp_hunt_finds_the_same_proof_as_one_thread(tt):
    """TH-27: nothing asserted that lazy SMP agrees with the single-threaded
    search. Node counts cannot be compared -- helpers perturb move ordering, so
    they differ by construction -- but the PROOF must not.
    """
    mate9 = "fuwk/3p/P1F1/KWU1[-] b"
    for workers in (1, 2, 4):
        tt.lib.th_tt_init(20)
        tt.lib.th_clear_history()
        bm = tt.ffi.new("uint16_t *")
        v = tt.lib.th_mate_hunt_mt(tt.to_c(T.Position.from_tfen(mate9)), 9, T.BLACK, workers, bm,
                                   tt.ffi.NULL)
        assert v == 29991, f"{workers} workers gave {v}"
        assert T.move_str(bm[0]) == "b4c2"

        tt.lib.th_tt_init(20)
        tt.lib.th_clear_history()
        assert tt.lib.th_mate_hunt_mt(tt.to_c(T.Position.from_tfen(mate9)), 8, T.BLACK,
                                      workers, bm, tt.ffi.NULL) == 0


def test_the_node_counter_is_cumulative_and_ignores_perft(tt):
    """TH-31: two facts about th_nodes that nothing recorded.

    It is cumulative for the life of the process -- neither th_tt_init nor
    th_seed resets it -- so a caller must difference around a search. And
    th_perft does not feed it at all, so differencing around a perft yields
    zero, which would read as "perft is free" to anyone measuring that way.
    th_perft's return value is the leaf count and is what to measure instead.
    """
    start = tt.to_c(T.Position.start())
    bm, snd = tt.ffi.new("uint16_t *"), tt.ffi.new("int *")

    n0 = tt.lib.th_nodes()
    tt.lib.th_solve(start, 6, bm, snd)
    n1 = tt.lib.th_nodes()
    assert n1 > n0

    tt.lib.th_tt_init(18)
    tt.lib.th_seed(DEFAULT_SEED)
    assert tt.lib.th_nodes() >= n1, "th_tt_init or th_seed reset the counter"

    n2 = tt.lib.th_nodes()
    assert tt.lib.th_perft(tt.to_c(T.Position.start()), 5) == 16021
    assert tt.lib.th_nodes() == n2, "th_perft now feeds g_nodes; update the callers"


def test_solve_hunt_resumes_from_its_checkpoint(tmp_path):
    """TH-26: resume is the documented overnight workflow and nothing tested it.

    Three runs against one scratch checkpoint: prove through depth 8, resume
    and continue at 10 without redoing 6 or 8, then run again with --fresh and
    watch it start over from 6. The checkpoint identity is also checked, since
    an inherited checkpoint from a different engine build would silently
    launder one engine's proof into another's (THB-07).
    """
    import json

    state = tmp_path / "s.json"
    def hunt(*extra):
        r = subprocess.run(
            [sys.executable, str(DIR / "solve_hunt.py"), "0", "--tt", "20",
             "--state", str(state), *extra],
            cwd=DIR, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return r.stdout

    first = hunt("--maxdepth", "8")
    assert "depth  6" in first and "depth  8" in first
    saved = json.loads(state.read_text())
    assert saved["proven_no_win_through"] == 8
    assert [d["depth"] for d in saved["depths"]] == [6, 8]
    assert state.with_suffix(".tt").exists()

    second = hunt("--maxdepth", "10")
    assert "resumed from" in second and "table reloaded" in second
    assert "depth  6" not in second and "depth 10" in second
    assert json.loads(state.read_text())["proven_no_win_through"] == 10

    third = hunt("--maxdepth", "8", "--fresh")
    assert "resumed from" not in third and "depth  6" in third

    # a checkpoint from another build must not be inherited
    poisoned = json.loads(state.read_text())
    poisoned["build"] = poisoned["build"] ^ 1
    state.write_text(json.dumps(poisoned))
    fourth = hunt("--maxdepth", "6")
    assert "differs in build; starting fresh" in fourth


def test_state_count_cross_check_and_headline():
    """TH-33: the headline state-space figure had nothing verifying its
    arithmetic, and the script carried a placements() stub that raised
    NotImplementedError and was never called.

    The full count cannot be enumerated -- that is the point of it -- so what
    is checked is the METHOD on a sub-problem countable both ways. The headline
    is pinned here against RULES.md so the two cannot drift apart silently.
    """
    r = subprocess.run([sys.executable, str(DIR / "scripts" / "state_count.py"), "--verify"],
                       cwd=DIR, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "AGREE" in r.stdout

    r = subprocess.run([sys.executable, str(DIR / "scripts" / "state_count.py")],
                       cwd=DIR, capture_output=True, text=True)
    assert "17,669,515,462,968" in r.stdout
    assert "4,417,378,865,742" in r.stdout
    assert "17,669,515,462,968" in (DIR / "RULES.md").read_text()


@pytest.mark.slow
def test_a_draw_can_be_proven(tt):
    """TH-29: the engine's ability to prove a DRAW, which nothing exercised.

    The backlog found 0 proven draws in 3,613 positions and concluded that a
    hand-crafted position was needed. It is not the position that was missing,
    it is the DEPTH. A draw proof needs every line to reach a terminal or a
    repetition before the horizon, and the only terminal-free component in
    reach is bare kings -- 312 states, being the 156 non-adjacent ordered king
    pairs times two sides to move. Lines in it are long, so the proof arrives
    around depth 90-100 and not at 14.

    Measured on 4/4/4/K2k[-] w: snd 0 through depth 74, snd 2 at 76 and 78,
    and exact at 80. The cheapest root found is the one used here: depth 100,
    ~117M nodes, ~7s. Marked slow for that reason.
    """
    bm, snd = tt.ffi.new("uint16_t *"), tt.ffi.new("int *")
    tt.lib.th_tt_init(24)
    tt.lib.th_clear_history()
    v = tt.lib.th_solve(tt.to_c(T.Position.from_tfen("2K1/4/4/2k1[-] w")), 100, bm, snd)
    assert (v, snd[0]) == (0, 3), "bare kings must be a PROVEN draw at this depth"


@pytest.mark.slow
def test_a_shallow_search_does_not_claim_the_draw(tt):
    """The other half, and the one that makes the test above non-vacuous: at
    depths the project actually runs, the same position is unproven. An engine
    that returned snd == 3 everywhere would pass the test above and be wrong.
    """
    bm, snd = tt.ffi.new("uint16_t *"), tt.ffi.new("int *")
    for depth in (14, 40):
        tt.lib.th_tt_init(22)
        tt.lib.th_clear_history()
        v = tt.lib.th_solve(tt.to_c(T.Position.from_tfen("2K1/4/4/2k1[-] w")), depth, bm, snd)
        assert v == 0 and snd[0] != 3, (depth, snd[0])


def test_reachable_census_low_plies():
    """TH-37. The reachable count is what prices a strong solve and a df-pn
    search; the syntactic 1.77e13 is an upper bound that says nothing about
    what a game can reach.

    Plies 1 and 2 must equal perft 1 and 2, since nothing transposes that early,
    and that is what makes this non-vacuous -- a census that had drifted from
    the move generator would fail there first.
    """
    sys.path.insert(0, str(DIR / "scripts"))
    import census

    assert census.KNOWN[1] == 6 and census.KNOWN[2] == 33      # == perft(1), perft(2)
    r = subprocess.run([sys.executable, str(DIR / "scripts" / "census.py"), "6"],
                       cwd=DIR, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "MISMATCH" not in r.stdout
    assert "55,183" in r.stdout


def test_dfpn_proves_the_recorded_mate():
    """TH-36's validation case: the second engine must agree with the first on
    the one position the project has published a proof for.

    Unbounded (no depth limit), so this is the horizon-free formulation the
    draw claim needs, not a bounded mate search wearing different clothes.
    ~2,770 nodes, well under a second.
    """
    sys.path.insert(0, str(DIR / "scripts"))
    import dfpn

    d = dfpn.DFPN(attacker=T.BLACK, node_cap=200_000)
    pn, dn = d.run(T.Position.from_tfen("fuwk/3p/P1F1/KWU1[-] b"))
    assert pn == 0, f"expected a proof; got pn={pn} dn={dn} after {d.nodes:,} nodes"
    assert d.nodes < 20_000, f"took {d.nodes:,} nodes; it used to take ~2,770"

    # ...and it must NOT prove a win for the other side from the same position
    d = dfpn.DFPN(attacker=T.WHITE, node_cap=200_000, depth_limit=9)
    pn, dn = d.run(T.Position.from_tfen("fuwk/3p/P1F1/KWU1[-] b"))
    assert dn == 0, f"White has no forced win here; got pn={pn} dn={dn}"


def test_dfpn_disproves_a_win_after_the_published_blunder():
    """1.Fd1-c2 is a Black mate in 9, so White has no forced win after it.
    df-pn reaches that as a positive DISPROOF, which is the thing alpha-beta
    structurally cannot do -- its horizon returns an unsound 0."""
    sys.path.insert(0, str(DIR / "scripts"))
    import dfpn

    d = dfpn.DFPN(attacker=T.WHITE, node_cap=600_000)
    pn, dn = d.run(T.Position.from_tfen("fuwk/3p/P1F1/KWU1[-] b"))
    assert dn == 0, f"expected a disproof; got pn={pn} dn={dn} after {d.nodes:,} nodes"


@pytest.mark.slow
def test_dfpn_agrees_with_the_alpha_beta_engine():
    """The cross-check that makes the second engine worth having.

    With a depth limit d, df-pn answers exactly the question th_mate_hunt(d)
    answers, so the two must agree position by position -- and they share no
    code beyond the move generator. Measured: 178 agreements and 0
    disagreements over depths 4, 6 and 8; a smaller sweep runs here.
    """
    r = subprocess.run([sys.executable, str(DIR / "scripts" / "dfpn.py"), "cross", "12", "4,6"],
                       cwd=DIR, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "DISAGREE 0" in r.stdout, r.stdout


# -- the C df-pn engine (TH-36) ---------------------------------------------

def _dfpn(tt, tfen, attacker, cap=4_000_000, depth_limit=-1, twins=1, bits=21):
    tt.lib.th_dfpn_init(bits)
    st = tt.ffi.new("uint64_t[12]")
    v = tt.lib.th_dfpn(tt.to_c(T.Position.from_tfen(tfen)), attacker, cap,
                       depth_limit, twins, st)
    return v, [st[i] for i in range(10)]


@pytest.mark.parametrize("twins", [0, 1])
def test_c_dfpn_proves_the_recorded_mate(tt, twins):
    """The second engine must agree with the first on the position the project
    has published a proof for -- with and without twin entries, since twins
    change what may be reused across paths and are the part most able to be
    subtly wrong."""
    v, s = _dfpn(tt, "fuwk/3p/P1F1/KWU1[-] b", T.BLACK, twins=twins)
    assert v == 1, f"expected a proof; got {v} after {s[0]:,} nodes"
    assert s[0] < 50_000, f"took {s[0]:,} nodes; it used to take ~2,800"

    # ...and White has no forced win from the same position. That is a positive
    # DISPROOF, which the alpha-beta engine structurally cannot produce.
    v, s = _dfpn(tt, "fuwk/3p/P1F1/KWU1[-] b", T.WHITE, twins=twins)
    assert v == -1, f"expected a disproof; got {v} after {s[0]:,} nodes"


def test_c_dfpn_proves_the_recorded_mate_in_13(tt):
    v, s = _dfpn(tt, "1uwk/1f1p/PW2/K1UF[-] w", T.WHITE, depth_limit=13)
    assert v == 1, f"expected a proof; got {v} after {s[0]:,} nodes"


@pytest.mark.parametrize("twins", [0, 1])
def test_c_dfpn_agrees_with_the_alpha_beta_engine(tt, twins):
    """The cross-check that makes a second engine worth having: with a depth
    limit d, df-pn answers exactly the question th_mate_hunt(d) answers, and
    the two share no code beyond the move generator. Measured over a much
    larger sweep than this one: 3,960 agreements, 0 disagreements."""
    import random

    random.seed(41)
    roots = []
    while len(roots) < 8:
        p = T.Position.start()
        for _ in range(random.randrange(1, 12)):
            ms = p.legal_moves()
            if not ms:
                break
            p.make(random.choice(ms))
        else:
            if p.legal_moves():
                roots.append(p.tfen())

    bm, snd = tt.ffi.new("uint16_t *"), tt.ffi.new("int *")
    checked = 0
    for tfen in roots:
        for d in (4, 6):
            for atk in (T.WHITE, T.BLACK):
                tt.lib.th_tt_init(20)
                tt.lib.th_clear_history()
                ab = tt.lib.th_mate_hunt_mt(tt.to_c(T.Position.from_tfen(tfen)), d, atk,
                                            1, bm, snd) > 29000
                v, s = _dfpn(tt, tfen, atk, cap=2_000_000, depth_limit=d, twins=twins)
                assert v != 0, f"node cap hit on {tfen} d{d}"
                assert (v == 1) == ab, f"{tfen} d{d} atk={atk}: alpha-beta {ab}, df-pn {v}"
                checked += 1
    assert checked == 32


def test_twin_entries_change_no_verdict(tt):
    """Twins are the part of this engine whose soundness rests on measurement
    rather than proof (see the header of tinyhouse.c's df-pn section), so the
    on/off verdicts are pinned against each other. Twins-off is the
    conservative rule and is sound by construction."""
    for tfen, atk in [("fuwk/3p/P1F1/KWU1[-] b", T.BLACK),
                      ("fuwk/3p/P1F1/KWU1[-] b", T.WHITE),
                      ("3k/4/4/K1U1[-] w", T.WHITE),
                      ("1uwk/P3/3p/K2F[UWf] w", T.WHITE)]:
        a, _ = _dfpn(tt, tfen, atk, cap=2_000_000, twins=0)
        b, sb = _dfpn(tt, tfen, atk, cap=2_000_000, twins=1)
        assert a == b, f"{tfen} atk={atk}: twins off {a}, twins on {b}"
        if a != 0:
            assert sb[7] == 0 or sb[4] > 0        # something was withheld or twinned


def test_a_shared_leg_blocks_a_double_mao_check(tt):
    """Found by the bitboard perft cross-check, not by any of the campaign's
    74,702-position walks: TH-16's check_block_square declared every double-mao
    check unblockable, but two maos attacking THROUGH THE SAME LEG SQUARE are
    both blocked by one drop on it.

    Here Black's a2 king is checked by the mao on c3 and the promoted mao on
    b4, both via b3. Black holds all four piece types: the four blocking drops
    on b3 are legal, and pruning them undercounted perft and handed the search
    a defender with four fewer defenses -- a wrong-PROVEN vector in both
    directions.
    """
    tfen = "1U~2/2U1/k1K1/4[FWpfuw] b"
    pos = T.Position.from_tfen(tfen)
    truth = sorted(T.move_str(m) for m in pos.legal_moves())
    assert truth == ["F@b3", "P@b3", "U@b3", "W@b3", "a2a1", "a2a3"]

    buf = tt.ffi.new("uint16_t[128]")
    n = tt.lib.th_moves(tt.to_c(pos), buf)
    got = sorted(T.move_str(buf[i]) for i in range(n))
    assert got == truth, f"C engine returned {got}"


def test_the_two_perft_engines_agree_on_random_walks(tt):
    """The permanent differential: the mailbox and bitboard movegens share no
    board representation, no move loop and no legality mechanism, so agreement
    between them is evidence in a way that re-running one of them is not.
    Writing the bitboard engine found the shared-leg double-mao-check pruning
    bug that 74,702 walked positions had missed; this keeps both engines
    disagreeing loudly rather than drifting apart quietly.
    """
    import random

    random.seed(97)
    roots = ["fuwk/3p/P3/KWUF[-] w", "1k2/4/2K1/4[PFUWpfuw] w",
             "3k/2U~1/4/K3[-] b", "1U~2/2U1/k1K1/4[FWpfuw] b"]
    compared = 0
    for root in roots:
        for _ in range(8):
            pos = T.Position.from_tfen(root)
            for ply in range(16):
                d = 4 if ply % 5 == 0 else 3
                a = tt.lib.th_perft_mailbox(tt.to_c(pos), d)
                b = tt.lib.th_perft_bitboard(tt.to_c(pos), d)
                assert a == b, f"{pos.tfen()} d{d}: mailbox {a:,} bitboard {b:,}"
                compared += 1
                ms = pos.legal_moves()
                if not ms:
                    break
                pos.make(random.choice(ms))
    assert compared > 300, compared


def test_tt_growth_preserves_the_table(tt):
    """The growing table's whole point: entries survive the rehash.

    The key is recoverable from the entry itself (key = xkey ^ data) and stored
    mate scores are ply-rebased at store time, so entries are position
    properties and rehashing moves them intact. Pinned by behaviour, not by
    counting: a warm re-solve after growth must collapse to near-nothing and
    return the identical value, exactly as it would without the growth.
    """
    import engine_c as E

    mate9 = "fuwk/3p/P1F1/KWU1[-] b"
    E.lib.th_tt_init(14)
    E.lib.th_clear_history()
    bm, snd = E.ffi.new("uint16_t *"), E.ffi.new("int *")
    n0 = E.lib.th_nodes()
    v_cold = E.lib.th_solve(E.to_c(T.Position.from_tfen(mate9)), 10, bm, snd)
    cold = E.lib.th_nodes() - n0
    fill_before = E.lib.th_tt_fill()
    assert v_cold == 29991 and fill_before > 0

    assert E.lib.th_tt_grow(17) == 0
    assert E.lib.th_tt_fill() >= fill_before * 0.95     # rare rehash collisions only

    n0 = E.lib.th_nodes()
    v_warm = E.lib.th_solve(E.to_c(T.Position.from_tfen(mate9)), 10, bm, snd)
    warm = E.lib.th_nodes() - n0
    assert v_warm == v_cold
    assert warm < cold * 0.05, f"warm {warm:,} vs cold {cold:,}: the table did not survive"


def test_solve_hunt_grows_and_resumes_across_the_growth(tmp_path):
    """End to end: the table starts small, grows on the projection, the
    checkpoint records the grown size, and a resume reopens at that size and
    reloads the dump rather than discarding it."""
    import json

    state = tmp_path / "s.json"

    def hunt(maxdepth):
        r = subprocess.run(
            [sys.executable, str(DIR / "solve_hunt.py"), "0", "--tt", "20",
             "--tt-start", "14", "--workers", "1",
             "--maxdepth", str(maxdepth), "--state", str(state)],
            cwd=DIR, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return r.stdout

    first = hunt(14)
    assert "GREW to 2^" in first
    saved = json.loads(state.read_text())
    assert saved["tt_bits_now"] > 14
    assert saved["tt_bits_now"] <= 20

    second = hunt(16)
    assert "resumed from" in second and "table reloaded" in second
    assert "depth 16" in second


def _solve_hunt_symbol(name):
    """solve_hunt.py parses argv at import, so pull one function out by source.

    Ugly on purpose and cheaper than restructuring the script: these two are
    pure formatting/arithmetic helpers with no module state.
    """
    import re
    src = (DIR / "solve_hunt.py").read_text()
    ns = {}
    exec(re.search(r"def fmt\(.*?\n\n", src, re.S).group(0), ns)
    exec(re.search(r"def %s\(.*?\n\n\n" % name, src, re.S).group(0), ns)
    return ns[name]


def test_progress_line_admits_when_it_passes_its_estimate():
    """A wrong ETA is worse than none: it decides whether a person waits or kills.

    The old form clamped to min(n/est, 0.99) and max(est-n, 0), so once the run
    passed its estimate it printed "~99% ... eta ~0m" and held there. Observed
    on a Black hunt sitting at 101.91G nodes against a 20.51G estimate for over
    a thousand seconds, reading as "nearly done" the whole time.
    """
    pl = _solve_hunt_symbol("progress_line")

    early = pl(24, 5_000_000_000, 90e6, 55, 20_510_000_000)
    assert "24% of est" in early and "eta ~" in early

    # the exact observed case
    past = pl(24, 101_910_000_000, 92.43e6, 1103, 20_510_000_000)
    assert "eta unknown" in past, past
    assert "99%" not in past and "eta ~0m" not in past, past
    assert "5.0x" in past, past

    assert "est" not in pl(6, 4000, 1e6, 0.1, None)      # no estimate at the first depth


@pytest.mark.slow
def test_tt_growth_steps_down_when_the_target_will_not_fit(tmp_path):
    """Refusing to grow is catastrophic, not conservative.

    A Black hunt asked for 2^31 (32.0 GiB) with 35.3 GiB free, missed the 0.9
    headroom test by 0.2 GiB, and stayed at the 2^20 START size -- then searched
    depth 24 through a 16 MiB table for 101.91G nodes, against 24.5G for the
    same depth on a right-sized one. A smaller growth would have fitted with
    room to spare, so the fix steps down instead of giving up.

    --tt 34 (256 GiB) cannot fit on any machine this runs on, which is what
    makes the assertion machine-independent.
    """
    out = subprocess.run(
        [sys.executable, str(DIR / "solve_hunt.py"), "1", "--tt", "34", "--force-tt",
         "--workers", "2", "--maxdepth", "16", "--fresh",
         "--state", str(tmp_path / "s.json")],
        capture_output=True, text=True, timeout=600)
    assert out.returncode == 0, out.stderr
    assert "instead" in out.stdout, out.stdout          # stepped down rather than refusing
    assert "GREW to 2^" in out.stdout, out.stdout       # and actually grew
    grew = [l for l in out.stdout.splitlines() if "GREW to 2^" in l]
    got = int(grew[0].split("GREW to 2^")[1].split()[0])
    assert got > 20, f"stayed at or near the start size: {grew[0]}"


@pytest.mark.slow
def test_resume_resizes_the_table_before_the_next_depth(tmp_path):
    """A growth refusal must not become permanent through the checkpoint.

    maybe_grow_tt was called only at the TAIL of the depth loop, so a resumed
    run reopened at the checkpoint's tt_bits_now and entered the next depth
    without reconsidering it. Observed: a Black hunt refused 2^31 by 0.2 GiB,
    checkpointed tt_bits_now=20, and the restart inherited the 16 MiB table --
    depth 24 passed 164G nodes still searching through it, against 24.5G for
    the same depth on a right-sized table. The step-down fix could not help,
    because nothing on the resume path called it.

    Saturate a 2^20 table, raise the cap, resume: it must grow BEFORE the next
    depth's first progress line, not after that depth completes.
    """
    state = tmp_path / "r.json"
    first = subprocess.run(
        [sys.executable, str(DIR / "solve_hunt.py"), "1", "--tt", "20", "--workers", "2",
         "--maxdepth", "20", "--fresh", "--state", str(state)],
        capture_output=True, text=True, timeout=1800)
    assert first.returncode == 0, first.stderr
    d = json.loads(state.read_text())
    assert d["tt_bits_now"] == 20, d["tt_bits_now"]
    d["tt_bits"] = 28                      # as a raised --tt would leave it
    state.write_text(json.dumps(d))

    out = subprocess.run(
        [sys.executable, str(DIR / "solve_hunt.py"), "1", "--tt", "28", "--workers", "2",
         "--maxdepth", "22", "--state", str(state)],
        capture_output=True, text=True, timeout=1800)
    assert out.returncode == 0, out.stderr
    assert "resumed from" in out.stdout
    grew = [l for l in out.stdout.splitlines() if "GREW to 2^" in l]
    assert grew, f"resume did not resize a saturated table:\n{out.stdout}"
    # and it happened before any depth-22 work, not after the depth finished
    body = out.stdout.split("GREW to 2^")[0]
    assert "d22" not in body and "depth 22" not in body, \
        f"table grew only AFTER depth 22 ran:\n{out.stdout}"
    assert json.loads(state.read_text())["tt_bits_now"] > 20
