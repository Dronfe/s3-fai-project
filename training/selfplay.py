import random
import logging
import os
import concurrent.futures
from core.board import Board
from search.minimax import search_best_move, get_evaluator
from core.movegen import MoveGen
from training.replay_buffer import ReplayBuffer


logger = logging.getLogger(__name__)

def play_self_game(max_moves=400, depth=2, randomness=0.1, weights=None):
    if weights is not None:
        get_evaluator().weights = weights
        
    board = Board()
    moves = []
    
    for _ in range(max_moves):
        legal = MoveGen.generate_legal(board)
        if not legal:
            break
            
        if random.random() < randomness:
            move = random.choice(legal)
        else:
            move = search_best_move(board, depth)
            if move is None:
                move = random.choice(legal)
                
        board.make_move(move)
        moves.append(move.uci(lambda x: __import__('core.bitboard', fromlist=['sq_name']).sq_name(x)))
        
    # Result
    legal = MoveGen.generate_legal(board)
    result = 0.0
    if not legal:
        # Checkmate or Stalemate
        stm = board.side_to_move
        king_bb = board.bb[stm][5]
        if king_bb != 0:
            lsb = king_bb & -king_bb
            king_sq = lsb.bit_length() - 1
            if board.is_square_attacked(king_sq, 1-stm):
                # Checkmate
                result = 1.0 if stm == 1 else -1.0
            else:
                result = 0.0  # Stalemate
    
    return moves, result

def generate_selfplay_positions(n_games, replay_buffer, depth=2, randomness=0.1, evaluator=None):
    # Use all CPU cores for maximum speed
    max_workers = os.cpu_count() or 4
    logger.info(f"Generating {n_games} games with {max_workers} workers...")
    
    weights = evaluator.weights if evaluator else get_evaluator().weights
    
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(play_self_game, 400, depth, randomness, weights)
            for _ in range(n_games)
        ]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                logger.error(f"Game failed: {e}")
                
    # Stats
    w_wins = sum(1 for _, r in results if r == 1.0)
    b_wins = sum(1 for _, r in results if r == -1.0)
    draws = sum(1 for _, r in results if r == 0.0)
    logger.info(f"Results: White={w_wins}, Black={b_wins}, Draws={draws}")
    
    # Process to Replay Buffer
    if evaluator is None:
        evaluator = get_evaluator()
        
    count = 0
    for moves, result in results:
        board = Board()
        for uci in moves:
            features = evaluator.get_features(board)
            
            # Target: White Win = +1, Black Win = -1
            target = result * 1.0
            if board.side_to_move == 1:  # Black
                target = -target
                
            replay_buffer.add(features, target)
            count += 1
            
            # Replay move
            legal = MoveGen.generate_legal(board)
            for m in legal:
                if m.uci(lambda x: __import__('core.bitboard', fromlist=['sq_name']).sq_name(x)) == uci:
                    board.make_move(m)
                    break
                    
    logger.info(f"Added {count} positions to replay buffer.")