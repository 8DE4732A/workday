"""
日志管理模块
统一的日志配置，同时输出到控制台和文件
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler


class IgnoreWindowsAsyncioErrorFilter(logging.Filter):
    """
    过滤Windows上asyncio的无害连接重置错误

    这些错误通常发生在客户端（浏览器）主动关闭连接时，
    是正常行为，不应该作为ERROR级别记录
    """
    def filter(self, record):
        # 过滤掉特定的Windows asyncio错误
        if record.levelno == logging.ERROR:
            error_msg = record.getMessage()
            # 检查是否是asyncio的连接关闭错误
            if (
                '_ProactorBasePipeTransport._call_connection_lost' in error_msg
                and 'WinError 10054' in error_msg
            ):
                # 降级为DEBUG级别，不完全忽略
                record.levelno = logging.DEBUG
                record.levelname = 'DEBUG'
                return True
        return True


class LogManager:
    """日志管理器"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._setup_logging()
            LogManager._initialized = True

    def _setup_logging(self):
        """设置日志配置"""
        # 创建日志目录
        log_dir = Path("./logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # 日志文件路径
        log_file = log_dir / f"workday_{datetime.now().strftime('%Y%m%d')}.log"
        error_log_file = log_dir / f"workday_error_{datetime.now().strftime('%Y%m%d')}.log"

        # 获取根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # 清除现有的处理器
        root_logger.handlers.clear()

        # 创建格式化器
        detailed_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        simple_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )

        # 控制台处理器 - 使用简单格式
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        console_handler.addFilter(IgnoreWindowsAsyncioErrorFilter())
        root_logger.addHandler(console_handler)

        # 文件处理器 - 使用详细格式，支持文件轮转
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        file_handler.addFilter(IgnoreWindowsAsyncioErrorFilter())
        root_logger.addHandler(file_handler)

        # ERROR 级别专用文件处理器 - 单独记录错误日志
        error_file_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(detailed_formatter)
        error_file_handler.addFilter(IgnoreWindowsAsyncioErrorFilter())
        root_logger.addHandler(error_file_handler)

        # 为asyncio日志添加过滤器（Windows特定）
        asyncio_logger = logging.getLogger('asyncio')
        asyncio_logger.addFilter(IgnoreWindowsAsyncioErrorFilter())

        # 创建应用专用日志记录器
        self.logger = logging.getLogger('workday')
        self.logger.info("=== Workday Application Started ===")

    def get_logger(self, name: str = None) -> logging.Logger:
        """
        获取日志记录器

        Args:
            name: 模块名称，如果为 None 则返回应用根日志记录器

        Returns:
            Logger 实例
        """
        if name:
            return logging.getLogger(f'workday.{name}')
        return logging.getLogger('workday')


# 全局日志管理器实例
log_manager = LogManager()


def get_logger(name: str = None) -> logging.Logger:
    """
    便捷函数：获取日志记录器

    Usage:
        from logger import get_logger
        logger = get_logger(__name__)
        logger.info("This is an info message")

    Args:
        name: 模块名称

    Returns:
        Logger 实���
    """
    return log_manager.get_logger(name)


# 为了向后兼容，也可以直接导入 logger
logger = get_logger()
