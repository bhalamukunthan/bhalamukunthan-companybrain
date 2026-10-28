import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import admin
from .auth import router as auth_router
from .chat import router as chat_router
from .database import init_db
from .documents import router as documents_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="CompanyBrain", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router.router)
app.include_router(admin.router)
app.include_router(documents_router.router)
app.include_router(chat_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
