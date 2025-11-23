# Chess System Engineering Plan

A hybrid chess engine with MinMax search and neural-network evaluations.

---

## Phase 1 — Core Engine

The brainstem of the system — handles all heavy lifting.

### What you build

- Bitboard-based representation for all 12 pieces
- Full game state tracking (castling, en-passant, move clocks)
- Zobrist hashing + transposition tables
- Pseudo-legal → legal move generation pipeline
- Special rules: castling, en-passant, promotions
- Check/mate/draw detection

### Search system

- MinMax + alpha-beta
- Iterative deepening
- Quiescence search
- Move ordering (TT move → captures → killers/history)

### Extras

- FEN parser
- SAN move generator
- Small lightweight opening book

## Phase 2 — Neural Network Integration

The "positional intuition module" — gives the bot strategic understanding beyond pure tactics.

### What you build

- NN input encoding (12 piece planes + metadata)
- Convolution-based architecture → scalar evaluation
- Output normalized to centipawns
- Hybrid evaluation: NN score + classical material score
- Backend function `nn_evaluate(fen)` integrated into MinMax leaf nodes

## Phase 3 — Backend Engine API (Flask)

Connects the thinking machine to the user interface.

### What you build

### Endpoints

- `POST /start_game`
- `POST /make_move`
- `POST /bot_move`
- `GET /game/<id>`

### Game state

- In-memory game state map
- Automatic cleanup of old sessions

### Integration

- Core engine integration via `search_best_move(fen, depth)`
- NN model loaded once at startup

## Phase 4 — Frontend (HTML/CSS/JS Only)

Simple, clean interface — no React, no drama.

### What you build

### Libraries

- Chessboard.js for board rendering
- Chess.js for move legality and PGN logic

### Layout

- Board center
- Controls left
- Evaluation bar, move list, captures on the right
- Status footer

### Communication

- REST communication (FEN → backend → move + eval → UI update)

### Features

- Live evaluation bar
- Analysis mode
- PGN export
- Themes
- Mobile-friendly layout

## Phase 5 — Logging & Storage System

The historian — never forgets a move unless you tell it to.

### What you build

### Tables

- `games`
- `moves`
- `pgn_archive`

### Functionality

- Log game after every move
- Export positions to training data format for the NN
- Retrieval of past games / PGNs
### Functionality

- Log game after every move
- Export positions to training data format for the NN
- Retrieval of past games / PGNs

## Phase 6 — Reinforcement Learning System

This is where your bot goes from “average club player” to “smug tactician who thinks it’s better than you.”

### Components

- Replay buffer with random sampling
- Self-play generator (engine plays engine)
- Training loop (train → evaluate → replace if stronger)

### Difficulty scaling

- Lower search depth
- Material-heavy evaluation
- Full NN-driven evaluation
- Deep MinMax depth

## Phase 7 — Full Training Pipeline

This gives your engine long-term memory and the ability to consistently evolve.

### Process

- Self-play generates new positions
- Replay buffer updates
- Model trains batches
- Evaluation matches between old vs new NN
- Replace model only if stronger (Elo-style gating)
- Periodic export of datasets

## Phase 8 — Deployment & Scaling

Make the system production-ready.

### What you build

- Gunicorn-based serving for Flask
- Optional Nginx for reverse proxy
- Docker container for reproducibility
- Redis for scaling game sessions
- Celery for heavy tasks (training / long searches)

## Phase 9 — Optimization & Quality

The "polish" phase that separates a hobby project from a professional one.

### Key improvements

- Move ordering profiling
- Faster make/unmake move functions
- Batched NN inference
- Unit tests for engine correctness
- Observability and logs
- CI/CD for safe iteration