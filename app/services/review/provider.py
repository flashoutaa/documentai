"""LLM 模型工厂（require.md 5.3：模型可配置切换）。

- provider=mock：不调用外部模型，各链走内置规则引擎，演示全流程
- provider=deepseek：OpenAI 兼容协议（base_url=https://api.deepseek.com）
- provider=openai / tongyi / ollama：对应官方接入
- 未配置 API Key 时自动降级为 mock，保证系统始终可用
"""
from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings

logger = logging.getLogger(__name__)


def resolve_provider() -> str:
    """根据配置与密钥可用性，返回实际生效的 provider。"""
    p = settings.LLM_PROVIDER.strip().lower()
    if p == "mock":
        return "mock"
    if p == "deepseek" and settings.DEEPSEEK_API_KEY:
        return "deepseek"
    if p == "openai" and settings.OPENAI_API_KEY:
        return "openai"
    if p == "tongyi" and settings.DASHSCOPE_API_KEY:
        return "tongyi"
    if p == "ollama":
        return "ollama"
    if p in ("deepseek", "openai", "tongyi"):
        logger.warning("provider=%s 未配置 API Key，降级为 mock 模式", p)
        return "mock"
    logger.warning("未知 provider=%s，降级为 mock 模式", p)
    return "mock"


def get_chat_model() -> BaseChatModel | None:
    """返回 LangChain Chat 模型；mock 模式返回 None（调用方走规则引擎）。"""
    provider = resolve_provider()

    if provider == "deepseek":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.LLM_MODEL or "deepseek-chat",
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.LLM_MODEL or "gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL or None,
            temperature=settings.LLM_TEMPERATURE,
        )
    if provider == "tongyi":
        from langchain_community.chat_models.tongyi import ChatTongyi

        return ChatTongyi(
            model=settings.LLM_MODEL or "qwen-plus",
            api_key=settings.DASHSCOPE_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.LLM_MODEL or "qwen2.5:7b",
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
        )
    return None


def llm_enabled() -> bool:
    return get_chat_model() is not None
