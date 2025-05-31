import pytest
import os
import time
from backend.app.core.llm_processing import parse_file_to_structured_data

@pytest.mark.asyncio
async def test_debug_llm_with_805_short_csv():
    """
    Debug test for LLM processing with the actual 8.05-short.csv file
    """
    csv_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "sample_data", "8.05-short.csv")
    
    if not os.path.exists(csv_file_path):
        pytest.skip(f"Sample file not found: {csv_file_path}")
    
    # Read the CSV file
    with open(csv_file_path, 'rb') as f:
        file_content = f.read()
    
    # Determine the MIME type
    mime_type = "text/csv"
    
    try:
        # Call the LLM processing function
        result = await parse_file_to_structured_data(
            file_bytes=file_content,
            mime_type=mime_type,
            original_filename="8.05-short.csv"
        )
        
        # Basic assertions
        assert result is not None, "Result should not be None"
        assert hasattr(result, 'punch_events'), "Result should have punch_events attribute"
        assert len(result.punch_events) > 0, "Should have parsed some punch events"
        
        # Print debug information
        print(f"\n=== DEBUG LLM RESULT ===")
        print(f"Number of punch events: {len(result.punch_events)}")
        print(f"First few events: {result.punch_events[:3]}")
        
        # Check the structure of the first event
        if result.punch_events:
            first_event = result.punch_events[0]
            print(f"First event structure: {first_event}")
            
            # Basic field checks
            assert hasattr(first_event, 'employee_name'), "Event should have employee_name"
            assert hasattr(first_event, 'date'), "Event should have date"
            assert hasattr(first_event, 'punch_type'), "Event should have punch_type"
            
    except Exception as e:
        print(f"\n=== DEBUG LLM ERROR ===")
        print(f"Error: {e}")
        print(f"Error type: {type(e)}")
        
        # Re-raise for pytest to catch
        raise

@pytest.mark.asyncio 
async def test_debug_llm_with_simple_csv():
    """
    Debug test with a simple, manually created CSV
    """
    simple_csv_content = """Employee Name,Date,Clock In,Clock Out
John Doe,2023-05-01,08:00,17:00
Jane Smith,2023-05-01,09:00,18:00
""".encode('utf-8')
    
    mime_type = "text/csv"
    
    try:
        result = await parse_file_to_structured_data(
            file_bytes=simple_csv_content,
            mime_type=mime_type,
            original_filename="simple_test.csv"
        )
        
        print(f"\n=== SIMPLE CSV RESULT ===")
        print(f"Result: {result}")
        print(f"Punch events: {result.punch_events if result else 'None'}")
        
    except Exception as e:
        print(f"\n=== SIMPLE CSV ERROR ===")
        print(f"Error: {e}")
        raise