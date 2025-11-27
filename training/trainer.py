import numpy as np
import logging
from core.evaluator import LearnableEvaluator
from configs.training_config import learning_rate

logger = logging.getLogger(__name__)

class Trainer:
    def __init__(self, replay_buffer, model_path=None):
        self.replay = replay_buffer
        self.evaluator = LearnableEvaluator(weights_path=model_path)
        
    def train_epoch(self, batch_size, iterations, save_path):
        total_error = 0.0
        
        for i in range(iterations):
            X_list, Y_list = self.replay.sample(batch_size)
            
            if not X_list:
                break
            
            X = np.stack(X_list) # (B, W)
            Y = np.array(Y_list) # (B,)
            
            # Prediction
            # Clip Piece Values (0-5) to be positive
            self.evaluator.weights[0:6] = np.maximum(self.evaluator.weights[0:6], 0)
            
            # MSE
            mse = np.mean(error ** 2)
            total_error += mse
            
            if (i + 1) % 50 == 0:
                logger.info(f"Iter {i+1}/{iterations}, MSE: {mse:.4f}")
                
        avg_mse = total_error / max(1, iterations)
        logger.info(f"Training Done. Avg MSE: {avg_mse:.4f}")
        
        self.evaluator.save(save_path)
        return avg_mse