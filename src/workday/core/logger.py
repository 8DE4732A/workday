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
    """过滤Windows上asyncio的无害连接重置错误"""
    def filter(self, record):
        if record.levelno == logging.ERROR:
            error_msg = record.getMessage()
            if (
                '_ProactorBasePipeTransport._call_connection_lost' in error_msg
                and 'WinError 10054' in error_msg
            ):
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
        from platformdirs import user_data_dir
        log_dir = Path(user_data_dir("workday", appauthor=False)) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"workday_{datetime.now().strftime('%Y%m%d')}.log"
        error_log_file = log_dir / f"workday_error_{datetime.now().strftime('%Y%m%d')}.log"

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.handlers.clear()

        detailed_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        simple_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        console_handler.addFilter(IgnoreWindowsAsyncioErrorFilter())
        root_logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        file_handler.addFilter(IgnoreWindowsAsyncioErrorFilter())
        root_logger.addHandler(file_handler)

        error_file_handler = RotatingFileHandler(
            error_log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(detailed_formatter)
        error_file_handler.addFilter(IgnoreWindowsAsyncioErrorFilter())
        root_logger.addHandler(error_file_handler)

        asyncio_logger = logging.getLogger('asyncio')
        asyncio_logger.addFilter(IgnoreWindowsAsyncioErrorFilter())

        self.logger = logging.getLogger('workday')
        self.logger.info("=== Workday Application Started ===")

    def get_logger(self, name: str = None) -> logging.Logger:
        if name:
            return logging.getLogger(f'workday.{name}')
        return logging.getLogger('workday')


# 全局日志管理器实例
log_manager = LogManager()


def get_logger(name: str = None) -> logging.Logger:
    return log_manager.get_logger(name)


logger = get_logger()
