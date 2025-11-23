# nn/evaluate.py
# Exposes nn_evaluate(board) -> int (centipawns), blends NN + classical eval.
import os
from typing import Optional

# lazy import torch/model to avoid hard dependency at Phase-2 runtime
try:
    from .encode import encode_board
    from .model import load_model
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False

# model path & device via env vars (optional)
MODEL_PATH = os.environ.get('CHESS_NN_MODEL', None)
DEVICE = os.environ.get('CHESS_NN_DEVICE', 'cpu')

# lazy-loaded model reference
_MODEL = None
def _get_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if not TORCH_AVAILABLE:
        _MODEL = None
        return None
    try:
        _MODEL = load_model(MODEL_PATH, device=DEVICE)
        return _MODEL
    except Exception:
        _MODEL = None
        return None

def nn_raw_eval(board) -> float:
    """
    Run the NN and return a float score (centipawns).
    Raises RuntimeError if model not available.
    """
    model = _get_model()
    if model is None:
        raise RuntimeError("NN model not available (torch or model failed to load).")
    import torch
    device = DEVICE
    tensor = encode_board(board, device=device)  # shape (1,16,8,8)
    with torch.no_grad():
        out = model(tensor)  # shape (1,) or scalar
        val = float(out.detach().cpu().item())
    return val

def nn_evaluate(board) -> int:
    """
    Blended evaluation: 0.7 * NN + 0.3 * classical_eval(board)
    Returns int centipawns. Falls back safely to classical eval if NN is unavailable.
    """
    # lazy import classical eval to avoid circular imports if search imports nn
    try:
        from search.minimax import evaluate_simple
    except Exception:
        # fallback: minimal material-only evaluator if classical evaluator missing
        def evaluate_simple(b):
            s = 0
            try:
                for color in (0,1):
                    sign = 1 if color == 0 else -1
                    for p in range(6):
                        bb = b.bb[color][p]
                        while bb:
                            lsb = bb & -bb
                            sq = lsb.bit_length() - 1
                            bb &= bb - 1
                            # basic values
                            vals = [100, 320, 330, 500, 900, 20000]
                            s += sign * vals[p]
            except Exception:
                s = 0
            return s

    classical_score = evaluate_simple(board)

    nn_score = None
    try:
        if TORCH_AVAILABLE:
            nn_score = nn_raw_eval(board)
    except Exception:
        nn_score = None

    if nn_score is None:
        # NN failed or not available -> return classical score
        return int(round(classical_score))
    blended = 0.7 * float(nn_score) + 0.3 * float(classical_score)
    return int(round(blended))
