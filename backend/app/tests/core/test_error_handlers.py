"""
Unit tests for the error handling module.

This module tests the implementation of task 5.3:
- Standardized error response formats
- Appropriate HTTP status codes  
- Clear error messages for the frontend
- Error categorization and logging
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.error_handlers import (
    ErrorCategory,
    ErrorSeverity,
    ErrorDetail,
    StandardErrorResponse,
    TimesheetAnalysisError,
    FileValidationError,
    FileSizeError,
    ParsingError,
    LLMServiceError,
    ComplianceAnalysisError,
    DatabaseError,
    ConfigurationError,
    ErrorHandler,
    validate_file_upload,
    map_core_exceptions,
    timesheet_analysis_error_handler,
    general_exception_handler
)

class TestErrorCategories:
    """Test error categories and severity enums."""
    
    def test_error_categories(self):
        """Test that all error categories are defined correctly."""
        assert ErrorCategory.VALIDATION == "validation"
        assert ErrorCategory.FILE_FORMAT == "file_format"
        assert ErrorCategory.LLM_SERVICE == "llm_service"
        assert ErrorCategory.DATABASE == "database"
        assert ErrorCategory.INTERNAL == "internal"
    
    def test_error_severity(self):
        """Test that all error severity levels are defined correctly."""
        assert ErrorSeverity.LOW == "low"
        assert ErrorSeverity.MEDIUM == "medium"
        assert ErrorSeverity.HIGH == "high"
        assert ErrorSeverity.CRITICAL == "critical"

class TestErrorDetail:
    """Test ErrorDetail Pydantic model."""
    
    def test_error_detail_creation(self):
        """Test creating a valid ErrorDetail."""
        detail = ErrorDetail(
            code="TEST_ERROR",
            message="Test error message",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW
        )
        assert detail.code == "TEST_ERROR"
        assert detail.message == "Test error message"
        assert detail.category == ErrorCategory.VALIDATION
        assert detail.severity == ErrorSeverity.LOW
        assert detail.field is None
        assert detail.suggestion is None
    
    def test_error_detail_with_all_fields(self):
        """Test creating ErrorDetail with all optional fields."""
        detail = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Invalid field value",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            field="email",
            suggestion="Please provide a valid email address",
            retry_after=60
        )
        assert detail.field == "email"
        assert detail.suggestion == "Please provide a valid email address"
        assert detail.retry_after == 60

class TestStandardErrorResponse:
    """Test StandardErrorResponse Pydantic model."""
    
    def test_standard_error_response(self):
        """Test creating a standard error response."""
        error_detail = ErrorDetail(
            code="TEST_ERROR",
            message="Test message",
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.MEDIUM
        )
        
        response = StandardErrorResponse(
            error=error_detail,
            request_id="test-123"
        )
        
        assert response.success is False
        assert response.error == error_detail
        assert response.request_id == "test-123"
        assert response.timestamp is not None
        assert response.debug_info is None

class TestTimesheetAnalysisError:
    """Test the base TimesheetAnalysisError exception class."""
    
    def test_basic_error_creation(self):
        """Test creating a basic TimesheetAnalysisError."""
        error = TimesheetAnalysisError(
            message="Test error",
            code="TEST_ERROR",
            category=ErrorCategory.INTERNAL
        )
        
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.category == ErrorCategory.INTERNAL
        assert error.severity == ErrorSeverity.MEDIUM  # Default
        assert error.http_status == 500  # Default
        assert error.field is None
        assert error.suggestion is None
    
    def test_error_with_all_parameters(self):
        """Test creating error with all parameters."""
        debug_info = {"context": "test"}
        
        error = TimesheetAnalysisError(
            message="Custom error",
            code="CUSTOM_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
            http_status=400,
            field="test_field",
            suggestion="Try again",
            retry_after=120,
            debug_info=debug_info
        )
        
        assert error.severity == ErrorSeverity.HIGH
        assert error.http_status == 400
        assert error.field == "test_field"
        assert error.suggestion == "Try again"
        assert error.retry_after == 120
        assert error.debug_info == debug_info

class TestSpecificErrorTypes:
    """Test specific error type classes."""
    
    def test_file_validation_error(self):
        """Test FileValidationError creation."""
        error = FileValidationError(
            message="Invalid file type",
            filename="test.xyz"
        )
        
        assert error.code == "FILE_VALIDATION_ERROR"
        assert error.category == ErrorCategory.FILE_FORMAT
        assert error.severity == ErrorSeverity.LOW
        assert error.http_status == 400
        assert error.debug_info["filename"] == "test.xyz"
        assert "supported file format" in error.suggestion
    
    def test_file_size_error(self):
        """Test FileSizeError creation."""
        error = FileSizeError(
            message="File too large",
            file_size=100000000,
            max_size=50000000
        )
        
        assert error.code == "FILE_SIZE_ERROR"
        assert error.category == ErrorCategory.FILE_SIZE
        assert error.http_status == 413
        assert error.debug_info["file_size"] == 100000000
        assert error.debug_info["max_size"] == 50000000
        assert "47MB" in error.suggestion
    
    def test_parsing_error(self):
        """Test ParsingError creation."""
        parsing_issues = ["Issue 1", "Issue 2"]
        error = ParsingError(
            message="Failed to parse",
            filename="test.csv",
            parsing_issues=parsing_issues
        )
        
        assert error.code == "PARSING_ERROR"
        assert error.category == ErrorCategory.PARSING
        assert error.http_status == 422
        assert error.debug_info["filename"] == "test.csv"
        assert error.debug_info["parsing_issues"] == parsing_issues
    
    def test_llm_service_error(self):
        """Test LLMServiceError creation."""
        error = LLMServiceError(
            message="LLM service unavailable",
            service_name="Google Gemini"
        )
        
        assert error.code == "LLM_SERVICE_ERROR"
        assert error.category == ErrorCategory.LLM_SERVICE
        assert error.severity == ErrorSeverity.HIGH
        assert error.http_status == 503
        assert error.retry_after == 300
        assert error.debug_info["service"] == "Google Gemini"
        assert "temporarily unavailable" in error.suggestion
    
    def test_compliance_analysis_error(self):
        """Test ComplianceAnalysisError creation."""
        error = ComplianceAnalysisError(
            message="Compliance analysis failed"
        )
        
        assert error.code == "COMPLIANCE_ANALYSIS_ERROR"
        assert error.category == ErrorCategory.COMPLIANCE_ANALYSIS
        assert error.http_status == 500
    
    def test_database_error(self):
        """Test DatabaseError creation."""
        error = DatabaseError(
            message="Database connection failed",
            operation="INSERT"
        )
        
        assert error.code == "DATABASE_ERROR"
        assert error.category == ErrorCategory.DATABASE
        assert error.severity == ErrorSeverity.HIGH
        assert error.debug_info["operation"] == "INSERT"
    
    def test_configuration_error(self):
        """Test ConfigurationError creation."""
        error = ConfigurationError(
            message="Missing API key",
            config_key="OPENAI_API_KEY"
        )
        
        assert error.code == "CONFIGURATION_ERROR"
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.debug_info["config_key"] == "OPENAI_API_KEY"

class TestErrorHandler:
    """Test the ErrorHandler utility class."""
    
    def test_create_error_response(self):
        """Test creating standardized error response."""
        error = FileValidationError(
            message="Invalid file",
            filename="test.txt"
        )
        
        response = ErrorHandler.create_error_response(
            error=error,
            request_id="test-123",
            include_debug=True
        )
        
        assert isinstance(response, StandardErrorResponse)
        assert response.success is False
        assert response.error.code == "FILE_VALIDATION_ERROR"
        assert response.request_id == "test-123"
        assert response.debug_info == error.debug_info
    
    def test_create_error_response_no_debug(self):
        """Test creating error response without debug info."""
        error = ParsingError(
            message="Parse failed",
            filename="test.csv"
        )
        
        response = ErrorHandler.create_error_response(
            error=error,
            include_debug=False
        )
        
        assert response.debug_info is None
    
    @patch('app.core.error_handlers.get_logger')
    def test_create_http_exception(self, mock_get_logger):
        """Test creating HTTPException from error."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        error = LLMServiceError(
            message="Service down",
            service_name="OpenAI"
        )
        
        http_exc = ErrorHandler.create_http_exception(
            error=error,
            request_id="test-456"
        )
        
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == 503
        assert isinstance(http_exc.detail, dict)
        assert http_exc.detail["success"] is False
        assert http_exc.detail["error"]["code"] == "LLM_SERVICE_ERROR"
        
        # Verify logging was called
        mock_logger.error.assert_called_once()
    
    @patch('app.core.error_handlers.get_logger')
    def test_handle_unexpected_error(self, mock_get_logger):
        """Test handling unexpected exceptions."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        original_exception = ValueError("Unexpected error")
        
        http_exc = ErrorHandler.handle_unexpected_error(
            exception=original_exception,
            context="test_context",
            request_id="test-789"
        )
        
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == 500
        assert "unexpected error" in http_exc.detail["error"]["message"].lower()
        
        # Verify logging was called - should be at least 2 calls (error + traceback)
        # But may be more due to nested logging in create_http_exception
        assert mock_logger.error.call_count >= 2

class TestFileValidation:
    """Test file upload validation function."""
    
    def test_valid_file(self):
        """Test validation of a valid file."""
        file_bytes = b"test,content\n1,2"
        filename = "test.csv"
        
        # Should not raise any exception
        validate_file_upload(file_bytes, filename, "text/csv")
    
    def test_empty_file(self):
        """Test validation of empty file."""
        with pytest.raises(FileValidationError) as exc_info:
            validate_file_upload(b"", "empty.csv")
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_file_too_large(self):
        """Test validation of oversized file."""
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        with pytest.raises(FileSizeError) as exc_info:
            validate_file_upload(large_content, "large.csv")
        
        assert exc_info.value.http_status == 413
        assert "50MB" in exc_info.value.suggestion
    
    def test_no_extension(self):
        """Test validation of file without extension."""
        with pytest.raises(FileValidationError) as exc_info:
            validate_file_upload(b"content", "noextension")
        
        assert "extension" in str(exc_info.value).lower()
    
    def test_unsupported_extension(self):
        """Test validation of unsupported file extension."""
        with pytest.raises(FileValidationError) as exc_info:
            validate_file_upload(b"content", "test.exe")
        
        assert "unsupported" in str(exc_info.value).lower()
        assert ".exe" in str(exc_info.value)
    
    def test_unusual_mime_type_warning(self):
        """Test that unusual MIME types generate warnings but don't fail."""
        with patch('app.core.error_handlers.logger') as mock_logger:
            # Should not raise exception, but should log warning
            validate_file_upload(b"content", "test.csv", "application/weird")
            
            mock_logger.warning.assert_called_once()
            assert "unusual mime type" in mock_logger.warning.call_args[0][0].lower()

class TestExceptionMapping:
    """Test mapping of core exceptions to standardized errors."""
    
    def test_map_value_error_unsupported(self):
        """Test mapping ValueError about unsupported types."""
        original = ValueError("Unsupported MIME type: application/unknown")
        
        mapped = map_core_exceptions(original, "test.unknown")
        
        assert isinstance(mapped, FileValidationError)
        assert mapped.debug_info["filename"] == "test.unknown"
    
    def test_map_value_error_general(self):
        """Test mapping general ValueError to ParsingError."""
        original = ValueError("Could not decode file")
        
        mapped = map_core_exceptions(original, "test.txt")
        
        assert isinstance(mapped, ParsingError)
        assert mapped.debug_info["filename"] == "test.txt"
    
    def test_map_runtime_error_llm(self):
        """Test mapping RuntimeError with LLM keywords."""
        original = RuntimeError("LLM API failed")
        
        mapped = map_core_exceptions(original, "processing")
        
        assert isinstance(mapped, LLMServiceError)
        assert "LLM" in mapped.debug_info["service"]
    
    def test_map_runtime_error_google(self):
        """Test mapping RuntimeError with Google keywords."""
        original = RuntimeError("Google API error occurred")
        
        mapped = map_core_exceptions(original, "processing")
        
        assert isinstance(mapped, LLMServiceError)
        assert "Google Gemini" in mapped.debug_info["service"]
    
    def test_map_database_error(self):
        """Test mapping database-related errors."""
        original = Exception("Database connection failed")
        
        mapped = map_core_exceptions(original, "database_operation")
        
        assert isinstance(mapped, DatabaseError)
        assert mapped.debug_info["operation"] == "database_operation"
    
    def test_map_unknown_error(self):
        """Test mapping unknown exception types."""
        original = KeyError("Unknown key error")
        
        mapped = map_core_exceptions(original, "unknown_context")
        
        assert isinstance(mapped, TimesheetAnalysisError)
        assert mapped.code == "UNMAPPED_ERROR"
        assert mapped.debug_info["original_exception"] == "KeyError"
        assert mapped.debug_info["context"] == "unknown_context"

class TestGlobalExceptionHandlers:
    """Test global FastAPI exception handlers."""
    
    @pytest.mark.asyncio
    async def test_timesheet_analysis_error_handler(self):
        """Test handling of TimesheetAnalysisError."""
        # Create mock request
        request = Mock(spec=Request)
        request.state.request_id = "test-123"
        request.app.debug = True
        
        # Create test error
        error = ParsingError(
            message="Parse failed",
            filename="test.csv"
        )
        
        # Call handler
        response = await timesheet_analysis_error_handler(request, error)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        assert "X-Error-Code" in response.headers
        assert response.headers["X-Error-Code"] == "PARSING_ERROR"
    
    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """Test handling of unexpected exceptions."""
        # Create mock request
        request = Mock(spec=Request)
        request.state.request_id = "test-456"
        request.app.debug = False
        request.method = "POST"
        request.url.path = "/api/analyze"
        
        # Create test exception
        error = ValueError("Unexpected error")
        
        with patch('app.core.error_handlers.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Call handler
            response = await general_exception_handler(request, error)
            
            assert isinstance(response, JSONResponse)
            assert response.status_code == 500
            assert "X-Error-Code" in response.headers
            assert response.headers["X-Error-Code"] == "INTERNAL_ERROR"
            
            # Verify logging
            assert mock_logger.error.call_count >= 1 