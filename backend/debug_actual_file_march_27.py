#!/usr/bin/env python3
"""
Debug script to test the actual CSV file and specifically check March 27 parsing
"""

import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.core.llm_processing import parse_file_to_structured_data

async def debug_actual_file():
    """Debug the actual CSV file mentioned by the user"""
    print("🔍 DEBUGGING ACTUAL FILE: 8.05-short.csv")
    print("=" * 80)
    
    # Read the actual CSV file
    csv_file_path = Path(__file__).parent.parent / "sample_data" / "8.05-short.csv"
    
    if not csv_file_path.exists():
        print(f"❌ File not found: {csv_file_path}")
        return
    
    print(f"✅ Found file: {csv_file_path}")
    
    # Read file content
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    # Parse with LLM
    file_bytes = file_content.encode('utf-8')
    result = await parse_file_to_structured_data(file_bytes, 'text/csv', '8.05-short.csv')
    
    print(f"\n🤖 LLM PARSING RESULT:")
    print(f"   Found {len(result.punch_events)} punch events")
    
    # Focus on BB employee March 27 events
    print(f"\n🎯 FOCUSING ON BB EMPLOYEE MARCH 27 EVENTS:")
    bb_march_27_events = []
    
    for event in result.punch_events:
        if 'BB' in event.employee_identifier_in_file:
            if event.timestamp.month == 3 and event.timestamp.day == 27:
                bb_march_27_events.append(event)
                print(f"\n   📍 Found March 27 event:")
                print(f"      Date parsed: {event.timestamp.date()} ({event.timestamp.strftime('%A')})")
                print(f"      Time parsed: {event.timestamp.strftime('%I:%M %p')}")
                print(f"      Punch type: {event.punch_type_as_parsed}")
                print(f"      Full timestamp: {event.timestamp}")
    
    if not bb_march_27_events:
        print(f"\n   ❌ NO MARCH 27 EVENTS FOUND FOR BB!")
        print(f"   Let's check what dates were found for BB:")
        
        for event in result.punch_events:
            if 'BB' in event.employee_identifier_in_file:
                print(f"      {event.timestamp.date()} ({event.timestamp.strftime('%A')}) - {event.timestamp.strftime('%I:%M %p')}")
    
    # Test shift parsing to see what date gets assigned
    print(f"\n🔧 SHIFT PARSING TEST:")
    from app.core.compliance_rules import parse_shifts_from_punch_events
    
    shifts_by_employee = parse_shifts_from_punch_events(result.punch_events)
    
    for employee_id, shifts in shifts_by_employee.items():
        if 'BB' in employee_id:
            print(f"\n   Employee: {employee_id}")
            for i, shift in enumerate(shifts, 1):
                if shift.shift_date.month == 3 and shift.shift_date.day in [26, 27]:
                    print(f"   Shift {i} (around March 26-27):")
                    print(f"     Shift date: {shift.shift_date} ({shift.shift_date.strftime('%A')})")
                    print(f"     Clock in: {shift.clock_in_time}")
                    print(f"     Clock out: {shift.clock_out_time}")
                    print(f"     Total hours: {shift.total_hours}")

if __name__ == "__main__":
    asyncio.run(debug_actual_file()) 