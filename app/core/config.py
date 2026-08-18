"""应用配置：从环境变量 / .env 读取。"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # 项目根目录


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    APP_NAME: str = "Word 文档智能审查系统"
    DEBUG: bool = True

    # 数据库（require.md 5.5：SQLite 开发 → PostgreSQL 生产，仅改此值）
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # 文件目录
    UPLOAD_DIR: str = "./data/uploads"
    EXPORT_DIR: str = "./data/exports"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # LLM（require.md 5.3：模型可配置切换）
    LLM_PROVIDER: str = "mock"  # mock | deepseek | openai | tongyi | ollama
    LLM_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.1

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    DASHSCOPE_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # 审查参数
    CHUNK_MAX_CHARS: int = 1200  # 单块最大字符数（分块审查）

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def upload_dir(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        if not p.is_absolute():
            p = BASE_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def export_dir(self) -> Path:
        p = Path(self.EXPORT_DIR)
        if not p.is_absolute():
            p = BASE_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def sqlite_path(self) -> Path | None:
        """若是 SQLite，返回 db 文件路径（用于依赖注入/建目录）。"""
        if self.DATABASE_URL.startswith("sqlite"):
            import re

            m = re.match(r"sqlite:///(.*)", self.DATABASE_URL)
            if m:
                path = Path(m.group(1))
                if not path.is_absolute():
                    path = BASE_DIR / path
                path.parent.mkdir(parents=True, exist_ok=True)
                return path
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
