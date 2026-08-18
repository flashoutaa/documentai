"""通用枚举与基础 schema。"""
from enum import Enum


class ReviewType(str, Enum):
    """四类审查（require.md 2.1-2.4）。"""

    TYPO = "typo"  # 错别字
    FORMAT = "format"  # 格式
    TERM = "term"  # 专有名词
    POLISH = "polish"  # 句意优化


class SuggestionStatus(str, Enum):
    """建议处理状态（require.md 3.2）。"""

    PENDING = "pending"  # 待处理
    ACCEPTED = "accepted"  # 已接受
    REJECTED = "rejected"  # 已拒绝
    MODIFIED = "modified"  # 已自行修改


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PARSED = "parsed"
    REVIEWED = "reviewed"
    FAILED = "failed"
