"""Deep null-window mate hunt from the start position for one color.
Usage: solve_hunt.py <color 0=white 1=black> [maxdepth] [ttbits]
A value > 29000 proves a forced win for that color (mate distance = 30000-v
in plies, check extensions included); anything else at depth d proves no
forced win within d quiet plies."""
import sys
import time

import engine_c as E
import tinyhouse as T

color = int(sys.argv[1])
maxd = int(sys.argv[2]) if len(sys.argv) > 2 else 36
ttbits = int(sys.argv[3]) if len(sys.argv) > 3 else 25

E.lib.th_tt_init(ttbits)
pos = E.to_c(T.Position.start())
bm = E.ffi.new("uint16_t *")
name = "WHITE" if color == 0 else "BLACK"
print(f"hunting forced {name} win, tt 2^{ttbits}", flush=True)
for d in range(6, maxd + 1, 2):
    t0 = time.perf_counter()
    v = E.lib.th_mate_hunt(pos, d, color, bm)
    dt = time.perf_counter() - t0
    print(f"depth {d:2d}  value {v:6d}  best {T.move_str(bm[0]) if bm[0] else '-':6s}"
          f"  nodes {E.lib.th_nodes():>15,}  {dt:8.1f}s", flush=True)
    if v > 29000:
        print(f"PROVEN: {name} forces a win, mate value {v} (win in {30000-v} plies)", flush=True)
        break
