import math 
from typing import Optional,Tuple,Dict
from core.board import Board
from core.move import Move
from core.movegen import MoveGen
from search.ordering import MoveOrderer
from core.bitboard import pawn,knight,bishop,king,rook,queen,white,black,pop_lsb


# Assigning values for each type of piece to use later for evaluation

material_value={
    pawn:100,
    knight:320,
    bishop:330,
    rook:500,
    queen:1000,
    king:20000,
} 


# Transposition tables 
exact=0
lower_bound=1
upper_bound=2 


class TTEntry:
    def __init__(self,key,depth,score,flag,best_move):
        self.key=key
        self.depth=depth
        self.score=score 
        self.flag=flag
        self.best_move=best_move 
        
class TranspositionTable:
    def __init__(self):
        self.table={}
        
    def store(self,key,depth,score,flag,best_move):
        e=self.table.get(key)
        if e is None or depth>= e.depth:
            self.table[key]=TTEntry(key,depth,score,flag,best_move)
        
    
    def probe(self,key):
        return self.table.get(key)
    

# Simple evaluation: material + piece-square + mobility
# Keep PST small and optional — using simple center bonuses (can expand later)     

pst_sample={
    pawn:[0]*64,
    knight:[0]*64,
    bishop:[0]*64,
    rook:[0]*64,
    queen:[0]*64,
    king:[0]*64,
} 


def evaluate_simple(board):
    total=0
    
    for color in (white,black):
        sign=1 if color==white else -1 
        for p in (pawn,knight,bishop,rook,queen,king):
            bb=board.bb[color][p]
            while bb:
                bb,sq=pop_lsb(bb)
                total+=sign*material_value[p]
                
                # Adding pst 
                total+=sign*pst_sample[p][sq]
    
    # Mobility bonus 
    try:
        wmoves=len(MoveGen.generate_pseudo_legal(board))
        # Count opponent moves roughly
        board.side_to_move=1-board.side_to_move
        omoves=len(MoveGen.generate_pseudo_legal(board))
        board.side_to_move=1-board.side_to_move
        mobility=(wmoves-omoves)
        total+=mobility
    except Exception:
        # Ignore the mobility thing if any errpr
        pass 
    return total 

# Quiescence: capture-only search to reduce horizon effect
max_q_depth=6

class SearchContext:
    def __init__(self,max_depth=6):
        self.tt=TranspositionTable()
        self.orderer=MoveOrderer(max_depth+8)
        self.nodes=0
        self.max_depth=max_depth

def quiescence(board,alpha,beta,ctx,ply=0):
    ctx.nodes+=1
    stand_pat=evaluate_simple(board)
    if stand_pat>=beta:
        return beta 
    if alpha <stand_pat:
        alpha=stand_pat
        
    if ply>=max_q_depth:
        return stand_pat 
    
    # Considering captures
    moves=MoveGen.generate_pseudo_legal(board)
    
    # Filter captures only 
    captures=[m for m in moves if m.capture is not None]
    
    # Order captures by mvv-lva using orderer
    captures=ctx.orderer.order_moves(captures,ply,None)
    
    for m in captures:
        board.make_move(m)
        score = -quiescence(board, -beta, -alpha, ctx, ply+1) #type: ignore 
        board.unmake_move()
        if score>=beta:
            return beta 
        if score>alpha:
            alpha=score
    return alpha 

def negamax(board,depth,alpha,beta,ctx,ply=0):
    """
    Returns (score, best_move) from the current side-to-move perspective.
    Score is centipawn advantage for White (positive=White better). We run negamax with sign flip by caller.
    """ 
    
    ctx.nodes+=1
    original_alpha=alpha
    
    
    # TT probe
    entry=ctx.tt.probe(board.key)
    if entry is not None and entry.depth>=depth:
        if entry.flag==exact:
            return entry.score,entry.best_move
        
        if entry.flag==lower_bound and entry.score<=alpha:
            return entry.score,entry.best_move
        
        if entry.flag==upper_bound and entry.score>=beta:
            return entry.score,entry.best_move 
        
        
    if depth == 0:
        try:
            # blended NN + classical eval
            from neural_network.evaluate import nn_evaluate
            score = nn_evaluate(board)
        except Exception:
        # fallback to quiescence/classical if something goes wrong
            score = quiescence(board, alpha, beta, ctx, ply)
        return score, None

    
    best_move=None
    best_score=-math.inf 
    
    
    # Generate legal moves 
    moves=MoveGen.generate_legal(board)
    if not moves:
        # no legal moves -> checkmate or stalemate
        # determine if side to move is in check
        # if in check -> checkmate (large negative score), else stalemate (0)
        # find king 
        
        king_bb=board.bb[1-board.side_to_move][king]
        
        if king_bb==0:
            return 0,None 
        
        _,king_sq=pop_lsb(king_bb)
        
        if board.is_square_attacked(king_sq,1-board.side_to_move):
            score= -material_value[king]-(ctx.max_depth - depth)*10 
            return score,None 
        else:
            return 0,None 
        
    
    # Order moves 
    
    tt_move=entry.best_move if entry is not None else None 
    ordered_moves=ctx.orderer.order_moves(moves,ply,tt_move)
    
    for m in ordered_moves:
        board.make_move(m)
        score,_=negamax(board,depth-1,-beta,-alpha,ctx,ply+1) #type: ignore 
        score= -score 
        board.unmake_move() 
        
        if score>best_score:
            best_score=score
            best_move=m 
            
        if best_score>alpha:
            alpha=best_score 
            
        if alpha>=beta:
            ctx.orderer.record_killer(m,ply)
            ctx.orderer.record_history(m,depth)
            break 
        
    # store in TT 
    flag=exact 
    if best_score<=original_alpha:
        flag=upper_bound
    elif best_score>=beta:
        flag=lower_bound
    
    ctx.tt.store(board.key,depth,best_score,flag,best_move)
    
    return best_score,best_move 


def iterative_deepening(root_board,max_depth):
    ctx=SearchContext(max_depth=max_depth)
    best_move=None
    
    for depth in range(1,max_depth+1):
        ctx.max_depth=depth
        ctx.orderer.max_depth=depth+8
        score,move=negamax(root_board,depth,-999_999,999_999,ctx,ply=0)
        if move is not None:
            best_move=move
    return best_move 


# High level api 
def search_best_move(board,depth):
    return iterative_deepening(board,depth)