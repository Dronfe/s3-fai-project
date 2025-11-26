from typing import List,Dict,Any 
from uuid import uuid4 
import time 
from core.board import Board
from core.move import Move 
from core.bitboard import sq_name,sq_index

class GameState:
    """This class tracks the state of a single game"""
    
    def __init__(self,board):
        self.id=str(uuid4())
        self.board=board if board is not None else Board() 
        self.move_history=[] 
        self.fen_history=[self.board_to_fen()]
        self.last_bot_move=None
        self.eval=None 
        self.game_over=False
        self.winner=None
        self.created_at=time.time()
        self.last_active=self.created_at
        
    def board_to_fen(self):
        pieces=[]
        for r in range(7,-1,-1):
            empty=0
            rank_s=""
            for f in range(8):
                sq=r*8+f
                piece=self.board.piece_at(sq)
                if piece is None:
                    empty+=1
                else:
                    if empty:
                        rank_s+=str(empty)
                        empty=0 
                    color,p=piece
                    symbol={0:'P',1:'p'}[color]
                    
                    # Map the piece types to letters
                    p_map={0:'P',1:'N',2:'B',3:'R',4:'Q',5:'K'}
                    ch=p_map[p]
                    rank_s+=ch if color==0 else ch.lower() 
                    
            if empty:
                rank_s+=str(empty)
            pieces.append(rank_s)
        board_part="/".join(pieces)
        side='w' if self.board.side_to_move == 0 else 'b'
        castle=""
        if self.board.castling & 1: castle+="K"
        if self.board.castling & 2: castle+="Q"
        if self.board.castling & 4: castle+="k"
        if self.board.castling & 8: castle+="q"
        if castle == "": castle = "-"
        
        ep="-" if self.board.en_passant is None else sq_name(self.board.en_passant)
        half=getattr(self.board,"halfmove",0)
        full=getattr(self.board,"fullmove",1)
        return f"{board_part} {side} {castle} {ep} {half} {full}"
    
    def apply_user_move(self,uci_move,legal_moves):
        """ Validate uci_move against provided legal_moves"""
        
        uci=uci_move.strip()
        if len(uci)<4:
            return False
        
        try:
            from_sq=sq_index(uci[0:2])
            to_sq=sq_index(uci[2:4])
        except Exception:
            return False
        
        promotion=None 
        if len(uci)>4:
            prom_char=uci[4].lower()
            prom_map={'q':4,'r':3,'b':2,'n':1}
            
            # Phase1 mapping: PAWN=0, KNIGHT=1, BISHOP=2, ROOK=3, QUEEN=4, KING=5
            promotion = prom_map.get(prom_char, None)
            
        # Match against provided legal moves 
        match_move=None
        
        for m in legal_moves:
            if m.from_sq==from_sq and m.to_sq == to_sq:
                if (m.promotion is None) or (m.promotion==promotion):
                    match_move=m
                    break
        if match_move is None:
            return False
        
        # Apply stuff
        self.board.make_move(match_move)
        uci_out=uci_move
        self.move_history.append(uci_out)
        self.fen_history.append(self.board_to_fen())
        self.last_active=time.time()
        
        return True 
    
    
    def apply_bot_move(self,move_obj,eval_score):
        self.board.make_move(move_obj)
        uci_str=move_obj.uci(sq_name)
        self.move_history.append(uci_str)
        self.last_bot_move=uci_str
        
        if eval_score is not None:
            self.eval=int(eval_score)
        
        self.fen_history.append(self.board_to_fen())
        self.last_active=time.time()
        
    def to_dict(self):
        return {
            "game_id": self.id,
            "fen": self.board_to_fen(),
            "moves": list(self.move_history),
            "last_bot_move": self.last_bot_move,
            "eval": self.eval,
            "game_over": self.game_over,
            "winner": self.winner,
            "created_at": self.created_at,
            "last_active": self.last_active,
        }