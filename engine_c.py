"""cffi (ABI mode) wrapper for tinyhouse.c. Auto-builds the shared library when
missing or stale, mirroring Pygin's build-script-plus-runtime-load architecture.
Positions convert to/from tinyhouse.Position, which stays the source of truth
for TFEN and rules documentation."""
import hashlib
import subprocess
from pathlib import Path

import cffi

import tinyhouse as T

_DIR = Path(__file__).parent
_SRC = _DIR / "tinyhouse.c"
_LIB = _DIR / "libtinyhouse.dylib"

# Build fingerprint, compiled in as TH_BUILD_ID and stamped into every .tt
# dump. Derived from the source rather than hand-maintained, because a format
# id nobody bumps when editing pseudo_moves protects nothing: a dump written by
# a build with different RULES has perfectly valid keys under the same Zobrist
# seed, and used to load with rc = 0.
_BUILD_ID = int.from_bytes(hashlib.sha1(_SRC.read_bytes()).digest()[:8], "little")

# THB-15: tinyhouse.py's DOUBLE_STEP toggle has no counterpart in tinyhouse.c,
# and the C engine is the one that searches. With the flag on, Python gives
# perft(1..5) = 6/36/274/2181/19317 and C gives 6/33/241/1855/16021 -- they are
# different games from ply 2. The sharp hazard is that server.py drives BOTH in
# one process: position_info enumerates the GUI's legal moves from the Python
# generator while analyze evaluates with C, so the GUI would offer a2a4=W and
# then hand back an evaluation from an engine that has no such move. A raise,
# not an assert, because asserts vanish under -O.
if T.DOUBLE_STEP:
    raise RuntimeError(
        "tinyhouse.DOUBLE_STEP is on but tinyhouse.c does not implement it. The "
        "two engines would search different games (perft(2): 36 vs 33); mirror "
        "the rule in pseudo_moves() before enabling it.")

if not _LIB.exists() or _LIB.stat().st_mtime < _SRC.stat().st_mtime:
    subprocess.run(["cc", "-O2", "-pthread", "-shared", f"-DTH_BUILD_ID={_BUILD_ID}ULL",
                    "-o", str(_LIB), str(_SRC)], check=True)

ffi = cffi.FFI()
ffi.cdef("""
typedef struct { int8_t board[16]; int8_t hands[2][4]; int8_t stm; } THPos;
void th_init(void);
int th_in_check(const THPos *p, int color);
int th_moves(THPos *p, uint16_t *out);
void th_make(THPos *p, uint16_t m);
int th_result(THPos *p);
uint64_t th_perft(THPos *p, int depth);
uint64_t th_key(const THPos *p);
uint64_t th_build_id(void);
int th_tt_init(int log2_entries);
void th_seed(uint64_t s);
int th_tt_save(const char *fname);
int th_tt_load(const char *fname);
uint64_t th_nodes(void);
int th_search(THPos *p, int depth, uint16_t *bestmove);
int th_solve(THPos *p, int depth, uint16_t *bestmove, int *snd);
int th_solve_mt(THPos *p, int depth, int workers, uint16_t *bestmove, int *snd);
int th_mate_hunt_mt(THPos *p, int depth, int color, int workers, uint16_t *bestmove);
int th_mate_hunt(THPos *p, int depth, int color, uint16_t *bestmove);
int th_root_moves(THPos *p, int depth, uint16_t *out_moves, int *out_values);
""")
lib = ffi.dlopen(str(_LIB))
lib.th_init()


# to_c is the real Python->C trust boundary. The C engine indexes hands[] and
# its neighbour tables straight off these values, so an unvalidated Position
# reads out of bounds and the search hands back a fabricated mate carrying the
# soundness flags that mean "proven". Every guard used to live in from_tfen,
# which a hand-built Position bypasses. Set False only to measure what the
# check costs; it is not a performance knob otherwise.
VALIDATE_TO_C = True


def to_c(pos: T.Position):
    if VALIDATE_TO_C:
        pos.validate()
    c = ffi.new("THPos *")
    for i, pc in enumerate(pos.board):
        c.board[i] = pc
    for color in (0, 1):
        for t in range(4):
            c.hands[color][t] = pos.hands[color][t]
    c.stm = pos.stm
    return c


def to_py(c) -> T.Position:
    pos = T.Position()
    pos.board = [c.board[i] for i in range(16)]
    pos.hands = [[c.hands[color][t] for t in range(4)] for color in (0, 1)]
    pos.stm = c.stm
    return pos


def perft(tfen: str, depth: int) -> int:
    return lib.th_perft(to_c(T.Position.from_tfen(tfen)), depth)


def legal_moves(pos: T.Position) -> list[int]:
    c = to_c(pos)
    buf = ffi.new("uint16_t[128]")
    n = lib.th_moves(c, buf)
    return [buf[i] for i in range(n)]


if __name__ == "__main__":
    import sys
    import time
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    tfen = sys.argv[2] if len(sys.argv) > 2 else "fuwk/3p/P3/KWUF[-] w"
    c = to_c(T.Position.from_tfen(tfen))
    for d in range(1, depth + 1):
        t0 = time.perf_counter()
        n = lib.th_perft(c, d)
        dt = time.perf_counter() - t0
        print(f"perft({d}) = {n}  {dt:.3f}s  {n/max(dt,1e-9)/1e6:.1f} Mnps")
