#!/usr/bin/env python3
"""
Direct backend test for CSV upload functionality
"""
import asyncio
import sys
import os
import pytest

# Add the backend directory to the path
sys.path.insert(0, '/Users/lei/repos/time-sheet-magic/backend')

from dotenv import load_dotenv
load_dotenv('.env.local')

from app.core.llm_processing import parse_file_to_structured_data

@pytest.mark.asyncio
async def test_csv_upload():
    """Test CSV upload with the actual file that's failing"""
    
    # Path to the test CSV file
    csv_file_path = '/Users/lei/repos/time-sheet-magic/sample_data/8.05-short.csv'
    
    print("🧪 Testing CSV Upload Directly")
    print("=" * 50)
    print(f"📁 File: {csv_file_path}")
    
    # Check if file exists
    if not os.path.exists(csv_file_path):
        print(f"❌ ERROR: File not found at {csv_file_path}")
        return
    
    # Read the file
    with open(csv_file_path, 'rb') as f:
        file_content = f.read()
    
    print(f"📊 File size: {len(file_content)} bytes")
    print(f"🔍 MIME type: text/csv")
    
    try:
        print("\n🚀 Starting LLM processing...")
        result = await parse_file_to_structured_data(
            file_bytes=file_content,
            mime_type='text/csv',
            original_filename='8.05-short.csv'
        )
        
        print("✅ SUCCESS!")
        print(f"📈 Parsed {len(result.punch_events)} punch events")
        print(f"⚠️ {len(result.parsing_issues)} parsing issues")
        
        if result.punch_events:
            print(f"\n📋 First event: {result.punch_events[0].employee_identifier_in_file} at {result.punch_events[0].timestamp}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print(f"🔧 Error type: {type(e)}")
        import traceback
        print(f"📄 Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    print("🔥 Direct Backend CSV Upload Test")
    asyncio.run(test_csv_upload()) 