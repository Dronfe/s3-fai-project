import os

# Paths
save_dir = "training/checkpoints"
model_path = os.path.join(save_dir, "model.json")
replay_buffer_path = os.path.join(save_dir, "replay_buffer.pkl")

# Training Hyperparameters
games_per_iter = 100        # Games to play per iteration
search_depth = [2]          # Depth for minimax search
exploration_noise = 0.1     # Randomness in self-play

batch_size = 128
train_iters_per_epoch = 200
epochs_per_iteration = 10
learning_rate = 0.0001      # Small LR for stable LMS
max_replay_size = 300000

# Evaluation
eval_games = 20
elo_threshold = 40
