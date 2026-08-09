import asyncio,json
from typing import Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import websockets
from .models import Candle
from .config import settings

def _with_app_id(url: str, app_id: str) -> str:
    """Ajoute ?app_id=... à l'URL si absent.

    Depuis la migration de l'API Deriv, `app_id` est obligatoire sur
    TOUTES les connexions WebSocket v3 (même pour les endpoints
    publics comme active_symbols / ticks_history). Sans lui, Deriv
    rejette la connexion avec un HTTP 401 avant même le handshake,
    ce qui correspond exactement à l'erreur observée sur Render.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if 'app_id' not in qs and app_id:
        qs['app_id'] = [app_id]
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

class DerivPublicClient:
    def __init__(self,url=None):
        self.url=_with_app_id(url or settings.deriv_ws_url, settings.deriv_app_id)
        self.req=0
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
