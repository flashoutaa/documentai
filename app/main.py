"""应用入口（FastAPI + Uvicorn）。

启动：uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.scripts.seed import ensure_seed_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 首次启动自动写入默认规范模板与内置专有名词（幂等）
    ensure_seed_data()
    logger.info("%s 启动完成（LLM provider=%s, model=%s）",
                settings.APP_NAME, settings.LLM_PROVIDER, settings.LLM_MODEL)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="基于大模型的 Word 文档智能审查系统（FastAPI + LangChain）",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "provider": settings.LLM_PROVIDER}
