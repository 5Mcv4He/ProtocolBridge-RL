"""Stimulus values vary independently of candidate code; frame boundaries are obligations."""
import random

def corpus(mode, phase):
    if mode not in ('byte','word') or phase not in ('public','terminal','evaluation'):
        raise ValueError('Unknown contract or split')
    rng=random.Random({'public':4021,'terminal':8123,'evaluation':12011}[phase])
    lengths=[1,2,3,4,7,16,17,1]
    frames=[]
    patterns=[0,255,1,128,85,170,127,254]
    for i,n in enumerate(lengths):
        frames.append([patterns[(i+j)%len(patterns)] if j<2 else rng.randrange(256) for j in range(n)])
    return frames

def encode(mode, frames):
    count=sum(len(f) if mode=='byte' else len(f)//2 for f in frames)
    return f'{int(mode=="word")} {len(frames)} {sum(map(len,frames))} {count}\n'+''.join(str(len(f))+' '+' '.join(map(str,f))+'\n' for f in frames)
