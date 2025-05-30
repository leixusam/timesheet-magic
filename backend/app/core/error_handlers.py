"""
Error Handling Module for Time Sheet Magic Backend

This module implements task 5.3 - Robust error handling for FastAPI endpoints and core modules.
It provides:
- Standardized error response formats
- Appropriate HTTP status codes
- Clear error messages for the frontend
- Error categorization and logging
- Custom exception classes
"""

import traceback
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.logging_config import get_logger

# Initialize logger for this module
logger = get_logger("error_handlers")

class ErrorCategory(str, Enum):
    """Categories of errors for better classification and handling."""
    
    # Input/Validation Errors (4xx)
    VALIDATION = "validation"
    FILE_FORMAT = "file_format" 
    FILE_SIZE = "file_size"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    
    # Processing Errors (4xx/5xx depending on context)
    PARSING = "parsing"
    LLM_SERVICE = "llm_service"
    COMPLIANCE_ANALYSIS = "compliance_analysis"
    
    # Infrastructure Errors (5xx)
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    CONFIGURATION = "configuration"
    INTERNAL = "internal"

class ErrorSeverity(str, Enum):
    """Severity levels for error classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorDetail(BaseModel):
    """Detailed error information for structured error responses."""
    code: str = Field(..., description="Unique error code for identification")
    message: str = Field(..., description="Human-readable error message")
    category: ErrorCategory = Field(..., description="Error category for classification")
    severity: ErrorSeverity = Field(..., description="Error severity level")
    field: Optional[str] = Field(None, description="Specific field that caused the error (for validation errors)")
    suggestion: Optional[str] = Field(None, description="Suggested action to resolve the error")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying (for rate limits)")

class StandardErrorResponse(BaseModel):
    """Standardized error response format for all API endpoints."""
    success: bool = Field(False, description="Always false for error responses")
    error: ErrorDetail = Field(..., description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Error timestamp")
    debug_info: Optional[Dict[str, Any]] = Field(None, description="Additional debug information (only in development)")

class TimesheetAnalysisError(Exception):
    """Base exception class for timesheet analysis errors."""
    
    def __init__(
        self,
        message: str,
        code: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        http_status: int = 500,
        field: Optional[str] = None,
        suggestion: Optional[str] = None,
        retry_after: Optional[int] = None,
        debug_info: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.severity = severity
        self.http_status = http_status
        self.field = field
        self.suggestion = suggestion
        self.retry_after = retry_after
        self.debug_info = debug_info or {}

class FileValidationError(TimesheetAnalysisError):
    """Exception for file validation errors."""
    
    def __init__(self, message: str, filename: str, suggestion: Optional[str] = None, **kwargs):
        # Use provided suggestion or default
        default_suggestion = "Please upload a supported file format (CSV, XLSX, PDF, or image files)"
        final_suggestion = suggestion or default_suggestion
        
        super().__init__(
            message=message,
            code="FILE_VALIDATION_ERROR",
            category=ErrorCategory.FILE_FORMAT,
            severity=ErrorSeverity.LOW,
            http_status=400,
            suggestion=final_suggestion,
            debug_info={"filename": filename},
            **kwargs
        )

class FileSizeError(TimesheetAnalysisError):
    """Exception for file size errors."""
    
    def __init__(self, message: str, file_size: int, max_size: int, **kwargs):
        max_size_mb = max_size // 1024 // 1024
        super().__init__(
            message=message,
            code="FILE_SIZE_ERROR",
            category=ErrorCategory.FILE_SIZE,
            severity=ErrorSeverity.LOW,
            http_status=413,
            suggestion=f"Please reduce file size to under {max_size_mb}MB",
            debug_info={"file_size": file_size, "max_size": max_size},
            **kwargs
        )

class ParsingError(TimesheetAnalysisError):
    """Exception for data parsing errors."""
    
    def __init__(self, message: str, filename: str, parsing_issues: Optional[List[str]] = None, **kwargs):
        super().__init__(
            message=message,
            code="PARSING_ERROR",
            category=ErrorCategory.PARSING,
            severity=ErrorSeverity.MEDIUM,
            http_status=422,
            suggestion="Verify the file contains valid timesheet data with employee names, dates, and clock times",
            debug_info={"filename": filename, "parsing_issues": parsing_issues or []},
            **kwargs
        )

class LLMServiceError(TimesheetAnalysisError):
    """Exception for LLM service errors."""
    
    def __init__(self, message: str, service_name: str = "LLM", **kwargs):
        super().__init__(
            message=message,
            code="LLM_SERVICE_ERROR",
            category=ErrorCategory.LLM_SERVICE,
            severity=ErrorSeverity.HIGH,
            http_status=503,
            suggestion="The AI processing service is temporarily unavailable. Please try again in a few minutes.",
            retry_after=300,  # 5 minutes
            debug_info={"service": service_name},
            **kwargs
        )

class ComplianceAnalysisError(TimesheetAnalysisError):
    """Exception for compliance analysis errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            code="COMPLIANCE_ANALYSIS_ERROR",
            category=ErrorCategory.COMPLIANCE_ANALYSIS,
            severity=ErrorSeverity.MEDIUM,
            http_status=500,
            suggestion="There was an error analyzing compliance violations. The file may contain unexpected data formats.",
            **kwargs
        )

class DatabaseError(TimesheetAnalysisError):
    """Exception for database errors."""
    
    def __init__(self, message: str, operation: str = "unknown", **kwargs):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            http_status=500,
            suggestion="Database operation failed. Please try again or contact support if the issue persists.",
            debug_info={"operation": operation},
            **kwargs
        )

class ConfigurationError(TimesheetAnalysisError):
    """Exception for configuration errors."""
    
    def __init__(self, message: str, config_key: str = "unknown", **kwargs):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR", 
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
            http_status=500,
            suggestion="Service configuration issue. Please contact support.",
            debug_info={"config_key": config_key},
            **kwargs
        )

class LLMProcessingError(TimesheetAnalysisError):
    """Custom exception for errors during LLM processing after successful parsing."""
    def __init__(self, message: str, original_filename: Optional[str] = None, suggestion: Optional[str] = None, llm_call_details: Optional[str] = None):
        super().__init__(
            message=message,
            original_filename=original_filename,
            suggestion=suggestion or "The AI model encountered an issue while analyzing the content. You can try uploading the file again. If the problem persists, the file content might be ambiguous or require adjustments.",
            llm_call_details=llm_call_details,
            status_code="error_llm_processing_failed"
        )

class LLMComplexityError(TimesheetAnalysisError):
    """Custom exception for when LLM fails due to file complexity (e.g., MALFORMED_FUNCTION_CALL)."""
    def __init__(self, message: str, original_filename: Optional[str] = None, suggestion: Optional[str] = None, llm_call_details: Optional[str] = None):
        super().__init__(
            message=message,
            original_filename=original_filename,
            suggestion=suggestion or "The file you uploaded appears to be too complex or large for our current automated analysis. Please try a simpler or smaller file, or use a standard timesheet format.",
            llm_call_details=llm_call_details,
            status_code="error_llm_complexity" # New status code
        )

class ErrorHandler:
    """Central error handling class for processing and responding to errors."""
    
    @staticmethod
    def create_error_response(
        error: TimesheetAnalysisError,
        request_id: Optional[str] = None,
        include_debug: bool = False
    ) -> StandardErrorResponse:
        """
        Create a standardized error response from a TimesheetAnalysisError.
        
        Args:
            error: The exception to convert to an error response
            request_id: Optional request ID for tracking
            include_debug: Whether to include debug information
            
        Returns:
            Standardized error response
        """
        error_detail = ErrorDetail(
            code=error.code,
            message=error.message,
            category=error.category,
            severity=error.severity,
            field=error.field,
            suggestion=error.suggestion,
            retry_after=error.retry_after
        )
        
        response = StandardErrorResponse(
            error=error_detail,
            request_id=request_id
        )
        
        if include_debug and error.debug_info:
            response.debug_info = error.debug_info
        
        return response
    
    @staticmethod
    def create_http_exception(
        error: TimesheetAnalysisError,
        request_id: Optional[str] = None,
        include_debug: bool = False
    ) -> HTTPException:
        """
        Create an HTTPException from a TimesheetAnalysisError.
        
        Args:
            error: The exception to convert
            request_id: Optional request ID for tracking
            include_debug: Whether to include debug information
            
        Returns:
            HTTPException with standardized error response
        """
        error_response = ErrorHandler.create_error_response(error, request_id, include_debug)
        
        # Log the error with appropriate level based on severity
        error_logger = get_logger("error_handlers", {"request_id": request_id})
        log_message = f"Error {error.code}: {error.message}"
        
        if error.severity == ErrorSeverity.CRITICAL:
            error_logger.critical(log_message)
        elif error.severity == ErrorSeverity.HIGH:
            error_logger.error(log_message)
        elif error.severity == ErrorSeverity.MEDIUM:
            error_logger.warning(log_message)
        else:
            error_logger.info(log_message)
        
        return HTTPException(
            status_code=error.http_status,
            detail=error_response.model_dump()
        )
    
    @staticmethod
    def handle_unexpected_error(
        exception: Exception,
        context: str = "unknown",
        request_id: Optional[str] = None,
        include_debug: bool = False
    ) -> HTTPException:
        """
        Handle unexpected errors by wrapping them in a standardized format.
        
        Args:
            exception: The unexpected exception
            context: Context where the error occurred
            request_id: Optional request ID for tracking
            include_debug: Whether to include debug information
            
        Returns:
            HTTPException with standardized error response
        """
        # Log the full traceback for debugging
        error_logger = get_logger("error_handlers", {"request_id": request_id})
        error_logger.error(f"Unexpected error in {context}: {str(exception)}")
        error_logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Create a standardized internal error
        debug_info = {
            "context": context,
            "exception_type": exception.__class__.__name__
        }
        
        if include_debug:
            debug_info["traceback"] = traceback.format_exc()
        
        internal_error = TimesheetAnalysisError(
            message="An unexpected error occurred while processing your request",
            code="INTERNAL_ERROR",
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.HIGH,
            http_status=500,
            suggestion="Please try again. If the issue persists, contact support.",
            debug_info=debug_info
        )
        
        return ErrorHandler.create_http_exception(internal_error, request_id, include_debug)

def validate_file_upload(file_bytes: bytes, filename: str, content_type: Optional[str] = None) -> None:
    """
    Validate uploaded file for common issues.
    
    Args:
        file_bytes: File content as bytes
        filename: Original filename
        content_type: MIME type of the file
        
    Raises:
        FileValidationError: If file validation fails
        FileSizeError: If file is too large
    """
    # Check file size (max 50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    if len(file_bytes) > MAX_FILE_SIZE:
        raise FileSizeError(
            message=f"File size ({len(file_bytes):,} bytes) exceeds maximum allowed size",
            file_size=len(file_bytes),
            max_size=MAX_FILE_SIZE
        )
    
    # Check if file is empty
    if len(file_bytes) == 0:
        raise FileValidationError(
            message="Uploaded file is empty",
            filename=filename
        )
    
    # Validate file extension
    if "." not in filename:
        raise FileValidationError(
            message="File must have a valid extension",
            filename=filename
        )
    
    file_extension = filename.split(".")[-1].lower()
    supported_extensions = {"csv", "xlsx", "xls", "pdf", "txt", "png", "jpg", "jpeg", "tiff", "bmp", "gif"}
    
    if file_extension not in supported_extensions:
        supported_list = ", ".join(sorted(supported_extensions))
        raise FileValidationError(
            message=f"Unsupported file type: .{file_extension}",
            filename=filename,
            suggestion=f"Supported formats: {supported_list}"
        )
    
    # Validate MIME type if provided
    if content_type:
        supported_mime_types = {
            "text/csv", "application/csv",
            "application/vnd.ms-excel", 
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/pdf", "text/plain"
        }
        
        if not (content_type in supported_mime_types or content_type.startswith("image/")):
            # Log warning but don't fail - browser MIME detection can be unreliable
            logger.warning(f"Unusual MIME type '{content_type}' for file '{filename}' - proceeding with extension-based validation")

def map_core_exceptions(exception: Exception, context: str = "unknown") -> TimesheetAnalysisError:
    """
    Map core module exceptions to standardized TimesheetAnalysisError instances.
    
    Args:
        exception: The original exception
        context: Context where the exception occurred
        
    Returns:
        Mapped TimesheetAnalysisError
    """
    if isinstance(exception, ValueError):
        if "unsupported" in str(exception).lower() or "mime type" in str(exception).lower():
            return FileValidationError(
                message=str(exception),
                filename=context
            )
        else:
            return ParsingError(
                message=str(exception),
                filename=context
            )
    
    elif isinstance(exception, RuntimeError):
        if "llm" in str(exception).lower() or "api" in str(exception).lower():
            return LLMServiceError(
                message=str(exception),
                service_name="Google Gemini" if "google" in str(exception).lower() else "LLM"
            )
        else:
            return ComplianceAnalysisError(
                message=str(exception)
            )
    
    elif "database" in str(exception).lower() or "sql" in str(exception).lower():
        return DatabaseError(
            message=str(exception),
            operation=context
        )
    
    else:
        # Default to internal error for unmapped exceptions
        return TimesheetAnalysisError(
            message=str(exception),
            code="UNMAPPED_ERROR",
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.MEDIUM,
            http_status=500,
            debug_info={"original_exception": exception.__class__.__name__, "context": context}
        )

# Global FastAPI exception handlers

async def timesheet_analysis_error_handler(request: Request, exc: TimesheetAnalysisError):
    """Global handler for TimesheetAnalysisError exceptions."""
    # Extract request ID from headers or generate one
    request_id = getattr(request.state, 'request_id', None)
    if not request_id:
        request_id = request.headers.get('X-Request-ID')
    
    # Determine if we should include debug info (e.g., in development)
    include_debug = request.app.debug if hasattr(request.app, 'debug') else False
    
    error_response = ErrorHandler.create_error_response(exc, request_id, include_debug)
    
    return JSONResponse(
        status_code=exc.http_status,
        content=error_response.model_dump(),
        headers={
            "X-Error-Code": exc.code,
            "X-Error-Category": exc.category.value
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Global handler for unexpected exceptions."""
    # Extract request ID
    request_id = getattr(request.state, 'request_id', None)
    if not request_id:
        request_id = request.headers.get('X-Request-ID')
    
    include_debug = request.app.debug if hasattr(request.app, 'debug') else False
    
    # Try to determine context from request path
    context = f"{request.method} {request.url.path}"
    
    http_exception = ErrorHandler.handle_unexpected_error(exc, context, request_id, include_debug)
    
    return JSONResponse(
        status_code=http_exception.status_code,
        content=http_exception.detail,
        headers={
            "X-Error-Code": "INTERNAL_ERROR",
            "X-Error-Category": ErrorCategory.INTERNAL.value
        }
    ) 