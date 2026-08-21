# Tinyhouse — Rules Specification

Tinyhouse is a 2-player chess variant on the chess.com Variants server (4PC engine),
created by @chye3mc, accepted 2023-04-24. Chess.com rule string (authoritative):

```
Crazyhouse EnPassant Play4Mate PromoteTo=FUW Prom=9 Stalemate=win
```

Sources, in order of authority:

1. The chess.com rule string above and a real chess.com game (ground truth).
2. Chess.com club forum post by the creator: <https://www.chess.com/clubs/forum/view/wof-tinyhouse>
   (rules summary, `promotedFrom` semantics, 2025 rule-change note on horse-check drops).
3. Chess.com Variants Wiki: <https://chess-variants.fandom.com/wiki/Tinyhouse> plus its
   Crazyhouse / Stalemate / Hors / Ferz / Wazir / Pawn / FEN4 pages (documents the same engine).

Empirical verification on chess.com itself was **not possible**: the Variants server
(play, game viewer, analysis board) is fully login-gated for anonymous visitors, and this
session cannot create accounts or enter credentials. Everything below is marked
VERIFIED (stated verbatim by a source) or INFERRED (derived; evidence given).

## Board and coordinates

- 4x4 board, files `a-d`, ranks `1-4`. White plays up (toward rank 4), Black down.
- On chess.com the board is embedded in the 4PC 14x14 grid at files f-i, ranks 6-9
  (VERIFIED via the wiki's FEN4). Absolute rank 9 = the small board's rank 4.
  `Prom=9` therefore means: each side promotes on the opponent's back rank
  (White on rank 4, Black on rank 1). VERIFIED, matches the wiki infobox
  "Pawns promote to FWU on the 9th rank".

## Starting position

```
4  f u w k        (black: Ferz a4, Horse b4, Wazir c4, King d4)
3  . . . p        (black Pawn d3)
2  P . . .        (white Pawn a2)
1  K W U F        (white: King a1, Wazir b1, Horse c1, Ferz d1)
   a b c d        White to move
```

VERIFIED: wiki FEN4 (rP=white, yP=black in FEN4 colors) and the prompt's ground truth agree.
The originally submitted position carried a stray `'promotedFrom':{'g6':'P'}` tag (white
Wazir b1 marked as promoted); the accepted version removed it (VERIFIED, forum post #3).
Position is symmetric under 180-degree rotation + color swap.

## Pieces and movement

| Piece | Letter | Moves |
|---|---|---|
| King | K | 1 step any direction. Cannot move into check. No castling (none possible/configured). |
| Ferz | F | 1 step diagonally. |
| Wazir | W | 1 step orthogonally. |
| Xiangqi Horse (mao) | U | Knight-shaped (2,1) move executed as 1 step orthogonal then 1 step diagonally outward. **Blocked** if the orthogonal step square is occupied (by either color). It does not attack the blocking square itself. |
| Pawn | P | 1 step straight forward to an empty square; captures 1 step diagonally forward. See below for double-step. |

All VERIFIED against the wiki piece pages (Hors: "(2,1) leaper, the orthogonal square has
to be empty"; Ferz "(1,1)"; Wazir "(1,0)"; Pawn "moves forward as a Wazir and captures
forward as a Ferz").

A mao check can be answered by dropping (or moving) a piece onto the horse's orthogonal
step square — that blocks the check. VERIFIED: forum post #12 (Sep 2025): "there has been
a change in the rules, one can block a check from the horse by dropping a piece."
(Earlier server behavior apparently disallowed this; current behavior allows it. We
implement current behavior.)

## Crazyhouse rules

VERIFIED (wiki Crazyhouse page, which documents the variants-server implementation):

- A captured piece switches color and goes to the capturer's hand ("bank").
- Instead of a board move, a player may **drop** a hand piece on any **empty** square;
  this counts as the move.
- **Pawns may not be dropped on the first or last rank** (here: ranks 1 and 4, both colors).
- A **promoted piece is captured as a pawn**: it enters the capturer's hand as a pawn,
  not as the piece it promoted to (the `promotedFrom` FEN4 tag tracks this; VERIFIED
  additionally by forum post #8).
- Drops may give check and checkmate (drop mates appear in the wiki's own Minihouse
  lines, e.g. `@Rf7#`). Drops may block checks. Kings are never in hand.
- Dropping is legal only if the resulting position leaves the mover's king out of
  check (a drop can never expose one's own king — adding a blocker never creates a
  mao attack — so when not in check, any-empty-square drops are always legal).

## Pawns: promotion, double-step, en passant

- **Promotion is forced** on reaching the last rank, to Ferz, Xiangqi Horse or Wazir
  only (`PromoteTo=FUW`; `U` = horse). VERIFIED: wiki "it must be promoted to a wazir,
  a ferz or a xiangqi horse"; forum "Promotion: Ferz, Xiangqi Horse, Wazir on the 9th rank".
  The promoted piece carries a *promoted* mark (see reversion rule above).
- **Double-step: INFERRED ABSENT.** The `EnPassant` tag is in the rule string, but the
  engine grants the double move only to pawns on their *base rank*, and:
  - the separate `PawnBaseRank` tag is absent from Tinyhouse's rule string, so the
    default applies — the 14x14 board's own 2nd rank from each player's edge, which
    lies outside the embedded 4x4 (the pawns live on absolute ranks 7-8);
  - the wiki Crazyhouse page's "Pawn dropped on 2nd rank can double move" refers to
    the embedded standard 8x8 board where base ranks exist inside the board.
  We therefore implement **no double-step** as the primary rule, with a visible
  `DOUBLE_STEP` toggle in the engine to quantify the alternative (a double-step here
  would land on the promotion rank and promote immediately).
  UNVERIFIED empirically; the login wall blocked the direct test.
- **En passant is provably dead either way.** An ep capture of a White double-step
  (a2-a4 etc.) would require a Black pawn on rank 4 attacking the passed rank-3 square.
  Black pawns can never be on rank 4: pawn drops are barred from ranks 1/4, Black pawns
  move down, and a Black pawn arriving on rank 1 promotes. Symmetrically for Black's
  double-step. So no ep capture is ever legal, regardless of the double-step question,
  and the engine carries **no ep state**. (This is why the `EnPassant` tag is inert.)

## Check, mate, stalemate, draws

- Standard check rules; king capture never occurs (moves into check are illegal).
- **Checkmate: the checkmated player loses** (`Play4Mate` = win by checkmate, no points).
- **Stalemate: the STALEMATED player WINS** (`Stalemate=win`). VERIFIED three times:
  rule string; wiki infobox tooltip "The stalemated player wins"; wiki Stalemate page
  "Stalemate Win results in a Win for the stalemated player"; forum "Gamerules:
  Stalemate Wins". Note: stalemate requires an empty hand — with any piece in hand and
  the mover not in check, a drop is always available (>= 6 empty squares always exist).
- **Repetition: draw.** Chess.com standard threefold repetition (position = board +
  promoted marks + hands + side to move). For solving we treat any forced infinite play
  as a draw (value iteration semantics); this is the standard convention and matches
  threefold in practice. INFERRED (server behavior not directly testable).
- **50-move rule:** the FEN4 spec carries a halfmove clock "used to determine if a draw
  can be claimed under the fifty-move rule". Claim-based and practically irrelevant here
  (captures/pawn moves/promotions dominate; repetition triggers far earlier in quiet
  lines). NOT implemented in the solver; documented simplification.
- No other draw sources: insufficient material cannot occur (material never leaves the
  game in Crazyhouse).

## Discrepancies between sources

| Point | chess.com (wins) | wiki |
|---|---|---|
| En passant tag | `EnPassant` present in rule string | Not shown in infobox gamerules (stub); moot — ep is dead (see above) |
| Stalemate | `Stalemate=win` | Article prose says only "checkmate your opponent"; infobox tooltip does state stalemated player wins |
| Time control | Forum: 45 sec | Infobox: 1+1 (irrelevant to rules) |

## State space and solvability

`scripts/state_count.py` counts syntactically legal states exactly (kings non-adjacent,
pawns confined to ranks 2-3, promoted marks only on the two pawn-origin units, hands as
multisets of raw types, side to move):

- **Upper bound: 17,669,515,462,968 (~1.8e13)** states; ~4.4e12 after factoring the
  4-element symmetry group (file mirror x color-flip rotation).
- Not counted: side-not-to-move-in-check exclusion and reachability, so the true
  reachable count is smaller, but even 0.1% reachability leaves ~1.8e10 states.

**Verdict: a full strong solve (retrograde DB over all states) is infeasible** on a
desktop — 4.4e12 slots at even 2 bits is >1 TB before indexing, and crazyhouse has no
material-based decomposition into subgames (material never leaves play, so there are no
small endgame classes to seed a retrograde pass). The realistic target is a **weak solve
of the starting position** via proof-number search (drops make the game sharp; forced
wins, if present, should be shallow), falling back to a strong engine. Phase 4 reports
which tier was reached.
