# storage/db.py
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os
from pathlib import Path

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
_db_env = os.environ.get("CHESS_DB")

# Determine DB Path
if _db_env:
    DB_PATH = _db_env if _db_env.startswith("sqlite://") else f"sqlite:///{os.path.abspath(_db_env)}"
else:
    # Check if running in Kaggle
    if os.path.exists("/kaggle/working"):
        default_db = Path("/kaggle/working/chess_data.db")
    else:
        default_db = Path(BASE_DIR) / "chess_data.db"
        
    default_db.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH = f"sqlite:///{default_db.resolve().as_posix()}"        

# Initialize Engine and Session
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class GameRecord(Base):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    result = Column(String(16), default="unknown")   # "1-0", "0-1", "1/2-1/2"
    pgn = Column(Text)

class MoveRecord(Base):
    __tablename__ = "moves"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, index=True)
    ply = Column(Integer)
    uci = Column(String(16))
    fen = Column(Text)
    eval = Column(Integer, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("DB initialized at", DB_PATH)