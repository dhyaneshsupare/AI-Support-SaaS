import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import auth, bots, chat, documents, users

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    os.makedirs(s.upload_dir, exist_ok=True)
    client = await init_db()
    yield
    await client.close()


app = FastAPI(title="AI Customer Support SaaS", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
for r in (auth.router, users.router, bots.router, documents.router, chat.router):
    app.include_router(r, prefix=API)


@app.get("/health")
async def health():
    return {"status": "ok"}
