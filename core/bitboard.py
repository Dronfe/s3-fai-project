files='abcdefgh'
ranks='12345678' 

white,black=0,1

pawn,knight,bishop,rook,queen,king=range(6)

def sq_name(idx):
    return files[idx%8]+ranks[idx//8]

def sq_index(name):
    file=files.index(name[0])
    rank=ranks.index(name[0]) 
    return rank*8 + file 

# Bitboard operations 
def bit(bb,sq):
    return (bb>>sq) & 1

def set_bit(bb,sq):
    return bb | (1<<sq)

def clear_bit(bb,sq):
    return bb &~(1<<sq)

def pop_lsb(bb):
    lsb=bb & -bb 
    idx=lsb.bit_length()-1
    return bb & (bb-1), idx 

# Precomputed attacks 

knight_attacks=[0]*64
king_attacks=[0]*64 


def init_knight_king():
    for sq in range(64):
        f=sq%8
        r=sq//8
        
        """Knight"""
        attacks=0
        for df,dr in [(-2,-1),(-2,1),(2,-1),(2,1),(-1,-2),(-1,2),(1,-2),(1,2)]:
            nf,nr=f+df,r+dr 
            
            if 0<=nf < 8 and 0<= nr < 8:
                attacks |=(1<<nr*8+nf)
                
        knight_attacks[sq]=attacks 
        
        """King"""
        attacks=0
        for df,dr in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            nf,nr=f+df,r+dr 
            if 0<=nf < 8 and 0<= nr < 8:
                attacks |=(1<<nr*8+nf)
                
        king_attacks[sq]=attacks  
        
init_knight_king() 


directions={'N':8,'S':-8,'E':1,'W':-1,'NE':9,'NW':7,'SE':-7,'SW':-9}

