import pytest
from backend.app.core.llm_processing import pydantic_to_gemini_tool_dict, parse_file_to_structured_data
from app.models.schemas import LLMProcessingOutput, LLMParsedPunchEvent
from backend.app.core.error_handlers import ParsingError
import os
from unittest.mock import MagicMock

# Mock Pydantic models for testing
class MockPydanticModelForTool(LLMProcessingOutput): # Inherits from a real one for field checks
    pass

class MockLLMParsedPunchEvent(LLMParsedPunchEvent):
    pass


def test_pydantic_to_gemini_tool_dict():
    """
    Tests the conversion of a Pydantic model to a Gemini tool dictionary.
    """
    tool_name = "test_tool"
    tool_description = "A test tool description."
    
    # LLMProcessingOutput is the model whose *parameters* are being defined by the tool.
    # The tool is expected to return data for punch_events and parsing_issues.
    tool_dict = pydantic_to_gemini_tool_dict(LLMProcessingOutput, tool_name, tool_description)

    assert tool_dict["name"] == tool_name
    assert tool_dict["description"] == tool_description
    assert "parameters" in tool_dict
    
    parameters_schema = tool_dict["parameters"]
    assert parameters_schema["type"] == "OBJECT"
    assert "properties" in parameters_schema
    
    properties = parameters_schema["properties"]
    assert "punch_events" in properties
    assert properties["punch_events"]["type"] == "ARRAY"
    assert properties["punch_events"]["items"]["type"] == "OBJECT"
    assert "properties" in properties["punch_events"]["items"]
    
    # Check if punch_events items properties are correctly converted to Gemini format
    punch_event_properties = properties["punch_events"]["items"]["properties"]
    
    # The schema should contain the correct field names from LLMParsedPunchEvent
    assert "employee_identifier_in_file" in punch_event_properties
    assert "timestamp" in punch_event_properties  
    assert "punch_type_as_parsed" in punch_event_properties
    
    # Types should be in Gemini format (STRING, not string)
    assert punch_event_properties["employee_identifier_in_file"]["type"] == "STRING"
    assert punch_event_properties["punch_type_as_parsed"]["type"] == "STRING"
    
    # Verify required fields are present
    punch_event_required = properties["punch_events"]["items"]["required"]
    expected_required = ["employee_identifier_in_file", "timestamp", "punch_type_as_parsed"]
    for field in expected_required:
        assert field in punch_event_required

    assert "parsing_issues" in properties
    assert properties["parsing_issues"]["type"] == "ARRAY"
    assert properties["parsing_issues"]["items"]["type"] == "STRING"
    
    assert "required" in parameters_schema
    assert "punch_events" in parameters_schema["required"]

# More tests for parse_file_to_structured_data will be added here.
# We will need to mock the get_gemini_response_with_function_calling function. 

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_text_success(mocker):
    """Tests successful parsing of a text file."""
    mock_llm_response = {
        "punch_events": [
            {
                "employee_identifier_in_file": "John Doe",
                "timestamp": "2023-01-01T09:00:00Z",
                "punch_type_as_parsed": "Clock In",
                "role_as_parsed": None,
                "department_as_parsed": None,
                "location_note_as_parsed": None,
                "notes_as_parsed": "Morning shift",
                "hourly_wage_as_parsed": None
            }
        ],
        "parsing_issues": ["Minor formatting inconsistency on line 5"]
    }
    mock_gemini_call = mocker.patch(
        "backend.app.core.llm_processing.get_gemini_response_with_function_calling",
        return_value=mock_llm_response
    )

    file_bytes = b"Employee: John Doe, Clock In: 09:00 AM Jan 1, 2023"
    mime_type = "text/plain"
    filename = "test.txt"

    result = await parse_file_to_structured_data(file_bytes, mime_type, filename)

    assert isinstance(result, LLMProcessingOutput)
    assert len(result.punch_events) == 1
    assert result.punch_events[0].employee_identifier_in_file == "John Doe"
    assert result.parsing_issues == ["Minor formatting inconsistency on line 5"]
    mock_gemini_call.assert_called_once()
    call_args = mock_gemini_call.call_args[1] # kwargs
    assert "prompt_parts" in call_args
    assert any(isinstance(part, str) and "John Doe" in part for part in call_args["prompt_parts"])
    assert "tools" in call_args
    assert len(call_args["tools"]) == 1
    assert call_args["tools"][0]["name"] == "extract_timesheet_data"

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_image_success(mocker):
    """Tests successful parsing of an image file (currently returns placeholder text)."""
    mock_llm_response = {
        "punch_events": [
            {
                "employee_identifier_in_file": "Jane Smith",
                "timestamp": "2023-01-01T17:00:00Z", 
                "punch_type_as_parsed": "Clock Out",
                "role_as_parsed": None,
                "department_as_parsed": None,
                "location_note_as_parsed": None,
                "notes_as_parsed": "End of shift",
                "hourly_wage_as_parsed": None
            }
        ],
        "parsing_issues": []
    }
    mock_gemini_call = mocker.patch(
        "backend.app.core.llm_processing.get_gemini_response_with_function_calling",
        return_value=mock_llm_response
    )

    file_bytes = b"fake_image_bytes"
    mime_type = "image/png"
    filename = "test.png"

    result = await parse_file_to_structured_data(file_bytes, mime_type, filename)

    assert isinstance(result, LLMProcessingOutput)
    assert len(result.punch_events) == 1
    assert result.punch_events[0].employee_identifier_in_file == "Jane Smith"
    assert not result.parsing_issues
    mock_gemini_call.assert_called_once()
    call_args = mock_gemini_call.call_args[1]
    # Current implementation converts images to text placeholders
    assert isinstance(call_args["prompt_parts"][0], str)
    assert "Image file: test.png" in call_args["prompt_parts"][0]

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_pdf_success(mocker):
    """Tests successful parsing of a PDF file (currently returns placeholder text)."""
    mock_llm_response = {
        "punch_events": [
            {
                "employee_identifier_in_file": "PDF User",
                "timestamp": "2023-01-01T12:00:00Z",
                "punch_type_as_parsed": "Break Start",
                "role_as_parsed": None,
                "department_as_parsed": None,
                "location_note_as_parsed": None,
                "notes_as_parsed": None,
                "hourly_wage_as_parsed": None
            }
        ],
        "parsing_issues": []
    }
    mock_gemini_call = mocker.patch(
        "backend.app.core.llm_processing.get_gemini_response_with_function_calling",
        return_value=mock_llm_response
    )
    file_bytes = b"fake_pdf_bytes"
    mime_type = "application/pdf"
    filename = "test.pdf"
    result = await parse_file_to_structured_data(file_bytes, mime_type, filename)
    assert result.punch_events[0].employee_identifier_in_file == "PDF User"
    mock_gemini_call.assert_called_once()
    call_args = mock_gemini_call.call_args[1]
    # Current implementation converts PDFs to text placeholders
    assert isinstance(call_args["prompt_parts"][0], str)
    assert "PDF file: test.pdf" in call_args["prompt_parts"][0]

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_llm_returns_error_string(mocker):
    """Tests handling when LLM utility returns an error string."""
    from backend.app.core.error_handlers import LLMServiceError
    
    error_message = "Error: LLM capacity issue."
    mocker.patch(
        "backend.app.core.llm_processing.get_gemini_response_with_function_calling",
        return_value=error_message
    )
    with pytest.raises(LLMServiceError):
        await parse_file_to_structured_data(b"text", "text/plain", "test.txt")

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_llm_returns_text_instead_of_fc(mocker):
    """Tests handling when LLM returns text instead of a function call."""
    from backend.app.core.error_handlers import ParsingError
    
    text_response = "The timesheet shows John Doe clocked in."
    mocker.patch(
        "backend.app.core.llm_processing.get_gemini_response_with_function_calling",
        return_value=text_response
    )
    with pytest.raises(ParsingError):
        await parse_file_to_structured_data(b"text", "text/plain", "test.txt")

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_pydantic_validation_error(mocker):
    """Tests handling when LLM returns data that fails Pydantic validation."""
    mock_llm_response = {
        "punch_events": [{"employee_identifier_in_file": "Bad Data", "invalid_field": "should not be here"}], # Missing required fields
        "parsing_issues": []
    }
    mocker.patch(
        "backend.app.core.llm_processing.get_gemini_response_with_function_calling",
        return_value=mock_llm_response
    )
    with pytest.raises(ParsingError):
        await parse_file_to_structured_data(b"text", "text/plain", "pydantic_error_test.txt")

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_unsupported_mime_type():
    """Tests handling of unsupported MIME types."""
    from backend.app.core.error_handlers import FileValidationError
    
    with pytest.raises(FileValidationError):
        await parse_file_to_structured_data(b"zip_content", "application/zip", "test.zip")

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_excel_mime_type_now_supported():
    """Tests that Excel MIME types are now supported through preprocessing."""
    file_bytes = b"fake_excel_bytes"
    filename = "test.xlsx"
    
    # Since we don't have a real Excel file, this will fail at the openpyxl parsing stage
    # But we expect a ParsingError now instead of FileValidationError
    with pytest.raises(ParsingError, match="Failed to process Excel file"):
        await parse_file_to_structured_data(file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename)

    filename_xls = "test.xls"
    with pytest.raises(ParsingError, match="Failed to process Excel file"):
        await parse_file_to_structured_data(file_bytes, "application/vnd.ms-excel", filename_xls)

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_text_unicode_decode_error():
    """Tests handling of text files that cannot be decoded as UTF-8."""
    from backend.app.core.error_handlers import LLMServiceError
    
    # This byte sequence is invalid UTF-8
    invalid_utf8_bytes = b"\xff\xfe\xfd"
    mime_type = "text/plain"
    filename = "bad_encoding.txt"

    # The actual error handling shows this will result in an LLMServiceError due to decode issues
    with pytest.raises(LLMServiceError):
        await parse_file_to_structured_data(invalid_utf8_bytes, mime_type, filename)

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_llm_call_general_exception(mocker):
    """Tests handling of a general exception during the LLM call."""
    from backend.app.core.error_handlers import LLMServiceError
    
    mocker.patch(
        "backend.app.core.llm_processing.get_gemini_response_with_function_calling",
        side_effect=Exception("Network error")
    )
    with pytest.raises(LLMServiceError):
        await parse_file_to_structured_data(b"text", "text/plain", "test.txt")

@pytest.mark.asyncio
async def test_parse_specific_excel_file_success_after_preprocessing(mocker):
    """
    Tests that attempting to parse the specific '8.05 - Time Clock Detail.xlsx' file
    succeeds after preprocessing, using the actual file.
    """
    excel_file_path = "sample_data/8.05 - Time Clock Detail.xlsx"
    original_filename = "8.05 - Time Clock Detail.xlsx"
    
    # Skip if file doesn't exist
    if not os.path.exists(excel_file_path):
        pytest.skip(f"Excel file not found: {excel_file_path}")
    
    # Mock the LLM call to return a successful response
    mock_response = MagicMock()
    mock_response.text = '{"punch_events": [{"employee_name": "John Doe", "date": "2023-05-01", "punch_type": "Clock In", "time": "08:00", "department": "Kitchen"}]}'
    
    # Mock the Google GenAI client
    mock_client = MagicMock()
    mock_model = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_model.generate_content.return_value = mock_response
    mock_client.return_value = mock_model
    
    mocker.patch('app.core.llm_processing.genai.GenerativeModel', return_value=mock_model)
    
    # Read the actual Excel file
    with open(excel_file_path, 'rb') as f:
        file_content = f.read()
    
    # Call the function
    result = await parse_file_to_structured_data(
        file_content=file_content,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        original_filename=original_filename
    )
    
    # Verify the result
    assert result is not None
    assert len(result.punch_events) == 1
    assert result.punch_events[0].employee_name == "John Doe"

# It might be useful to have a fixture for common mock LLM responses
# if more tests are added that require similar successful data structures.

# To run these tests, ensure pytest and pytest-asyncio are installed.
# Also, ensure that the GOOGLE_API_KEY or GEMINI_API_KEY environment variable is set if you intend to run
# the main_test() in llm_processing.py directly, though these unit tests mock out the actual API call. 