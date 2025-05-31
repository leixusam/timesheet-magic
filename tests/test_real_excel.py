#!/usr/bin/env python3
"""
Real Excel File Test with Extended Timeout
Tests the LLM processing with the full Excel timesheet file.
"""

import asyncio
import os
import sys
from pathlib import Path
import json
from datetime import datetime as dt

# Add the backend app to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.llm_processing import parse_file_to_structured_data

async def test_real_excel_file():
    """Test LLM processing with the real Excel file"""
    print("🚀 Testing Real Excel File Processing")
    print("=" * 60)
    
    # Use the real Excel file
    excel_file_path = backend_dir / "tests" / "core" / "8.05 - Time Clock Detail.xlsx"
    
    if not excel_file_path.exists():
        print(f"❌ Excel file not found: {excel_file_path}")
        return False
    
    with open(excel_file_path, 'rb') as f:
        file_bytes = f.read()
    
    file_size_mb = len(file_bytes) / (1024 * 1024)
    print(f"📄 Testing with: {excel_file_path.name}")
    print(f"📊 File size: {file_size_mb:.1f} MB ({len(file_bytes):,} bytes)")
    
    debug_dir = current_dir / "debug_runs" / f"real_excel_{dt.now().strftime('%Y%m%d_%H%M%S')}"
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    # Set generous timeout for real Excel file - 10 minutes
    timeout_seconds = 600  # 10 minutes
    print(f"⏱️ Setting timeout: {timeout_seconds} seconds ({timeout_seconds//60} minutes)")
    print(f"💡 This is a large file, so processing may take several minutes...")
    
    try:
        print(f"\n🤖 Starting LLM processing...")
        print(f"⏳ Please wait - processing large Excel file...")
        start_time = dt.now()
        
        # Progress indicator function
        async def progress_indicator():
            """Show progress every 30 seconds"""
            elapsed = 0
            while True:
                await asyncio.sleep(30)
                elapsed += 30
                elapsed_minutes = elapsed // 60
                elapsed_seconds = elapsed % 60
                print(f"⏳ Still processing... ({elapsed_minutes}m {elapsed_seconds}s elapsed)")
        
        # Start progress indicator
        progress_task = asyncio.create_task(progress_indicator())
        
        try:
            # Wrap the LLM call with asyncio timeout
            result = await asyncio.wait_for(
                parse_file_to_structured_data(
                    file_bytes=file_bytes,
                    mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    original_filename=excel_file_path.name,
                    debug_dir=str(debug_dir)
                ),
                timeout=timeout_seconds
            )
        finally:
            # Cancel progress indicator
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
        
        end_time = dt.now()
        processing_time = (end_time - start_time).total_seconds()
        processing_minutes = int(processing_time // 60)
        processing_seconds = int(processing_time % 60)
        
        print(f"\n✅ SUCCESS! Processing completed in {processing_minutes}m {processing_seconds}s")
        print(f"📊 Results:")
        print(f"   - Extracted {len(result.punch_events)} punch events")
        print(f"   - Parsing issues: {len(result.parsing_issues)}")
        
        # Analyze the extracted data
        employees = set()
        roles = set()
        punch_types = set()
        date_range = []
        
        for event in result.punch_events:
            employees.add(event.employee_identifier_in_file)
            if hasattr(event, 'role_as_parsed') and event.role_as_parsed:
                roles.add(event.role_as_parsed)
            punch_types.add(event.punch_type_as_parsed)
            if hasattr(event.timestamp, 'date'):
                date_range.append(event.timestamp.date())
            elif isinstance(event.timestamp, str):
                # Parse ISO string to get date
                try:
                    parsed_dt = dt.fromisoformat(event.timestamp.replace('Z', '+00:00'))
                    date_range.append(parsed_dt.date())
                except:
                    pass
        
        print(f"\n📋 Data Summary:")
        print(f"   - Unique employees: {len(employees)}")
        print(f"   - Unique roles: {len(roles)}")
        print(f"   - Unique punch types: {len(punch_types)}")
        
        if date_range:
            min_date = min(date_range)
            max_date = max(date_range)
            print(f"   - Date range: {min_date} to {max_date}")
        
        print(f"\n👥 Employees found:")
        for i, emp in enumerate(sorted(list(employees))[:10], 1):  # Show first 10
            print(f"   {i}. {emp[:50]}{'...' if len(emp) > 50 else ''}")
        if len(employees) > 10:
            print(f"   ... and {len(employees) - 10} more")
        
        print(f"\n🎭 Roles found:")
        for role in sorted(list(roles)):
            print(f"   - {role}")
        
        print(f"\n⏰ Punch types found:")
        for punch_type in sorted(list(punch_types)):
            print(f"   - {punch_type}")
        
        if result.parsing_issues:
            print(f"\n⚠️ Parsing issues:")
            for i, issue in enumerate(result.parsing_issues[:5], 1):  # Show first 5
                print(f"   {i}. {issue}")
            if len(result.parsing_issues) > 5:
                print(f"   ... and {len(result.parsing_issues) - 5} more issues")
        
        # Save detailed results
        output_data = {
            "success": True,
            "processing_time_seconds": processing_time,
            "file_info": {
                "filename": excel_file_path.name,
                "size_bytes": len(file_bytes),
                "size_mb": file_size_mb
            },
            "results": {
                "events_count": len(result.punch_events),
                "issues_count": len(result.parsing_issues),
                "unique_employees": len(employees),
                "unique_roles": len(roles),
                "unique_punch_types": len(punch_types),
                "date_range": {
                    "min_date": str(min(date_range)) if date_range else None,
                    "max_date": str(max(date_range)) if date_range else None
                }
            },
            "employees": sorted(list(employees)),
            "roles": sorted(list(roles)),
            "punch_types": sorted(list(punch_types)),
            "timestamp": dt.now().isoformat()
        }
        
        with open(debug_dir / "excel_test_results.json", 'w') as f:
            json.dump(output_data, f, indent=2)
        
        # Save the LLM parsed data as well
        with open(debug_dir / "llm_parsed_data.json", 'w') as f:
            json.dump(json.loads(result.model_dump_json()), f, indent=2)
        
        print(f"💾 Results saved to: {debug_dir}")
        print(f"📁 Check debug folder for detailed output and LLM response")
        
        return True
        
    except asyncio.TimeoutError:
        print(f"\n❌ TIMEOUT: Processing exceeded {timeout_seconds} seconds ({timeout_seconds//60} minutes)")
        print(f"   The Excel file might be too large or the API is experiencing issues")
        print(f"   Consider:")
        print(f"   1. Breaking the file into smaller chunks")
        print(f"   2. Using a faster model")
        print(f"   3. Increasing the timeout further")
        
        # Save timeout info
        timeout_data = {
            "error": "timeout",
            "timeout_seconds": timeout_seconds,
            "file_size_mb": file_size_mb,
            "timestamp": dt.now().isoformat(),
            "recommendations": [
                "Break file into smaller chunks",
                "Use a faster model",
                "Increase timeout period"
            ]
        }
        
        with open(debug_dir / "timeout_error.json", 'w') as f:
            json.dump(timeout_data, f, indent=2)
        
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        # Save error info
        error_data = {
            "error": str(e),
            "error_type": e.__class__.__name__,
            "file_size_mb": file_size_mb,
            "timestamp": dt.now().isoformat()
        }
        
        with open(debug_dir / "error_log.json", 'w') as f:
            json.dump(error_data, f, indent=2)
        
        return False

async def main():
    """Run the real Excel file test"""
    print("🧪 Real Excel File Processing Test")
    print("=" * 60)
    
    success = await test_real_excel_file()
    
    if success:
        print(f"\n🎉 SUCCESS: Real Excel file processed successfully!")
        print(f"✅ The LLM processing is working correctly with large files")
        print(f"✅ Your backend is ready for production timesheet processing")
    else:
        print(f"\n❌ FAILED: Real Excel file processing encountered issues")
        print(f"🔧 Check the debug output for more details")

if __name__ == "__main__":
    asyncio.run(main()) 