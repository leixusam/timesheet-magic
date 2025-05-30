"""
Logging configuration module for the Time Sheet Magic backend.

This module implements task 5.1 - basic logging for analysis.py and other core backend modules.
It provides structured logging for:
- Raw input type
- Parse success/failure 
- Processing time
- General application events
- Error tracking
"""

import logging
import logging.config
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class TimesheetLoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter that adds context to log messages.
    Useful for adding request IDs, user IDs, etc. to all log messages.
    """
    def process(self, msg, kwargs):
        # Add extra context to the message
        if self.extra:
            context_str = " | ".join([f"{k}={v}" for k, v in self.extra.items()])
            return f"[{context_str}] {msg}", kwargs
        return msg, kwargs

class LoggingConfig:
    """Configuration and setup for application logging."""
    
    @staticmethod
    def setup_logging(
        log_level: str = "INFO",
        log_to_file: bool = True,
        log_dir: str = "logs",
        include_request_id: bool = True
    ) -> None:
        """
        Set up comprehensive logging for the application.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Whether to log to files in addition to console
            log_dir: Directory to store log files
            include_request_id: Whether to include request ID in logs
        """
        
        # Create logs directory if it doesn't exist
        if log_to_file:
            Path(log_dir).mkdir(exist_ok=True)
        
        # Define log format
        detailed_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(funcName)s:%(lineno)d | %(message)s"
        )
        
        simple_format = "%(asctime)s | %(levelname)-8s | %(message)s"
        
        # Configure logging
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    "format": detailed_format,
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                },
                "simple": {
                    "format": simple_format,
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": "simple",
                    "stream": "ext://sys.stdout"
                }
            },
            "loggers": {
                "timesheet": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                },
                "timesheet.analysis": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                },
                "timesheet.llm": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                },
                "timesheet.compliance": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                },
                "timesheet.reporting": {
                    "level": log_level,
                    "handlers": ["console"],
                    "propagate": False
                }
            },
            "root": {
                "level": log_level,
                "handlers": ["console"]
            }
        }
        
        # Add file handlers if requested
        if log_to_file:
            # General application log
            config["handlers"]["file_general"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "detailed",
                "filename": os.path.join(log_dir, "timesheet_app.log"),
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            }
            
            # Analysis-specific log
            config["handlers"]["file_analysis"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": os.path.join(log_dir, "analysis.log"),
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            }
            
            # Error log
            config["handlers"]["file_error"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": os.path.join(log_dir, "errors.log"),
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 10,
                "encoding": "utf8"
            }
            
            # Add file handlers to loggers
            for logger_name in config["loggers"]:
                config["loggers"][logger_name]["handlers"].extend([
                    "file_general", "file_error"
                ])
            
            # Analysis logger gets its own file too
            config["loggers"]["timesheet.analysis"]["handlers"].append("file_analysis")
        
        # Apply configuration
        logging.config.dictConfig(config)
        
        # Log that logging has been configured
        logger = logging.getLogger("timesheet")
        logger.info(f"Logging configured - Level: {log_level}, File logging: {log_to_file}")

def get_logger(name: str, extra_context: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Get a logger with optional context.
    
    Args:
        name: Logger name (will be prefixed with 'timesheet.')
        extra_context: Additional context to include in all log messages
        
    Returns:
        Configured logger instance
    """
    full_name = f"timesheet.{name}" if not name.startswith("timesheet") else name
    logger = logging.getLogger(full_name)
    
    if extra_context:
        return TimesheetLoggerAdapter(logger, extra_context)
    
    return logger

def log_analysis_start(
    logger: logging.Logger,
    request_id: str,
    filename: str,
    file_size: int,
    mime_type: str,
    file_extension: Optional[str] = None
) -> None:
    """
    Log the start of timesheet analysis with file details.
    Implements task 5.1.1 requirement for logging raw input type.
    """
    logger.info(
        f"Analysis started | Request ID: {request_id} | "
        f"File: {filename} | Size: {file_size:,} bytes | "
        f"MIME: {mime_type} | Extension: {file_extension or 'N/A'}"
    )

def log_parsing_result(
    logger: logging.Logger,
    request_id: str,
    filename: str,
    success: bool,
    events_found: int,
    processing_time: float,
    issues: Optional[list] = None
) -> None:
    """
    Log parsing results with success/failure status and processing time.
    Implements task 5.1.1 requirements for parse success/failure and processing time.
    """
    status = "SUCCESS" if success else "FAILED"
    
    logger.info(
        f"Parsing {status} | Request ID: {request_id} | "
        f"File: {filename} | Events: {events_found} | "
        f"Time: {processing_time:.2f}s"
    )
    
    if issues:
        for issue in issues:
            logger.warning(f"Parsing issue | Request ID: {request_id} | Issue: {issue}")
    
    if not success:
        logger.error(f"Parsing failed for {filename} | Request ID: {request_id}")

def log_compliance_analysis(
    logger: logging.Logger,
    request_id: str,
    violations_found: int,
    employee_count: int,
    analysis_time: float
) -> None:
    """
    Log compliance analysis results.
    """
    logger.info(
        f"Compliance analysis completed | Request ID: {request_id} | "
        f"Violations: {violations_found} | Employees: {employee_count} | "
        f"Time: {analysis_time:.2f}s"
    )

def log_llm_request(
    logger: logging.Logger,
    request_id: str,
    model_name: str,
    content_size: int,
    attempt: int = 1
) -> None:
    """
    Log LLM API request details.
    """
    logger.debug(
        f"LLM request | Request ID: {request_id} | "
        f"Model: {model_name} | Content size: {content_size:,} chars | "
        f"Attempt: {attempt}"
    )

def log_llm_response(
    logger: logging.Logger,
    request_id: str,
    success: bool,
    response_time: float,
    response_type: str,
    error_msg: Optional[str] = None
) -> None:
    """
    Log LLM API response details.
    """
    status = "SUCCESS" if success else "FAILED"
    
    logger.info(
        f"LLM response {status} | Request ID: {request_id} | "
        f"Time: {response_time:.2f}s | Type: {response_type}"
    )
    
    if error_msg:
        logger.error(f"LLM error | Request ID: {request_id} | Error: {error_msg}")

def log_database_operation(
    logger: logging.Logger,
    operation: str,
    table: str,
    success: bool,
    record_id: Optional[str] = None,
    error_msg: Optional[str] = None
) -> None:
    """
    Log database operations.
    """
    status = "SUCCESS" if success else "FAILED"
    
    logger.info(
        f"Database {operation} {status} | Table: {table}" +
        (f" | ID: {record_id}" if record_id else "")
    )
    
    if error_msg:
        logger.error(f"Database error | Operation: {operation} | Table: {table} | Error: {error_msg}")

def log_performance_metric(
    logger: logging.Logger,
    operation: str,
    duration: float,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log performance metrics for monitoring.
    """
    details_str = ""
    if details:
        details_str = " | " + " | ".join([f"{k}: {v}" for k, v in details.items()])
    
    logger.info(f"Performance | {operation} | Duration: {duration:.2f}s{details_str}")

# Initialize logging when module is imported
# This ensures logging is configured as early as possible
_logging_initialized = False

def ensure_logging_initialized():
    """Ensure logging is initialized - call this from main.py or other entry points."""
    global _logging_initialized
    if not _logging_initialized:
        # Get log level from environment or use INFO as default
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        
        # Create logs directory relative to backend directory
        backend_dir = Path(__file__).parent.parent
        log_dir = backend_dir / "logs"
        
        # Check if we're in a test environment
        is_testing = "pytest" in sys.modules or os.getenv("TESTING") == "true"
        
        LoggingConfig.setup_logging(
            log_level=log_level,
            log_to_file=not is_testing,  # Don't create log files during testing
            log_dir=str(log_dir)
        )
        _logging_initialized = True 