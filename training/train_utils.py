import torch 
import numpy as np 

def batch_from_samples(X_list,Y_list,device='cpu'):
    """
    X_list: list of numpy arrays shape (C,8,8)
    Y_list: list of floats
    """ 
    X_arr=np.stack(X_list,axis=0).astype('float32')    
    y_arr=np.array(Y_list,dtype='float32').reshape(-1,1)
    X_t=torch.from_numpy(X_arr).to(device)
    Y_t=torch.from_numpy(y_arr).to(device)
    
    return X_t,Y_t 

