import random
import os 
import pickle 
from collections import deque 
import threading 

class ReplayBuffer:
    """Stores (encoded_tensor_bytes, value_target) pairs."""
    def __init__(self,capacity=300000,path=None):
        self.capacity=capacity
        self.buffer=deque(maxlen=capacity)
        self.lock=threading.RLock()
        self.path=path
        
        
    def add(self,encoded_np,value_target):
        with self.lock:
            self.buffer.append((encoded_np,float(value_target)))
            
    
    def sample(self,batch_size):
        with self.lock:
            batch=random.sample(list(self.buffer),min(batch_size,len(self.buffer)))
            
        X=[x[0] for x in batch]
        Y=[x[1] for x in batch]
        return X,Y
    
    def __len__(self):
        return len(self.buffer)
    
    def save(self,filename):
        with open(filename,"wb") as f: 
            pickle.dump(list(self.buffer),f)
    
    def load(self,filename):
        with open(filename,'rb') as f:
            data=pickle.load(f)
        with self.lock:
            self.buffer=deque(data,maxlen=self.capacity)
            