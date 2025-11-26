import math 
import logging 
from core.board import Board 
from core.movegen import MoveGen
from search.minimax import search_best_move 
from neural_network.model import load_model 
import neural_network.evaluate as nn_evaluate_module 
from configs.training_config import device

logger=logging.getLogger(__name__)

def _safe_elo_from_score(score,eps=1e-8):
    """
    Given observed score S (0..1) for the 'new' model, estimate Elo difference D:
    Clip S to avoid division by zero.
    Returns D (positive => new model stronger).
    """ 
    
    s=min(max(score,eps),1.0-eps)
    return 400.0*math.log10(s/(1.0-s))

def evaluate_models_head_to_head(old_model_path,new_model_path,n_games,depth):
    """
    Play `n_games` games between old and new models. Alternate colors each game.
    Each move is chosen by the engine for the side to move using that side's model (we swap active model
    before calling search_best_move).
    """ 
    
    new_model=None
    old_model=None
    
    try:
        new_model=load_model(new_model_path,device=device)
    except Exception as e:
        logger.exception(f"Failed to load new model {new_model_path}:{e}")
    
    
    try:
        old_model=load_model(old_model_path,device=device)
    except Exception as e:
        logger.exception(f"Failed to load old model {old_model_path}:{e}")
        
        
    prev_model=getattr(nn_evaluate_module,"_model",None) 
    
    points_new=0.0
    points_old=0.0 
    
    
    for g in range(n_games):
        board=Board()
        
        # Determining which color the models play in the current game 
        
        new_is_white=(g%2==0)
        
        # Playing the gane 
        
        move_c=0
        
        while move_c<1000:
            #0 is white and 1 is black
            stm=board.side_to_move 
            
            if (stm==0 and new_is_white) or (stm==1 and not new_is_white):
                
                # Move of new model
                nn_evaluate_module._model=new_model 
                
                # Search depth 
                chosen=search_best_move(board=board,depth=depth)
            else:
                nn_evaluate_module._model=old_model
                chosen=search_best_move(board=board,depth=depth)
                
            
            if chosen is None:
                # if no move is done then it is a checkmate or stalemate
                break 
            board.make_move(chosen)
            move_c+=1
            legal_after=MoveGen.generate_legal(board=board)
            if not legal_after:
                break 
            
        # If game is finished detect the result 
        legal_now=MoveGen.generate_legal(board=board)
        if not legal_now:
            
            # side to move has no legal moves -> checkmate or stalemate
            # if side to move is in check -> previous player delivered mate 
            king_bb=board.bb[1-board.side_to_move][5]
            if king_bb==0:
                # If there is no king treat it as a draw 
                Winner=None 
            else:
                if board.is_square_attacked(king_bb,1-board.side_to_move):
                    # If checkmate the winner is previous side 
                    winner_side=1-board.side_to_move
                    
                    # Determine the winner 
                    
                    if (winner_side==0 and new_is_white) or (winner_side==1 and not new_is_white):
                        points_new+=1.0
                    else:
                        points_old+=1.0
                
                else:
                    # If it is stalemate 
                    points_old+=0.5
                    points_new+=0.5
        else:
            # If move limit is reached treat as draw 
            points_new+=0.5
            points_old+=0.5
    
    # Restoring the previous model
    nn_evaluate_module._model = prev_model
    
    total=points_old+points_new 
    
    # total should equal n_games
    
    score_new_frac = points_new / max(1.0, (points_new + points_old))
    # score_old_frac = points_old / max(1.0, (points_new + points_old))
    elo_diff = _safe_elo_from_score(score_new_frac)
    return {
        "score_old": float(points_old),
        "score_new": float(points_new),
        "elo_diff": float(elo_diff)
    }