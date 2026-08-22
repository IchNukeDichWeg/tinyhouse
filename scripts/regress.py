"""Paired nodes-to-depth + solver-digest regression harness.

Two fields per (position, depth), because they detect different things and
neither is sufficient:

- VALUES (plus soundness flags and best move, folded into one digest) catch a
  change that alters what the engine concludes. They are extremely stable --
  measured against five mutations planted in search(), the published root
  values caught none of them -- so on their own they are a record, not a
  detector.
- NODES-TO-DEPTH catches a change that alters how the engine gets there. Same
  five mutations: node counts caught four. This is the detector.

Calibrated against five mutations planted in search() -- TT mate-score
re-basing removed, root killers not reset, mate-distance pruning clamp removed,
history update removed, rep-safety store gate removed. This harness catches
ALL FIVE; the published-value pin in test_solver.py catches none of them. The
margins vary enormously, though: 22.97% for the history update, 0.02% (four
nodes) for the rep-safety gate. A mutation quieter than the quietest of those
is not ruled out, and neither field is a soundness proof. Treat a green run as
"nothing detectably changed", never as "still correct".

Determinism: every entry gets a fresh transposition table AND a cleared history
table (th_clear_history), so the numbers do not depend on the order entries are
run in, on how many ran before, or on anything else in the process.

Depth choice is load-bearing and 10/12 is not arbitrary. At 6/8 a
path-dependent-store mutation shows up as a ONE-node difference, which is luck;
at 10/12 the same mutation is a percent-scale signal.

NOT A PERFORMANCE PROXY. This is a regression DETECTOR at a fixed shallow depth
pair, and it cannot stand in for the depth the product runs at. Measured: the
TH-17 move-ordering bonus made this suite 11.21% cheaper while making the
depth-18 start-position hunt 19.33% more expensive, and the depth-18 Black hunt
70% more expensive. Judge an ordering or pruning change on the deep hunts, not
on this.

  scripts/regress.py                 compare against the committed baseline
  scripts/regress.py --update        rewrite the baseline (say why in the commit)
  scripts/regress.py --lib PATH      run a scratch build instead
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import tinyhouse as T  # noqa: E402

# Frozen. Adding a position invalidates every baseline number, so append only,
# and never reorder.
POSITIONS = [
    "fuwk/3p/P3/KWUF[-] w",          # start
    "fuwk/3p/P1F1/KWU1[-] b",        # published mate in 9
    "1uwk/1f1p/PW2/K1UF[-] w",       # published mate in 13
    "1uwk/Pf1p/4/KWUF[-] w",         # published mate in 13
    "f1w1/2k1/K2p/W1UF[Up] b",       # the THB-01 ply-budget repro
    "1k2/4/2K1/4[PFUWpfuw] w",       # drop-heavy: eight pieces in hand
    "1uwk/P3/3p/K2F[UWf] w",         # promotion and hands in play
    "3k/1U2/4/K3[f] b",              # mao check, single blocking drop
]
DEPTHS = (10, 12)
TT_BITS = 22
BASELINE = Path(__file__).parent / "regress_baseline.json"


def measure(E):
    rows = []
    for tfen in POSITIONS:
        for depth in DEPTHS:
            E.lib.th_tt_init(TT_BITS)
            E.lib.th_clear_history()
            c = E.to_c(T.Position.from_tfen(tfen))
            bm, snd = E.ffi.new("uint16_t *"), E.ffi.new("int *")
            n0 = E.lib.th_nodes()
            value = E.lib.th_solve(c, depth, bm, snd)
            rows.append({"tfen": tfen, "depth": depth, "value": value, "snd": snd[0],
                         "best": T.move_str(bm[0]) if bm[0] else None,
                         "nodes": E.lib.th_nodes() - n0})
    digest = hashlib.sha1(
        json.dumps([[r["tfen"], r["depth"], r["value"], r["snd"], r["best"]] for r in rows],
                   sort_keys=True).encode()).hexdigest()[:16]
    return {"digest": digest, "depths": list(DEPTHS), "tt_bits": TT_BITS, "rows": rows}


def load_engine(lib_path):
    if not lib_path:
        import engine_c
        return engine_c
    # One dylib per process: two builds of the same library cannot share a
    # loader, and importing engine_c here would load the repo's as well.
    import cffi
    ffi = cffi.FFI()
    ffi.cdef((Path(__file__).parent.parent / "engine_c.py").read_text()
             .split('ffi.cdef("""')[1].split('""")')[0])
    lib = ffi.dlopen(lib_path)
    lib.th_init()

    def to_c(pos):
        pos.validate()
        c = ffi.new("THPos *")
        for i, pc in enumerate(pos.board):
            c.board[i] = pc
        for col in (0, 1):
            for t in range(4):
                c.hands[col][t] = pos.hands[col][t]
        c.stm = pos.stm
        return c

    return type("ScratchEngine", (), {"ffi": ffi, "lib": lib, "to_c": staticmethod(to_c)})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--lib", default=None, help="a scratch dylib, for calibration")
    a = ap.parse_args()

    got = measure(load_engine(a.lib))
    if a.update:
        BASELINE.write_text(json.dumps(got, indent=1) + "\n")
        print(f"baseline written: digest {got['digest']}, "
              f"{sum(r['nodes'] for r in got['rows']):,} nodes total")
        sys.exit(0)

    want = json.loads(BASELINE.read_text())
    bad = []
    if got["digest"] != want["digest"]:
        bad.append(f"digest {want['digest']} -> {got['digest']}")
    for w, g in zip(want["rows"], got["rows"]):
        if (w["value"], w["snd"], w["best"]) != (g["value"], g["snd"], g["best"]):
            bad.append(f"{g['tfen']} d{g['depth']}: value/snd/best "
                       f"{w['value']}/{w['snd']}/{w['best']} -> {g['value']}/{g['snd']}/{g['best']}")
        elif w["nodes"] != g["nodes"]:
            bad.append(f"{g['tfen']} d{g['depth']}: nodes {w['nodes']:,} -> {g['nodes']:,} "
                       f"({(g['nodes'] / max(w['nodes'], 1) - 1) * 100:+.2f}%)")
    if bad:
        print("REGRESSION HARNESS: changed\n  " + "\n  ".join(bad))
        sys.exit(1)
    print(f"regression harness: unchanged (digest {got['digest']}, "
          f"{sum(r['nodes'] for r in got['rows']):,} nodes total)")
