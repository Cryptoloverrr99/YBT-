def stars_for(matches): return max(1,min(4,len(matches)))
def find_matching_timeframes(zone,snapshots,atr_map,tolerance_atr):
    matches=[]
    for tf,zones in snapshots.items():
        if tf==zone.timeframe: continue
        tol=max(1e-12,atr_map.get(tf,0)*tolerance_atr)
        for z in zones:
            if z.active and z.side==zone.side and abs(z.price-zone.price)<=tol:
                matches.append(tf); break
    return [zone.timeframe]+matches
