import asyncio,logging,os
import uvicorn
from .scanner import MultiTFScanner
from .api import app as fastapi_app

logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')

async def run_http_server():
    """Petit serveur HTTP pour satisfaire le port-check de Render
    sur le plan gratuit (Web Service). Ne fait rien d'autre que
    répondre /health ; le vrai travail se fait dans le scanner."""
    port = int(os.getenv('PORT', '10000'))
    config = uvicorn.Config(fastapi_app, host='0.0.0.0', port=port, log_level='warning')
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    await asyncio.gather(
        run_http_server(),
        MultiTFScanner().run_forever(),
    )

if __name__=='__main__': asyncio.run(main())
