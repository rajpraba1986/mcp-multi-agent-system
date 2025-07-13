"""
Logging setup and utilities for MCP Toolbox integration.

This module provides centralized logging configuration and utilities
for the entire application.
"""

import logging
import logging.config
import sys
from typing import Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime

import structlog


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
    include_timestamp: bool = True,
    include_caller: bool = False
) -> None:
    """
    Set up application logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        json_format: Whether to use JSON formatting
        include_timestamp: Whether to include timestamps
        include_caller: Whether to include caller information
    """
    # Convert level string to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso") if include_timestamp else lambda _, __, event_dict: event_dict,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if json_format else structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Create formatters
    if json_format:
        formatter = JsonFormatter(include_timestamp=include_timestamp, include_caller=include_caller)
    else:
        format_string = ""
        if include_timestamp:
            format_string += "%(asctime)s - "
        format_string += "%(name)s - %(levelname)s"
        if include_caller:
            format_string += " - %(filename)s:%(lineno)d"
        format_string += " - %(message)s"
        
        formatter = logging.Formatter(format_string)
    
    # Create handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        # Ensure log directory exists
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        force=True
    )
    
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    
    # Create application logger
    logger = logging.getLogger("mcp_toolbox_app")
    logger.info(f"Logging configured with level: {level}")


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_timestamp: bool = True, include_caller: bool = False):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_caller = include_caller
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if self.include_timestamp:
            log_entry["timestamp"] = datetime.fromtimestamp(record.created).isoformat()
        
        if self.include_caller:
            log_entry["file"] = record.filename
            log_entry["line"] = record.lineno
            log_entry["function"] = record.funcName
        
        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class LoggingMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Configured logger
    """
    return logging.getLogger(name)


def log_function_call(func):
    """
    Decorator to log function calls.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed with error: {e}")
            raise
    
    return wrapper


def log_async_function_call(func):
    """
    Decorator to log async function calls.
    
    Args:
        func: Async function to decorate
        
    Returns:
        Decorated async function
    """
    async def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"Calling async {func.__name__} with args={args}, kwargs={kwargs}")
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Async {func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Async {func.__name__} failed with error: {e}")
            raise
    
    return wrapper


class LogContext:
    """Context manager for adding context to log messages."""
    
    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize log context.
        
        Args:
            logger: Logger to add context to
            **context: Context key-value pairs
        """
        self.logger = logger
        self.context = context
        self.original_filter = None
    
    def __enter__(self):
        """Enter the context."""
        # Add context filter
        self.original_filter = ContextFilter(self.context)
        self.logger.addFilter(self.original_filter)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context."""
        if self.original_filter:
            self.logger.removeFilter(self.original_filter)


class ContextFilter(logging.Filter):
    """Filter to add context to log records."""
    
    def __init__(self, context: Dict[str, Any]):
        super().__init__()
        self.context = context
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record."""
        if not hasattr(record, "extra_data"):
            record.extra_data = {}
        
        record.extra_data.update(self.context)
        return True


def setup_performance_logging():
    """Set up performance logging for monitoring."""
    perf_logger = logging.getLogger("performance")
    
    # Create performance handler with specific format
    perf_handler = logging.StreamHandler()
    perf_formatter = logging.Formatter(
        "PERF - %(asctime)s - %(message)s"
    )
    perf_handler.setFormatter(perf_formatter)
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.INFO)
    
    return perf_logger


def log_performance(operation: str, duration: float, **metrics):
    """
    Log performance metrics.
    
    Args:
        operation: Name of the operation
        duration: Duration in seconds
        **metrics: Additional performance metrics
    """
    perf_logger = logging.getLogger("performance")
    
    message = f"{operation} completed in {duration:.3f}s"
    if metrics:
        metric_str = ", ".join([f"{k}={v}" for k, v in metrics.items()])
        message += f" - {metric_str}"
    
    perf_logger.info(message)


class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, operation: str, logger: Optional[logging.Logger] = None):
        """
        Initialize performance timer.
        
        Args:
            operation: Name of the operation being timed
            logger: Optional logger to use
        """
        self.operation = operation
        self.logger = logger or logging.getLogger("performance")
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        """Start timing."""
        import time
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log result."""
        import time
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        if exc_type is None:
            self.logger.info(f"{self.operation} completed in {duration:.3f}s")
        else:
            self.logger.warning(f"{self.operation} failed after {duration:.3f}s")
    
    @property
    def duration(self) -> Optional[float]:
        """Get the duration if timing is complete."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
