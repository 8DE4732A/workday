"""
配置管理模块
优先从数据库读取配置，支持运行时动态修改
如果数据库中没有配置，则使用 CONFIG_SCHEMA 中定义的默认值初始化
"""
import os
from typing import Any, Dict
from dataclasses import dataclass

# 延迟导入 Database 以避免循环依赖
# from database import Database


@dataclass
class RecordingConfig:
    """录制配置"""
    capture_interval: int = 1
    chunk_duration: int = 15
    quality: int = 85
    format: str = "jpg"
    output_dir: str = "./recordings"
    monitor_index: int = 0  # 0 = 所有显示器，1 = 主显示器，2+ = 其他显示器


@dataclass
class AnalysisConfig:
    """分析配置"""
    interval: int = 15
    batch_duration: int = 15
    model: str = "ep-20251120104157-fxtrj"
    prompt: str = ""
    debug_mode: bool = False


@dataclass
class RetentionConfig:
    """数据保留配置"""
    days: int = 3


@dataclass
class APIConfig:
    """API 服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True


@dataclass
class DatabaseConfig:
    """数据库配置"""
    path: str = "./workday.db"


@dataclass
class SecretsConfig:
    """敏感信息配置（API Keys等）"""
    ark_api_key: str = ""


class Config:
    """配置管理类 - 优先从数据库读取，支持动态修改"""

    # 配置项定义：key -> (type, category, description, default_value, is_sensitive)
    CONFIG_SCHEMA = {
        # Recording
        'recording.capture_interval': ('int', 'recording', '截图间隔（秒）', 1, False),
        'recording.chunk_duration': ('int', 'recording', 'Chunk时长（秒）', 15, False),
        'recording.quality': ('int', 'recording', '图片质量 (1-100)', 85, False),
        'recording.format': ('string', 'recording', '输出格式 (jpg/png/mp4)', 'jpg', False),
        'recording.output_dir': ('string', 'recording', '输出目录', './recordings', False),
        'recording.monitor_index': ('int', 'recording', '显示器索引 (0=全部, 1=主显示器, 2+=其他)', 0, False),

        # Analysis
        'analysis.interval': ('int', 'analysis', '分析间隔（分钟）', 15, False),
        'analysis.batch_duration': ('int', 'analysis', '批次时长（分钟）', 15, False),
        'analysis.model': ('string', 'analysis', 'AI模型名称', 'ep-20251120104157-fxtrj', False),
        'analysis.debug_mode': ('bool', 'analysis', '调试模式（不调用LLM，生成默认总结）', False, False),

        # Retention
        'retention.days': ('int', 'retention', '数据保留天数', 3, False),

        # API
        'api.host': ('string', 'api', 'API监听地址', '0.0.0.0', False),
        'api.port': ('int', 'api', 'API监听端口', 8000, False),
        'api.debug': ('bool', 'api', '调试模式', True, False),

        # Database
        'database.path': ('string', 'database', '数据库文件路径', './workday.db', False),

        # Secrets (敏感信息)
        'secrets.ark_api_key': ('string', 'secrets', 'ARK API密钥', '', True),
    }

    # 敏感配置项列表（用于快速判断）
    SENSITIVE_KEYS = {key for key, (_, _, _, _, is_sensitive) in CONFIG_SCHEMA.items() if is_sensitive}

    @staticmethod
    def mask_value(value: str, show_chars: int = 4) -> str:
        """
        掩码敏感值

        Args:
            value: 原始值
            show_chars: 显示前后各多少个字符

        Returns:
            掩码后的值
        """
        if not value or len(value) <= show_chars * 2:
            return '*' * 8  # 如果值太短，全部掩码

        prefix = value[:show_chars]
        suffix = value[-show_chars:]
        masked_length = len(value) - show_chars * 2

        return f"{prefix}{'*' * min(masked_length, 8)}{suffix}"

    @staticmethod
    def is_masked(value: str) -> bool:
        """
        判断值是否已被掩码

        Args:
            value: 值

        Returns:
            是否已掩码
        """
        return '*' in value and not value.replace('*', '').strip() == ''

    def __init__(self, db_path: str = "./workday.db"):
        self.db_path = db_path
        self._db = None
        self._config_cache = {}
        self._load_config()

    def _get_db(self):
        """延迟初始化数据库连接"""
        if self._db is None:
            # 延迟导入以避免循环依赖
            from database import Database
            self._db = Database(self.db_path)
        return self._db

    def _load_config(self):
        """加载配置：优先从数据库，否则从默认值初始化"""
        try:
            db = self._get_db()

            # 检查数据库中是否已有配置
            if not db.config_exists():
                # 首次运行，从默认值和环境变量初始化数据库
                self._init_config_from_defaults()
            else:
                # 从数据库加载配置
                self._config_cache = db.get_all_configs()

        except Exception as e:
            # 如果数据库加载失败，回退到默认值
            import logging
            logging.error(f"Failed to load config from database: {e}, using default values")
            self._load_defaults_only()

    def _init_config_from_defaults(self):
        """从 CONFIG_SCHEMA 默认值和环境变量初始化配置到数据库"""
        from logger import get_logger
        logger = get_logger(__name__)

        logger.info("Initializing configuration from default values to database...")

        # 读取环境变量
        env_api_key = os.getenv('ARK_API_KEY', '')

        # 准备配置列表
        configs = []

        for key, (value_type, category, description, default_value, is_sensitive) in self.CONFIG_SCHEMA.items():
            # 使用默认值
            value = default_value

            # 如果是 API Key，优先使用环境变量
            if key == 'secrets.ark_api_key' and env_api_key:
                value = env_api_key

            # 转换为字符串存储
            value_str = str(value)

            configs.append({
                'key': key,
                'value': value_str,
                'type': value_type,
                'category': category,
                'description': description
            })

        # 批量写入数据库
        db = self._get_db()
        db.set_configs_batch(configs)

        # 重新加载到缓存
        self._config_cache = db.get_all_configs()

        logger.info(f"Initialized {len(configs)} configuration items to database")
        if env_api_key:
            logger.info("ARK API Key loaded from environment variable")
        else:
            logger.warning("ARK API Key not found in environment variable, using empty default")

    def _load_defaults_only(self):
        """仅从默认值加载配置（回退方案）"""
        # 构建配置缓存
        for key, (value_type, category, description, default_value, is_sensitive) in self.CONFIG_SCHEMA.items():
            value = default_value

            # 如果是 API Key，尝试从环境变量获取
            if key == 'secrets.ark_api_key':
                value = os.getenv('ARK_API_KEY', '')

            self._config_cache[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键（如 'recording.capture_interval'）
            default: 默认值

        Returns:
            配置值
        """
        return self._config_cache.get(key, default)

    def set(self, key: str, value: Any):
        """
        设置配置项（更新数据库和缓存）

        Args:
            key: 配置键
            value: 配置值
        """
        if key not in self.CONFIG_SCHEMA:
            raise ValueError(f"Unknown config key: {key}")

        value_type, category, description, _, is_sensitive = self.CONFIG_SCHEMA[key]

        # 如果是敏感配置且值被掩码，则不更新（保持原值）
        if is_sensitive and self.is_masked(str(value)):
            from logger import get_logger
            logger = get_logger(__name__)
            logger.warning(f"Skipping update for {key}: value is masked")
            return

        # 转换为字符串
        value_str = str(value)

        # 更新数据库
        db = self._get_db()
        db.set_config(key, value_str, value_type, category, description)

        # 更新缓存
        if value_type == 'int':
            self._config_cache[key] = int(value)
        elif value_type == 'float':
            self._config_cache[key] = float(value)
        elif value_type == 'bool':
            self._config_cache[key] = str(value).lower() in ('true', '1', 'yes')
        else:
            self._config_cache[key] = value

    def reload(self):
        """重新加载配置"""
        self._config_cache = {}
        self._load_config()

    @property
    def recording(self) -> RecordingConfig:
        """获取录制配置"""
        return RecordingConfig(
            capture_interval=self.get('recording.capture_interval', 1),
            chunk_duration=self.get('recording.chunk_duration', 15),
            quality=self.get('recording.quality', 85),
            format=self.get('recording.format', 'jpg'),
            output_dir=self.get('recording.output_dir', './recordings'),
            monitor_index=self.get('recording.monitor_index', 0)
        )

    @property
    def analysis(self) -> AnalysisConfig:
        """获取分析配置"""
        return AnalysisConfig(
            interval=self.get('analysis.interval', 15),
            batch_duration=self.get('analysis.batch_duration', 15),
            model=self.get('analysis.model', 'ep-20251120104157-fxtrj'),
            prompt=self.get('analysis.prompt', ''),
            debug_mode=self.get('analysis.debug_mode', False)
        )

    @property
    def retention(self) -> RetentionConfig:
        """获取数据保留配置"""
        return RetentionConfig(
            days=self.get('retention.days', 3)
        )

    @property
    def api(self) -> APIConfig:
        """获取 API 配置"""
        return APIConfig(
            host=self.get('api.host', '0.0.0.0'),
            port=self.get('api.port', 8000),
            debug=self.get('api.debug', True)
        )

    @property
    def database(self) -> DatabaseConfig:
        """获取数据库配置"""
        return DatabaseConfig(
            path=self.get('database.path', './workday.db')
        )

    @property
    def secrets(self) -> SecretsConfig:
        """获取敏感信息配置"""
        return SecretsConfig(
            ark_api_key=self.get('secrets.ark_api_key', '')
        )

    def to_dict(self, mask_sensitive: bool = False) -> Dict[str, Any]:
        """
        导出配置为嵌套字典

        Args:
            mask_sensitive: 是否掩码敏感信息

        Returns:
            嵌套的配置字典
        """
        result = {}

        for key, value in self._config_cache.items():
            # 掩码敏感值
            if mask_sensitive and key in self.SENSITIVE_KEYS and value:
                value = self.mask_value(str(value))

            parts = key.split('.')
            current = result

            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = value
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

        return result

    def get_all_with_metadata(self, mask_sensitive: bool = True) -> Dict[str, dict]:
        """
        获取所有配置及其元数据

        Args:
            mask_sensitive: 是否掩码敏感信息

        Returns:
            配置字典，key -> metadata
        """
        db = self._get_db()
        all_configs = {}

        for key in self.CONFIG_SCHEMA.keys():
            config_item = db.get_config(key)
            if config_item:
                # 如果是敏感配置且需要掩码
                if mask_sensitive and key in self.SENSITIVE_KEYS:
                    config_item = config_item.copy()  # 复制以避免修改原数据
                    config_item['value'] = self.mask_value(config_item['value'])
                    config_item['is_sensitive'] = True
                else:
                    config_item['is_sensitive'] = False

                all_configs[key] = config_item
            else:
                # 如果数据库中没有，使用缓存值
                value_type, category, description, default_value, is_sensitive = self.CONFIG_SCHEMA[key]
                value = str(self._config_cache.get(key, default_value))

                # 掩码敏感值
                if mask_sensitive and is_sensitive:
                    value = self.mask_value(value)

                all_configs[key] = {
                    'key': key,
                    'value': value,
                    'type': value_type,
                    'category': category,
                    'description': description,
                    'is_sensitive': is_sensitive
                }

        return all_configs

    def get_with_mask(self, key: str, mask: bool = True) -> Any:
        """
        获取配置项（可选掩码）

        Args:
            key: 配置键
            mask: 是否掩码（仅对敏感信息有效）

        Returns:
            配置值
        """
        value = self._config_cache.get(key)

        if mask and key in self.SENSITIVE_KEYS and value:
            return self.mask_value(str(value))

        return value


# 全局配置实例
config = Config()
