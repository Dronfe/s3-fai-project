import os
import torch

games_per_iter=20
search_depth=(2,2)

# Proabability of making random move during self-play
exploration_noise=0.05 

# Training hyperparameters
batch_size=64
train_iters_per_epoch=200
epochs_per_iteration=2

# Dynamic paths for Colab support
save_dir = os.getenv("SAVE_DIR", "training/checkpoints")
replay_buffer_path = os.path.join(save_dir, "replay_buffer.pkl")
max_replay_size=300000


# Evaluaton
eval_games=50
eval_search_depth=4
# A model is considered as an improvement if it improves by atleast the threshold elo
elo_threshold=40 

# Device detection
device = 'cpu'
if torch.cuda.is_available():
    device = 'cuda'
else:
    try:
        import torch_xla.core.xla_model as xm
        device = xm.xla_device()
    except ImportError:
        pass
