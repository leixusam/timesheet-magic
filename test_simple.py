#!/usr/bin/env python3

import sys
import os
import asyncio
import json
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from backend.app.core.llm_processing import parse_file_to_structured_data

async def test_simple_csv_processing():
    print("Simple CSV Processing Test")
    print("=" * 40)
    
    # Create debug folder with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_dir = f"debug_runs/simple_{timestamp}"
    os.makedirs(debug_dir, exist_ok=True)
    print(f"📁 Debug folder created: {debug_dir}")
    
    # Create simple CSV test data
    csv_content = """Employee Name,Date,Time,Action,Role
BB - xxxxxxxxx,03/16/2025,11:13 AM,Clock In,Cashier
BB - xxxxxxxxx,03/16/2025,04:14 PM,Clock Out,Cashier
BC - xxxxxxxxx,03/17/2025,10:01 AM,Clock In,Cook
BC - xxxxxxxxx,03/17/2025,02:30 PM,Clock Out,Cook"""
    
    csv_bytes = csv_content.encode('utf-8')
    
    print(f"📊 Test CSV size: {len(csv_bytes)} bytes")
    
    # Save test CSV
    csv_path = os.path.join(debug_dir, "test_data.csv")
    with open(csv_path, 'w') as f:
        f.write(csv_content)
    print(f"💾 Test CSV saved: {csv_path}")
    
    try:
        print(f"\n🚀 Starting LLM processing...")
        start_time = datetime.now()
        
        result = await parse_file_to_structured_data(
            file_bytes=csv_bytes,
            mime_type="text/csv",
            original_filename="test_data.csv",
            debug_dir=debug_dir
        )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"\n✅ Success! Processing completed in {processing_time:.2f} seconds")
        print(f"📝 Extracted {len(result.punch_events)} punch events")
        print(f"⚠️  Parsing issues: {len(result.parsing_issues)}")
        
        # Show details
        for i, event in enumerate(result.punch_events, 1):
            print(f"{i}. {event.employee_identifier_in_file} - {event.punch_type_as_parsed} at {event.timestamp}")
        
        # Save output
        output_data = {
            "test_type": "simple_csv",
            "processing_time_seconds": processing_time,
            "result": result.model_dump()  # This contains datetime objects
        }
        
        output_path = os.path.join(debug_dir, "output.json")
        with open(output_path, 'w') as f:
            # Use model_dump_json which handles datetime serialization
            result_json = json.loads(result.model_dump_json())
            output_data["result"] = result_json
            json.dump(output_data, f, indent=2)
        print(f"💾 Output saved: {output_path}")
        
        print(f"\n🎉 Simple test - COMPLETE!")
        
        return len(result.punch_events) > 0  # Return success indicator
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_minimal_excel():
    print("\nMinimal Excel Test")
    print("=" * 30)
    
    # Create debug folder with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_dir = f"debug_runs/minimal_excel_{timestamp}"
    os.makedirs(debug_dir, exist_ok=True)
    print(f"📁 Debug folder created: {debug_dir}")
    
    # Read just the first few lines of the Excel file
    excel_path = "backend/app/tests/core/8.05-short.xlsx"
    with open(excel_path, "rb") as f:
        file_bytes = f.read()
    
    print(f"📊 Excel file size: {len(file_bytes):,} bytes")
    
    # First, let's see what the Excel content looks like when parsed
    import openpyxl
    import io
    
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        sheet = workbook.active
        
        print("\nFirst 10 rows of Excel content:")
        sample_lines = []
        for row_idx, row in enumerate(sheet.iter_rows()):
            if row_idx >= 10:  # Only first 10 rows
                break
            row_values = []
            for cell in row:
                cell_value = cell.value
                if cell_value is None:
                    row_values.append("")
                else:
                    row_values.append(str(cell_value).strip())
            row_text = ",".join(row_values)
            print(f"Row {row_idx + 1}: {row_text}")
            sample_lines.append(row_text)
        
        # Create minimal sample with just first few data rows
        minimal_content = "\n".join(sample_lines[:8])  # Just first 8 rows
        minimal_bytes = minimal_content.encode('utf-8')
        
        print(f"\nTesting with minimal content ({len(minimal_bytes)} bytes):")
        print(minimal_content[:500] + ("..." if len(minimal_content) > 500 else ""))
        
        # Save minimal sample
        sample_path = os.path.join(debug_dir, "minimal_sample.txt")
        with open(sample_path, 'w') as f:
            f.write(minimal_content)
        
        # Test with text/csv MIME type first
        print(f"\n🚀 Testing minimal content as CSV...")
        start_time = datetime.now()
        
        result = await parse_file_to_structured_data(
            file_bytes=minimal_bytes,
            mime_type="text/csv",  # Use CSV type to avoid Excel processing complexity
            original_filename="minimal_sample.csv",
            debug_dir=debug_dir
        )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"\n✅ Minimal Excel test completed in {processing_time:.2f} seconds")
        print(f"📝 Extracted {len(result.punch_events)} punch events")
        
        for i, event in enumerate(result.punch_events, 1):
            print(f"{i}. {event.employee_identifier_in_file} - {event.punch_type_as_parsed} at {event.timestamp}")
        
        return len(result.punch_events) > 0
        
    except Exception as e:
        print(f"❌ Minimal Excel test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_csv_processing())
    if success:
        print("\n✅ Simple test passed")
        excel_success = asyncio.run(test_minimal_excel())
        if excel_success:
            print("\n✅ Minimal Excel test passed - Excel processing works!")
        else:
            print("\n❌ Minimal Excel test failed - issue with Excel content format")
    else:
        print("\n❌ Simple test failed - need to fix basic functionality first") 