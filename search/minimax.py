from core.movegen import MoveGen
from core.evaluator import LearnableEvaluator

# Global evaluator instance
_evaluator = None

def get_evaluator():
    global _evaluator
    if _evaluator is None:
        _evaluator = LearnableEvaluator()
    return _evaluator

def set_evaluator(evaluator):
    global _evaluator
    _evaluator = evaluator

def search_best_move(board, depth):
    evaluator = get_evaluator()
    best_move = None
    best_score = -float('inf')
    alpha = -float('inf')
    beta = float('inf')
    
    moves = MoveGen.generate_legal(board)
    if not moves:
        return None
        
    for move in moves:
        board.make_move(move)
        score = -negamax(board, depth - 1, -beta, -alpha, evaluator)
        board.unmake_move()
        
        if score > best_score:
            best_score = score
            best_move = move
            
        alpha = max(alpha, score)
        
    return best_move

def negamax(board, depth, alpha, beta, evaluator):
    if depth == 0:
        return evaluator.evaluate(board)
        
    moves = MoveGen.generate_legal(board)
    if not moves:
        # Checkmate or Stalemate
        
        # Check if king is attacked
        stm = board.side_to_move
        king_bb = board.bb[stm][5]
        if king_bb == 0: # King captured (shouldn't happen in legal chess)
            return -20000
            
        # Find king square
        lsb = king_bb & -king_bb
        king_sq = lsb.bit_length() - 1
        
        if board.is_square_attacked(king_sq, 1-stm):
            return -20000 + depth # Prefer faster mate
        return 0 # Stalemate
        
    best_score = -float('inf')
    
    for move in moves:
        board.make_move(move)
        score = -negamax(board, depth - 1, -beta, -alpha, evaluator)
        board.unmake_move()
        
        if score > best_score:
            best_score = score
            
        alpha = max(alpha, score)
        if alpha >= beta:
            break
            
    return best_score