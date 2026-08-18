"""API v1 路由聚合。"""
from fastapi import APIRouter

from app.api.v1 import documents, suggestions, tasks, templates, terms

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(documents.router)
api_router.include_router(templates.router)
api_router.include_router(terms.router)
api_router.include_router(tasks.router)
api_router.include_router(suggestions.router)
