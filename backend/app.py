from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import sys
import os
import uuid

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.board import Board
from search.minimax import search_best_move, get_evaluator

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define Base Directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load Engine
MODEL_PATH = os.path.join(BASE_DIR, "training", "checkpoints", "model.json")
if os.path.exists(MODEL_PATH):
    logger.info(f"Loading model from {MODEL_PATH}")
    get_evaluator().load(MODEL_PATH)
else:
    logger.info(f"No model found at {MODEL_PATH}, using default weights.")

# In-memory game state
games = {}

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    try:
        game_id = str(uuid.uuid4())
        board = Board() # Start position
        games[game_id] = board
        
        return jsonify({
            'ok': True,
            'game_id': game_id,
            'fen': 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
        })
    except Exception as e:
        logger.error(f"Error starting game: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/make_move', methods=['POST'])
def make_move():
    try:
        data = request.json
        game_id = data.get('game_id')
        uci = data.get('move')
        
        if game_id not in games:
            return jsonify({'error': 'Game not found'}), 404
            
        board = games[game_id]
        
        # Parse UCI move
        # We need to find the legal move object that matches this UCI string
        moves = from_uci(board, uci)
        
        if moves:
            board.make_move(moves[0])
            return jsonify({'ok': True, 'fen': get_fen(board)})
        else:
            # Debugging: Log why it failed
            logger.error(f"Illegal move rejected: {uci}")
            logger.error(f"Current FEN: {board.fen()}")
            
            from core.movegen import MoveGen
            legal_moves = MoveGen.generate_legal(board)
            sq_name = __import__('core.bitboard', fromlist=['sq_name']).sq_name
            legal_ucis = [m.uci(sq_name) for m in legal_moves]
            logger.error(f"Legal moves: {legal_ucis}")
            
            return jsonify({'error': 'Illegal move'}), 400
            
    except Exception as e:
        logger.error(f"Error making move: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/bot_move', methods=['POST'])
def bot_move():
    try:
        data = request.json
        game_id = data.get('game_id')
        depth = data.get('depth', 3)
        
        if game_id not in games:
            return jsonify({'error': 'Game not found'}), 404
            
        board = games[game_id]
        
        # Search
        best_move = search_best_move(board, depth)
        
        if best_move:
            # Convert to UCI
            uci = best_move.uci(lambda x: __import__('core.bitboard', fromlist=['sq_name']).sq_name(x))
            
            # Apply move to our state
            board.make_move(best_move)
            
            # Get eval (simple static eval for now)
            score = get_evaluator().evaluate(board)
            
            return jsonify({
                'ok': True, 
                'best_move': uci,
                'eval': float(score),
                'time_s': 0.1 # Placeholder
            })
        else:
            return jsonify({'error': 'No legal moves or game over'}), 200
            
    except Exception as e:
        logger.error(f"Error bot move: {e}")
        return jsonify({'error': str(e)}), 500

# Helper to parse UCI
def from_uci(board, uci):
    # This is a bit hacky, we generate all legal moves and check uci
    from core.movegen import MoveGen
    legal_moves = MoveGen.generate_legal(board)
    sq_name = __import__('core.bitboard', fromlist=['sq_name']).sq_name
    
    if not uci:
        return []
        
    uci = uci.lower().strip()
    
    # Handle e2-e4 format
    uci = uci.replace('-', '')
    
    matched = []
    for m in legal_moves:
        m_uci = m.uci(sq_name)
        if m_uci == uci:
            matched.append(m)
            
    # If no match, try appending 'q' for promotion if it's a promotion move
    if not matched and len(uci) == 4:
        # Check if this could be a promotion
        # If any legal move matches the first 4 chars and is a promotion
        for m in legal_moves:
            m_uci = m.uci(sq_name)
            if len(m_uci) == 5 and m_uci[:4] == uci and m_uci[4] == 'q':
                matched.append(m)
                
    return matched

def get_fen(board):
    return board.fen()

if __name__ == '__main__':
    app.run(debug=True, port=5000)