import os 
from dotenv import load_dotenv
import torch

load_dotenv() 

# Lazy importing the model 
try:
    from neural_network.encode import encode_board 
    from neural_network.model import load_model 
    torch_available=True 
except Exception:
    torch_available=False 
    
    
# Get model path and device via env 
model_path=os.getenv('CHESS_NN_MODEL')
device=os.getenv('DEVICE')

_model=None

def set_active_model(model):
    global _model
    _model = model

def _get_model():
    global _model 
    if _model is not None:
        return _model 
    
    if not torch_available:
        _model=None
        return None 

    try:
        _model=load_model(model_path,device=device) #type: ignore 
        return _model 
    except Exception:
        _model=None
        return None 
    
def nn_raw_eval(board):
    model=_get_model()
    if model is None:
        raise RuntimeError("Model is not available")
    # Use the device of the model parameters
    device = next(model.parameters()).device
    tensor=encode_board(board,device=device)
    
    with torch.no_grad():
        out=model(tensor)
        val=float(out.detach().cpu().item())
    return val 


def nn_evaluate(board):
    
    try:
        from search.minimax import evaluate_simple #type: ignore
    except Exception:
        
        def evaluate_simple(b):
            s=0
            try:
                for color in (0,1):
                    sign=1 if color==0 else -1 
                    for p in range(6):
                        bb=b.bb[color][p]
                        while bb:
                            lsb=bb & -bb 
                            sq=lsb.bit_length()-1
                            bb &=bb-1 
                            
                            vals=[100, 320, 330, 500, 900, 20000]
                            s+=sign*vals[p]
            except Exception:
                s=0
            return s
        
    classical_score=evaluate_simple(board)
    
    nn_score=None
    
    try:
        if torch_available:
            nn_score=nn_raw_eval(board)
    except Exception:
        nn_score=None 
        
    if nn_score is None:
        
        return int(round(classical_score))
    blended=0.7*float(nn_score)+0.3*float(classical_score)
    
    return int(round(blended))