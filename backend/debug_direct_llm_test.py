#!/usr/bin/env python3
"""
Direct LLM test to see what the AI is parsing from the CSV data
that should contain overtime violations.
"""

import sys
import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.core.llm_processing import parse_file_to_structured_data

# Sample CSV data based on the screenshot the user showed
CSV_DATA_WITH_OVERTIME = """
BB - xxxxxxxxx / 649190 / Cashier,,,,,NAME,Hourly

3/16/2025,,Sun,,11:13 AM,4:14 PM,5.42,48.78
3/16/2025,,Sun,,4:42 PM,5:08 PM,,
3/20/2025,9.00,Thu,,5:02 PM,10:01 PM,4.98,44.82
3/21/2025,9.00,Fri,,5:02 PM,10:13 PM,5.13,73.17
3/21/2025,,Fri,,10:42 PM,1:39 AM,,
3/23/2025,9.00,Sun,,11:02 AM,3:13 PM,6.40,57.60
3/23/2025,,Sun,,3:52 PM,6:05 PM,,
3/24/2025,9.00,Mon,,5:36 PM,9:53 PM,6.56,59.04
3/24/2025,,Mon,,10:11 PM,12:29 AM,,
3/25/2025,9.00,Tue,,5:04 PM,10:25 PM,5.35,48.15
3/27/2025,9.00,Thu,,5:05 PM,12:05 AM,7.00,63.00
3/28/2025,9.00,Fri,,4:43 PM,9:37 PM,7.43,66.87
3/28/2025,,Fri,,10:06 PM,12:50 AM,,
""".strip()

async def test_direct_llm_parsing():
    """Test LLM parsing directly with CSV data"""
    
    print("🔍 TESTING DIRECT LLM PARSING")
    print("=" * 80)
    
    print(f"\n📝 CSV DATA TO PARSE:")
    print(CSV_DATA_WITH_OVERTIME)
    
    try:
        # Convert to bytes for the function
        csv_bytes = CSV_DATA_WITH_OVERTIME.encode('utf-8')
        
        print(f"\n🤖 CALLING LLM...")
        
        # Call the LLM processing function directly
        result = await parse_file_to_structured_data(
            file_bytes=csv_bytes,
            mime_type='text/csv',
            original_filename='test_overtime_data.csv',
            debug_dir=None
        )
        
        print(f"✅ LLM PARSING COMPLETED")
        print(f"📊 Found {len(result.punch_events)} punch events")
        
        if result.parsing_issues:
            print(f"⚠️  Parsing issues: {len(result.parsing_issues)}")
            for issue in result.parsing_issues:
                print(f"   - {issue}")
        
        # Analyze the parsed events
        print(f"\n📋 PARSED PUNCH EVENTS:")
        bb_events = []
        
        for i, event in enumerate(result.punch_events, 1):
            employee = event.employee_identifier_in_file
            timestamp = event.timestamp
            punch_type = event.punch_type_as_parsed
            
            print(f"   {i}. {employee}: {punch_type}")
            print(f"      Time: {timestamp.strftime('%Y-%m-%d %I:%M %p')} (day {timestamp.day})")
            
            if 'BB' in employee:
                bb_events.append(event)
        
        print(f"\n👤 BB SPECIFIC EVENTS: {len(bb_events)}")
        
        # Group BB events by date to see shifts
        from collections import defaultdict
        bb_by_date = defaultdict(list)
        
        for event in bb_events:
            date_key = event.timestamp.date()
            bb_by_date[date_key].append(event)
        
        for date, events in sorted(bb_by_date.items()):
            print(f"\n📅 BB events on {date}:")
            total_duration = 0
            
            clock_ins = []
            clock_outs = []
            
            for event in sorted(events, key=lambda x: x.timestamp):
                time_str = event.timestamp.strftime('%I:%M %p')
                print(f"   - {event.punch_type_as_parsed}: {time_str}")
                
                if 'in' in event.punch_type_as_parsed.lower():
                    clock_ins.append(event.timestamp)
                elif 'out' in event.punch_type_as_parsed.lower():
                    clock_outs.append(event.timestamp)
            
            # Calculate work duration if we have pairs
            if len(clock_ins) == len(clock_outs):
                for clock_in, clock_out in zip(clock_ins, clock_outs):
                    duration = (clock_out - clock_in).total_seconds() / 3600
                    total_duration += duration
                    print(f"   Duration: {duration:.2f} hours")
            
            if total_duration > 8.0:
                overtime = total_duration - 8.0
                print(f"   🚨 OVERTIME DETECTED: {overtime:.2f} hours over 8-hour limit")
                
                if total_duration > 12.0:
                    double_time = total_duration - 12.0
                    print(f"   💥 DOUBLE TIME: {double_time:.2f} hours over 12-hour limit")
            else:
                print(f"   ✅ No overtime ({total_duration:.2f} hours)")
        
        # Test overtime detection
        print(f"\n⚡ TESTING SHIFT PARSING AND OVERTIME DETECTION...")
        
        from app.core.compliance_rules import (
            detect_daily_overtime_violations, 
            detect_weekly_overtime_violations,
            parse_shifts_from_punch_events
        )
        
        # Get the actual logical shifts as parsed by the system
        shifts_by_employee = parse_shifts_from_punch_events(result.punch_events)
        
        print(f"\n🔧 LOGICAL SHIFTS (as detected by smart shift boundary detection):")
        for employee_id, shifts in shifts_by_employee.items():
            if 'BB' in employee_id:
                print(f"\n👤 {employee_id} has {len(shifts)} logical shifts:")
                
                for i, shift in enumerate(shifts, 1):
                    print(f"\n   📋 Shift {i} (Date: {shift.shift_date}):")
                    print(f"      Clock In:  {shift.clock_in_time.strftime('%I:%M %p') if shift.clock_in_time else 'N/A'}")
                    print(f"      Clock Out: {shift.clock_out_time.strftime('%I:%M %p') if shift.clock_out_time else 'N/A'}")
                    print(f"      Total Hours: {shift.total_hours_worked:.2f}")
                    print(f"      Punch Events: {len(shift.punch_events)}")
                    
                    for j, event in enumerate(shift.punch_events):
                        day_suffix = "st" if event.timestamp.day == 1 else "nd" if event.timestamp.day == 2 else "rd" if event.timestamp.day == 3 else "th"
                        print(f"        {j+1}. {event.punch_type_as_parsed}: {event.timestamp.strftime('%I:%M %p')} on {event.timestamp.strftime('%b %d')}{day_suffix}")
                    
                    if shift.total_hours_worked > 8.0:
                        overtime = shift.total_hours_worked - 8.0
                        print(f"      🚨 OVERTIME: {overtime:.2f} hours over 8-hour limit")
                        
                        if shift.total_hours_worked > 12.0:
                            double_time = shift.total_hours_worked - 12.0
                            print(f"      💥 DOUBLE TIME: {double_time:.2f} hours over 12-hour limit")
                    else:
                        print(f"      ✅ No overtime")
        
        daily_ot = detect_daily_overtime_violations(result.punch_events)
        weekly_ot = detect_weekly_overtime_violations(result.punch_events)
        
        print(f"\n🎯 VIOLATION DETECTION RESULTS:")
        print(f"   Daily overtime violations: {len(daily_ot)}")
        print(f"   Weekly overtime violations: {len(weekly_ot)}")
        
        for violation in daily_ot:
            print(f"   📋 Daily OT: {violation.rule_id} - {violation.employee_identifier} on {violation.date_of_violation}")
            print(f"       Details: {violation.specific_details}")
        
        for violation in weekly_ot:
            print(f"   📋 Weekly OT: {violation.rule_id} - {violation.employee_identifier} on {violation.date_of_violation}")
            print(f"       Details: {violation.specific_details}")
        
        if len(daily_ot) == 0 and len(weekly_ot) == 0:
            print(f"   ❌ NO OVERTIME VIOLATIONS DETECTED!")
            print(f"   This suggests:")
            print(f"   1. LLM is not parsing times correctly (AM/PM issue)")
            print(f"   2. Shift parsing is grouping incorrectly")
            print(f"   3. Overtime logic has an issue")
            print(f"   4. Date parsing is wrong")
        elif len(daily_ot) > 0 and len(weekly_ot) == 0:
            print(f"   ⚠️  Daily OT found but no Weekly OT - might be expected if not over 40hrs/week")
        
        # Let's also check if there are really long shifts that should trigger double time
        long_shifts = []
        for employee_id, shifts in shifts_by_employee.items():
            if 'BB' in employee_id:
                for shift in shifts:
                    if shift.total_hours_worked > 12.0:
                        long_shifts.append((shift.shift_date, shift.total_hours_worked))
        
        if long_shifts:
            print(f"\n💪 LONG SHIFTS DETECTED (>12 hours):")
            for shift_date, hours in long_shifts:
                print(f"   - {shift_date}: {hours:.2f} hours (should trigger double time)")
        else:
            print(f"\n💤 No shifts over 12 hours detected")
        
        # Check weekly totals
        print(f"\n📅 WEEKLY TOTALS CHECK:")
        weekly_hours = defaultdict(float)
        
        for employee_id, shifts in shifts_by_employee.items():
            if 'BB' in employee_id:
                for shift in shifts:
                    # Get the Sunday of the week containing this shift
                    days_since_sunday = shift.shift_date.weekday() + 1 if shift.shift_date.weekday() != 6 else 0
                    week_start = shift.shift_date - timedelta(days=days_since_sunday)
                    weekly_hours[week_start] += shift.total_hours_worked
        
        for week_start, total_hours in weekly_hours.items():
            week_end = week_start + timedelta(days=6)
            print(f"   Week {week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')}: {total_hours:.2f} hours")
            if total_hours > 40.0:
                weekly_ot_hours = total_hours - 40.0
                print(f"      🚨 WEEKLY OVERTIME: {weekly_ot_hours:.2f} hours over 40-hour limit")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Set environment variable for testing
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("❌ No GOOGLE_API_KEY or GEMINI_API_KEY found. Please set one for testing.")
        print("For testing: export GOOGLE_API_KEY='your_key_here'")
    else:
        asyncio.run(test_direct_llm_parsing()) 