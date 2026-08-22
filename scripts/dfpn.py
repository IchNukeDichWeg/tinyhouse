"""df-pn prototype for TH-36. **THIS DOES NOT WORK YET — see STATUS below.**

STATUS: the prototype fails its own validation case. On the recorded mate in 9
(`fuwk/3p/P1F1/KWU1[-] b`, Black to move, independently proven by the alpha-beta
engine at depth 9 under two Zobrist seeds) it does not reach a proof in a
million nodes with the sound store rule, and with the store rule relaxed it
returns DISPROVED in 858 nodes, which is flatly wrong. **Nothing it reports can
be trusted, including its diagnostics.** It is committed as groundwork with the
validation case wired up, not as a working engine, and the TH-36 gating
milestone is BLOCKED on making it pass.

Two candidate causes, and I did not manage to separate them:
  1. a defect in this implementation (thresholds, child selection, or the
     phi/delta frame at AND nodes are the usual suspects);
  2. the conservative graph-history rule genuinely starving the table -- with
     it on, 99.99% of values are withheld as path-dependent and the table
     freezes at 15-71 entries over a million nodes, which is what the backlog
     predicted would happen.
Cause 2 cannot be claimed while cause 1 is open, so it is not claimed.


Why a second engine at all: the alpha-beta search returns an UNSOUND 0 at its
horizon, so a draw is the *absence* of a proof rather than a positive goal. It
can prove a draw only where no line still reaches the horizon, which in practice
means bare kings at depth ~80-100 (see test_solver.py) and nothing resembling
the start position. df-pn has no horizon: every leaf is a terminal or a
repetition, so "not a win" is a thing it can prove directly.

Formulation: phi/delta (Nagai), so the recurrences are uniform across OR and
AND nodes -- phi(n) = min over children of delta(c), delta(n) = sum of phi(c).
An OR node is the attacker to move, an AND node the defender.

GHI: a repetition is path-dependent, so a value that depended on hitting an
ANCESTOR is never stored. Same conservative rule the alpha-beta engine uses on
its store side. Kishimoto-Muller twin entries would recover some of what that
throws away and are the obvious next step; the milestone below is what decides
whether it is worth building.

  scripts/dfpn.py mate9          the validation case (currently FAILS)
  scripts/dfpn.py milestone [N]  root dn against nodes spent, from the start
                                 -- meaningless until mate9 passes
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import tinyhouse as T  # noqa: E402

INF = float("inf")


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

        if self.depth_limit is not None and depth >= self.depth_limit:
            self.horizon_hits += 1
            return ((INF, 0) if is_or else (0, INF)), INF

        if k in path:                       # ancestor repetition: a draw
            self.rep_hits += 1
            # A draw is not a win for the attacker. Report the DEPTH of the
            # ancestor it repeated, not just "tainted": a value is only
            # path-dependent for the nodes at or below that ancestor, exactly
            # the rep_min rule the alpha-beta engine uses on its store side.
            # Tainting everything above would overstate the damage.
            return ((INF, 0) if is_or else (0, INF)), path[k]

        term = self.terminal(pos, is_or)
        if term:
            self.tt[k] = term
            return term, INF

        path[k] = depth
        moves = pos.legal_moves()
        rep_min = INF
        while True:
            phi, delta, child_rep = self.children(pos, moves, path, depth)
            rm = min(rep_min, child_rep)
            if phi >= phi_th or delta >= delta_th:
                path.pop(k, None)
                if rm < depth and self.rep_safe:
                    self.unstorable += 1
                else:
                    if rm < depth:
                        self.unstorable += 1
                    self.tt[k] = (phi, delta)
                return (phi, delta), rm
            # descend into the most-proving child: the one with the smallest
            # DELTA. The thresholds passed down use that child's PHI, not its
            # delta -- delta(n) is the sum of the children's phi, so the slack
            # available to this child is delta_th minus what the others already
            # account for.
            best, best_cd, second_cd, best_cp = None, INF, INF, INF
            for m in moves:
                pos.make(m)
                ck = self.key(pos)
                cphi, cdelta = ((INF, 0) if pos.stm == self.attacker else (0, INF)) \
                    if ck in path else self.lookup(ck)
                pos.unmake()
                if cdelta < best_cd:
                    second_cd = best_cd
                    best, best_cd, best_cp = m, cdelta, cphi
                elif cdelta < second_cd:
                    second_cd = cdelta
            child_phi_th = delta_th - (delta - best_cp)
            child_delta_th = min(phi_th, second_cd + 1)
            pos.make(best)
            _, t = self.mid(pos, child_phi_th, child_delta_th, path, depth + 1)
            pos.unmake()
            rep_min = min(rep_min, t)

    def children(self, pos, moves, path, depth):
        phi, delta, rep_min = INF, 0, INF
        for m in moves:
            pos.make(m)
            ck = self.key(pos)
            if ck in path:
                cphi, cdelta = ((INF, 0) if pos.stm == self.attacker else (0, INF))
                rep_min = min(rep_min, path[ck])
            else:
                cphi, cdelta = self.lookup(ck)
            pos.unmake()
            phi = min(phi, cdelta)
            delta += cphi
        return phi, delta, rep_min

    def run(self, pos):
        """Returns (pn, dn) at the root in OR-node terms, i.e. from the
        ATTACKER's point of view, whichever side is to move."""
        path = {}
        try:
            self.mid(pos, INF, INF, path)
        except Budget:
            pass
        phi, delta = self.tt.get(self.key(pos), (1, 1))
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
            print(f"      {st:11s} pn={pn} dn={dn}  nodes {d.nodes:>9,}  tt {len(d.tt):>9,}"
                  f"  path-dependent {d.unstorable:>9,}  {time.perf_counter()-t0:6.1f}s")
    else:
        cap = int(sys.argv[2]) if len(sys.argv) > 2 else 400_000
        pos = T.Position.start()
        print(f"  milestone: df-pn on 'White forces a win' from {pos.tfen()}")
        print(f"  {'nodes':>10s} {'root pn':>10s} {'root dn':>10s} {'tt':>10s} "
              f"{'rep leaves':>11s} {'withheld':>10s}")
        for budget in (cap // 8, cap // 4, cap // 2, cap):
            d = DFPN(attacker=T.WHITE, node_cap=budget)
            pn, dn = d.run(T.Position.start())
            print(f"  {d.nodes:>10,} {str(pn):>10s} {str(dn):>10s} {len(d.tt):>10,} "
                  f"{d.rep_hits:>11,} {d.unstorable:>10,}", flush=True)
        print("\n  Falling dn would mean the disproof is converging and df-pn is viable")
        print("  for the draw claim; a dn that plateaus while the table fills would mean")
        print("  it is not. Neither reading is available while the validation case fails.")
