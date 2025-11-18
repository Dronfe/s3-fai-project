# Chess Bot with MinMax Algorithm + Reinforcement Learning - Architecture Plan

## High-Level Architecture

### Core Components

1. **Game Engine**
   - Chess board state representation
   - Legal move generator
   - Move validator
   - Win/draw/loss detector
   - FEN notation parser (for board states)

2. **MinMax Algorithm Module**
   - Traditional MinMax with alpha-beta pruning
   - Configurable search depth
   - Position evaluation function (the part that RL will improve)

3. **Reinforcement Learning System**
   - State feature extractor
   - Neural network for position evaluation
   - Experience replay buffer
   - Training loop

4. **Game Logger**
   - Database/file system for game storage
   - Move-by-move recording
   - Metadata (timestamps, outcomes, player info)

---

## Detailed Component Design

### 1. Game State Representation

**Input to Bot:**
- Current board position (8x8 grid with piece positions)
- Previous N moves (both player and bot), suggested N=5-10
- Game metadata: whose turn, castling rights, en passant square
- Move history in standard notation

**Data Structure:**
```
GameState:
  - current_board: 8x8 matrix
  - move_history: list of (from_square, to_square, piece, captured_piece)
  - turn_count: integer
  - active_player: white/black
  - castling_rights: dict
  - en_passant_square: optional
```

---

### 2. MinMax Algorithm with Evaluation Function

**Traditional Components:**
- **Search Tree:** Explores possible moves up to depth D
- **Alpha-Beta Pruning:** Optimizes search by cutting branches
- **Move Ordering:** Prioritizes promising moves (captures, checks)

**Evaluation Function (RL-Enhanced):**
- **Static Features:** Material count, piece positioning, king safety
- **Neural Network Component:** Takes board state + move history → outputs position score
- **Hybrid Approach:** Combine traditional heuristics with learned evaluation

**Flow:**
1. Generate all legal moves
2. For each move, recursively evaluate resulting positions
3. Use evaluation function (traditional + NN) at leaf nodes
4. Backpropagate scores with min/max logic
5. Select move with best evaluation

---

### 3. Reinforcement Learning Integration

**Learning Framework:** Use TD-Learning (Temporal Difference) or Policy Gradient

**Key Elements:**

**A. State Representation for NN:**
- Board position encoded as multi-channel tensor (piece types, colors, positions)
- Previous moves encoded as sequence
- Additional features: castling rights, king safety metrics, material balance
- Output: Single scalar (position evaluation score)

**B. Training Data Collection:**
- After each move: Store (state, action, reward)
- Terminal reward: +1 for win, -1 for loss, 0 for draw
- Intermediate rewards: Based on position changes (optional, or use only terminal)

**C. Experience Replay:**
- Store tuples: (board_state, move_history, position_evaluation, game_outcome)
- Sample randomly during training to break correlation
- Buffer size: 10,000-100,000 games

**D. Training Loop:**
- Play N games (self-play or against opponents)
- Store experiences in replay buffer
- Periodically (every M games): Sample batch, train NN
- Update evaluation function in MinMax
- Iterate

**E. Reward Structure:**
- **Terminal rewards:** Win (+1), Loss (-1), Draw (0)
- **Optional intermediate rewards:** Capturing pieces, controlling center, threatening opponent
- **TD target:** Use outcome-based learning (compare predicted evaluation vs actual game result)

---

### 4. Game Logger System

**Storage Format:**

**Game Metadata Table:**
- Game ID (unique)
- Timestamp
- Players (bot vs human/bot vs bot)
- Final outcome (win/loss/draw)
- Total moves
- Opening used
- Final position (FEN)

**Move Log Table:**
- Game ID (foreign key)
- Move number
- Player (white/black)
- Move notation (algebraic: e4, Nf3, etc.)
- Board state before move (FEN)
- Board state after move (FEN)
- Time taken (optional)
- Evaluation score (bot's assessment)

**Storage Options:**
- **SQL Database:** PostgreSQL/SQLite for structured queries
- **JSON Files:** One file per game for simplicity
- **Hybrid:** Metadata in DB, full games in JSON

**Logging Features:**
- Export games to PGN format (standard chess notation)
- Query games by outcome, opening, date
- Analyze bot's decision patterns over time
- Track improvement metrics

---

## Implementation Strategy

### Phase 1: Foundation (Weeks 1-2)
1. Implement chess engine (board, moves, rules)
2. Build basic MinMax with traditional evaluation
3. Create game logger (start with JSON files)
4. Test bot plays legal, reasonable games

### Phase 2: RL Integration (Weeks 3-4)
1. Design neural network architecture
2. Implement state encoder
3. Create experience replay buffer
4. Build training loop (self-play)
5. Integrate NN evaluation into MinMax

### Phase 3: Training & Optimization (Weeks 5-6)
1. Run extended self-play sessions
2. Monitor learning curves
3. Tune hyperparameters (learning rate, search depth, NN size)
4. Implement checkpointing (save best models)

### Phase 4: Evaluation & Refinement (Week 7+)
1. Test against standard chess engines
2. Analyze logged games for patterns
3. Refine reward structure
4. Add opening book (optional)
5. Optimize search speed

---

## Technical Considerations

### MinMax Optimization
- **Search Depth:** Start with 3-4 plies, increase as hardware allows
- **Iterative Deepening:** Search progressively deeper within time limits
- **Transposition Tables:** Cache evaluated positions
- **Quiescence Search:** Extend search at volatile positions (captures)

### Neural Network Design
- **Input:** Board tensor (12 channels: 6 piece types × 2 colors) + history features
- **Architecture:** CNN layers → fully connected → single output
- **Size:** Start modest (3-5 conv layers, 128-256 filters)
- **Output:** Activation like tanh (range -1 to +1)

### Training Challenges
- **Exploration vs Exploitation:** Epsilon-greedy or temperature-based move selection
- **Catastrophic Forgetting:** Maintain diverse replay buffer
- **Credit Assignment:** Terminal rewards only, or use TD-lambda
- **Computational Cost:** Self-play is expensive; parallelize if possible

### Logging Efficiency
- Batch writes to database (not after every move)
- Index database by game outcome and date
- Compress old games if storage is limited
- Optional: Log only bot games (not test games)

---

## Success Metrics

1. **Performance:** ELO rating against standard engines
2. **Learning:** Win rate improvement over time (self-play)
3. **Consistency:** Reduction in blunders (losing pieces/checkmate in N)
4. **Data Quality:** Complete game logs with accurate move notation
5. **Efficiency:** Moves per second during search

---

## Future Enhancements

- **Opening Book:** Load standard openings to improve early game
- **Endgame Tablebases:** Perfect play in simple endgames
- **Parallel Search:** MCTS alternative to MinMax
- **Multi-Agent Training:** Train against diverse opponents
- **Explainability:** Visualize NN's attention on board features
- **Web Interface:** Deploy bot for online play with real-time logging

---

This architecture balances classical chess AI (MinMax) with modern machine learning (RL), creating a bot that improves through experience while maintaining strategic depth. The logging system ensures full traceability for analysis and debugging.