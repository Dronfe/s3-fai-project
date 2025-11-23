import numpy as np
import torch 
from typing import Optional 

files='abcdefgh'
ranks='12345678'

def _sq_to_coord(sq):
    return sq//8,sq%8 

def encode_board(board,device='cpu'):
    """
    Encodes a Board into a tensor shape (1, C, 8, 8).
    Channels:
      0-5   : white P,N,B,R,Q,K
      6-11  : black P,N,B,R,Q,K
      12    : side-to-move (1 if white to move else 0)
      13    : castling mask normalized (0..1)
      14    : en-passant one-hot
      15    : halfmove clock normalized
    Returns: torch.FloatTensor on device
    """ 
    
    c=16 
    planes=np.zeros((c,8,8),dtype=np.float32)
    
    for color in (0,1):
        base=0 if color==0 else 6 
        for ptype in range(6):
            plane_idx=base+ptype
            bb=board.bb[color][ptype]
            
            while bb:
                lsb=bb & -bb 
                sq=lsb.bit_length()-1
                bb&=bb-1 
                r,f=_sq_to_coord(sq)
                planes[plane_idx,r,f]=1.0 
                
    # side to move 
    planes[12,:,:]=1.0 if getattr(board,"side_to_move",0)==0 else 0.0
    
    # Normalising castling rights 
    cast_mask=getattr(board,"castling",0)
    planes[13,:,:]=float(cast_mask)/15.0
    
    # en-passant
    ep=getattr(board,"en_passant",None)
    if ep is not None:
        r,f=_sq_to_coord(ep)
        planes[14,r,f]=1.0 
        
    # Normalizing halfmove clock    
    halfmove=getattr(board,"halfmove",0)
    planes[15,:,:]=min(1.0,float(halfmove)/100.0)
    
    tensor=torch.from_numpy(planes).unsqueeze(0)
    
    if device is not None:
        tensor=tensor.to(device)
    return tensor 


    