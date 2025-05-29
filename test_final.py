#!/usr/bin/env python3

import sys
import os
import asyncio
import json
import shutil
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from backend.app.core.llm_processing import parse_file_to_structured_data

async def test_final_excel_processing():
    print("Final CSV Processing Test with Debug Output")
    print("=" * 60)
    
    # Create debug folder with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_dir = f"debug_runs/run_{timestamp}"
    os.makedirs(debug_dir, exist_ok=True)
    print(f"📁 Debug folder created: {debug_dir}")
    
    # Read the Excel file
    excel_path = "backend/app/tests/core/8.05-short.csv"
    with open(excel_path, "rb") as f:
        file_bytes = f.read()
    
    print(f"📊 File size: {len(file_bytes):,} bytes")
    
    # Save a copy of the input file
    input_filename = f"input_{timestamp}.csv"
    input_save_path = os.path.join(debug_dir, input_filename)
    shutil.copy2(excel_path, input_save_path)
    print(f"💾 Input file saved: {input_save_path}")
    
    try:
        print(f"\n🚀 Starting LLM processing...")
        start_time = datetime.now()
        
        result = await parse_file_to_structured_data(
            file_bytes=file_bytes,
            mime_type="text/csv",
            original_filename=os.path.basename(excel_path),
            debug_dir=debug_dir
        )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"\n✅ Success! Processing completed in {processing_time:.2f} seconds")
        print(f"📝 Extracted {len(result.punch_events)} punch events")
        print(f"⚠️  Parsing issues: {len(result.parsing_issues)}")
        
        # Show summary of employees and their punch counts
        employee_counts = {}
        role_counts = {}
        for event in result.punch_events:
            emp_id = event.employee_identifier_in_file
            role = event.role_as_parsed or "Unknown"
            
            if emp_id not in employee_counts:
                employee_counts[emp_id] = 0
            employee_counts[emp_id] += 1
            
            if role not in role_counts:
                role_counts[role] = 0
            role_counts[role] += 1
        
        print(f"\n👥 Employee Summary:")
        for emp_id, count in employee_counts.items():
            print(f"  {emp_id}: {count} punch events")
        
        print(f"\n🎭 Role Summary:")
        for role, count in role_counts.items():
            print(f"  {role}: {count} punch events")
        
        # Show date range
        timestamps = [event.timestamp for event in result.punch_events]
        if timestamps:
            # Convert datetime objects to strings if needed
            if hasattr(timestamps[0], 'isoformat'):
                dates = [ts.isoformat().split('T')[0] for ts in timestamps]  
            else:
                dates = [str(ts).split('T')[0] for ts in timestamps]
            min_date = min(dates)
            max_date = max(dates)
            print(f"\n📅 Date Range: {min_date} to {max_date}")
        else:
            min_date = max_date = None
        
        # Save output as JSON
        output_data = {
            "metadata": {
                "input_file": os.path.basename(excel_path),
                "processing_timestamp": timestamp,
                "processing_time_seconds": processing_time,
                "total_punch_events": len(result.punch_events),
                "total_parsing_issues": len(result.parsing_issues),
                "employee_counts": employee_counts,
                "role_counts": role_counts,
                "date_range": {
                    "min_date": min_date if timestamps else None,
                    "max_date": max_date if timestamps else None
                }
            },
            "parsed_data": json.loads(result.model_dump_json())  # Handle datetime serialization
        }
        
        output_filename = f"output_{timestamp}.json"
        output_save_path = os.path.join(debug_dir, output_filename)
        with open(output_save_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Output file saved: {output_save_path}")
        
        # Save a readable summary
        summary_filename = f"summary_{timestamp}.txt"
        summary_save_path = os.path.join(debug_dir, summary_filename)
        with open(summary_save_path, 'w', encoding='utf-8') as f:
            f.write(f"Excel Timesheet Processing Summary\n")
            f.write(f"{'=' * 40}\n\n")
            f.write(f"Input File: {os.path.basename(excel_path)}\n")
            f.write(f"Processing Time: {processing_time:.2f} seconds\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"Results:\n")
            f.write(f"- Total Punch Events: {len(result.punch_events)}\n")
            f.write(f"- Parsing Issues: {len(result.parsing_issues)}\n")
            f.write(f"- Date Range: {min_date if timestamps else 'N/A'} to {max_date if timestamps else 'N/A'}\n\n")
            
            f.write(f"Employee Summary:\n")
            for emp_id, count in employee_counts.items():
                f.write(f"- {emp_id}: {count} punch events\n")
            
            f.write(f"\nRole Summary:\n")
            for role, count in role_counts.items():
                f.write(f"- {role}: {count} punch events\n")
                
            if result.parsing_issues:
                f.write(f"\nParsing Issues:\n")
                for i, issue in enumerate(result.parsing_issues, 1):
                    f.write(f"{i}. {issue}\n")
            
            f.write(f"\nFirst 5 Punch Events (for verification):\n")
            for i, event in enumerate(result.punch_events[:5], 1):
                f.write(f"{i}. {event.employee_identifier_in_file} - {event.punch_type_as_parsed} at {event.timestamp}\n")
                if event.role_as_parsed:
                    f.write(f"   Role: {event.role_as_parsed}\n")
        
        print(f"📄 Summary file saved: {summary_save_path}")
        
        print(f"\n🎉 LLM Processing Task 3.3 - COMPLETE!")
        print(f"🔍 Review files in: {debug_dir}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Save error log
        error_filename = f"error_{timestamp}.txt"
        error_save_path = os.path.join(debug_dir, error_filename)
        with open(error_save_path, 'w', encoding='utf-8') as f:
            f.write(f"Error during processing:\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Error: {str(e)}\n\n")
            f.write("Traceback:\n")
            f.write(traceback.format_exc())
        print(f"💾 Error log saved: {error_save_path}")

if __name__ == "__main__":
    asyncio.run(test_final_excel_processing()) 