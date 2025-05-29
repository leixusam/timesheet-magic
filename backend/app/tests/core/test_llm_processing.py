import pytest
from backend.app.core.llm_processing import pydantic_to_gemini_tool_dict, parse_file_to_structured_data
from backend.app.models.schemas import LLMProcessingOutput, LLMParsedPunchEvent
import os

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
    
    # Check if punch_events items properties match LLMParsedPunchEvent schema
    punch_event_schema_props = LLMParsedPunchEvent.model_json_schema().get("properties", {})
    assert properties["punch_events"]["items"]["properties"] == punch_event_schema_props
    punch_event_schema_required = LLMParsedPunchEvent.model_json_schema().get("required", [])
    assert properties["punch_events"]["items"]["required"] == punch_event_schema_required


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
                "employee_name": "John Doe",
                "event_type": "Clock In",
                "timestamp_utc": "2023-01-01T09:00:00Z",
                "original_timestamp_str": "09:00 AM Jan 1, 2023",
                "timezone_str": "UTC",
                "notes": "Morning shift"
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
    assert result.punch_events[0].employee_name == "John Doe"
    assert result.parsing_issues == ["Minor formatting inconsistency on line 5"]
    mock_gemini_call.assert_called_once()
    call_args = mock_gemini_call.call_args[1] # kwargs
    assert "prompt_parts" in call_args
    assert any(isinstance(part, str) and "John Doe" in part for part in call_args["prompt_parts"])
    assert "tools" in call_args
    assert len(call_args["tools"]) == 1
    assert call_args["tools"][0]["name"] == "timesheet_data_extractor"

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_image_success(mocker):
    """Tests successful parsing of an image file."""
    mock_llm_response = {
        "punch_events": [
            {
                "employee_name": "Jane Smith", "event_type": "Clock Out", 
                "timestamp_utc": "2023-01-01T17:00:00Z",
                "original_timestamp_str": "05:00 PM Jan 1, 2023", 
                "timezone_str": "PST", "notes": "End of shift"
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
    assert result.punch_events[0].employee_name == "Jane Smith"
    assert not result.parsing_issues
    mock_gemini_call.assert_called_once()
    call_args = mock_gemini_call.call_args[1]
    assert any(isinstance(part, dict) and part["mime_type"] == "image/png" for part in call_args["prompt_parts"])

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_pdf_success(mocker):
    """Tests successful parsing of a PDF file."""
    mock_llm_response = {
        "punch_events": [{"employee_name": "PDF User", "event_type": "Break Start", "timestamp_utc": "2023-01-01T12:00:00Z", "original_timestamp_str": "12:00", "timezone_str": "UTC"}],
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
    assert result.punch_events[0].employee_name == "PDF User"
    mock_gemini_call.assert_called_once()
    call_args = mock_gemini_call.call_args[1]
    assert any(isinstance(part, dict) and part["mime_type"] == "application/pdf" for part in call_args["prompt_parts"])

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_llm_returns_error_string(mocker):
    """Tests handling when LLM utility returns an error string."""
    error_message = "Error: LLM capacity issue."
    mocker.patch(
        "backend.app.core.llm_processing.get_gemini_response_with_function_calling",
        return_value=error_message
    )
    with pytest.raises(RuntimeError, match=f"LLM utility failed for .*test.txt.*: {error_message}"):
        await parse_file_to_structured_data(b"text", "text/plain", "test.txt")

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_llm_returns_text_instead_of_fc(mocker):
    """Tests handling when LLM returns text instead of a function call."""
    text_response = "The timesheet shows John Doe clocked in."
    mocker.patch(
        "backend.app.core.llm_processing.get_gemini_response_with_function_calling",
        return_value=text_response
    )
    result = await parse_file_to_structured_data(b"text", "text/plain", "test.txt")
    assert not result.punch_events
    assert len(result.parsing_issues) == 1
    assert "LLM did not use the function call" in result.parsing_issues[0]
    assert text_response in result.parsing_issues[0]

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_pydantic_validation_error(mocker):
    """Tests handling when LLM returns data that fails Pydantic validation."""
    mock_llm_response = {
        "punch_events": [{"employee_name": "Bad Data", "invalid_field": "should not be here"}], # invalid_field will cause error
        "parsing_issues": []
    }
    mocker.patch(
        "backend.app.core.llm_processing.get_gemini_response_with_function_calling",
        return_value=mock_llm_response
    )
    with pytest.raises(RuntimeError, match="LLM returned function call arguments, but failed to create Pydantic model"):
        await parse_file_to_structured_data(b"text", "text/plain", "pydantic_error_test.txt")

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_unsupported_mime_type():
    """Tests handling of unsupported MIME types."""
    with pytest.raises(ValueError, match="Unsupported MIME type for LLM processing: application/zip"):
        await parse_file_to_structured_data(b"zip_content", "application/zip", "test.zip")

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_excel_mime_type_raises_error():
    """Tests that raw Excel MIME types raise a ValueError as direct parsing is not supported."""
    file_bytes = b"fake_excel_bytes"
    filename = "test.xlsx"
    with pytest.raises(ValueError, match=f"Direct LLM schema extraction from raw Excel bytes .* for \'{filename}\' is not reliably supported"):
        await parse_file_to_structured_data(file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename)

    filename_xls = "test.xls"
    with pytest.raises(ValueError, match=f"Direct LLM schema extraction from raw Excel bytes .* for \'{filename_xls}\' is not reliably supported"):
        await parse_file_to_structured_data(file_bytes, "application/vnd.ms-excel", filename_xls)

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_text_unicode_decode_error():
    """Tests handling of text files that cannot be decoded as UTF-8."""
    # This byte sequence is invalid UTF-8
    invalid_utf8_bytes = b"\xff\xfe\xfd"
    mime_type = "text/plain"
    filename = "bad_encoding.txt"

    with pytest.raises(ValueError, match=f"Could not decode text-based file '{filename}' as UTF-8"):
        await parse_file_to_structured_data(invalid_utf8_bytes, mime_type, filename)

@pytest.mark.asyncio
async def test_parse_file_to_structured_data_llm_call_general_exception(mocker):
    """Tests handling of a general exception during the LLM call."""
    mocker.patch(
        "backend.app.core.llm_processing.get_gemini_response_with_function_calling",
        side_effect=Exception("Network error")
    )
    with pytest.raises(RuntimeError, match="Error during LLM processing for .*test.txt.* Network error"):
        await parse_file_to_structured_data(b"text", "text/plain", "test.txt")

@pytest.mark.asyncio
async def test_parse_specific_excel_file_success_after_preprocessing(mocker):
    """
    Tests that attempting to parse the specific '8.05 - Time Clock Detail.xlsx' file
    now succeeds by pre-processing it to text and then calling the LLM.
    """
    excel_file_path = "backend/app/tests/core/8.05 - Time Clock Detail.xlsx"
    original_filename = "8.05 - Time Clock Detail.xlsx"
    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    if not os.path.exists(excel_file_path):
        pytest.skip(f"Test Excel file not found at {excel_file_path}")
        return

    with open(excel_file_path, "rb") as f:
        file_bytes = f.read()
    
    # Mock the LLM call
    # IMPORTANT: Timestamps below are illustrative. You need to determine the correct UTC conversions 
    # based on the Excel sheet's implicit timezone and date/time formats.
    # Assume for this example that 9.00 means 9:00 AM and times are in US/Eastern for UTC conversion.
    mock_llm_response = {
        "punch_events": [
            {
                "employee_name": "BB - xxxxxxxxx / 649190 / Cashier", 
                "event_type": "Clock In",
                "timestamp_utc": "2025-03-16T13:00:00Z", # Assuming 9:00 AM US/Eastern = 13:00 UTC (adjust for actual TZ and DST)
                "original_timestamp_str": "3/16/2025 9.00 Sun", # Or how it appears to the LLM
                "timezone_str": "America/New_York", # Example
                "notes": "Clock in for 3/16"
            },
            {
                "employee_name": "BB - xxxxxxxxx / 649190 / Cashier",
                "event_type": "Clock Out",
                "timestamp_utc": "2025-03-16T15:13:00Z", # Assuming 11:13 AM US/Eastern
                "original_timestamp_str": "3/16/2025 11:13 AM Sun",
                "timezone_str": "America/New_York",
                "notes": "Clock out for 3/16"
            },
            {
                "employee_name": "BB - xxxxxxxxx / 649190 / Cashier",
                "event_type": "Clock In",
                "timestamp_utc": "2025-03-16T20:42:00Z", # Assuming 4:42 PM US/Eastern
                "original_timestamp_str": "3/16/2025 4:42 PM Sun",
                "timezone_str": "America/New_York",
                "notes": "Second clock in for 3/16"
            },
            {
                "employee_name": "BB - xxxxxxxxx / 649190 / Cashier",
                "event_type": "Clock Out",
                "timestamp_utc": "2025-03-16T21:06:00Z", # Assuming 5:06 PM US/Eastern
                "original_timestamp_str": "3/16/2025 5:06 PM Sun",
                "timezone_str": "America/New_York",
                "notes": "Second clock out for 3/16"
            }
            # Add more punch events as needed to represent the Excel data accurately
        ],
        "parsing_issues": ["Example parsing issue from Excel content"]
    }
    mock_gemini_call = mocker.patch(
        "backend.app.core.llm_processing.get_gemini_response_with_function_calling",
        return_value=mock_llm_response
    )

    result = await parse_file_to_structured_data(file_bytes, mime_type, original_filename)

    assert isinstance(result, LLMProcessingOutput)
    assert len(result.punch_events) == 4 # Adjusted to match mock
    assert result.punch_events[0].employee_name == "BB - xxxxxxxxx / 649190 / Cashier"
    assert result.punch_events[0].event_type == "Clock In"
    assert result.punch_events[1].event_type == "Clock Out"
    assert result.parsing_issues == ["Example parsing issue from Excel content"]
    
    mock_gemini_call.assert_called_once()
    call_args = mock_gemini_call.call_args[1] # kwargs
    assert "prompt_parts" in call_args
    
    # Check if some key content from the Excel (now text) was passed to LLM
    # This depends on how openpyxl stringifies the content. We expect CSV-like text.
    # You should adjust these checks based on actual content of your Excel's active sheet.
    # For example, check for a known header or a unique cell value.
    extracted_text_content_found = False
    for part in call_args["prompt_parts"]:
        if isinstance(part, str) and "Extracted Excel Content (CSV-like format)" in part:
            # Further check for some specific strings you expect from your Excel data
            assert "Employee / Job:,BB - xxxxxxxxx / 649190 / Cashier" in part # Header + employee info
            assert "3/16/2025,9.00,Sun,11:13 AM,,4:14 PM" in part # Example data row stringified
            assert "Hourly,,OT,,TIPS" in part # Check for part of the header row
            extracted_text_content_found = True
            break
    assert extracted_text_content_found, "Extracted Excel text content was not found in LLM prompt parts."

    assert "tools" in call_args
    assert len(call_args["tools"]) == 1
    assert call_args["tools"][0]["name"] == "timesheet_data_extractor"

# It might be useful to have a fixture for common mock LLM responses
# if more tests are added that require similar successful data structures.

# To run these tests, ensure pytest and pytest-asyncio are installed.
# Also, ensure that the GOOGLE_API_KEY or GEMINI_API_KEY environment variable is set if you intend to run
# the main_test() in llm_processing.py directly, though these unit tests mock out the actual API call. 