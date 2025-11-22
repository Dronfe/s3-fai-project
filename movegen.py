# === core/movegen.py ===
# Full pseudo-legal and legal move generation

from typing import List

# We'll assume the Board, constants and attack tables are available in scope

class MoveGen:
    @staticmethod
    def generate_pseudo_legal(board: Board) -> List[Move]:
        moves: List[Move] = []
        stm = board.side_to_move
        opp = 1 - stm
        occ = board.occupancies[2]

        # Pawns
        pawns = board.bb[stm][PAWN]
        while pawns:
            pawns, sq = pop_lsb(pawns)
            rank = sq // 8
            if stm == WHITE:
                # single push
                to = sq + 8
                if to < 64 and not bit(occ, to):
                    if to // 8 == 7:
                        # promotions
                        for promo in (QUEEN, ROOK, BISHOP, KNIGHT):
                            moves.append(Move(sq, to, (stm, PAWN), promotion=promo))
                    else:
                        moves.append(Move(sq, to, (stm, PAWN)))
                    # double push
                    if rank == 1:
                        to2 = sq + 16
                        if not bit(occ, to2):
                            moves.append(Move(sq, to2, (stm, PAWN)))
                # captures
                for df in (-1, 1):
                    f = (sq % 8) + df
                    if 0 <= f < 8:
                        t = sq + 8 + df
                        if t < 64:
                            if bit(board.occupancies[opp], t):
                                if t // 8 == 7:
                                    for promo in (QUEEN, ROOK, BISHOP, KNIGHT):
                                        moves.append(Move(sq, t, (stm, PAWN), capture=board.piece_at(t), promotion=promo))
                                else:
                                    moves.append(Move(sq, t, (stm, PAWN), capture=board.piece_at(t)))
                            # en-passant
                            if board.en_passant is not None and t == board.en_passant:
                                moves.append(Move(sq, t, (stm, PAWN), capture=(opp, PAWN), is_en_passant=True))
            else:
                to = sq - 8
                if to >= 0 and not bit(occ, to):
                    if to // 8 == 0:
                        for promo in (QUEEN, ROOK, BISHOP, KNIGHT):
                            moves.append(Move(sq, to, (stm, PAWN), promotion=promo))
                    else:
                        moves.append(Move(sq, to, (stm, PAWN)))
                    if rank == 6:
                        to2 = sq - 16
                        if not bit(occ, to2):
                            moves.append(Move(sq, to2, (stm, PAWN)))
                for df in (-1, 1):
                    f = (sq % 8) + df
                    if 0 <= f < 8:
                        t = sq - 8 + df
                        if t >= 0:
                            if bit(board.occupancies[opp], t):
                                if t // 8 == 0:
                                    for promo in (QUEEN, ROOK, BISHOP, KNIGHT):
                                        moves.append(Move(sq, t, (stm, PAWN), capture=board.piece_at(t), promotion=promo))
                                else:
                                    moves.append(Move(sq, t, (stm, PAWN), capture=board.piece_at(t)))
                            if board.en_passant is not None and t == board.en_passant:
                                moves.append(Move(sq, t, (stm, PAWN), capture=(opp, PAWN), is_en_passant=True))

        # Knights
        knights = board.bb[stm][KNIGHT]
        while knights:
            knights, sq = pop_lsb(knights)
            attacks = KNIGHT_ATTACKS[sq] & ~board.occupancies[stm]
            bb = attacks
            while bb:
                bb, to = pop_lsb(bb)
                cap = board.piece_at(to) if bit(board.occupancies[opp], to) else None
                moves.append(Move(sq, to, (stm, KNIGHT), capture=cap))

        # Kings
        kings = board.bb[stm][KING]
        while kings:
            kings, sq = pop_lsb(kings)
            attacks = KING_ATTACKS[sq] & ~board.occupancies[stm]
            bb = attacks
            while bb:
                bb, to = pop_lsb(bb)
                cap = board.piece_at(to) if bit(board.occupancies[opp], to) else None
                moves.append(Move(sq, to, (stm, KING), capture=cap))
            # castling (pseudo-legal) - basic empty squares check
            if stm == WHITE and sq == sq_index('e1'):
                # king side
                if (board.castling & 1) and not (board.occupancies[2] & ((1<<sq_index('f1')) | (1<<sq_index('g1')))):
                    moves.append(Move(sq, sq_index('g1'), (stm, KING), is_castling=True))
                # queen side
                if (board.castling & 2) and not (board.occupancies[2] & ((1<<sq_index('d1')) | (1<<sq_index('c1')) | (1<<sq_index('b1')))):
                    moves.append(Move(sq, sq_index('c1'), (stm, KING), is_castling=True))
            if stm == BLACK and sq == sq_index('e8'):
                if (board.castling & 4) and not (board.occupancies[2] & ((1<<sq_index('f8')) | (1<<sq_index('g8')))):
                    moves.append(Move(sq, sq_index('g8'), (stm, KING), is_castling=True))
                if (board.castling & 8) and not (board.occupancies[2] & ((1<<sq_index('d8')) | (1<<sq_index('c8')) | (1<<sq_index('b8')))):
                    moves.append(Move(sq, sq_index('c8'), (stm, KING), is_castling=True))

        # Sliding pieces
        for piece_type in (BISHOP, ROOK, QUEEN):
            pieces = board.bb[stm][piece_type]
            while pieces:
                pieces, sq = pop_lsb(pieces)
                if piece_type == BISHOP:
                    dirs = (9, 7, -7, -9)
                elif piece_type == ROOK:
                    dirs = (8, -8, 1, -1)
                else:
                    dirs = (8, -8, 1, -1, 9, 7, -7, -9)
                for d in dirs:
                    cur = sq
                    while True:
                        nxt = cur + d
                        if not (0 <= nxt < 64):
                            break
                        # horizontal wrap check
                        if d in (1, -1) and (nxt // 8) != (cur // 8):
                            break
                        # diagonal wrap prevention
                        if abs((nxt % 8) - (cur % 8)) > 1 and d in (9,7,-7,-9):
                            break
                        cur = nxt
                        if bit(board.occupancies[stm], cur):
                            break
                        cap = board.piece_at(cur) if bit(board.occupancies[opp], cur) else None
                        moves.append(Move(sq, cur, (stm, piece_type), capture=cap))
                        if bit(board.occupancies[opp], cur):
                            break

        return moves

    @staticmethod
    def generate_legal(board: Board) -> List[Move]:
        legal = []
        for m in MoveGen.generate_pseudo_legal(board):
            board.make_move(m)
            # find king of side who just moved
            king_bb = board.bb[1-board.side_to_move][KING]
            if king_bb == 0:
                board.unmake_move(); continue
            _, king_sq = pop_lsb(king_bb)
            if not board.is_square_attacked(king_sq, 1-board.side_to_move):
                # if move was castling, ensure king doesn't pass through check
                if m.is_castling:
                    # squares king passes through
                    if m.to_sq == sq_index('g1'):
                        bad = board.is_square_attacked(sq_index('e1'), 1-board.side_to_move) or board.is_square_attacked(sq_index('f1'), 1-board.side_to_move) or board.is_square_attacked(sq_index('g1'), 1-board.side_to_move)
                        if bad:
                            board.unmake_move(); continue
                    if m.to_sq == sq_index('c1'):
                        bad = board.is_square_attacked(sq_index('e1'), 1-board.side_to_move) or board.is_square_attacked(sq_index('d1'), 1-board.side_to_move) or board.is_square_attacked(sq_index('c1'), 1-board.side_to_move)
                        if bad:
                            board.unmake_move(); continue
                    if m.to_sq == sq_index('g8'):
                        bad = board.is_square_attacked(sq_index('e8'), 1-board.side_to_move) or board.is_square_attacked(sq_index('f8'), 1-board.side_to_move) or board.is_square_attacked(sq_index('g8'), 1-board.side_to_move)
                        if bad:
                            board.unmake_move(); continue
                    if m.to_sq == sq_index('c8'):
                        bad = board.is_square_attacked(sq_index('e8'), 1-board.side_to_move) or board.is_square_attacked(sq_index('d8'), 1-board.side_to_move) or board.is_square_attacked(sq_index('c8'), 1-board.side_to_move)
                        if bad:
                            board.unmake_move(); continue
                legal.append(m)
            board.unmake_move()
        return legal