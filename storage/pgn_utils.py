# storage/pgn_utils.py
from typing import List, Dict
import time
import datetime

def moves_to_pgn(moves: List[str], metadata: Dict[str,str] = None) -> str:
    
    metadata = metadata or {}
    headers = []
    for k,v in metadata.items():
        headers.append(f'[{k} "{v}"]')
    headers_text = "\n".join(headers)
    body = []
    for i in range(0, len(moves), 2):
        num = i//2 + 1
        white = moves[i]
        black = moves[i+1] if i+1 < len(moves) else ""
        body.append(f"{num}. {white} {black}".strip())
    body_text = " ".join(body)
    res = ""
    if headers_text:
        res += headers_text + "\n\n"
    res += body_text + "\n"
    return res