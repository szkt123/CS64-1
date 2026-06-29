from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import infer, runs, train, ranking
import sys
import asyncio


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
app = FastAPI(title='Figure Quality Platform API')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(train.router)
app.include_router(runs.router)
app.include_router(infer.router)
app.include_router(ranking.router)


@app.get('/api/health')
def health():
    return {'ok': True}
