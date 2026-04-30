"""
配置管理模块
优先从数据库读取配置，支持运行时动态修改
"""
import logging
import os
from pathlib import Path
from typing import Any
from dataclasses import dataclass


def get_data_dir() -> Path:
    """返回跨平台用户数据目录，并确保它存在"""
    from platformdirs import user_data_dir
    d = Path(user_data_dir("workday", appauthor=False))
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class RecordingConfig:
    capture_interval: int = 1
    chunk_duration: int = 15
    quality: int = 85
    format: str = "jpg"
    output_dir: str = ""
    monitor_index: int = 0


@dataclass
class AnalysisConfig:
    interval: int = 15
    batch_duration: int = 15
    debug_mode: bool = False


@dataclass
class RetentionConfig:
    days: int = 3


@dataclass
class LLMConfig:
    api_base: str = ""
    api_key: str = ""
    model: str = ""


@dataclass
class DatabaseConfig:
    path: str = ""


class Config:
    """配置管理类 - 优先从数据库读取，支持动态修改"""

    CONFIG_SCHEMA = {
        'recording.capture_interval': ('int', 'recording', '截图间隔（秒）', 1, False),
        'recording.chunk_duration': ('int', 'recording', 'Chunk时长（秒）', 15, False),
        'recording.quality': ('int', 'recording', '图片质量 (1-100)', 85, False),
        'recording.format': ('string', 'recording', '输出格式 (jpg/png/mp4)', 'jpg', False),
        'recording.output_dir': ('string', 'recording', '输出目录', '', False),
        'recording.monitor_index': ('int', 'recording', '显示器索引 (0=全部, 1=主显示器, 2+=其他)', 0, False),
        'analysis.interval': ('int', 'analysis', '分析间隔（分钟）', 15, False),
        'analysis.batch_duration': ('int', 'analysis', '批次时长（分钟）', 15, False),
        'analysis.debug_mode': ('bool', 'analysis', '调试模式（不调用LLM，生成默认总结）', False, False),
        'retention.days': ('int', 'retention', '数据保留天数', 3, False),
        'database.path': ('string', 'database', '数据库文件路径', '', False),
        'llm.api_base': ('string', 'llm', 'API Base URL', '', False),
        'llm.api_key': ('string', 'llm', 'API Key', '', True),
        'llm.model': ('string', 'llm', '模型 ID', '', False),
    }

    SENSITIVE_KEYS = {key for key, (_, _, _, _, is_sensitive) in CONFIG_SCHEMA.items() if is_sensitive}

    @staticmethod
    def mask_value(value: str, show_chars: int = 4) -> str:
        if not value or len(value) <= show_chars * 2:
            return '*' * 8
        prefix = value[:show_chars]
        suffix = value[-show_chars:]
        return f"{prefix}{'*' * min(len(value) - show_chars * 2, 8)}{suffix}"

    @staticmethod
    def is_masked(value: str) -> bool:
        return '*' in value and value.replace('*', '').strip() != ''

    def __init__(self, db_path: str = ""):
        data_dir = get_data_dir()
        self.db_path = db_path or str(data_dir / "workday.db")
        self._default_recordings_dir = str(data_dir / "recordings")
        self._db = None
        self._config_cache: dict = {}
        self._load_config()

    def _get_db(self):
        if self._db is None:
            from workday.core.database import Database
            self._db = Database(self.db_path)
        return self._db

    def _resolve_value(self, key: str, value: Any) -> Any:
        """将 schema 默认值替换为运行时实际路径"""
        if key == 'llm.api_key':
            return os.getenv('ARK_API_KEY', '') or value
        if key == 'recording.output_dir':
            return self._default_recordings_dir
        if key == 'database.path':
            return self.db_path
        return value

    def _load_config(self):
        try:
            db = self._get_db()
            if not db.config_exists():
                self._init_config_from_defaults()
            else:
                self._config_cache = db.get_all_configs()
        except Exception as e:
            logging.error(f"Failed to load config from database: {e}, using default values")
            self._load_defaults_only()

    def _init_config_from_defaults(self):
        from workday.core.logger import get_logger
        _logger = get_logger(__name__)
        _logger.info("Initializing configuration from default values to database...")

        configs = []
        for key, (value_type, category, description, default_value, _) in self.CONFIG_SCHEMA.items():
            value = self._resolve_value(key, default_value)
            configs.append({'key': key, 'value': str(value), 'type': value_type,
                            'category': category, 'description': description})

        db = self._get_db()
        db.set_configs_batch(configs)
        self._config_cache = db.get_all_configs()
        _logger.info(f"Initialized {len(configs)} configuration items to database")

    def _load_defaults_only(self):
        for key, (_, _, _, default_value, _) in self.CONFIG_SCHEMA.items():
            self._config_cache[key] = self._resolve_value(key, default_value)

    def get(self, key: str, default: Any = None) -> Any:
        return self._config_cache.get(key, default)

    def set(self, key: str, value: Any):
        if key not in self.CONFIG_SCHEMA:
            raise ValueError(f"Unknown config key: {key}")
        value_type, category, description, _, is_sensitive = self.CONFIG_SCHEMA[key]
        if is_sensitive and self.is_masked(str(value)):
            from workday.core.logger import get_logger
            get_logger(__name__).warning(f"Skipping update for {key}: value is masked")
            return
        db = self._get_db()
        db.set_config(key, str(value), value_type, category, description)
        if value_type == 'int':
            self._config_cache[key] = int(value)
        elif value_type == 'float':
            self._config_cache[key] = float(value)
        elif value_type == 'bool':
            self._config_cache[key] = str(value).lower() in ('true', '1', 'yes')
        else:
            self._config_cache[key] = value

    def reload(self):
        self._config_cache = {}
        self._load_config()

    @property
    def recording(self) -> RecordingConfig:
        return RecordingConfig(
            capture_interval=self.get('recording.capture_interval', 1),
            chunk_duration=self.get('recording.chunk_duration', 15),
            quality=self.get('recording.quality', 85),
            format=self.get('recording.format', 'jpg'),
            output_dir=self.get('recording.output_dir', self._default_recordings_dir),
            monitor_index=self.get('recording.monitor_index', 0)
        )

    @property
    def analysis(self) -> AnalysisConfig:
        return AnalysisConfig(
            interval=self.get('analysis.interval', 15),
            batch_duration=self.get('analysis.batch_duration', 15),
            debug_mode=self.get('analysis.debug_mode', False)
        )

    @property
    def retention(self) -> RetentionConfig:
        return RetentionConfig(days=self.get('retention.days', 3))

    @property
    def database(self) -> DatabaseConfig:
        return DatabaseConfig(path=self.get('database.path', self.db_path))

    @property
    def llm(self) -> LLMConfig:
        return LLMConfig(
            api_base=self.get('llm.api_base', ''),
            api_key=self.get('llm.api_key', ''),
            model=self.get('llm.model', ''),
        )

    def get_with_mask(self, key: str, mask: bool = True) -> Any:
        value = self._config_cache.get(key)
        if mask and key in self.SENSITIVE_KEYS and value:
            return self.mask_value(str(value))
        return value


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
