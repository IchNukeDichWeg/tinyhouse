"""df-pn (depth-first proof-number search) for TH-36, and the gating milestone.

Why a second engine at all: the alpha-beta search returns an UNSOUND 0 at its
horizon, so a draw is the *absence* of a proof rather than a positive goal. It
can prove a draw only where no line still reaches the horizon, which in practice
means bare kings at around depth 80 (see test_solver.py) and nothing resembling
the start position. df-pn has no horizon -- every leaf is a terminal or a
repetition -- so "not a win" is something it can prove directly.

Formulation: phi/delta (Nagai), so the recurrences are uniform across OR and
AND nodes -- phi(n) = min over children of delta(c), delta(n) = sum of phi(c).
An OR node is the attacker to move, an AND node the defender.

GHI: a repetition is path-dependent, so a value that depended on hitting an
ANCESTOR is never stored in the global table -- the same conservative rule the
alpha-beta engine applies on its store side. Such a value IS kept in a per-node
local cache, because within one call of mid() the path prefix is fixed, which is
exactly the condition the value is relative to. That local cache is not an
optimisation: df-pn advances by re-reading a child after searching it, so a
child whose value went nowhere reads back as the (1, 1) initial estimate and is
searched again forever. Kishimoto-Muller twin entries would recover more of what
the conservative rule throws away across siblings and re-visits, and are the
obvious next step.

Validated against the alpha-beta engine, which is the point of a second engine.
With a depth limit d, this answers exactly the question th_mate_hunt(d) answers
-- "does the attacker force a win within d plies?" -- so the two must agree
position by position, and they share no code beyond the move generator.
Measured: **178 agreements, 0 disagreements** over depths 4, 6 and 8. On the
recorded mate in 9 it proves in 1,863 nodes depth-limited and 2,770 unbounded,
against the ~1,949 the backlog reported for a depth-limited prototype.

This module is the REFERENCE implementation. The shipped engine is the C one in
tinyhouse.c (th_dfpn), which adds Kishimoto-Muller twin entries; this exists to
cross-check it, and being slow and simple is the point.

  scripts/dfpn.py mate9          the validation case (Python)
  scripts/dfpn.py cross [N]      Python df-pn vs the alpha-beta engine
  scripts/dfpn.py milestone [N]  root dn against nodes spent (Python)
  scripts/dfpn.py ccross [N]     C df-pn vs the alpha-beta engine
  scripts/dfpn.py cpy [N]        C df-pn vs this Python reference
  scripts/dfpn.py ctwins [CAP]   twin entries on vs off
  scripts/dfpn.py cmilestone [CAP] the gating milestone, C engine
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import tinyhouse as T  # noqa: E402

# A finite sentinel, not float("inf"), and saturating arithmetic below.
# delta(n) is a SUM over children, so the numbers compound with depth; Python
# ints are unbounded, and once one exceeds the float range, comparing it with a
# float infinity raises OverflowError mid-search. A large int plus min() at
# every accumulation keeps the whole thing in integer arithmetic.
INF = 1 << 60

# An unbounded search can nest deeper than CPython's default 1000 frames.
sys.setrecursionlimit(100_000)


def fmt(n):
    return "INF" if n >= INF else f"{n:,}"


class Budget(Exception):
    pass


class DFPN:
    def __init__(self, attacker, node_cap, rep_safe=True, depth_limit=None):
        self.attacker = attacker
        self.cap = node_cap
        # A depth limit turns this back into a bounded mate search: past it the
        # attacker is treated as having failed. That is what the backlog's
        # ~1,949-node figure for the recorded mate in 9 was measured on, and it
        # is NOT the unbounded search the draw claim needs -- the horizon is
        # back, just wearing different clothes. Kept because it validates the
        # algorithm against a known answer.
        self.depth_limit = depth_limit
        self.horizon_hits = 0
        # rep_safe=False stores path-dependent values anyway. UNSOUND under
        # graph-history interaction, and only ever used to separate "df-pn does
        # not work here" from "the conservative GHI rule is what stops it".
        self.rep_safe = rep_safe
        self.tt = {}           # key -> (phi, delta)
        self.nodes = 0
        self.rep_hits = 0
        self.unstorable = 0

    def key(self, pos):
        return (bytes(pos.board), bytes(pos.hands[0]), bytes(pos.hands[1]), pos.stm)

    def terminal(self, pos, is_or):
        """(phi, delta) if this node is terminal, else None."""
        r = pos.result()
        if r is None:
            return None
        # stalemate WINS here, so the side to move wins on r == 1 and loses on -1
        winner = pos.stm if r == 1 else 1 - pos.stm
        proved = winner == self.attacker
        return (0, INF) if proved == is_or else (INF, 0)

    def lookup(self, k):
        return self.tt.get(k, (1, 1))

    def mid(self, pos, phi_th, delta_th, path, depth=0):
        self.nodes += 1
        if self.nodes > self.cap:
            raise Budget()
        k = self.key(pos)
        is_or = pos.stm == self.attacker

        # A terminal is a terminal AT the depth limit too: a mate reached
        # exactly at the limit is a proof, not a failure. Testing the limit
        # first is what stopped a depth-9 search from seeing a mate in 9.
        term = self.terminal(pos, is_or)
        if term:
            self.tt[k] = term
            return term, INF

        if k in path:                       # ancestor repetition: a draw
            self.rep_hits += 1
            # A draw is not a win for the attacker. Report the DEPTH of the
            # ancestor it repeated, not just "tainted": a value is only
            # path-dependent for the nodes at or below that ancestor, exactly
            # the rep_min rule the alpha-beta engine uses on its store side.
            # Tainting everything above would overstate the damage.
            return ((INF, 0) if is_or else (0, INF)), path[k]

        if self.depth_limit is not None and depth >= self.depth_limit:
            self.horizon_hits += 1
            return ((INF, 0) if is_or else (0, INF)), INF

        path[k] = depth
        moves = pos.legal_moves()
        # Values for children that the conservative rule WITHHELD from the
        # global table. They are valid here and only here: within one call of
        # mid the path prefix is fixed, which is exactly the condition their
        # path-dependence is relative to.
        #
        # Without this the algorithm has no progress guarantee at all. df-pn
        # advances by re-reading a child after searching it; a child whose
        # value was not stored reads back as the (1, 1) initial estimate, so the
        # parent picks it again, searches it again, and never terminates. That
        # infinite loop -- not the conservative rule itself -- is what stalled
        # this prototype at 15 table entries over a million nodes.
        local = {}
        rep_min = INF
        while True:
            phi, delta, child_rep, best, best_cp, second_cd, best_key = \
                self.scan(pos, moves, path, local)
            rm = min(rep_min, child_rep)
            if phi >= phi_th or delta >= delta_th:
                path.pop(k, None)
                if rm < depth:
                    self.unstorable += 1
                    if not self.rep_safe:
                        self.tt[k] = (phi, delta)
                else:
                    self.tt[k] = (phi, delta)
                return (phi, delta), rm
            # Descend into the most-proving child: the one with the smallest
            # DELTA. The thresholds passed down use that child's PHI, not its
            # delta -- delta(n) is the sum of the children's phi, so the slack
            # available to this child is delta_th minus what the others already
            # account for.
            child_phi_th = min(delta_th - (delta - best_cp), INF)
            child_delta_th = min(phi_th, second_cd + 1, INF)
            pos.make(best)
            cv, t = self.mid(pos, child_phi_th, child_delta_th, path, depth + 1)
            pos.unmake()
            local[best_key] = cv
            rep_min = min(rep_min, t)

    def scan(self, pos, moves, path, local):
        """One pass over the children: the node's (phi, delta), the shallowest
        ancestor any child repeats, and the most-proving child."""
        phi, delta, rep_min = INF, 0, INF
        best, best_cd, second_cd, best_cp, best_key = None, INF, INF, INF, None
        for m in moves:
            pos.make(m)
            ck = self.key(pos)
            if ck in path:
                # a child that repeats an ancestor is a draw on THIS path, and
                # that is checked before `local` so the taint is not lost
                cphi, cdelta = (INF, 0) if pos.stm == self.attacker else (0, INF)
                rep_min = min(rep_min, path[ck])
                self.rep_hits += 1
            elif ck in local:
                cphi, cdelta = local[ck]
            else:
                cphi, cdelta = self.tt.get(ck, (1, 1))
            pos.unmake()
            phi = min(phi, cdelta)
            delta = min(delta + cphi, INF)      # saturating: never overflow
            if cdelta < best_cd:
                second_cd = best_cd
                best, best_cd, best_cp, best_key = m, cdelta, cphi, ck
            elif cdelta < second_cd:
                second_cd = cdelta
        return phi, delta, rep_min, best, best_cp, second_cd, best_key

    def run(self, pos):
        """Returns (pn, dn) at the root in OR-node terms, i.e. from the
        ATTACKER's point of view, whichever side is to move.

        The root is only written to the table once it is solved, since it is
        searched with infinite thresholds. So on a capped run its numbers are
        recomputed from its children -- otherwise a capped search reports the
        (1, 1) initial estimate and the whole progress signal is invisible.
        """
        path = {}
        try:
            self.mid(pos, INF, INF, path)
        except Budget:
            pass
        k = self.key(pos)
        if k in self.tt:
            phi, delta = self.tt[k]
        else:
            phi, delta = self.scan(pos, pos.legal_moves(), {}, {})[:2]
        return (phi, delta) if pos.stm == self.attacker else (delta, phi)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "mate9"
    if mode == "mate9":
        tfen = "fuwk/3p/P1F1/KWU1[-] b"
        pos = T.Position.from_tfen(tfen)
        print(f"  {tfen}  attacker BLACK, recorded as a mate in 9")
        print("  EXPECTED: PROVED. Anything else means this prototype is not "
              "correct yet.\n")
        for label, kw in (("depth-limited to 9 (a bounded mate search)", dict(depth_limit=9)),
                          ("depth-limited to 9, storing path-dependent values", dict(depth_limit=9, rep_safe=False)),
                          ("UNBOUNDED, rep-safe store", dict()),
                          ("UNBOUNDED, storing path-dependent values (UNSOUND)", dict(rep_safe=False))):
            d = DFPN(attacker=T.BLACK, node_cap=1_000_000, **kw)
            t0 = time.perf_counter()
            pn, dn = d.run(pos)
            st = "PROVED" if pn == 0 else ("DISPROVED" if dn == 0 else "still open")
            print(f"    {label}")
            print(f"      {st:11s} pn={fmt(pn)} dn={fmt(dn)}  nodes {d.nodes:>9,}  tt {len(d.tt):>9,}"
                  f"  path-dependent {d.unstorable:>9,}  {time.perf_counter()-t0:6.1f}s")
    elif mode in ("ccross", "cpy", "ctwins", "cmilestone"):
        import engine_c as E

        st = E.ffi.new("uint64_t[12]")

        def cdfpn(tfen, atk, cap=4_000_000, lim=-1, twins=1, tt=22):
            E.lib.th_dfpn_init(tt)
            v = E.lib.th_dfpn(E.to_c(T.Position.from_tfen(tfen)), atk, cap, lim, twins, st)
            return v, [st[i] for i in range(10)]

        def sample(n, seed=17):
            import random
            random.seed(seed)
            out = []
            while len(out) < n:
                p = T.Position.start()
                for _ in range(random.randrange(1, 14)):
                    ms = p.legal_moves()
                    if not ms:
                        break
                    p.make(random.choice(ms))
                else:
                    if p.legal_moves():
                        out.append(p.tfen())
            return out

        if mode == "ccross":
            n_pos = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            depths = [int(x) for x in (sys.argv[3].split(",") if len(sys.argv) > 3 else ["4", "6", "8", "10"])]
            bm, snd = E.ffi.new("uint16_t *"), E.ffi.new("int *")
            agree = dis = capped = 0
            bad = []
            t0 = time.perf_counter()
            for tfen in sample(n_pos):
                for d in depths:
                    for atk in (0, 1):
                        E.lib.th_tt_init(20)
                        E.lib.th_clear_history()
                        v = E.lib.th_mate_hunt_mt(E.to_c(T.Position.from_tfen(tfen)), d, atk, 1, bm, snd)
                        ab = v > 29000
                        r, s2 = cdfpn(tfen, atk, cap=4_000_000, lim=d)
                        if r == 0:
                            capped += 1
                            continue
                        if (r == 1) == ab:
                            agree += 1
                        else:
                            dis += 1
                            bad.append((tfen, d, atk, v, r))
            print(f"  C df-pn vs alpha-beta: {n_pos} positions x depths {depths} x both "
                  f"colours, {time.perf_counter() - t0:.0f}s")
            print(f"    agree {agree}   DISAGREE {dis}   node cap hit {capped}")
            for b in bad[:5]:
                print(f"      {b}")
            sys.exit(1 if dis else 0)

        if mode == "cpy":
            n_pos = int(sys.argv[2]) if len(sys.argv) > 2 else 25
            agree = dis = capped = 0
            bad = []
            t0 = time.perf_counter()
            for tfen in sample(n_pos, seed=23):
                for d in (4, 6):
                    for atk in (0, 1):
                        r, _ = cdfpn(tfen, atk, cap=2_000_000, lim=d)
                        f = DFPN(attacker=atk, node_cap=200_000, depth_limit=d)
                        pn, dn = f.run(T.Position.from_tfen(tfen))
                        py = 1 if pn == 0 else (-1 if dn == 0 else 0)
                        if r == 0 or py == 0:
                            capped += 1
                        elif r == py:
                            agree += 1
                        else:
                            dis += 1
                            bad.append((tfen, d, atk, r, py))
            print(f"  C df-pn vs the Python reference: {n_pos} positions, "
                  f"{time.perf_counter() - t0:.0f}s")
            print(f"    agree {agree}   DISAGREE {dis}   either capped {capped}")
            for b in bad[:5]:
                print(f"      {b}")
            sys.exit(1 if dis else 0)

        if mode == "ctwins":
            cap = int(sys.argv[2]) if len(sys.argv) > 2 else 4_000_000
            print(f"  Kishimoto-Muller twin entries, on vs off. Cap {cap:,} nodes.\n")
            work = [("recorded mate in 9", "fuwk/3p/P1F1/KWU1[-] b", 1, -1),
                    ("recorded mate in 13", "1uwk/1f1p/PW2/K1UF[-] w", 0, 13),
                    ("no White win after 1.Fd1-c2", "fuwk/3p/P1F1/KWU1[-] b", 0, -1),
                    ("start, White", "fuwk/3p/P3/KWUF[-] w", 0, -1)]
            print(f"  {'case':30s} {'twins':>6s} {'result':>10s} {'nodes':>12s} "
                  f"{'withheld':>10s} {'twin store':>11s} {'twin hits':>11s}")
            for label, tfen, atk, lim in work:
                for tw in (0, 1):
                    t0 = time.perf_counter()
                    r, s2 = cdfpn(tfen, atk, cap=cap, lim=lim, twins=tw)
                    lab = {1: "PROVED", -1: "DISPROVED", 0: "open"}[r]
                    print(f"  {label:30s} {'on' if tw else 'off':>6s} {lab:>10s} "
                          f"{s2[0]:>12,} {s2[7]:>10,} {s2[4]:>11,} {s2[5]:>11,}"
                          f"   {time.perf_counter() - t0:5.1f}s", flush=True)
                print()
            sys.exit(0)

        cap = int(sys.argv[2]) if len(sys.argv) > 2 else 20_000_000
        who = T.WHITE if len(sys.argv) <= 3 else int(sys.argv[3])
        pos = T.Position.start()
        name = "White" if who == T.WHITE else "Black"
        roots = sorted(pos.legal_moves(), key=T.move_str)
        print(f"  milestone (C engine, twins on): df-pn on '{name} forces a win' "
              f"from {pos.tfen()}\n")
        print(f"  {'nodes':>12s} {'resolved':>9s} {'rep leaves':>12s} {'withheld':>10s} "
              f"{'twin hits':>12s}   " + "".join(f"{T.move_str(m):>11s}" for m in roots))
        for budget in (cap // 8, cap // 4, cap // 2, cap):
            E.lib.th_dfpn_init(24)
            v = E.lib.th_dfpn(E.to_c(pos), who, budget, -1, 1, st)
            s2 = [st[i] for i in range(10)]
            cells, done = [], 0
            p2 = T.Position.start()
            for m in roots:
                p2.make(m)
                r2, s3 = cdfpn(p2.tfen(), who, cap=budget // 6, lim=-1, tt=22)
                p2.unmake()
                if r2 == -1:
                    cells.append(f"{'DISPROVED':>11s}"); done += 1
                elif r2 == 1:
                    cells.append(f"{'PROVED':>11s}"); done += 1
                else:
                    cells.append(f"{s3[2]:>11,}")
            print(f"  {s2[0]:>12,} {done:>6d}/{len(roots)} {s2[3]:>12,} {s2[7]:>10,} "
                  f"{s2[5]:>12,}   " + "".join(cells), flush=True)
        print("\n  A dn column that falls is a disproof converging; one that sits still"
              "\n  while the table fills is one that is not.")
        sys.exit(0)

    elif mode == "cross":
        # The real validation. With a depth limit d this answers exactly the
        # question th_mate_hunt(d) answers, so the two engines must agree
        # position by position -- and they share no code beyond the move
        # generator, so agreement is evidence rather than a tautology.
        import random

        import engine_c as E

        n_pos = int(sys.argv[2]) if len(sys.argv) > 2 else 40
        depths = [int(x) for x in (sys.argv[3].split(",") if len(sys.argv) > 3 else ["4", "6"])]
        random.seed(17)
        roots = []
        while len(roots) < n_pos:
            p = T.Position.start()
            for _ in range(random.randrange(1, 14)):
                ms = p.legal_moves()
                if not ms:
                    break
                p.make(random.choice(ms))
            else:
                if p.legal_moves():
                    roots.append(p.tfen())
        bm, snd = E.ffi.new("uint16_t *"), E.ffi.new("int *")
        agree = disagree = capped = 0
        bad = []
        t0 = time.perf_counter()
        for tfen in roots:
            for d in depths:
                for atk in (0, 1):
                    E.lib.th_tt_init(20)
                    E.lib.th_clear_history()
                    v = E.lib.th_mate_hunt_mt(E.to_c(T.Position.from_tfen(tfen)), d, atk, 1, bm, snd)
                    ab = v > 29000
                    f = DFPN(attacker=atk, node_cap=200_000, depth_limit=d)
                    pn, dn = f.run(T.Position.from_tfen(tfen))
                    if pn == 0:
                        got = True
                    elif dn == 0:
                        got = False
                    else:
                        capped += 1
                        continue
                    if got == ab:
                        agree += 1
                    else:
                        disagree += 1
                        bad.append((tfen, d, atk, v, pn, dn))
        print(f"  {len(roots)} positions x depths {depths} x both colours, "
              f"{time.perf_counter() - t0:.0f}s")
        print(f"    agree {agree}   DISAGREE {disagree}   node cap hit {capped}")
        for b in bad[:5]:
            print(f"      {b}")
        sys.exit(1 if disagree else 0)
    else:
        cap = int(sys.argv[2]) if len(sys.argv) > 2 else 400_000
        who = T.WHITE if len(sys.argv) <= 3 else int(sys.argv[3])
        pos = T.Position.start()
        name = "White" if who == T.WHITE else "Black"
        print(f"  milestone: df-pn on '{name} forces a win' from {pos.tfen()}")
        print("  The aggregate root dn is a poor progress signal -- it is a SUM over"
              " root moves,\n  so a move that finishes contributes 0 and the total can"
              " fall for the wrong\n  reason. What converges or does not is the per-move"
              " picture.\n")
        roots = sorted(pos.legal_moves(), key=T.move_str)
        hdr = "".join(f"{T.move_str(m):>11s}" for m in roots)
        print(f"  {'nodes':>10s} {'resolved':>9s} {'rep leaves':>11s} {'withheld':>10s}   {hdr}")
        for budget in (cap // 8, cap // 4, cap // 2, cap):
            d = DFPN(attacker=who, node_cap=budget)
            d.run(T.Position.start())
            cells, done = [], 0
            p2 = T.Position.start()
            for m in roots:
                p2.make(m)
                phi, delta = d.tt.get(d.key(p2), (1, 1))
                cpn, cdn = (phi, delta) if p2.stm == who else (delta, phi)
                p2.unmake()
                if cdn == 0:
                    cells.append(f"{'DISPROVED':>11s}")
                    done += 1
                elif cpn == 0:
                    cells.append(f"{'PROVED':>11s}")
                    done += 1
                else:
                    cells.append(f"{fmt(cdn):>11s}")
            print(f"  {d.nodes:>10,} {done:>6d}/{len(roots)} {d.rep_hits:>11,} "
                  f"{d.unstorable:>10,}   " + "".join(cells), flush=True)
        print("\n  A dn column that falls is a disproof converging; one that sits still"
              "\n  while the table fills is one that is not.")
