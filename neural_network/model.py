import torch 
import torch.nn as nn 
import torch.nn.functional as F 


class SmallEvalNet(nn.Module):
    """
    Input: (B, C=16, 8, 8)
    Output: (B,) scalar interpreted as centipawns (float)
    """
    
    def __init__(self,in_channels=16,hidden=64):
        super().__init__()
        
        self.conv1=nn.Conv2d(in_channels,hidden,kernel_size=3,padding=1)
        self.bn1=nn.BatchNorm2d(hidden)
        self.conv2=nn.Conv2d(hidden,hidden,kernel_size=3,padding=1)
        self.bn2=nn.BatchNorm2d(hidden)
        self.conv3=nn.Conv2d(hidden,hidden,kernel_size=3,padding=1)
        self.bn3=nn.BatchNorm2d(hidden)
        
        self.fc1=nn.Linear(hidden*8*8,128)
        self.fc2=nn.Linear(128,1)
        
        self._init_weights() 
        
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m,nn.Conv2d):
                nn.init.kaiming_normal_(m.weight,nonlinearity='relu')
                
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m,nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
                    
    
    def forward(self,x):
        x=F.relu(self.bn1(self.conv1(x)))
        x=F.relu(self.bn2(self.conv2(x)))
        x=F.relu(self.bn3(self.conv3(x)))
        x=x.view(x.size(0),-1)
        x=F.relu(self.fc1(x))
        out=self.fc2(x) 
        return out.squeeze(1)
    

def load_model(path=None,device='cpu'):
    dev=torch.device(device if device is not None else 'cpu')
    model=SmallEvalNet(in_channels=16)
    model.to(dev)
    model.eval()
    
    if path:
        state=torch.load(path,map_location=dev)
        
        if isinstance(state,dict) and 'model_state_dict' in state:
            model.load_state_dict(state['model_state_dict'])
        else:
            model.load_state_dict(state)
    
    return model 

                