"""
数据库模型定义
参考 Dayflow 的数据结构设计
"""
from datetime import datetime
from typing import Optional
from enum import Enum


class ChunkStatus(str, Enum):
    """录制片段状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchStatus(str, Enum):
    """批次状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RecordingChunk:
    """录制片段模型"""
    def __init__(
        self,
        id: Optional[int] = None,
        start_ts: int = 0,
        end_ts: int = 0,
        file_path: str = "",
        status: str = ChunkStatus.PENDING,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.file_path = file_path
        self.status = status
        self.created_at = created_at or datetime.now()

    @property
    def duration(self) -> float:
        """获取录制时长（秒）"""
        return self.end_ts - self.start_ts


class Batch:
    """分析批次模型"""
    def __init__(
        self,
        id: Optional[int] = None,
        day: str = "",
        start_ts: int = 0,
        end_ts: int = 0,
        status: str = BatchStatus.PENDING,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.day = day
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.status = status
        self.created_at = created_at or datetime.now()


class Observation:
    """观察记录模型 - 第一阶段 LLM 分析结果"""
    def __init__(
        self,
        id: Optional[int] = None,
        batch_id: int = 0,
        start_ts: int = 0,
        end_ts: int = 0,
        observation: str = "",
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.batch_id = batch_id
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.observation = observation
        self.created_at = created_at or datetime.now()

    @property
    def duration(self) -> float:
        """获取观察时长（秒）"""
        return self.end_ts - self.start_ts


class TimelineCard:
    """时间线卡片模型"""
    def __init__(
        self,
        id: Optional[int] = None,
        batch_id: int = 0,
        title: str = "",
        description: str = "",
        start_ts: int = 0,
        end_ts: int = 0,
        category: str = "",
        video_path: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.batch_id = batch_id
        self.title = title
        self.description = description
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.category = category
        self.video_path = video_path
        self.created_at = created_at or datetime.now()

    @property
    def duration(self) -> float:
        """获取活动时长（秒）"""
        return self.end_ts - self.start_ts


class TokenUsage:
    """Token使用记录模型"""
    def __init__(
        self,
        id: Optional[int] = None,
        request_type: str = "",  # 'transcribe' 或 'generate_cards'
        model: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        batch_id: Optional[int] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.request_type = request_type
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.batch_id = batch_id
        self.created_at = created_at or datetime.now()


# 数据库初始化 SQL
INIT_SQL = """
-- 录制片段表
CREATE TABLE IF NOT EXISTS recording_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_ts INTEGER NOT NULL,
    end_ts INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 分析批次表
CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    start_ts INTEGER NOT NULL,
    end_ts INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 观察记录表（第一阶段 LLM 分析结果）
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    start_ts INTEGER NOT NULL,
    end_ts INTEGER NOT NULL,
    observation TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
);

-- 时间线卡片表（第二阶段 LLM 分析结果）
CREATE TABLE IF NOT EXISTS timeline_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    start_ts INTEGER NOT NULL,
    end_ts INTEGER NOT NULL,
    category TEXT,
    video_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
);

-- 配置表
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'string',
    category TEXT NOT NULL DEFAULT 'general',
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Token使用记录表
CREATE TABLE IF NOT EXISTS token_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_type TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    batch_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE SET NULL
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_chunks_start_ts ON recording_chunks(start_ts);
CREATE INDEX IF NOT EXISTS idx_chunks_status ON recording_chunks(status);
CREATE INDEX IF NOT EXISTS idx_batches_day ON batches(day);
CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status);
CREATE INDEX IF NOT EXISTS idx_observations_batch_id ON observations(batch_id);
CREATE INDEX IF NOT EXISTS idx_observations_start_ts ON observations(start_ts);
CREATE INDEX IF NOT EXISTS idx_timeline_batch_id ON timeline_cards(batch_id);
CREATE INDEX IF NOT EXISTS idx_timeline_start_ts ON timeline_cards(start_ts);
CREATE INDEX IF NOT EXISTS idx_config_category ON config(category);
CREATE INDEX IF NOT EXISTS idx_token_usage_created_at ON token_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_batch_id ON token_usage(batch_id);
"""
