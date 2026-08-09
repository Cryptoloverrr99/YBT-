import asyncio,time,logging
from .config import settings
from .deriv_client import DerivPublicClient
from .zone_engine import YBTZoneEngine
from .alignment import find_matching_timeframes,stars_for
from .dedup import AlertDeduplicator
from .notifier import TelegramNotifier
from .models import ZoneAlert
log=logging.getLogger(__name__)

ALLOWED={'forex','commodities','indices','synthetic_index','synthetics','derived'}
class MultiTFScanner:
    def __init__(self):
        self.client=DerivPublicClient(); self.engine=YBTZoneEngine(settings); self.dedup=AlertDeduplicator(); self.notifier=TelegramNotifier(settings.telegram_bot_token,settings.telegram_chat_id)
    async def scan_symbol(self,meta):
        symbol=meta.get('underlying_symbol') or meta.get('symbol'); display=meta.get('underlying_symbol_name') or meta.get('display_name') or symbol
        snapshots={}; atr_map={}; created=[]
        for tf,g in settings.timeframes.items():
            candles=await self.client.candles(symbol,g,settings.history_bars)
            zones,new,metrics=self.engine.analyze(symbol,tf,candles); snapshots[tf]=zones
            atr_map[tf]=self._atr(candles); created += [(z,metrics) for z in new]
        for z,metrics in created:
            matches=find_matching_timeframes(z,snapshots,atr_map,settings.alignment_tolerance_atr)
            a=ZoneAlert(z.key(),display,z.timeframe,z.side,z.price,z.score,stars_for(matches),matches,int(time.time()),metrics['magnet_score'],metrics['freshness'])
            if self.dedup.already_sent(a.zone_id): continue
            await self.notifier.send(a); self.dedup.mark_sent(a.zone_id,a.timestamp)
            log.info('ZONE ALERT %s %s %s %s',display,z.timeframe,z.side,a.stars)
    @staticmethod
    def _atr(candles):
        if not candles:return 0
        n=min(14,len(candles)); return sum(c.high-c.low for c in candles[-n:])/n
    async def run_once(self):
        syms=await self.client.active_symbols()
        selected=[s for s in syms if str(s.get('market','')).lower() in ALLOWED and not int(s.get('is_trading_suspended',0) or 0)]
        log.info('Scanning %d symbols sequentially',len(selected))
        for meta in selected:
            try: await self.scan_symbol(meta)
            except Exception: log.exception('Failed %s',meta.get('underlying_symbol') or meta.get('symbol'))
    async def run_forever(self):
        while True:
            t=time.monotonic()
            try: await self.run_once()
            except Exception: log.exception('Scanner cycle failed')
            await asyncio.sleep(max(1,settings.poll_seconds-(time.monotonic()-t)))
