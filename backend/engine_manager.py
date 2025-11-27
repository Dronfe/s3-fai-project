import threading
import time
from typing import Dict
import logging 
from core.board import Board
from core.move import Move
from core.movegen import MoveGen
from search.minimax import search_best_move

try:
    from core.evaluator import LearnableEvaluator
    from search.minimax import get_evaluator
    nn_available=True
except Exception:
    nn_available=False
    
    
from backend.game_state import GameState

logger = logging.getLogger(__name__)

class EngineManager:
    
    def __init__(self,session_seconds=60*60):
        self.games={}
        self.lock=threading.RLock()
        self.session_ttl=session_seconds
        self._stop_cleaner=threading.Event()
        self._cleaner_thread = threading.Thread(target=self._session_cleaner_loop, daemon=True) #type: ignore
        self._cleaner_thread.start()
        logger.info("EngineManager initialized. Evaluator available: %s", nn_available)
        
    
    def start_new_game(self):
        gs=GameState(board=Board())
        with self.lock:
            self.games[gs.id]=gs 
        logger.info(f"New game started: {gs.id}")
        return gs.id 
    
    
    def get_game_state(self,game_id):
        with self.lock:
            gs=self.games.get(game_id)
            if not gs:
                return None 
            gs.last_active=time.time()
            return gs.to_dict()
        
    def make_user_move(self,game_id,uci_move):
        with self.lock:
            gs=self.games.get(game_id)
            if not gs:
                return {"ok": False, "error": "game_not_found"} 
            
            # Get legal moves
            
            legal=MoveGen.generate_legal(gs.board)
            applied=gs.apply_user_move(uci_move,legal)
            if not applied:
                logger.warning(f"Illegal move attempt {uci_move} in game {game_id}")
                return {"ok": False, "error": "illegal_move"} 
            
            # Update the state and return it 
            logger.info(f"User move {uci_move} applied in game {game_id}" )
            return {"ok": True, "game": gs.to_dict()}
            
    def get_bot_response(self,game_id,depth=3):
        """
        Search for best move at given depth, apply it, and return move + eval + fen
        """ 
        with self.lock:
            gs=self.games.get(game_id)
            if not gs:
                return {"ok": False, "error": "game_not_found"}
            board=gs.board
        
        # run search outside lock to allow other ops (but we will apply move under lock)
        start=time.perf_counter()
        
        try:
            best_move=search_best_move(board=board,depth=depth)
        except Exception as e:
            logger.exception(f"Search failed for game {game_id}: {e}")
            return {"ok": False, "error": "search_failed", "message": str(e)}
        
        duration=time.perf_counter() -start 
        
        
        if best_move is None:
            logger.info(f"No best move found for game {game_id} (maybe game over)") 
            with self.lock:
                gs.last_active=time.time()
            return {"ok":False,"error":"no_move_found"}
        
        
        eval_score=None 
        
        try:
            # Use global evaluator from search/minimax
            evaluator = get_evaluator()
            if evaluator:
                eval_score = evaluator.evaluate(board)
        except Exception:
            eval_score=None 
            
        
        # Applying the move under lock 
        with self.lock:
            gs=self.games.get(game_id)
            if not gs:
                return {"ok": False, "error": "game_not_found_after_search"} 
            gs.apply_bot_move(best_move,eval_score)
            gs.last_active=time.time()
            
        logger.info(f"Bot move { best_move.uci(lambda x: __import__('core.bitboard', fromlist=['sq_name']).sq_name(x))} applied for game {game_id} (depth={depth}, time={duration})")
        
        return {
            "ok": True,
            "best_move": best_move.uci(__import__('core.bitboard', fromlist=['sq_name']).sq_name),
            "eval": eval_score,
            "fen": gs.board_to_fen(),
            "time_s": duration
        }

    def _session_cleaner_loop(self):
        
        while not self._stop_cleaner.is_set():
            now=time.time()
            removed=[]
            with self.lock:
                for gid,gs in list(self.games.items()):
                    if now-gs.lock_active >self.session_ttl:
                        removed.append(gid)
                        del self.games[gid]
            if removed:
                logger.info(f"Session cleaner removed {len(removed)} sessions: {removed}")
            
            self._stop_cleaner.wait(30.0)
            
    def stop(self):
        self._stop_cleaner.set()
        self._cleaner_thread.join(timeout=2.0)