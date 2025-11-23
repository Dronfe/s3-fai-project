import random 

class Zobrist:
    def __init__(self):
        random.seed(0xC0FFEE)
        self.piece_keys=[[[self._r64() for _ in range(64)] for _ in range(6)] for _ in range(2)]
        self.side_key=self._r64()
        self.castle_keys=[self._r64() for _ in range(16)]
        self.ep_keys=[self._r64() for _ in range(8)]
        
    def _r64(self):
        return random.getrandbits(64)