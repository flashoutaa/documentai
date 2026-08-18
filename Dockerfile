# ===== 后端镜像（FastAPI + LangChain + uv）=====
# 基于官方 uv 镜像（内置 uv + Python 3.14）
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 1) 先拷贝依赖清单并安装（利用 Docker 层缓存）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 2) 拷贝应用代码与迁移脚本
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# 3) 运行参数
EXPOSE 8000

# 启动：先建表（Alembic 迁移），再启动 Uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
