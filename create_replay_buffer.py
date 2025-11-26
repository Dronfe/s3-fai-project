from training.replay_buffer import ReplayBuffer
from training.selfplay import generate_selfplay_positions
import os

def create_initial_replay_buffer():
    print("Creating initial replay buffer...")
    rb = ReplayBuffer()
    # Generate 10 games for initial buffer
    generate_selfplay_positions(n_games=10, replay_buffer=rb)
    
    os.makedirs("training", exist_ok=True)
    rb.save("training/replay_buffer.pkl")
    print("Initial replay buffer saved to training/replay_buffer.pkl")

if __name__ == "__main__":
    create_initial_replay_buffer()
