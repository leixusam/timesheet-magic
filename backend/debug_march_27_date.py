#!/usr/bin/env python3
"""
Debug script to investigate the March 27 vs March 26 date issue
"""

import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.core.llm_processing import parse_file_to_structured_data

# The specific CSV data showing the March 27 issue
CSV_DATA_MARCH_27 = """
Employee / Job:,,,BB - xxxxxxxxx / 649190 / Cashier,,,,,,,,,,,,,,,,,,,,,,,,,,

2490,,,3/27/2025,,9.00,,Thu,,,5:05 PM,,,,12:05 AM,,7.00,,63.00,,,0.00,,,0.00,,,63.00,,0.00
"""

async def debug_march_27_parsing():
    """Debug the March 27 date parsing issue"""
    print("🔍 DEBUGGING MARCH 27 DATE PARSING")
    print("=" * 80)
    
    print(f"\n📊 CSV INPUT:")
    print("   Date: 3/27/2025 (Thursday)")
    print("   Shift: 5:05 PM - 12:05 AM")
    print("   Expected: March 27, 2025")
    
    # Parse with LLM
    result = await parse_file_to_structured_data(CSV_DATA_MARCH_27, "march27_test.csv", "march27_test.csv")
    
    print(f"\n🤖 LLM PARSING RESULT:")
    print(f"   Found {len(result.punch_events)} punch events")
    
    for event in result.punch_events:
        if 'BB' in event.employee_identifier_in_file:
            print(f"\n   Employee: {event.employee_identifier_in_file}")
            print(f"   Date parsed: {event.timestamp.date()} ({event.timestamp.strftime('%A')})")
            print(f"   Time parsed: {event.timestamp.strftime('%I:%M %p')}")
            print(f"   Punch type: {event.punch_type_as_parsed}")
            print(f"   Full timestamp: {event.timestamp}")
    
    # Test shift parsing
    print(f"\n🔧 SHIFT PARSING TEST:")
    from app.core.compliance_rules import parse_shifts_from_punch_events
    
    shifts_by_employee = parse_shifts_from_punch_events(result.punch_events)
    
    for employee_id, shifts in shifts_by_employee.items():
        if 'BB' in employee_id:
            print(f"\n   Employee: {employee_id}")
            for i, shift in enumerate(shifts, 1):
                print(f"   Shift {i}:")
                print(f"     Shift date: {shift.shift_date} ({shift.shift_date.strftime('%A')})")
                print(f"     Clock in: {shift.clock_in_time}")
                print(f"     Clock out: {shift.clock_out_time}")
                print(f"     Total hours: {shift.total_hours}")

if __name__ == "__main__":
    asyncio.run(debug_march_27_parsing()) 