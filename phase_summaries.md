Context:
I have completed Phase 1 (core engine) and Phase 2 (MinMax search module).
My engine now supports:

Full bitboard board representation

Legal move generation

Make/unmake with snapshots

Zobrist hashing

Negamax + alpha-beta

Iterative deepening

Move ordering (TT move, MVV-LVA, killer, history)

Transposition table

Simple classical evaluation

Now I want to replace/augment the classical evaluation with a neural-network-based evaluation function, while keeping MinMax as the final decision-maker.

Your Task — Build Phase 3: Neural Evaluation Integration

Integrate a neural network–based evaluation into the existing search pipeline.
Follow this file structure:

nn/
    model.py
    encode.py
    evaluate.py

Requirements
1. Position Encoding (encode.py)

Implement a function that converts the current Board object into NN input tensors:

12 piece planes (one per piece type × color) → shape: (12, 8, 8)

Side-to-move plane

Castling rights plane

En-passant plane

Optional: move count / halfmove clocks

Return a PyTorch tensor ready for inference.

2. Neural Network Model (model.py)

Implement a small convolutional or residual network that outputs a single scalar evaluation in centipawns.

Requirements:

Input: the encoded tensor

Architecture: simple CNN or ResNet block

Output: single float → scaled to centipawns

GPU-optional, CPU-compatible

Provide load_model() to load weights once at startup

3. Evaluation Integration (evaluate.py)

Create a module that:

Provides a function:

def nn_evaluate(board: Board) -> int


Calls the encoder and model

Converts the NN output to an integer score

Blends NN score with classical score:

final = int(0.7 * nn_eval + 0.3 * classical_eval(board))


Is drop-in replaceable inside Phase-2 search

Must NOT modify MinMax, only plug into evaluation calls

4. Search Integration

Modify Phase 2’s evaluation logic so that:

When depth == 0 → use the blended NN evaluation

Quiescence still uses classical eval (NN optional there)

Everything else remains the same

5. Code Style

Do not rewrite Phase 1 or Phase 2 code

Keep all NN logic inside the nn/ folder

Functions must be modular, clean, and friendly for future training (Phase 6/7)

Deliverables

Provide full code for:

nn/encode.py

nn/model.py

nn/evaluate.py

Instructions on exactly where to call nn_evaluate() in the search code 