import json
import os
import logging
import numpy as np

logger = logging.getLogger(__name__)

class LearnableEvaluator:
    def __init__(self, weights_path=None):
        # Features: 6 Piece Values + 6*64 PSTs = 390 weights
        self.num_weights = 390
        self.weights = np.zeros(self.num_weights, dtype=np.float32)
        
        if weights_path and os.path.exists(weights_path):
            self.load(weights_path)
        else:
            self._init_defaults()
            
    def _init_defaults(self):
        # Standard Piece Values (Pawns)
        # P=1, N=3.2, B=3.3, R=5, Q=9, K=200
        self.weights[0] = 0.1
        self.weights[1] = 0.32
        self.weights[2] = 0.33
        self.weights[3] = 0.5
        self.weights[4] = 0.9
        self.weights[5] = 20.0
        # PSTs start at 0
        
    def get_features(self, board):
        # Extract sparse features for White
        features = np.zeros(self.num_weights, dtype=np.float32)
        
        for color in [0, 1]: # 0=White, 1=Black
            sign = 1.0 if color == 0 else -1.0
            
            for pt in range(6): # P,N,B,R,Q,K
                bb = board.bb[color][pt]
                idx_val = pt
                idx_pst_start = 6 + pt * 64
                
                while bb:
                    lsb = bb & -bb
                    sq = lsb.bit_length() - 1
                    bb &= bb - 1
                    
                    pst_sq = sq if color == 0 else (sq ^ 56) # Flip for Black
                    
                    features[idx_val] += sign
                    features[idx_pst_start + pst_sq] += sign
                    
        return features

    def evaluate(self, board):
        # Dot product of features and weights
        features = self.get_features(board)
        score = np.dot(features, self.weights)
        
        # Return score from side-to-move perspective
        return score if board.side_to_move == 0 else -score

    def save(self, path):
        try:
            with open(path, 'w') as f:
                json.dump({'weights': self.weights.tolist()}, f)
        except Exception as e:
            logger.error(f"Save failed: {e}")

    def load(self, path):
        try:
            with open(path, 'r') as f:
                self.weights = np.array(json.load(f)['weights'], dtype=np.float32)
        except Exception as e:
            logger.error(f"Load failed: {e}")
