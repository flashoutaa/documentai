"""API 依赖（v0.1 无鉴权，预留扩展）。"""
from app.core.database import get_db

__all__ = ["get_db"]
