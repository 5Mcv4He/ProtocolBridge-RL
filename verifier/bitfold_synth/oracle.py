"""Integer semantics, independent of reference RTL expressions and DC elaboration."""
import random

def value(mode,data):
    if type(data) is not int or not 0<=data<256:raise ValueError('Byte required')
    bits=format(data,'08b')
    if mode=='population':return bits.count('1')
    if mode=='trailing_zero':return len(bits)-len(bits.rstrip('0'))
    raise ValueError('Unknown bit operation')

def corpus(mode,phase):
    seeds={'public':1307,'terminal':3313,'evaluation':5323}
    if phase not in seeds:raise ValueError('Unknown phase')
    values=list(range(256));random.Random(seeds[phase]).shuffle(values)
    # Every input in ascending, descending and shuffled predecessor contexts.
    return [(x,value(mode,x)) for x in list(range(256))+list(range(255,-1,-1))+values]
