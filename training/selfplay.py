import random
import time 
from core.board import Board
from search.minimax import search_best_move 
from core.movegen import MoveGen
from neural_network.encode import encode_board
from training.replay_buffer import ReplayBuffer
from storage.storage_api import save_game 
import logging 
import concurrent.futures
import os

logger=logging.getLogger(__name__)

def play_self_game(max_moves=200,search_depth_white=2,search_depth_black=2,use_randomness=0.0):
    
    """
    Play a single self-play game between identical engines (same search).
    Returns (moves_list_uci, result_value)
    result_value: +1.0 for white win, -1.0 for black win, 0.0 for draw
    """ 
    
    board=Board()
    moves=[]
    
    for ply in range(max_moves):
        stm=board.side_to_move
        depth=search_depth_white if stm==0 else search_depth_black
        
        # Allow little randomness 
        
        legal=MoveGen.generate_legal(board=board)
        if not legal:
            # End the game 
            break
        
        if random.random() <use_randomness:
            mv=random.choice(legal)
        else:
            mv=search_best_move(board,depth)
            if mv is None:
                mv=random.choice(legal)
        
        board.make_move(mv)
        moves.append(mv.uci(lambda x:__import__('core.bitboard',fromlist=['sq_name']).sq_name(x))) 
        
        # find king of side who is now to move  
        king_bb=board.bb[1-board.side_to_move][5]
        
        # Index of king 
        if king_bb==0:
            break
        
    result = 0.0
    # check if side to move has legal moves
    legal = MoveGen.generate_legal(board)
    if not legal:
        winner = 1 - board.side_to_move
        result = 1.0 if winner == 0 else -1.0
    else:
        result = 0.0  
    # save PGN via storage
    try:
        save_game(moves, result="1-0" if result==1.0 else ("0-1" if result==-1.0 else "1/2-1/2"))
    except Exception as e:
        logger.exception("Failed to save game: %s", e)
    return moves, result 



def generate_selfplay_positions(n_games,replay_buffer,depths=(2,2),randomness=0.02):
    
    """
    Generate n_games of self-play and push positions with final outcome into replay buffer.
    Each recorded training sample maps a position -> final game result (z) from white POV.
    """ 
    
    # Use fewer workers than CPU count to avoid overloading if other things are running
    max_workers = max(1, os.cpu_count() - 1)
    
    logger.info(f"Starting {n_games} games with {max_workers} workers...")
    
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(play_self_game, search_depth_white=depths[0], search_depth_black=depths[1], use_randomness=randomness)
            for _ in range(n_games)
        ]
        
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            try:
                moves, result = future.result()
                results.append((moves, result))
                if (i + 1) % 1 == 0:
                    logger.info(f"Completed {i+1}/{n_games} games")
            except Exception as e:
                logger.exception(f"Game generation failed: {e}")

    logger.info(f"All {n_games} games completed. Processing results...")

    for moves, result in results:
        # Replay the game 
        
        board=Board()
        
        for uci in moves:
            enc=encode_board(board,device='cpu')
            
            enc_np=enc.squeeze(0).cpu().numpy() #type: ignore 
            
            val=result 
            replay_buffer.add(enc_np,val)
            
            legal=MoveGen.generate_legal(board=board)
            
            applied=False
            for m in legal:
                if m.uci(lambda x: __import__('core.bitboard', fromlist=['sq_name']).sq_name(x))== uci:
                    board.make_move(m)
                    applied=True 
                    break
            
            if not applied:
                if legal:
                    board.make_move(random.choice(legal))
    
    logger.info(f"Added {len(results)} games to replay buffer")