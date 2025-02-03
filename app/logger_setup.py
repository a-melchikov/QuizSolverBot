__all__ = [
    "LogConfig",
    "LoggerSetup",
    "LogLevel",
    "get_logger",
]

from dataclasses import dataclass
from enum import Enum
import logging
from logging import (
    Handler,
    Logger,
    getLogger,
    StreamHandler,
)
from logging.handlers import RotatingFileHandler


class LogLevel(Enum):
    """
    Enum representing the log levels.
    """

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    def __str__(self) -> str:
        return self.name


@dataclass
class LogConfig:
    """
    Dataclass for configuring logging settings.

    Attributes:
        level (LogLevel): Global log level for the logger.
        filename (str | None): File name for the log file.
        max_bytes (int): Maximum size of the log file before rotation.
        backup_count (int): Number of backup log files to keep.
        console_level (LogLevel): Log level for console output.
        file_level (LogLevel): Log level for file output.
    """

    level: LogLevel = LogLevel.INFO
    filename: str | None = "../app.log"
    max_bytes: int = 500_000
    backup_count: int = 1
    console_level: LogLevel = LogLevel.DEBUG
    file_level: LogLevel = LogLevel.ERROR

    def __post_init__(self) -> None:
        """
        Validates configuration values after initialization.
        """
        if self.max_bytes <= 0:
            raise ValueError("max_bytes must be greater than 0")
        if self.backup_count < 0:
            raise ValueError("backup_count cannot be negative")


class LoggerSetup:
    """
    Class to configure and initialize a logger.

    Attributes:
        logger (Logger): The configured logger instance.
    """

    def __init__(
        self,
        log_config: LogConfig,
        logger_name: str,
        format_str: str = "%(asctime)s : %(name)s : %(levelname)s : %(message)s",
    ) -> None:
        """
        Initializes the logger with the given configuration.

        Args:
            logger_name (str): Name of the logger.
            format_str (str): Logging format string.
            log_config (LogConfig): Configuration for the logger.
        """
        self.logger: Logger = getLogger(logger_name)
        self._log_config = log_config
        self._format_str = format_str
        self._setup_logger()

    def _setup_logger(self) -> None:
        """
        Configures the logger.
        """
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        self.logger.setLevel(self._log_config.level.value)
        handlers = self._get_handlers()
        for handler in handlers:
            self.logger.addHandler(handler)

    def _get_handlers(self) -> list[Handler]:
        """
        Creates and configures log handlers.
        """
        handlers: list[Handler] = []

        formatter = logging.Formatter(self._format_str)

        if self._log_config.filename:
            file_handler = RotatingFileHandler(
                filename=self._log_config.filename,
                maxBytes=self._log_config.max_bytes,
                backupCount=self._log_config.backup_count,
            )
            file_handler.setLevel(self._log_config.file_level.value)
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)

        console = StreamHandler()
        console.setLevel(self._log_config.console_level.value)
        console.setFormatter(formatter)
        handlers.append(console)

        return handlers

    def restart_logger(self, new_config: LogConfig) -> None:
        """
        Restarts the logger with a new configuration.
        """
        self._log_config = new_config
        self._setup_logger()

    def get_logger(self) -> Logger:
        """
        Returns the configured logger.
        """
        return self.logger


def get_logger(logger_name: str = "default") -> Logger:
    """
    Retrieves a logger with a predefined configuration.
    """
    log_config = LogConfig()
    logger_setup = LoggerSetup(log_config=log_config, logger_name=logger_name)
    return logger_setup.get_logger()


if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.debug("DEBUG message")
    logger.info("INFO message")
    logger.warning("WARNING message")
    logger.error("ERROR message")
    logger.critical("CRITICAL message")