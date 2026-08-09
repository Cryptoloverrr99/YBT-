from .models import Candle, Zone
from .indicators import atr, pivot_high, pivot_low, ema
import math

class YBTZoneEngine:
    """Faithful Python implementation of the computational parts of YBT LH v2.2.
    Chart-only colors/boxes/labels are intentionally excluded; scoring, clustering,
    freshness, lifecycle and new-zone creation follow the supplied Pine source.
    """
    def __init__(self,s): self.s=s

    def _age_factor(self, born, last):
        if not self.s.use_age_weight: return 1.0
        age=max(0,last-born)
        return max(.55,1-min(1,age/self.s.freshness_memory_horizon)*.35)
    def _visual_score(self,z,last): return z.score*self._age_factor(z.born_bar,last)
    def _upsert(self,zones,side,price,born,boost,atrv,last):
        dist=atrv*self.s.cluster_merge_atr
        best=None
        for z in zones:
            if z.active and z.side==side and abs(z.price-price)<=dist:
                if best is None or abs(z.price-price)<abs(best.price-price): best=z
        if best:
            old=best.score; best.score=old+boost; best.price=(best.price*old+price*boost)/best.score; best.last_update_bar=last
            return None
        if len(zones)>=self.s.max_zones:
            inactive=[z for z in zones if not z.active]
            victim=min(inactive,key=lambda z:z.born_bar) if inactive else min(zones,key=lambda z:(self._visual_score(z,last),z.born_bar))
            zones.remove(victim)
        z=Zone('', '', side, price, float(boost), born, True, None, last)
        zones.append(z); return z

    def analyze(self,symbol,timeframe,candles):
        if len(candles)<max(self.s.pivot_left_bars+self.s.pivot_right_bars+5,self.s.atr_length+5): return [],[]
        a=atr(candles,self.s.atr_length); zones=[]; created=[]; last=len(candles)-1
        for i in range(self.s.pivot_left_bars,last-self.s.pivot_right_bars+1):
            av=a[i] if i<len(a) and math.isfinite(a[i]) else max(candles[i].high-candles[i].low,1e-12)
            ph=pivot_high(candles,self.s.pivot_left_bars,self.s.pivot_right_bars,i)
            pl=pivot_low(candles,self.s.pivot_left_bars,self.s.pivot_right_bars,i)
            boost=1
            if self.s.use_volume_weight:
                pv=candles[i].volume
                start=max(0,i-49); vols=[x.volume for x in candles[start:i+1] if x.volume>0]
                sma=sum(vols)/len(vols) if vols else 0
                ratio=pv/sma if sma>0 else 1
                boost=3 if ratio>2.5 else 2 if ratio>1.2 else 1
            if ph:
                z=self._upsert(zones,'upper',candles[i].high,i,boost,av,last)
                if z: z.symbol=symbol; z.timeframe=timeframe; created.append(z)
            if pl:
                z=self._upsert(zones,'lower',candles[i].low,i,boost,av,last)
                if z: z.symbol=symbol; z.timeframe=timeframe; created.append(z)
        # Lifecycle on the latest completed candle, as in Pine.
        c=candles[-1]
        for z in list(zones):
            if z.active and self.s.active_score_decay>0: z.score=max(0,z.score-self.s.active_score_decay)
            swept=z.active and ((z.side=='upper' and c.high>=z.price) or (z.side=='lower' and c.low<=z.price))
            if swept:
                z.active=False; z.off_bar=last; z.score=max(.15,z.score*self.s.faded_score_factor)
            if z.score<.15 or (not z.active and z.off_bar is not None and last-z.off_bar>self.s.purge_faded_zones_after):
                if z in created: created.remove(z)
                zones.remove(z)
        created=[z for z in created if z.score>=self.s.new_zone_alert_min_score]
        # Magnet/readiness metrics based on final field.
        metrics=self.field_metrics(candles,zones)
        return zones,created,metrics

    def field_metrics(self,candles,zones):
        if not candles: return {'magnet_score':0,'freshness':0,'field_bias':0}
        close=candles[-1].close; last=len(candles)-1
        active=[z for z in zones if z.active and z.score>=self.s.minimum_heat_score_to_show]
        if not active:return {'magnet_score':0,'freshness':0,'field_bias':0}
        av=atr(candles,self.s.atr_length); a=av[-1] if av and math.isfinite(av[-1]) else max(candles[-1].high-candles[-1].low,1e-12)
        upper=[z for z in active if z.side=='upper']; lower=[z for z in active if z.side=='lower']
        def nearest(arr,side):
            if not arr:return None
            valid=[z for z in arr if (z.price>=close if side=='upper' else z.price<=close)]
            if not valid: valid=arr
            return min(valid,key=lambda z:abs(z.price-close))
        nu=nearest(upper,'upper'); nl=nearest(lower,'lower')
        ud=abs(nu.price-close) if nu else None; ld=abs(nl.price-close) if nl else None
        up=(nu.score*max(0,1-min(1,ud/(a*self.s.pressure_span_atr)))) if nu and a else 0
        lo=(nl.score*max(0,1-min(1,ld/(a*self.s.pressure_span_atr)))) if nl and a else 0
        total=up+lo; bias=(up-lo)/total*100 if total else 0
        upper_heat=sum(self._visual_score(z,last) for z in upper); lower_heat=sum(self._visual_score(z,last) for z in lower)
        freshness=sum(((self._age_factor(z.born_bar,last)-.55)/.45*100)*z.score for z in active)/sum(z.score for z in active)
        heat=min(35,(upper_heat+lower_heat)/max(1,self.s.visual_saturation_score*2)*35)
        prox=max((max(0,1-min(1,ud/(a*self.s.pressure_span_atr))) if ud is not None else 0),(max(0,1-min(1,ld/(a*self.s.pressure_span_atr))) if ld is not None else 0))*25
        biaspart=min(12,abs(bias)/100*12); freshnesspart=freshness*.20
        closes=[x.close for x in candles]; em=ema(closes,self.s.trend_context_length); trend=(em[-1]-em[-6]) if len(em)>6 else 0
        trendside=1 if trend>a*.03 else -1 if trend<-a*.03 else 0
        dominant=1 if bias>=0 else -1
        trendpart=8 if trendside==0 or abs(bias)<15 else (8 if trendside==dominant else 4)
        score=round(min(100,heat+prox+freshnesspart+biaspart+trendpart))
        return {'magnet_score':int(score),'freshness':int(round(freshness)),'field_bias':bias}
