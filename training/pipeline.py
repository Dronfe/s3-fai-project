import logging
import os
import time
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.evaluator import LearnableEvaluator
from training.selfplay import generate_selfplay_positions
from training.trainer import Trainer
from training.replay_buffer import ReplayBuffer
import configs.training_config as cfg

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("training.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TrainingPipeline:
    def __init__(self):
        self.evaluator = LearnableEvaluator(weights_path=cfg.model_path)
        self.replay_buffer = ReplayBuffer(capacity=cfg.max_replay_size)
        self.trainer = Trainer(self.replay_buffer, model_path=cfg.model_path)
        
        # Ensure directories exist
        os.makedirs(cfg.save_dir, exist_ok=True)
        
    def run(self):
        logger.info("Starting Training Pipeline...")
        logger.info(f"Config: Games/Iter={cfg.games_per_iter}, Epochs/Iter={cfg.epochs_per_iteration}, LR={cfg.learning_rate}")
        
        for iteration in range(1, 151): # Run for 150 iterations
            start_time = time.time()
            logger.info(f"\n=== Iteration {iteration} ===")
            
            # 1. Self-Play
            logger.info("Phase 1: Self-Play Data Collection")
            generate_selfplay_positions(
                n_games=cfg.games_per_iter,
                replay_buffer=self.replay_buffer,
                depth=cfg.search_depth[0],
                randomness=cfg.exploration_noise,
                evaluator=self.evaluator
            )
            
            # 2. Training
            logger.info(f"Phase 2: Training (Buffer Size: {len(self.replay_buffer)})")
            if len(self.replay_buffer) < cfg.batch_size:
                logger.warning("Not enough data to train yet. Skipping.")
                continue
                
            avg_mse = self.trainer.train_epoch(
                batch_size=cfg.batch_size,
                iterations=cfg.train_iters_per_epoch,
                save_path=cfg.model_path
            )
            
            # 3. Logging
            duration = time.time() - start_time
            logger.info(f"")
            logger.info(f"=" * 60)
            logger.info(f"ITERATION {iteration} SUMMARY")
            logger.info(f"=" * 60)
            logger.info(f"Duration: {duration:.1f}s ({duration/60:.1f} min)")
            logger.info(f"Average MSE: {avg_mse:.6f}")
            logger.info(f"Buffer Size: {len(self.replay_buffer)}")
            logger.info(f"=" * 60)
            logger.info(f"")
            
            # Save Checkpoint
            checkpoint_path = os.path.join(cfg.save_dir, f"model_iter_{iteration}.json")
            self.evaluator.save(checkpoint_path)
            
if __name__ == "__main__":
    pipeline = TrainingPipeline()
    pipeline.run()