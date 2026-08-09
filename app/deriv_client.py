import asyncio,json
from typing import Any
import websockets
from .models import Candle
from .config import settings

class DerivPublicClient:
    def __init__(self,url=None): self.url=url or settings.deriv_ws_url; self.req=0
    async def _request(self,payload):
        self.req+=1; payload={**payload,'req_id':self.req}
        async with websockets.connect(self.url,ping_interval=20,ping_timeout=20,close_timeout=5,max_size=8_000_000) as ws:
            await ws.send(json.dumps(payload))
            while True:
                d=json.loads(await asyncio.wait_for(ws.recv(),30))
                if d.get('req_id')==self.req or d.get('msg_type') in {'active_symbols','candles','history'}:
                    if 'error' in d: raise RuntimeError(d['error'].get('message','Deriv API error'))
                    return d
    async def active_symbols(self):
        d=await self._request({'active_symbols':'full'}); return d.get('active_symbols',[])
    async def candles(self,symbol,granularity,count):
        d=await self._request({'ticks_history':symbol,'end':'latest','count':count,'granularity':granularity,'style':'candles','subscribe':0})
        raw=d.get('candles',[])
        return [Candle(int(x.get('epoch',x.get('open_time'))),float(x['open']),float(x['high']),float(x['low']),float(x['close']),float(x.get('volume',0) or 0)) for x in raw]
