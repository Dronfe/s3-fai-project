import torch 
import torch.nn as nn 
import torch.optim as optim 
from neural_network.model import SmallEvalNet,load_model 
from training.replay_buffer import ReplayBuffer
from training.train_utils import batch_from_samples
import math 
import time 
import logging 
import os 


logger=logging.getLogger(__name__)

class Trainer:
    def __init__(self,replay_buffer,device,model_path):
        self.replay=replay_buffer
        self.device=torch.device(device if device is not None else 'cpu')
        self.model=SmallEvalNet(in_channels=16).to(self.device)
        
        if model_path and os.path.exists(model_path):
            self.model=load_model(model_path,device=self.device) #type: ignore 
            
        self.optimizer=optim.Adam(self.model.parameters(),lr=1e-4)
        self.criterion=nn.MSELoss()
            
    
    def train_epoch(self,batch_size=64,iterations=100,save_path=None):
        # Check for XLA
        is_xla = False
        try:
            import torch_xla.core.xla_model as xm
            if self.device.type == 'xla':
                is_xla = True
        except ImportError:
            pass

        self.model.train()
        for it in range(iterations):
            if len(self.replay)<batch_size:
                logger.warning("Not enough samples in replay buffer")
                break
            
            X_list,Y_list=self.replay.sample(batch_size)
            
            Xb,Yb=batch_from_samples(X_list=X_list,Y_list=Y_list,device=self.device) #type: ignore 
            
            preds=self.model(Xb).view(-1,1)
            
            targets=Yb*1000.0 
            loss=self.criterion(preds,targets)
            self.optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(self.model.parameters(),5.0)
            
            if is_xla:
                xm.optimizer_step(self.optimizer)
            else:
                self.optimizer.step()
                
            if it%1==0:
                # For XLA, we might want to print less frequently or use xm.master_print
                if is_xla:
                    xm.master_print(f"Train iteration {it}/{iterations} loss={loss.item()}")
                else:
                    logger.info(f"Train iteration {it}/{iterations} loss={loss.item()}")
            
            if save_path:
                if is_xla:
                    xm.save(self.model.state_dict(), save_path)
                else:
                    torch.save(self.model.state_dict(),save_path)
                logger.info(f"Model saved to {save_path}")
                
    def evaluate_on_samples(self,X_list,Y_list):
        self.model.eval()
        with torch.no_grad():
            Xb,Yb=batch_from_samples(X_list=X_list,Y_list=Y_list,device=self.device) #type: ignore 
            preds=self.model(Xb).view(-1,1) 
            
            # convert preds to numpy and compare MSE
            mse=((preds.cpu().numpy() -(Yb.cpu().numpy()*1000.0))**2).mean()
            return mse