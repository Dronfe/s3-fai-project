import os 
import logging
import time 
from pathlib import Path
import sys
import shutil 
# Ensure project root is on sys.path when running this module as a script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from configs.training_config import * 

# Compatibility for potential typos or old config versions
if 'max_replay_size' not in globals() and 'nax_replay_size' in globals():
    max_replay_size = nax_replay_size
if 'eval_games' not in globals() and 'exal_games' in globals():
    eval_games = exal_games 
from training.replay_buffer import ReplayBuffer
from training.selfplay import generate_selfplay_positions
from training.trainer import Trainer
from training.evaluator import evaluate_models 
import torch
from neural_network.model import SmallEvalNet,load_model 


logger=logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TrainingPipeline:
    def __init__(self,config_module=None):
        self.cfg=globals()
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        self.replay=ReplayBuffer(capacity=max_replay_size)
        
        self.iteration_id=0
        self.best_model_path=os.path.join(save_dir,"best_model.pth")
        
        self.latest_model_path=os.path.join(save_dir,"latest_model.pth")
        
        # Creating the initial model 
        if not os.path.exists(self.latest_model_path): 
            m = SmallEvalNet(in_channels=16)
            torch.save(m.state_dict(), self.latest_model_path)
            shutil.copy(self.latest_model_path, self.best_model_path)
            
    def iteration(self):
        self.iteration_id+=1
        it=self.iteration_id
        logger.info(f"=== Starting training iteration {it} ===") 
        
        # Generate self play
        games_to_gen=games_per_iter
        logger.info(f"Generating {games_to_gen} self-play games (depths {str(search_depth)}, noise={exploration_noise})...")
        
        generate_selfplay_positions(n_games=games_to_gen,replay_buffer=self.replay,depths=search_depth,randomness=exploration_noise)
        
        logger.info(f"Replay buffer size after generation: {len(self.replay)}")
        
        # Saving a snapshot of each game 
        replay_path = os.path.join(save_dir, f"replay_iter_{it}.pkl")
        
        try:
            self.replay.save(replay_path)
            logger.info(f"Saved replay buffer to {replay_path}")
        except Exception as e:
            logger.exception(f"Failed to save replay buffer: {e}")
            
            
        # Training the model 
        
        logger.info(f"Training candidate model for {epochs_per_iteration} epochs (iters/epoch={train_iters_per_epoch})...")
        
        trainer=Trainer(model_path=self.latest_model_path,replay_buffer=self.replay,device=device)
        candidate_path=os.path.join(save_dir,f"candidate_iter_{it}.pt")
        
        trainer.train_epoch(batch_size=batch_size,iterations=train_iters_per_epoch,save_path=candidate_path)
        
        
        # Evaluating both models 
        
        logger.info("Evaluating candidate vs current latest model...")
        
        old_model=self.latest_model_path
        new_model=candidate_path
        score_old,score_new,elo_diff=evaluate_models(old_model,new_model,eval_games,eval_search_depth) 
        logger.info(f"Evaluation: old_score={score_old} new_score={score_new} elo_diff={elo_diff}") 
        
        promoted=False
        if elo_diff>=elo_threshold:
            promoted=True 
            
            # update the copies 
            shutil.copy(new_model, self.latest_model_path)
            shutil.copy(new_model, self.best_model_path) 
            
            logger.info(f"Promoted candidate to latest and best (elo_diff={elo_diff} >= {elo_threshold}).")
            
        else:
            # if the elo improvement is not met reject it 
            
            reject_path=os.path.join(save_dir,f"rejected_iter_{it}.pth") 
            shutil.copy(new_model,reject_path)
            logger.info(f"Candidate rejected (elo_diff={elo_diff} < {elo_threshold}). Saved to {reject_path}")
            
        return {
            "iteration": it,
            "games_generated": games_to_gen,
            "replay_size": len(self.replay),
            "elo_diff": elo_diff,
            "promoted": promoted,
            "candidate_path": candidate_path
        } 
        
    
    def run_forever(self,sleep_between_iters=5):
        try:
            while True:
                info=self.iteration()
                logger.info(f"Iteration finished: {info}")
                time.sleep(sleep_between_iters)
        except KeyboardInterrupt:
            logger.info("Pipeline interrupted by user. Exiting cleanly.")
            
if __name__ == "__main__":
    p = TrainingPipeline()
    p.run_forever()