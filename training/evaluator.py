import logging 
from training import elo 

logger=logging.getLogger(__name__)


def evaluate_models(old_model_path,new_model_path,n_games,depth):
    
    """
    Wrapper that calls the training functions
    """ 
    
    logger.info(f"Evaluating models: old={old_model_path} new={new_model_path} games={n_games} depth={depth}")
    
    res = elo.evaluate_models_head_to_head(old_model_path, new_model_path, n_games, depth)
    logger.info(f"Evaluation result: {res}") 
    
    
    return res["score_old"], res["score_new"], res["elo_diff"]