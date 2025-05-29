import pytest
import os
import time
from backend.app.core.llm_processing import parse_file_to_structured_data

@pytest.mark.asyncio
async def test_debug_llm_with_805_short_csv():
    """
    Debug test for LLM processing with the actual 8.05-short.csv file
    """
    # Read the actual CSV file
    csv_file_path = os.path.join(os.path.dirname(__file__), "8.05-short.csv")
    
    with open(csv_file_path, 'rb') as f:
        file_bytes = f.read()
    
    # Also read as text to see what we're working with
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    print(f"[DEBUG] File size: {len(file_bytes)} bytes")
    print(f"[DEBUG] File lines: {len(file_content.split('\n'))}")
    print(f"[DEBUG] Expected events: 86")
    
    try:
        # Create debug directory for this test
        debug_dir = f"debug_runs/805_short_debug_{int(time.time())}"
        
        # Attempt to process the file
        result = await parse_file_to_structured_data(
            file_bytes=file_bytes,
            mime_type="text/csv",
            original_filename="8.05-short.csv",
            debug_dir=debug_dir
        )
        
        print(f"[DEBUG] Success! Found {len(result.punch_events)} punch events")
        print(f"[DEBUG] Expected 86 events, got {len(result.punch_events)} ({len(result.punch_events)/86*100:.1f}% coverage)")
        print(f"[DEBUG] Parsing issues: {len(result.parsing_issues)}")
        
        if result.parsing_issues:
            for issue in result.parsing_issues:
                print(f"[DEBUG] Issue: {issue}")
        
        # Verify we got some results
        assert len(result.punch_events) > 0, "Should have found some punch events"
        
        # Print a sample of what we found
        print(f"[DEBUG] First 3 events:")
        for i, event in enumerate(result.punch_events[:3]):
            print(f"  {i+1}: {event.employee_identifier_in_file} - {event.punch_type_as_parsed} at {event.timestamp}")
        
        if len(result.punch_events) > 3:
            print(f"[DEBUG] Last 3 events:")
            for i, event in enumerate(result.punch_events[-3:]):
                print(f"  {len(result.punch_events)-2+i}: {event.employee_identifier_in_file} - {event.punch_type_as_parsed} at {event.timestamp}")
            
    except Exception as e:
        print(f"[DEBUG] Error occurred: {str(e)}")
        # Don't fail the test on API errors, just log them
        if "temporarily unavailable" in str(e) or "500 INTERNAL" in str(e):
            pytest.skip(f"Skipping due to temporary API error: {str(e)}")
        else:
            raise

@pytest.mark.asyncio 
async def test_debug_llm_with_simple_csv():
    """
    Debug test with a very simple CSV to isolate LLM issues
    """
    simple_csv = """Employee,Date,Time,Action,Department
John Smith,2024-05-27,09:00,In,Kitchen
John Smith,2024-05-27,17:30,Out,Kitchen
Jane Doe,2024-05-27,08:00,In,Front
Jane Doe,2024-05-27,16:00,Out,Front"""
    
    try:
        result = await parse_file_to_structured_data(
            file_bytes=simple_csv.encode('utf-8'),
            mime_type="text/csv", 
            original_filename="simple_test.csv"
        )
        
        print(f"[DEBUG] Simple CSV - Found {len(result.punch_events)} punch events")
        print(f"[DEBUG] Simple CSV - Parsing issues: {result.parsing_issues}")
        
        assert len(result.punch_events) > 0, "Should have found some punch events in simple CSV"
        
        # Print what we found
        for i, event in enumerate(result.punch_events):
            print(f"[DEBUG] Simple CSV Event {i+1}: {event.employee_identifier_in_file} - {event.punch_type_as_parsed} at {event.timestamp}")
        
    except Exception as e:
        print(f"[DEBUG] Simple CSV Error: {str(e)}")
        if "temporarily unavailable" in str(e) or "500 INTERNAL" in str(e):
            pytest.skip(f"Skipping simple CSV test due to temporary API error: {str(e)}")
        else:
            raise