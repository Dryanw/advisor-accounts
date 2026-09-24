from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.idempotency_cache import IdempotencyCache
from app.routes import accounts, transfers


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.idempotency_cache = IdempotencyCache(ttl_seconds=86400)
    yield


app = FastAPI(title="advisor-accounts", lifespan=lifespan)
app.include_router(accounts.router)
app.include_router(transfers.router)
