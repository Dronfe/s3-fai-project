import os
import time
import logging
from pathlib import Path
from typing import Optional
import shutil

from configs.training_config import *
from training.replay_buffer import ReplayBuffer
from training.selfplay import generate_selfplay_positions
from training.trainer import Trainer
from training.evaluator import evaluate_models

from neural_network.model import SmallEvalNet, load_model

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TrainingPipeline:
    def __init__(self, config_module=None):
        # load configuration constants from module-level names
        self.cfg = globals()
        # ensure checkpoint dir exists
        Path(MODEL_SAVE_DIR).mkdir(parents=True, exist_ok=True)
        # replay buffer
        self.replay = ReplayBuffer(capacity=MAX_REPLAY_SIZE)
        # iteration counter
        self.iteration_idx = 0
        # track best model path
        self.best_model_path = os.path.join(MODEL_SAVE_DIR, "best_model.pt")
        self.latest_model_path = os.path.join(MODEL_SAVE_DIR, "latest_model.pt")
        # create initial model if not present
        if not os.path.exists(self.latest_model_path):
            logger.info("No existing latest model found — creating fresh model.")
            # save initial model
            import torch
            # also seed best_model with same
            shutil.copy(self.latest_model_path, self.best_model_path)

    def iteration(self):
        self.iteration_idx += 1
        it = self.iteration_idx
        logger.info("=== Starting training iteration %d ===", it)

        # 1) Self-play generation
        games_to_gen = SELFPLAY_GAMES_PER_ITER
        logger.info("Generating %d self-play games (depths %s, noise=%.3f)...", games_to_gen, str(SEARCH_DEPTH_SELFPLAY), EXPLORATION_NOISE)
        # generate_selfplay_positions pushes encoded positions into replay_buffer
        generate_selfplay_positions(n_games=games_to_gen, replay_buffer=self.replay, depths=SEARCH_DEPTH_SELFPLAY, randomness=EXPLORATION_NOISE)

        # Save replay buffer snapshot
        try:
            self.replay.save(replay_path)
        except Exception as e:
            logger.exception("Failed to save replay buffer: %s", e)

        # 2) Training
        trainer = Trainer(self.replay, device=DEVICE)
        candidate_path = os.path.join(MODEL_SAVE_DIR, f"candidate_iter_{it}.pt")
        trainer.train_epoch(batch_size=BATCH_SIZE, iterations=TRAIN_ITERS_PER_EPOCH, save_path=candidate_path)

        # 3) Evaluation (model vs model)
        old_model = self.latest_model_path
        new_model = candidate_path
        score_old, score_new, elo_diff = evaluate_models(old_model, new_model, EVAL_GAMES, EVAL_SEARCH_DEPTH)

        promoted = False
        if elo_diff >= ELO_THRESHOLD:
            # promote
            promoted = True
            # update best/latest copies
            shutil.copy(new_model, self.latest_model_path)
            shutil.copy(new_model, self.best_model_path)
            logger.info("Promoted candidate to latest and best (elo_diff=%.2f >= %d).", elo_diff, ELO_THRESHOLD)
        else:
            # reject candidate (keep for records)
            rejected_path = os.path.join(MODEL_SAVE_DIR, f"rejected_iter_{it}.pt")
            shutil.copy(new_model, rejected_path)
            logger.info("Candidate rejected (elo_diff=%.2f < %d). Saved to %s", elo_diff, ELO_THRESHOLD, rejected_path)

        # logging summary
        logger.info("Iteration %d summary: games=%d samples=%d elo_diff=%.2f promoted=%s", it, games_to_gen, len(self.replay), elo_diff, promoted)
        return {
            "iteration": it,
            "games_generated": games_to_gen,
            "replay_size": len(self.replay),
            "elo_diff": elo_diff,
            "promoted": promoted,
            "candidate_path": candidate_path
        }

    def run_forever(self, sleep_between_iters: int = 5):
        try:
            while True:
                info = self.iteration()
                logger.info("Iteration finished: %s", info)
                time.sleep(sleep_between_iters)
        except KeyboardInterrupt:
            logger.info("Pipeline interrupted by user. Exiting cleanly.")

if __name__ == "__main__":
    p = TrainingPipeline()
    p.run_forever()
