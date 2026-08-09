from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
app=FastAPI(title='Deriv YBT LH Monitor')
@app.get('/health')
async def health(): return {'status':'ok'}
@app.get('/')
async def index(): return FileResponse(Path(__file__).parent.parent/'frontend'/'index.html')
