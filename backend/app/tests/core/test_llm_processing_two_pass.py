"""
Unit Tests for Two-Pass LLM Processing

Tests the employee discovery and per-employee parsing functions using
real sample data files to ensure the two-pass approach works correctly.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from pathlib import Path

from app.core.llm_processing_two_pass import (
    discover_employees_in_file,
    parse_employee_punches,
    process_employees_in_parallel,
    stitch_employee_results,
    parse_file_to_structured_data_two_pass
)
from app.models.two_pass_schemas import (
    EmployeeDiscoveryResult,
    EmployeeDiscoveryOutput,
    PerEmployeeParsingOutput
)
from app.models.schemas import LLMParsedPunchEvent
from app.core.error_handlers import LLMServiceError, ParsingError, LLMComplexityError


# ===== FIXTURE: SAMPLE DATA LOADER =====

@pytest.fixture
def sample_data_dir():
    """Get the path to the sample_data directory"""
    return Path(__file__).parent.parent.parent.parent.parent / "sample_data"


@pytest.fixture
def sample_csv_content(sample_data_dir):
    """Load the 8.05-short.csv sample file content"""
    csv_file = sample_data_dir / "8.05-short.csv"
    if csv_file.exists():
        return csv_file.read_text(encoding='utf-8')
    else:
        # Fallback content if file doesn't exist
        return """Employee / Job:,,,BB - xxxxxxxxx / 649190 / Cashier,,,,,,,,,,,,,,,,,,,,,,,,,,
2490,,,3/16/2025,,9.00,,Sun,,,11:13 AM,,,,4:14 PM,,5.42,,48.78,,,0.00,,,0.00,,,48.78,,0.00
Employee / Job:,,,FM - xxxxxxxxx / 584862 / Cook,,,,,,,,,,,,,,,,,,,,,,,,,,
2490,,,3/17/2025,,12.00,,Mon,,,8:01 AM,,,,5:15 PM,,9.23,,110.76,,,0.00,,,0.00,,,110.76,,0.00"""


@pytest.fixture
def sample_simple_csv():
    """Simple CSV content for basic testing"""
    return """Employee,Date,Start Time,End Time
John Doe,2024-01-15,09:00,17:00
Jane Smith,2024-01-15,10:00,18:00
John Doe,2024-01-16,09:30,17:30"""


@pytest.fixture
def complex_csv_content():
    """Complex CSV content that should trigger two-pass processing"""
    employees = ["John Doe", "Jane Smith", "Bob Wilson", "Mary Johnson", "Tom Brown"]
    content = "Employee,Date,Time In,Time Out,Role\n"
    
    # Generate many rows to trigger complexity threshold
    for i in range(50):
        for emp in employees:
            content += f"{emp},2024-03-{15 + (i % 10)},09:00,17:00,Server\n"
    
    return content


# ===== MOCK RESPONSES =====

@pytest.fixture
def mock_discovery_response_success():
    """Mock successful employee discovery response from Gemini"""
    return {
        "employees": [
            {
                "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                "punch_count_estimate": 8,
                "canonical_name_suggestion": "BB"
            },
            {
                "employee_identifier_in_file": "FM - xxxxxxxxx / 584862 / Cook", 
                "punch_count_estimate": 12,
                "canonical_name_suggestion": "FM"
            },
            {
                "employee_identifier_in_file": "FA - xxxxxxxxx / 557233 / Shift Lead",
                "punch_count_estimate": 6,
                "canonical_name_suggestion": "FA"
            }
        ],
        "discovery_issues": []
    }


@pytest.fixture
def mock_employee_parsing_response_success():
    """Mock successful per-employee parsing response from Gemini"""
    return {
        "punch_events": [
            {
                "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                "timestamp": "2025-03-16T11:13:00",
                "punch_type_as_parsed": "Clock In",
                "role_as_parsed": "Cashier",
                "department_as_parsed": None,
                "location_note_as_parsed": None,
                "notes_as_parsed": None,
                "hourly_wage_as_parsed": 9.00
            },
            {
                "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                "timestamp": "2025-03-16T16:14:00",
                "punch_type_as_parsed": "Clock Out",
                "role_as_parsed": "Cashier",
                "department_as_parsed": None,
                "location_note_as_parsed": None,
                "notes_as_parsed": None,
                "hourly_wage_as_parsed": 9.00
            }
        ],
        "parsing_issues": []
    }


# ===== TESTS: EMPLOYEE DISCOVERY (Task 10.1) =====

@pytest.mark.asyncio
async def test_discover_employees_success(sample_csv_content):
    """Test successful employee discovery with real sample data"""
    
    # Mock the actual discovery that finds employees in the real file
    mock_response = {
        "employees": [
            {
                "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                "punch_count_estimate": 26,
                "canonical_name_suggestion": "BB"
            },
            {
                "employee_identifier_in_file": "BC - xxxxxxxxx / 664690 / Cook",
                "punch_count_estimate": 20,
                "canonical_name_suggestion": "BC"
            },
            {
                "employee_identifier_in_file": "FA - xxxxxxxxx / 557233 / Shift Lead",
                "punch_count_estimate": 14,
                "canonical_name_suggestion": "FA"
            },
            {
                "employee_identifier_in_file": "FM - xxxxxxxxx / 584862 / Cook",
                "punch_count_estimate": 26,
                "canonical_name_suggestion": "FM"
            }
        ],
        "discovery_issues": []
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.return_value = mock_response
        
        result = await discover_employees_in_file(
            file_content=sample_csv_content,
            original_filename="8.05-short.csv"
        )
        
        # Verify the result structure
        assert isinstance(result, EmployeeDiscoveryOutput)
        assert len(result.employees) == 4
        
        # Verify employee data - check that the employees from our mock are present
        employee_identifiers = [emp.employee_identifier_in_file for emp in result.employees]
        assert "BB - xxxxxxxxx / 649190 / Cashier" in employee_identifiers
        assert "FM - xxxxxxxxx / 584862 / Cook" in employee_identifiers
        assert "FA - xxxxxxxxx / 557233 / Shift Lead" in employee_identifiers
        assert "BC - xxxxxxxxx / 664690 / Cook" in employee_identifiers
        
        # Verify punch count estimates are reasonable (normalization may modify them)
        bb_employee = next(emp for emp in result.employees if "BB" in emp.employee_identifier_in_file)
        assert bb_employee.punch_count_estimate > 0
        
        # Verify Gemini was called correctly
        mock_gemini.assert_called_once()
        call_args = mock_gemini.call_args
        assert call_args[1]["prompt_parts"] is not None
        assert call_args[1]["tools"] is not None
        assert len(call_args[1]["tools"]) == 1
        assert call_args[1]["tools"][0]["name"] == "discover_employees"


@pytest.mark.asyncio
async def test_discover_employees_with_validation_issues(sample_csv_content):
    """Test employee discovery with validation issues (hallucinated employees)"""
    
    # Mock response with an employee that doesn't exist in the file
    mock_response = {
        "employees": [
            {
                "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",  
                "punch_count_estimate": 8,
                "canonical_name_suggestion": "BB"
            },
            {
                "employee_identifier_in_file": "FAKE_EMPLOYEE_123",  # This doesn't exist in the file
                "punch_count_estimate": 5,
                "canonical_name_suggestion": "Fake"
            }
        ],
        "discovery_issues": []
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.return_value = mock_response
        
        result = await discover_employees_in_file(
            file_content=sample_csv_content,
            original_filename="8.05-short.csv"
        )
        
        # The normalization process should filter out the fake employee
        # We should only get employees that actually exist in the file
        assert len(result.employees) >= 1  # At least the valid ones from the real file
        
        # Verify the fake employee was filtered out by checking identifiers
        employee_identifiers = [emp.employee_identifier_in_file for emp in result.employees]
        assert "FAKE_EMPLOYEE_123" not in employee_identifiers
        
        # Should have validation issues reported about the fake employee
        assert len(result.discovery_issues) > 0
        validation_issue = any("FAKE_EMPLOYEE_123" in issue for issue in result.discovery_issues)
        assert validation_issue


@pytest.mark.asyncio
async def test_discover_employees_deduplication(sample_simple_csv):
    """Test employee discovery deduplication logic"""
    
    # Mock response with duplicate employees
    mock_response = {
        "employees": [
            {
                "employee_identifier_in_file": "John Doe",
                "punch_count_estimate": 2,
                "canonical_name_suggestion": "John Doe"
            },
            {
                "employee_identifier_in_file": "John Doe",  # Duplicate
                "punch_count_estimate": 4,  # Higher count - should be used
                "canonical_name_suggestion": "John D"
            },
            {
                "employee_identifier_in_file": "Jane Smith",
                "punch_count_estimate": 2,
                "canonical_name_suggestion": "Jane Smith"
            }
        ],
        "discovery_issues": []
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.return_value = mock_response
        
        result = await discover_employees_in_file(
            file_content=sample_simple_csv,
            original_filename="test.csv"
        )
        
        # Should have deduplicated to 2 unique employees
        assert len(result.employees) == 2
        
        # John Doe should appear only once (deduplicated)
        john_does = [emp for emp in result.employees if emp.employee_identifier_in_file == "John Doe"]
        assert len(john_does) == 1
        
        # Should have deduplication notes in issues
        has_dedup_issue = any("duplicate" in issue.lower() for issue in result.discovery_issues)
        assert has_dedup_issue


@pytest.mark.asyncio
async def test_discover_employees_error_handling():
    """Test error handling during employee discovery"""
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        # Test LLM service error
        mock_gemini.side_effect = Exception("Google API Error 500 INTERNAL server error")
        
        with pytest.raises(Exception):  # Should propagate the error
            await discover_employees_in_file(
                file_content="test content",
                original_filename="test.csv"
            )


@pytest.mark.asyncio
async def test_discover_employees_empty_file():
    """Test employee discovery with empty file content"""
    
    mock_response = {
        "employees": [],
        "discovery_issues": ["No employees found in file"]
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.return_value = mock_response
        
        result = await discover_employees_in_file(
            file_content="",
            original_filename="empty.csv"
        )
        
        assert isinstance(result, EmployeeDiscoveryOutput)
        assert len(result.employees) == 0
        assert len(result.discovery_issues) > 0


@pytest.mark.asyncio 
async def test_discover_employees_performance_metrics(sample_csv_content):
    """Test that discovery function returns timing information"""
    
    mock_response = {
        "employees": [
            {
                "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",  # Use existing employee
                "punch_count_estimate": 5,
                "canonical_name_suggestion": "Test"
            }
        ],
        "discovery_issues": []
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.return_value = mock_response
        
        start_time = datetime.now()
        result = await discover_employees_in_file(
            file_content=sample_csv_content,
            original_filename="test.csv"
        )
        end_time = datetime.now()
        
        # Should complete reasonably quickly
        duration = (end_time - start_time).total_seconds()
        assert duration < 10.0  # Should complete within 10 seconds
        
        # Verify result is valid
        assert isinstance(result, EmployeeDiscoveryOutput)


# ===== TESTS: PER-EMPLOYEE PARSING (Task 10.2) =====

@pytest.mark.asyncio
async def test_parse_employee_punches_success(sample_csv_content):
    """Test successful per-employee parsing with real sample data"""
    
    mock_response = {
        "punch_events": [
            {
                "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                "timestamp": "2025-03-16T11:13:00",
                "punch_type_as_parsed": "Clock In",
                "role_as_parsed": "Cashier",
                "department_as_parsed": None,
                "location_note_as_parsed": None,
                "notes_as_parsed": None,
                "hourly_wage_as_parsed": 9.00
            },
            {
                "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                "timestamp": "2025-03-16T16:14:00",
                "punch_type_as_parsed": "Clock Out",
                "role_as_parsed": "Cashier",
                "department_as_parsed": None,
                "location_note_as_parsed": None,
                "notes_as_parsed": None,
                "hourly_wage_as_parsed": 9.00
            }
        ],
        "parsing_issues": []
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.return_value = mock_response
        
        result = await parse_employee_punches(
            file_content=sample_csv_content,
            employee_identifier="BB - xxxxxxxxx / 649190 / Cashier",
            original_filename="8.05-short.csv"
        )
        
        # Verify the result structure
        assert isinstance(result, PerEmployeeParsingOutput)
        assert result.employee_identifier == "BB - xxxxxxxxx / 649190 / Cashier"
        assert len(result.punch_events) == 2
        
        # Verify punch event data
        punch_events = result.punch_events
        clock_in = punch_events[0]
        assert clock_in.employee_identifier_in_file == "BB - xxxxxxxxx / 649190 / Cashier"
        assert clock_in.punch_type_as_parsed == "Clock In"
        assert clock_in.role_as_parsed == "Cashier"
        assert clock_in.hourly_wage_as_parsed == 9.00
        assert isinstance(clock_in.timestamp, datetime)
        
        clock_out = punch_events[1]
        assert clock_out.punch_type_as_parsed == "Clock Out"
        
        # Verify Gemini was called correctly
        mock_gemini.assert_called_once()
        call_args = mock_gemini.call_args
        assert "BB - xxxxxxxxx / 649190 / Cashier" in call_args[1]["prompt_parts"][0]
        assert call_args[1]["tools"][0]["name"] == "parse_employee_punches"


@pytest.mark.asyncio
async def test_parse_employee_punches_no_events():
    """Test per-employee parsing when no events are found for the employee"""
    
    mock_response = {
        "punch_events": [],  # No events found
        "parsing_issues": ["No punch events found for this employee"]
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.return_value = mock_response
        
        result = await parse_employee_punches(
            file_content="some file content",
            employee_identifier="NONEXISTENT_EMPLOYEE",
            original_filename="test.csv"
        )
        
        # Should return empty results but not fail
        assert isinstance(result, PerEmployeeParsingOutput)
        assert result.employee_identifier == "NONEXISTENT_EMPLOYEE"
        assert len(result.punch_events) == 0
        assert len(result.parsing_issues) == 1
        assert "No punch events found" in result.parsing_issues[0]


@pytest.mark.asyncio
async def test_parse_employee_punches_timestamp_formats():
    """Test per-employee parsing with various timestamp formats"""
    
    mock_response = {
        "punch_events": [
            {
                "employee_identifier_in_file": "John Doe",
                "timestamp": "2025-03-16T11:13:00Z",  # With Z timezone
                "punch_type_as_parsed": "Clock In"
            },
            {
                "employee_identifier_in_file": "John Doe", 
                "timestamp": "2025-03-16T16:14:00",  # Without timezone
                "punch_type_as_parsed": "Clock Out"
            }
        ],
        "parsing_issues": []
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.return_value = mock_response
        
        result = await parse_employee_punches(
            file_content="some content",
            employee_identifier="John Doe",
            original_filename="test.csv"
        )
        
        # Should parse both timestamp formats successfully
        assert len(result.punch_events) == 2
        
        for punch_event in result.punch_events:
            assert isinstance(punch_event.timestamp, datetime)
            assert punch_event.timestamp.year == 2025
            assert punch_event.timestamp.month == 3
            assert punch_event.timestamp.day == 16


@pytest.mark.asyncio
async def test_parse_employee_punches_filtering():
    """Test that per-employee parsing filters out other employees' events"""
    
    mock_response = {
        "punch_events": [
            {
                "employee_identifier_in_file": "John Doe",  # Target employee
                "timestamp": "2025-03-16T11:13:00",
                "punch_type_as_parsed": "Clock In"
            },
            {
                "employee_identifier_in_file": "Jane Smith",  # Wrong employee - should be filtered
                "timestamp": "2025-03-16T12:00:00",
                "punch_type_as_parsed": "Clock In"
            }
        ],
        "parsing_issues": []
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.return_value = mock_response
        
        result = await parse_employee_punches(
            file_content="some content",
            employee_identifier="John Doe",
            original_filename="test.csv"
        )
        
        # Should only return events for the requested employee
        assert len(result.punch_events) == 1
        assert result.punch_events[0].employee_identifier_in_file == "John Doe"


# ===== TESTS: PARALLEL PROCESSING AND RESULT STITCHING (Task 10.3) =====

@pytest.mark.asyncio
async def test_process_employees_in_parallel():
    """Test parallel processing of multiple employees"""
    
    # Mock employee discovery results
    employees = [
        EmployeeDiscoveryResult(
            employee_identifier_in_file="Employee A",
            punch_count_estimate=5,
            canonical_name_suggestion="A"
        ),
        EmployeeDiscoveryResult(
            employee_identifier_in_file="Employee B", 
            punch_count_estimate=3,
            canonical_name_suggestion="B"
        )
    ]
    
    # Mock responses for each employee
    mock_responses = [
        {
            "punch_events": [
                {
                    "employee_identifier_in_file": "Employee A",
                    "timestamp": "2025-03-16T09:00:00",
                    "punch_type_as_parsed": "Clock In"
                }
            ],
            "parsing_issues": []
        },
        {
            "punch_events": [
                {
                    "employee_identifier_in_file": "Employee B",
                    "timestamp": "2025-03-16T10:00:00",
                    "punch_type_as_parsed": "Clock In"
                }
            ],
            "parsing_issues": []
        }
    ]
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.side_effect = mock_responses
        
        results = await process_employees_in_parallel(
            file_content="test content",
            employees=employees,
            original_filename="test.csv",
            batch_size=2
        )
        
        # Should have results for both employees
        assert len(results) == 2
        
        # Verify both employees were processed
        employee_ids = [result.employee_identifier for result in results]
        assert "Employee A" in employee_ids
        assert "Employee B" in employee_ids


@pytest.mark.asyncio
async def test_stitch_employee_results():
    """Test stitching together results from multiple employees"""
    
    # Create mock employee parsing results
    employee_results = [
        PerEmployeeParsingOutput(
            employee_identifier="Employee A",
            punch_events=[
                LLMParsedPunchEvent(
                    employee_identifier_in_file="Employee A",
                    timestamp=datetime(2025, 3, 16, 9, 0),
                    punch_type_as_parsed="Clock In"
                )
            ],
            parsing_issues=[]
        ),
        PerEmployeeParsingOutput(
            employee_identifier="Employee B",
            punch_events=[
                LLMParsedPunchEvent(
                    employee_identifier_in_file="Employee B",
                    timestamp=datetime(2025, 3, 16, 10, 0),
                    punch_type_as_parsed="Clock In"
                )
            ],
            parsing_issues=[]
        )
    ]
    
    # Mock discovery result for comparison
    discovery_result = EmployeeDiscoveryOutput(
        employees=[
            EmployeeDiscoveryResult(
                employee_identifier_in_file="Employee A",
                punch_count_estimate=1,
                canonical_name_suggestion="A"
            ),
            EmployeeDiscoveryResult(
                employee_identifier_in_file="Employee B",
                punch_count_estimate=1,
                canonical_name_suggestion="B"
            )
        ],
        discovery_issues=[]
    )
    
    result = stitch_employee_results(
        discovery_result=discovery_result,
        employee_parsing_results=employee_results,
        original_filename="test.csv"
    )
    
    # Should combine all punch events
    assert len(result["punch_events"]) == 2
    
    # Should have processing metadata
    assert "processing_metadata" in result
    assert result["processing_metadata"]["discovered_employees"] == 2


# ===== INTEGRATION TESTS: COMPLETE TWO-PASS WORKFLOW (Task 10.4) =====

@pytest.mark.asyncio
async def test_two_pass_workflow_integration(sample_csv_content):
    """Test complete two-pass workflow with sample data"""
    
    # Mock the full workflow
    discovery_response = {
        "employees": [
            {
                "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                "punch_count_estimate": 8,
                "canonical_name_suggestion": "BB"
            }
        ],
        "discovery_issues": []
    }
    
    parsing_response = {
        "punch_events": [
            {
                "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                "timestamp": "2025-03-16T11:13:00",
                "punch_type_as_parsed": "Clock In",
                "role_as_parsed": "Cashier",
                "hourly_wage_as_parsed": 9.00
            }
        ],
        "parsing_issues": []
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        # First call (discovery) returns employee list
        # Second call (per-employee parsing) returns punch events
        mock_gemini.side_effect = [discovery_response, parsing_response]
        
        # Run complete two-pass workflow
        result = await parse_file_to_structured_data_two_pass(
            file_content=sample_csv_content,
            original_filename="8.05-short.csv"
        )
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "punch_events" in result
        assert "processing_metadata" in result
        
        # Verify punch events were found
        assert len(result["punch_events"]) >= 1
        
        # Verify processing metadata
        metadata = result["processing_metadata"]
        assert metadata["processing_mode"] == "two_pass"
        
        # Verify Gemini was called for both phases
        assert mock_gemini.call_count == 2


# ===== PERFORMANCE TESTS (Task 10.5) =====

@pytest.mark.asyncio
async def test_discovery_performance_logging(sample_csv_content, caplog):
    """Test that performance logging works correctly for discovery"""
    
    mock_response = {
        "employees": [
            {
                "employee_identifier_in_file": "Test Employee",
                "punch_count_estimate": 5,
                "canonical_name_suggestion": "Test"
            }
        ],
        "discovery_issues": []
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.return_value = mock_response
        
        await discover_employees_in_file(
            file_content=sample_csv_content,
            original_filename="8.05-short.csv"
        )
        
        # Check that debug logs were created (timing info is in debug logs)
        debug_logs = [record for record in caplog.records if record.levelname == "DEBUG"]
        assert len(debug_logs) > 0
        
        # Should have logs about the discovery process
        discovery_logs = [log for log in debug_logs if "discovery" in log.message.lower() or "8.05-short.csv" in log.message]
        assert len(discovery_logs) > 0


@pytest.mark.asyncio
async def test_two_pass_vs_single_pass_performance_comparison(complex_csv_content):
    """Test performance comparison between two-pass and single-pass approaches"""
    
    # This test verifies that two-pass approach properly handles complex files
    # In a real scenario, single-pass might fail on complex content due to token limits
    
    mock_discovery = {
        "employees": [
            {
                "employee_identifier_in_file": "John Doe",
                "punch_count_estimate": 50,
                "canonical_name_suggestion": "John"
            },
            {
                "employee_identifier_in_file": "Jane Smith",
                "punch_count_estimate": 50,
                "canonical_name_suggestion": "Jane"
            }
        ],
        "discovery_issues": []
    }
    
    mock_parsing = {
        "punch_events": [
            {
                "employee_identifier_in_file": "John Doe",
                "timestamp": "2024-03-15T09:00:00",
                "punch_type_as_parsed": "Clock In"
            }
        ],
        "parsing_issues": []
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.side_effect = [mock_discovery, mock_parsing, mock_parsing]
        
        start_time = datetime.now()
        result = await parse_file_to_structured_data_two_pass(
            file_content=complex_csv_content,
            original_filename="complex.csv"
        )
        end_time = datetime.now()
        
        # Should complete successfully
        assert isinstance(result, dict)
        assert "punch_events" in result
        
        # Should complete in reasonable time
        duration = (end_time - start_time).total_seconds()
        assert duration < 30.0  # Should complete within 30 seconds
        
        # Should have performance metrics
        metadata = result.get("processing_metadata", {})
        assert "workflow_stages" in metadata


# ===== EDGE CASE TESTS (Task 10.7) =====

@pytest.mark.asyncio
async def test_single_employee_file():
    """Test two-pass processing with file containing only one employee"""
    
    single_employee_content = """Employee,Date,Time In,Time Out
John Doe,2024-03-15,09:00,17:00"""
    
    mock_discovery = {
        "employees": [
            {
                "employee_identifier_in_file": "John Doe",
                "punch_count_estimate": 2,
                "canonical_name_suggestion": "John"
            }
        ],
        "discovery_issues": []
    }
    
    mock_parsing = {
        "punch_events": [
            {
                "employee_identifier_in_file": "John Doe",
                "timestamp": "2024-03-15T09:00:00",
                "punch_type_as_parsed": "Clock In"
            },
            {
                "employee_identifier_in_file": "John Doe",
                "timestamp": "2024-03-15T17:00:00",
                "punch_type_as_parsed": "Clock Out"
            }
        ],
        "parsing_issues": []
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.side_effect = [mock_discovery, mock_parsing]
        
        result = await parse_file_to_structured_data_two_pass(
            file_content=single_employee_content,
            original_filename="single_employee.csv"
        )
        
        # Should handle single employee correctly
        assert len(result["punch_events"]) == 2
        assert result["processing_metadata"]["discovered_employees"] == 1


@pytest.mark.asyncio
async def test_no_employees_file():
    """Test two-pass processing with file containing no employees"""
    
    empty_content = "Date,Note\n2024-03-15,No staff scheduled"
    
    mock_discovery = {
        "employees": [],
        "discovery_issues": ["No employees found in file"]
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.return_value = mock_discovery
        
        result = await parse_file_to_structured_data_two_pass(
            file_content=empty_content,
            original_filename="no_employees.csv"
        )
        
        # Should handle no employees gracefully
        assert len(result["punch_events"]) == 0
        assert result["processing_metadata"]["discovered_employees"] == 0
        assert len(result["parsing_issues"]) > 0


@pytest.mark.asyncio
async def test_malformed_data_file():
    """Test two-pass processing with malformed file data"""
    
    malformed_content = "This is not a proper timesheet file\nJust some random text\n123,456,abc"
    
    mock_discovery = {
        "employees": [],
        "discovery_issues": ["File appears to be malformed or not a timesheet"]
    }
    
    with patch('llm_utils.google_utils.get_gemini_response_with_function_calling_async') as mock_gemini:
        mock_gemini.return_value = mock_discovery
        
        result = await parse_file_to_structured_data_two_pass(
            file_content=malformed_content,
            original_filename="malformed.txt"
        )
        
        # Should handle malformed data gracefully
        assert len(result["punch_events"]) == 0
        assert len(result["parsing_issues"]) > 0
        malformed_issue = any("malformed" in issue.lower() for issue in result["parsing_issues"])
        assert malformed_issue 