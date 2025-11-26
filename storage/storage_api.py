# storage_api.py
from storage.db import SessionLocal, GameRecord, MoveRecord, init_db
from storage.pgn_utils import moves_to_pgn
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
init_db()   

def save_game(moves: List[str], result: str = "1/2-1/2", meta: Optional[dict] = None) -> int:
  
    s = SessionLocal()
    try:
        pgn = moves_to_pgn(moves, meta or {})
        gr = GameRecord(result=result, pgn=pgn)
        s.add(gr)
        s.flush()
        game_id = gr.id
        # store moves
        for ply, m in enumerate(moves, start=1):
            mr = MoveRecord(game_id=game_id, ply=ply, uci=m, fen="")  
            s.add(mr)
        s.commit()
        logger.info("Saved game %d (%d moves)", game_id, len(moves))
        return game_id
    except Exception as e:
        s.rollback()
        logger.exception("save_game failed: %s", e)
        raise
    finally:
        s.close()

def list_games(limit: int = 20):
    s = SessionLocal()
    try:
        return s.query(GameRecord).order_by(GameRecord.created_at.desc()).limit(limit).all()
    finally:
        s.close()