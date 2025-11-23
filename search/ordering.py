#ordering.py
# Move ordering utilities: TT move, MVV-LVA, killer moves, history heuristic.
from typing import List, Optional, Tuple, Dict
from core.move import Move
from core.bitboard import pawn, knight, bishop, rook, queen, king

# Piece values for MVV-LVA and evaluation tie-ins
PIECE_VALUE = {
    pawn: 100,
    knight: 320,
    bishop: 330,
    rook: 500,
    queen: 900,
    king: 20000
}

class MoveOrderer:
    def __init__(self, max_depth: int = 64):
        # killer[ply][0..1] -> store up to 2 killer moves per ply
        self.max_depth = max_depth
        self.killer: List[List[Optional[Tuple[int,int,int]]]] = [[None, None] for _ in range(max_depth)]
        # history[(from,to,prom)] = score
        self.history: Dict[Tuple[int,int,Optional[int]], int] = {}

    def clear(self):
        self.killer = [[None, None] for _ in range(self.max_depth)]
        self.history.clear()

    def record_killer(self, move: Move, ply: int):
        key = (move.from_sq, move.to_sq, move.promotion)
        if ply >= len(self.killer):
            return
        if self.killer[ply][0] == key:
            return
        # push into first slot, shift old to second
        self.killer[ply][1] = self.killer[ply][0]
        self.killer[ply][0] = key

    def record_history(self, move: Move, depth: int):
        key = (move.from_sq, move.to_sq, move.promotion)
        # increment by depth^2 to prefer deeper successes
        self.history[key] = self.history.get(key, 0) + (depth * depth)

    def mvv_lva_score(self, move: Move) -> int:
        """
        Higher score for captures where victim is valuable and attacker is cheap.
        We'll invert to higher-is-better.
        """
        if move.capture is None:
            return 0
        victim = move.capture[1]
        attacker = move.piece[1]
        return (PIECE_VALUE[victim] * 10) - PIECE_VALUE[attacker]

    def score_move(self, move: Move, ply: int, tt_move: Optional[Move]) -> int:
        """
        Produce a composite integer score where higher means search earlier.
        Order: TT best -> captures (MVV-LVA) -> killer -> history -> quiet
        """
        # 1) TT move highest priority
        if tt_move is not None and (move.from_sq, move.to_sq, move.promotion) == (tt_move.from_sq, tt_move.to_sq, tt_move.promotion):
            return 10_000_000

        # 2) Captures: MVV-LVA
        mvv = self.mvv_lva_score(move)
        if mvv:
            return 5_000_000 + mvv  # keep captures above killers/history

        # 3) Killer moves
        key = (move.from_sq, move.to_sq, move.promotion)
        if ply < len(self.killer):
            if self.killer[ply][0] == key:
                return 4_000_000
            if self.killer[ply][1] == key:
                return 3_900_000

        # 4) History heuristic
        hist = self.history.get(key, 0)
        if hist:
            return 1000 + hist

        # 5) Quiet move fallback (prefer captures/more interesting)
        return 0

    def order_moves(self, moves: List[Move], ply: int, tt_move: Optional[Move]) -> List[Move]:
        """
        Return moves sorted descending by score (best first).
        """
        scored = [(self.score_move(m, ply, tt_move), m) for m in moves]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]