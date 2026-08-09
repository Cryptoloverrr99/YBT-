from .models import Candle
import math

def true_range(prev_close, c):
    return max(c.high-c.low, abs(c.high-prev_close), abs(c.low-prev_close))

def atr(candles, length):
    out=[float('nan')]*len(candles)
    if len(candles)<length: return out
    trs=[]
    for i,c in enumerate(candles):
        trs.append(c.high-c.low if i==0 else true_range(candles[i-1].close,c))
        if i+1>=length: out[i]=sum(trs[i+1-length:i+1])/length
    return out

def pivot_high(candles, left, right, i):
    if i-left<0 or i+right>=len(candles): return False
    v=candles[i].high
    return all(v>=candles[j].high for j in range(i-left,i)) and all(v>candles[j].high for j in range(i+1,i+right+1))

def pivot_low(candles,left,right,i):
    if i-left<0 or i+right>=len(candles): return False
    v=candles[i].low
    return all(v<=candles[j].low for j in range(i-left,i)) and all(v<candles[j].low for j in range(i+1,i+right+1))

def ema(values,length):
    if not values: return []
    a=2/(length+1); out=[values[0]]
    for v in values[1:]: out.append(a*v+(1-a)*out[-1])
    return out
