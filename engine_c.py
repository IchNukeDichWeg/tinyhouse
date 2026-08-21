"""cffi (ABI mode) wrapper for tinyhouse.c. Auto-builds the shared library when
missing or stale, mirroring Pygin's build-script-plus-runtime-load architecture.
Positions convert to/from tinyhouse.Position, which stays the source of truth
for TFEN and rules documentation."""
import subprocess
from pathlib import Path

import cffi

import tinyhouse as T

_DIR = Path(__file__).parent
_SRC = _DIR / "tinyhouse.c"
_LIB = _DIR / "libtinyhouse.dylib"

if not _LIB.exists() or _LIB.stat().st_mtime < _SRC.stat().st_mtime:
    subprocess.run(["cc", "-O2", "-pthread", "-shared", "-o", str(_LIB), str(_SRC)], check=True)

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
void th_tt_init(int log2_entries);
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


def to_c(pos: T.Position):
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
