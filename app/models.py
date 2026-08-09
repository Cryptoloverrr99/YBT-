from dataclasses import dataclass, field
import hashlib

@dataclass(frozen=True)
class Candle:
    epoch:int; open:float; high:float; low:float; close:float; volume:float=0.0

@dataclass
class Zone:
    symbol:str; timeframe:str; side:str; price:float; score:float; born_bar:int
    active:bool=True; off_bar:int|None=None; last_update_bar:int|None=None
    def key(self)->str:
        # Stable identity for a newly-created zone. The birth bar is the pivot bar.
        raw=f"{self.symbol}|{self.timeframe}|{self.side}|{self.born_bar}|{self.price:.12g}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

@dataclass
class ZoneAlert:
    zone_id:str; symbol:str; timeframe:str; side:str; price:float; score:float
    stars:int; matching_timeframes:list[str]; timestamp:int; magnet_score:int=0
    freshness:int=0
    def text(self)->str:
        stars='⭐'*self.stars
        tf=', '.join(self.matching_timeframes) if self.matching_timeframes else self.timeframe
        return (f"🚨 ZONE READY\n\nPAIRE : {self.symbol}\nTF DÉCLENCHEUR : {self.timeframe}\n"
                f"STARS : {stars}\nTF CONCERNÉS : {tf}\nTYPE : {self.side.upper()}\n"
                f"ZONE : {self.price}\nHEAT : {self.score:.2f}\nMAGNET : {self.magnet_score}/100\n"
                f"FRESHNESS : {self.freshness}/100")
