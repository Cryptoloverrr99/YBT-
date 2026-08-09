import httpx
from .models import ZoneAlert
class TelegramNotifier:
    def __init__(self,token,chat_id): self.token=token; self.chat_id=chat_id
    async def send(self,a:ZoneAlert):
        if not self.token or not self.chat_id: raise RuntimeError('TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not configured')
        url=f'https://api.telegram.org/bot{self.token}/sendMessage'
        async with httpx.AsyncClient(timeout=20) as c:
            r=await c.post(url,json={'chat_id':self.chat_id,'text':a.text()}); r.raise_for_status()
