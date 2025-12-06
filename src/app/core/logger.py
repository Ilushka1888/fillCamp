import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# Цвета ANSI для консольного вывода
class Colors:
    """ANSI коды для цветного вывода в консоли."""

    RESET = "\033[0m"
    BOLD = "\033[1m"

    # Цвета текста
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Яркие цвета
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


class ColoredFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: Colors.BRIGHT_CYAN,
        logging.INFO: Colors.BRIGHT_GREEN,
        logging.WARNING: Colors.BRIGHT_YELLOW,
        logging.ERROR: Colors.BRIGHT_RED,
        logging.CRITICAL: Colors.BOLD + Colors.BRIGHT_RED,
    }

    def __init__(self, fmt: str, use_color: bool = True):
        super().__init__(fmt)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        if self.use_color:
            levelname_original = record.levelname

            color = self.LEVEL_COLORS.get(record.levelno, "")
            record.levelname = f"{color}{record.levelname}{Colors.RESET}"

            formatted = super().format(record)

            record.levelname = levelname_original

            return formatted
        else:
            return super().format(record)


class CampBotLogger:
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        log_dir: str | Path = "logs",
        log_file: Optional[str] = None,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5,
        console_output: bool = True,
        file_output: bool = True,
    ):
        self.name = name
        self.level = level
        self.log_dir = Path(log_dir)
        self.log_file = log_file or "campbot.log"
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.console_output = console_output
        self.file_output = file_output

        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

        self._logger.handlers.clear()

        self._setup_handlers()

    def _setup_handlers(self) -> None:
        console_format = (
            "%(levelname)s\t"
            "%(asctime)s - "
            "%(name)s - "
            "%(message)s"
        )

        file_format = (
            "%(levelname)-8s "
            "%(asctime)s - "
            "%(name)s - "
            "%(funcName)s:%(lineno)d - "
            "%(message)s"
        )

        date_format = "%Y-%m-%d %H:%M:%S"

        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.level)
            console_formatter = ColoredFormatter(
                console_format,
                use_color=True,
            )
            console_formatter.datefmt = date_format
            console_handler.setFormatter(console_formatter)
            self._logger.addHandler(console_handler)

        if self.file_output:
            self.log_dir.mkdir(parents=True, exist_ok=True)

            log_path = self.log_dir / self.log_file

            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(self.level)
            file_formatter = ColoredFormatter(
                file_format,
                use_color=False,
            )
            file_formatter.datefmt = date_format
            file_handler.setFormatter(file_formatter)
            self._logger.addHandler(file_handler)

    def debug(self, message: str, *args, **kwargs) -> None:
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        self._logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        self._logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        kwargs.setdefault("exc_info", True)
        self._logger.error(message, *args, **kwargs)

    warn = warning

    def set_level(self, level: int | str) -> None:
        if isinstance(level, str):
            level = getattr(logging, level.upper())

        self._logger.setLevel(level)
        for handler in self._logger.handlers:
            handler.setLevel(level)

    def get_level(self) -> int:
        return self._logger.level

    @property
    def logger(self) -> logging.Logger:
        return self._logger

_loggers: dict[str, CampBotLogger] = {}


def get_logger(
    name: str,
    level: Optional[int | str] = None,
    **kwargs,
) -> CampBotLogger:
    if name in _loggers:
        return _loggers[name]

    if level is None:
        try:
            from src.app.core.config import config
            level_str = config.LOG_LEVEL.upper()
            level = getattr(logging, level_str, logging.INFO)
        except Exception:
            level = logging.INFO

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    logger = CampBotLogger(name, level=level, **kwargs)
    _loggers[name] = logger

    return logger


def configure_root_logger(
    level: Optional[int | str] = None,
    log_dir: str | Path = "logs",
    log_file: str = "campbot.log",
) -> None:
    if level is None:
        try:
            from src.app.core.config import config
            level_str = config.LOG_LEVEL.upper()
            level = getattr(logging, level_str, logging.INFO)
        except Exception:
            level = logging.INFO

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    root_logger = get_logger("campbot", level=level, log_dir=log_dir, log_file=log_file)

    logging.root.setLevel(level)
