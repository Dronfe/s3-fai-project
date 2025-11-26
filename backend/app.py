from flask import Flask,request,jsonify
from flask_cors import CORS
import logging
import time 
import os
from backend.engine_manager import EngineManager
from neural_network.model import load_model
from neural_network.evaluate import set_active_model

# Configuring logging 
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger("chess_backend")

app=Flask(__name__)
CORS(app)

# Load model if available
MODEL_PATH = "training/checkpoints/latest_model.pt"
if os.path.exists(MODEL_PATH):
    try:
        logger.info(f"Loading model from {MODEL_PATH}...")
        model = load_model(MODEL_PATH)
        set_active_model(model)
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")

engine=EngineManager(session_seconds=60*60)

@app.route("/start_game",methods=['POST'])
def start_game():
    try:
        game_id=engine.start_new_game()
        state=engine.get_game_state(game_id=game_id)
        
        return jsonify({"ok": True, "game_id": game_id, "fen": state["fen"], "status": "started"}) #type: ignore 
        
    except Exception as e:
        logger.exception(f"start_game failed: {e}")
        return jsonify({"ok": False, "error": "internal_error", "message": str(e)}), 500 
    
    
@app.route("/make_move",methods=["POST"])
def make_move():
    data=request.get_json(force=True)
    game_id=data.get("game_id")
    move=data.get("move")
    if not game_id or not move:
        return jsonify({"ok": False, "error": "missing_parameters"}), 400
    res=engine.make_user_move(game_id=game_id,uci_move=move)
    if not res.get("ok"):
        return jsonify(res),400 
    return jsonify(res)

@app.route("/bot_move",methods=['POST'])
def bot_move():
    data=request.get_json(force=True)
    game_id = data.get("game_id")
    depth = int(data.get("depth", 5))
    if not game_id:
        return jsonify({"ok": False, "error": "missing_game_id"}), 400
    start=time.perf_counter()
    res=engine.get_bot_response(game_id=game_id,depth=depth)
    duration = time.perf_counter() - start
    if not res.get("ok"):
        return jsonify(res), 400
    
    logger.info(f"bot_move for {game_id}: depth={depth} time={duration}")
    return jsonify(res)

@app.route("/game/<game_id>", methods=["GET"])
def get_game(game_id):
    state = engine.get_game_state(game_id)
    if state is None:
        return jsonify({"ok": False, "error": "game_not_found"}), 404
    return jsonify({"ok": True, "game": state})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"ok": False, "error": "not_found"}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.exception("Internal error: %s", e)
    return jsonify({"ok": False, "error": "internal_error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)