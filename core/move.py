from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class Move:
    from_sq:int 
    to_sq:int
    piece:Tuple[int,int]
    capture: Optional[Tuple[int,int]]=None 
    promotion: Optional[int]=None 
    is_en_passant: bool=False 
    is_castling: bool=False 
    
    
    def uci(self,sq_name_fn):
        s=f"{sq_name_fn(self.from_sq)}{sq_name_fn(self.to_sq)}"
        KNIGHT, BISHOP, ROOK, QUEEN = range(1,5)
        
        if self.promotion is not None:
            # promotion: use piece letter mapping 2->B,3->N,4->R,5->Q (internal mapping may vary) 
            
            prom_map={BISHOP:'b',KNIGHT:'n',ROOK:'r',QUEEN:'q'} 
            
            s+=prom_map.get(self.promotion,'q')
        return s 