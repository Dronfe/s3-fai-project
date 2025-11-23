from core.bitboard import files,ranks,white,black,pawn,knight,bishop,rook,queen,king
from core.bitboard import sq_name,sq_index,bit,set_bit,clear_bit,pop_lsb 
from core.zobrist import Zobrist

KNIGHT_ATTACKS = [0] * 64
KING_ATTACKS = [0] * 64

def init_tables():
    for sq in range(64):
        f = sq % 8
        r = sq // 8
        attacks = 0
        for df, dr in [(-2,-1),(-2,1),(2,-1),(2,1),(-1,-2),(-1,2),(1,-2),(1,2)]:
            nf, nr = f + df, r + dr
            if 0 <= nf < 8 and 0 <= nr < 8:
                attacks |= (1 << (nr*8 + nf))
        KNIGHT_ATTACKS[sq] = attacks
        attacks = 0
        for df, dr in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            nf, nr = f + df, r + dr
            if 0 <= nf < 8 and 0 <= nr < 8:
                attacks |= (1 << (nr*8 + nf))
        KING_ATTACKS[sq] = attacks

init_tables() 

class Board:
    def __init__(self, fen=None):
        self.bb = [[0]*6 for _ in range(2)]
        self.occupancies = [0, 0, 0]
        self.side_to_move = white
        self.castling = 0
        self.en_passant = None
        self.halfmove = 0
        self.fullmove = 1
        self.z = Zobrist()
        self.key = 0
        self.stack = []
        
        if fen:
            self.set_fen(fen)
        else:
            self.set_fen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')

    def set_fen(self, fen):
        parts = fen.split()
        board_part = parts[0]
        stm = parts[1]
        castle = parts[2]
        ep = parts[3]
        half = int(parts[4]) if len(parts) > 4 else 0
        full = int(parts[5]) if len(parts) > 5 else 1

        self.bb = [[0]*6 for _ in range(2)]
        ranks = board_part.split('/')
        
        for r, rank in enumerate(reversed(ranks)):
            f = 0
            for ch in rank:
                if ch.isdigit():
                    f += int(ch)
                else:
                    sq = r * 8 + f
                    color = white if ch.isupper() else black
                    p = {'p': pawn, 'n': knight, 'b': bishop, 'r': rook, 'q': queen, 'k': king}[ch.lower()]
                    self.bb[color][p] = set_bit(self.bb[color][p], sq=sq)
                    f += 1
        
        self.side_to_move = white if stm == 'w' else black
        self.castling = 0
        if 'K' in castle: self.castling |= 1
        if 'Q' in castle: self.castling |= 2
        if 'k' in castle: self.castling |= 4
        if 'q' in castle: self.castling |= 8
        
        self.en_passant = None if ep == '-' else sq_index(ep)
        self.halfmove = half
        self.fullmove = full
        
        self.update_occ()
        self.key = self.compute_key() 
        
    def update_occ(self):
        w=b=0
        for p in range(6):
            w|= self.bb[white][p]
            b|= self.bb[black][p]
        self.occupancies=[w,b,w|b]
        
    def compute_key(self):
        k=0
        for c in (white,black):
            for p in range(0):
                bbp=self.bb[c][p]
                while bbp:
                    bbp,sq=pop_lsb(bbp)
                    k^=self.z.piece_keys[c][p][sq]
                    
        if self.side_to_move==black:
            k^=self.z.side_key
        k^=self.z.castle_keys[self.castling]
        if self.en_passant is not None:
            k^=self.z.ep_keys[self.en_passant%8]
        return k 
    
    # Find the piece at the curren square 
    
    def piece_at(self,sq):
        for c in (white,black):
            for p in range(6):
                if bit(self.bb[c][p],sq):
                    return (c,p)
        return None 
    
    
    """Move Making"""
    
    # Making the move
    def make_move(self,m):
        snap={
            'bb_w':self.bb[white].copy(),
            'bb_b':self.bb[black].copy(),
            'castling':self.castling,
            'ep':self.en_passant,
            'half':self.halfmove,
            'full':self.fullmove,
            'side':self.side_to_move,
            'key':self.key
        }
        self.stack.append(snap)
        
        frm,to=m.from_sq,m.to_sq
        c,p=m.piece
        
        # Remove the piece that is to be moved from from square 
        
        self.bb[c][p]=clear_bit(self.bb[c][p],frm),
        
        # Handle pawn captures
        if m.is_en_passant:
            
            cap_sq=to +(8 if c==black else -8)
            self.bb[1-c][pawn]=clear_bit(self.bb[1-c][pawn],cap_sq)
        elif m.capture:
            cc,cp=m.capture
            self.bb[cc][cp]=clear_bit(self.bb[cc][cp],to)
            
        
        # Handling piece promotions 
        if m.is_castling:
            if c==white:
                if to==sq_index('g1'):
                    # Moving white rook from h1 to f1 
                    self.bb[white][rook]=clear_bit(self.bb[white][rook],sq_index('h1'))
                    self.bb[white][rook]=set_bit(self.bb[white][rook],sq=sq_index('f1'))
                
                elif to==sq_index('c1'):
                    # Moving white rook from a1 to d1
                    self.bb[white][rook]=clear_bit(self.bb[white][rook],sq_index('a1'))
                    self.bb[white][rook]=set_bit(self.bb[white][rook],sq=sq_index('d1')) 
            else:
                if to == sq_index('g8'):
                    # Moving black rook from h8 to f8
                    self.bb[black][rook] = clear_bit(self.bb[black][rook], sq_index('h8'))
                    self.bb[black][rook] = set_bit(self.bb[black][rook], sq_index('f8'))
                elif to == sq_index('c8'):
                    # Moving black rook from a8 to d8
                    self.bb[black][rook] = clear_bit(self.bb[black][rook], sq_index('a8'))
                    self.bb[black][rook] = set_bit(self.bb[black][rook], sq_index('d8'))
            
        # Updating en-passant targets
        
        self.en_passant=None
        if p==pawn and abs(to-frm)==16:
            self.en_passant=(to+frm)//2
        
        """Updating castling rights""" 
        
        # King got moved
        if p==king:
            if c==white:
                self.castling &=~3
            else:
                self.castling &=~12 
                
        # Rook moved or rook is captured 
        
        if p==rook:
            if c==white:
                if frm==sq_index('h1'):
                    self.castling &=~1
                if frm==sq_index('a1'):
                    self.castling &=~2
            else:
                if frm==sq_index('h8'):
                    self.castling &=~4
                if frm==sq_index('a8'):
                    self.castling &=~8
                    
        # If a rook got captured adjust the rights of opponent accordingly
            
        if m.capture and m.capture[1]==rook:
            cap_sq=m.to_sq
            if m.capture[0]==white:
                if cap_sq==sq_index('h1'):
                    self.castling &=~1
                if cap_sq==sq_index('a1'):
                    self.castling &=~2
            else:
                if cap_sq==sq_index('h8'):
                    self.castling &=~4
                if cap_sq==sq_index('a8'):
                    self.castling &=~8 
                    
        # Checking if full move or halfmove
        if m.capture or p==pawn:
            self.halfmove=0
        else:
            self.halfmove+=1
        
        if self.side_to_move==black:
            self.fullmove+=1
        self.side_to_move=1-self.side_to_move 
        
        
        self.update_occ()
        self.key=self.compute_key() 
        
    
    # Undoing the move 
    def unmake_move(self):
        snap = self.stack.pop()
        self.bb[white] = snap['bb_w']
        self.bb[black] = snap['bb_b']
        self.castling = snap['castling']
        self.en_passant = snap['ep']
        self.halfmove = snap['half']
        self.fullmove = snap['full']
        self.side_to_move = snap['side']
        self.key = snap['key']
        self.update_occ() 
        
    
    """Attack Detection"""
    def is_square_attacked(self,sq,by):
        
        # Pawn attacks 
        if by==white:
            pawns=self.bb[white][pawn] 
                
            # Checking the bounds 
            if sq-7>=0 and (sq%8)!=7 and bit(pawns,sq-7):
                return True
            if sq - 9 >= 0 and (sq % 8) != 0 and bit(pawns, sq-9):
                return True 
        else:
            pawns=self.bb[black][pawn]
            
            # Checking the boundaries
            if sq + 7 < 64 and (sq % 8) != 0 and bit(pawns, sq+7):
                return True
            if sq + 9 < 64 and (sq % 8) != 7 and bit(pawns, sq+9):
                return True
            
        # Knight attacks
        if KNIGHT_ATTACKS[sq] & self.bb[by][knight]:
            return True
        
        # king
        if KING_ATTACKS[sq] & self.bb[by][king]:
            return True 
        
        
        # Sliding pieces 
        
        for d in (8,-8,1,-1):
            cur=sq 
            while True:
                nxt=cur+d 
                
                if not (0<=nxt < 64):
                    break
                
                if d in (1, -1) and (nxt // 8) != (cur // 8):
                    break
                
                cur=nxt 
                
                if bit(self.occupancies[2],cur):
                    if bit(self.bb[by][rook] | self.bb[by][queen],cur):
                        return True
                    break 
                
        # Bishop/queen diagonals
        for d in (9, 7, -7, -9):
            cur = sq
            while True:
                nxt = cur + d
                if not (0 <= nxt < 64):
                    break
                if abs((nxt % 8) - (cur % 8)) > 1:
                    break
                cur = nxt
                if bit(self.occupancies[2], cur):
                    if bit(self.bb[by][bishop] | self.bb[by][queen], cur):
                        return True
                    break
        return False