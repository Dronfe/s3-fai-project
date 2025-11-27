import math
import logging
import random
from collections import defaultdict
from core.board import Board
from core.movegen import MoveGen
from search.minimax import search_best_move, set_evaluator, get_evaluator, negamax
from core.evaluator import LearnableEvaluator
from core.bitboard import pop_lsb

logger=logging.getLogger(__name__)

def _safe_elo_from_score(score,eps=1e-8):
    """
    Given observed score S (0..1) for the 'new' model, estimate Elo difference D:
    Clip S to avoid division by zero.
    Returns D (positive => new model stronger).
    """

    s=min(max(score,eps),1.0-eps)
    return 400.0*math.log10(s/(1.0-s))

def search_with_randomness(board, depth, temperature=0.3):
    """
    Search for best move with some randomness to create variety.

    Args:
        board: Current board state
        depth: Search depth
        temperature: Randomness factor (0=deterministic, 1=very random)

    Returns:
        Selected move
    """
    evaluator = get_evaluator()
    moves = MoveGen.generate_legal(board)

    if not moves:
        return None

    if len(moves) == 1:
        return moves[0]

    # Evaluate all legal moves
    move_scores = []
    for move in moves:
        board.make_move(move)
        score = -negamax(board, depth-1, -999_999, 999_999, evaluator)
        board.unmake_move()
        move_scores.append((move, score))

    # Sort by score (best first)
    move_scores.sort(key=lambda x: x[1], reverse=True)

    # With some probability, choose from top 3 moves instead of always best
    if temperature > 0 and random.random() < temperature and len(move_scores) >= 3:
        # Choose randomly from top 3 moves
        top_moves = move_scores[:3]
        return random.choice(top_moves)[0]
    else:
        # Choose best move
        return move_scores[0][0]

def evaluate_models_head_to_head(old_model_path,new_model_path,n_games,depth):
    """
    Play `n_games` games between old and new models. Alternate colors each game.
    Each move is chosen by the engine for the side to move using that side's model (we swap active model
    before calling search_best_move).
    """

    new_evaluator=None
    old_evaluator=None

    try:
        new_evaluator=LearnableEvaluator(weights_path=new_model_path)
    except Exception as e:
        logger.exception(f"Failed to load new model {new_model_path}:{e}")
        # Fallback to default
        new_evaluator=LearnableEvaluator()

    try:
        old_evaluator=LearnableEvaluator(weights_path=old_model_path)
    except Exception as e:
        logger.exception(f"Failed to load old model {old_model_path}:{e}")
        # Fallback to default
        old_evaluator=LearnableEvaluator()

    # Save current evaluator to restore later
    prev_evaluator = get_evaluator()

    points_new=0.0
    points_old=0.0

    # Add some randomness to create variety in games
    TEMPERATURE = 0.4  # Increased randomness to avoid draws

    for g in range(n_games):
        board=Board()

        # Determining which color the models play in the current game

        new_is_white=(g%2==0)

        # Playing the game with repetition detection

        move_c=0
        position_history = defaultdict(int)  # Track position repetitions

        # Add starting position
        position_history[board.key] += 1

        # Reduced move limit to prevent endless games
        MAX_MOVES = 150  # Reasonable game length

        while move_c < MAX_MOVES:
            #0 is white and 1 is black
            stm=board.side_to_move

            if (stm==0 and new_is_white) or (stm==1 and not new_is_white):

                # Move of new model
                set_evaluator(new_evaluator)

                # Search with slight randomness
                chosen=search_with_randomness(board, depth, temperature=TEMPERATURE)
            else:
                set_evaluator(old_evaluator)
                chosen=search_with_randomness(board, depth, temperature=TEMPERATURE)


            if chosen is None:
                # if no move is done then it is a checkmate or stalemate
                break

            board.make_move(chosen)
            move_c+=1

            # Track position for repetition detection
            position_history[board.key] += 1

            # Check for threefold repetition (draw)
            if position_history[board.key] >= 3:
                logger.debug(f"Game {g}: Draw by threefold repetition at move {move_c}")
                points_new += 0.5
                points_old += 0.5
                break

            legal_after=MoveGen.generate_legal(board=board)
            if not legal_after:
                break
        else:
            # This else block executes if the while loop completes normally (no break)
            # which means move_c >= MAX_MOVES
            logger.debug(f"Game {g}: Draw by move limit ({MAX_MOVES} moves)")
            points_new += 0.5
            points_old += 0.5
            continue

        # If we broke out of the loop (checkmate/stalemate/repetition), we fall through here.
        # But wait, repetition break is above.
        # If we broke due to repetition, we already added points.
        # We need to be careful not to double count or crash.
        
        # If we broke due to repetition, we should continue to next game.
        if position_history[board.key] >= 3:
            continue

        # If game is finished detect the result
        legal_now=MoveGen.generate_legal(board=board)
        if not legal_now:

            # side to move has no legal moves -> checkmate or stalemate
            # if side to move is in check -> previous player delivered mate
            king_bb=board.bb[board.side_to_move][5]  # Fixed: use current side_to_move
            if king_bb==0:
                # If there is no king treat it as a draw
                logger.debug(f"Game {g}: Draw (no king found)")
                points_new += 0.5
                points_old += 0.5
            else:
                # Extract the king square from the bitboard
                _, king_sq = pop_lsb(king_bb)

                if board.is_square_attacked(king_sq, 1-board.side_to_move):
                    # If checkmate the winner is previous side
                    winner_side=1-board.side_to_move

                    logger.debug(f"Game {g}: Checkmate! Winner: {'White' if winner_side == 0 else 'Black'}, "
                               f"New was {'White' if new_is_white else 'Black'}")

                    # Determine the winner

                    if (winner_side==0 and new_is_white) or (winner_side==1 and not new_is_white):
                        points_new+=1.0
                    else:
                        points_old+=1.0

                else:
                    # If it is stalemate
                    logger.debug(f"Game {g}: Stalemate")
                    points_old+=0.5
                    points_new+=0.5

    # Restoring the previous evaluator
    set_evaluator(prev_evaluator)

    total=points_old+points_new

    # total should equal n_games
    logger.info(f"Evaluation complete: New={points_new}/{n_games}, Old={points_old}/{n_games}, "
                f"Total={total} (expected {n_games})")

    score_new_frac = points_new / max(1.0, (points_new + points_old))
    # score_old_frac = points_old / max(1.0, (points_new + points_old))
    elo_diff = _safe_elo_from_score(score_new_frac)
    return {
        "score_old": float(points_old),
        "score_new": float(points_new),
        "elo_diff": float(elo_diff)
    }