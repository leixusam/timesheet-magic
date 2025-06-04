#!/usr/bin/env python3
"""
Debug script to track timestamps through the entire meal break calculation pipeline
to identify exactly where timezone conversion is still happening.
"""

import sys
import os
import pytz
from datetime import datetime, timedelta, date
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.models.schemas import LLMParsedPunchEvent, ViolationInstance
from app.core.compliance_rules import (
    detect_meal_break_violations, 
    parse_shifts_from_punch_events, 
    WorkShift,
    _serialize_punch_event_for_violation,
    _create_shift_summary_for_violation,
    _check_first_meal_break_violation
)

def debug_timezone_discrepancy():
    """Debug timezone discrepancy step by step through the pipeline"""
    print("🔍 DEBUGGING TIMEZONE DISCREPANCY IN MEAL BREAK CALCULATION")
    print("=" * 80)
    
    # Create test events that might match the actual data causing the issue
    # Based on the screenshot: times that result in 07:28 AM meal break detection
    
    # Scenario 1: Simple case with just Clock In/Out (like screenshot shows 2 events)
    print("\n📋 SCENARIO 1: Simple Clock In/Out (should show NO meal breaks)")
    test_events_simple = [
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee",
            timestamp=datetime(2025, 3, 25, 0, 56),  # 12:56 AM local
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=18.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee",
            timestamp=datetime(2025, 3, 25, 10, 30),  # 10:30 AM local
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=18.00
        )
    ]
    
    debug_meal_break_pipeline(test_events_simple, "Simple")
    
    # Scenario 2: Events with meal break punches that might create the 07:28 discrepancy
    print("\n" + "=" * 80)
    print("📋 SCENARIO 2: With meal break events (might show meal break at 07:28)")
    test_events_with_meal = [
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee",
            timestamp=datetime(2025, 3, 25, 0, 56),  # 12:56 AM local
            punch_type_as_parsed="Clock In", 
            role_as_parsed="Cook",
            hourly_wage_as_parsed=18.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee",
            timestamp=datetime(2025, 3, 25, 7, 28),  # 07:28 AM - potential meal break start
            punch_type_as_parsed="Meal Break Start",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=18.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee",
            timestamp=datetime(2025, 3, 25, 7, 58),  # 07:58 AM - potential meal break end
            punch_type_as_parsed="Meal Break End",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=18.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee",
            timestamp=datetime(2025, 3, 25, 10, 30),  # 10:30 AM local
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=18.00
        )
    ]
    
    debug_meal_break_pipeline(test_events_with_meal, "With Meal Break")
    
    # Scenario 3: UTC timestamps that might get converted differently
    print("\n" + "=" * 80)
    print("📋 SCENARIO 3: UTC timestamps (might show timezone conversion issues)")
    utc_tz = pytz.UTC
    test_events_utc = [
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee UTC",
            timestamp=utc_tz.localize(datetime(2025, 3, 25, 8, 56)),  # 8:56 AM UTC = 12:56 AM Pacific (in March DST)
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=18.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee UTC",
            timestamp=utc_tz.localize(datetime(2025, 3, 25, 15, 28)),  # 3:28 PM UTC = 7:28 AM Pacific
            punch_type_as_parsed="Meal Break Start",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=18.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee UTC",
            timestamp=utc_tz.localize(datetime(2025, 3, 25, 15, 58)),  # 3:58 PM UTC = 7:58 AM Pacific
            punch_type_as_parsed="Meal Break End",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=18.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee UTC",
            timestamp=utc_tz.localize(datetime(2025, 3, 25, 18, 30)),  # 6:30 PM UTC = 10:30 AM Pacific
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=18.00
        )
    ]
    
    debug_meal_break_pipeline(test_events_utc, "UTC")

def debug_meal_break_pipeline(events, scenario_name):
    """Debug the meal break pipeline step by step"""
    print(f"\n🔄 DEBUGGING {scenario_name.upper()} SCENARIO")
    print("-" * 60)
    
    print(f"\n📝 STEP 1: Input Punch Events ({len(events)} events)")
    for i, event in enumerate(events, 1):
        tz_info = f" (TZ: {event.timestamp.tzinfo})" if event.timestamp.tzinfo else " (naive)"
        print(f"   {i}. {event.punch_type_as_parsed}: {event.timestamp.isoformat()}{tz_info}")
        print(f"      Formatted: {event.timestamp.strftime('%Y-%m-%d %I:%M:%S %p')}")
    
    # Step 2: Parse into shifts
    print(f"\n🔄 STEP 2: Parsing into shifts...")
    shifts_by_employee = parse_shifts_from_punch_events(events)
    
    for employee_id, shifts in shifts_by_employee.items():
        print(f"\n👤 Employee: {employee_id}")
        for shift_idx, shift in enumerate(shifts):
            print(f"\n   📅 Shift {shift_idx + 1}:")
            print(f"      Date: {shift.shift_date}")
            
            # Debug shift analysis - call analyze_shift manually and track changes
            print(f"\n   🔍 BEFORE analyze_shift():")
            print(f"      - Raw punch events: {len(shift.punch_events)}")
            for i, event in enumerate(shift.punch_events):
                tz_info = f" (TZ: {event.timestamp.tzinfo})" if event.timestamp.tzinfo else " (naive)"
                print(f"        {i+1}. {event.punch_type_as_parsed}: {event.timestamp.isoformat()}{tz_info}")
            
            # Call analyze_shift to process the events
            shift.analyze_shift()
            
            print(f"\n   🔍 AFTER analyze_shift():")
            print(f"      - Clock In: {shift.clock_in_time.isoformat() if shift.clock_in_time else 'None'}")
            if shift.clock_in_time:
                tz_info = f" (TZ: {shift.clock_in_time.tzinfo})" if shift.clock_in_time.tzinfo else " (naive)"
                print(f"        Formatted: {shift.clock_in_time.strftime('%Y-%m-%d %I:%M:%S %p')}{tz_info}")
                
            print(f"      - Clock Out: {shift.clock_out_time.isoformat() if shift.clock_out_time else 'None'}")
            if shift.clock_out_time:
                tz_info = f" (TZ: {shift.clock_out_time.tzinfo})" if shift.clock_out_time.tzinfo else " (naive)"
                print(f"        Formatted: {shift.clock_out_time.strftime('%Y-%m-%d %I:%M:%S %p')}{tz_info}")
            
            print(f"      - Total Hours: {shift.total_hours_worked:.2f}")
            
            # Add detailed debug info about work periods
            print(f"      - Work Periods: {len(shift.continuous_work_periods) if hasattr(shift, 'continuous_work_periods') else 'N/A'}")
            if hasattr(shift, 'continuous_work_periods'):
                for i, (start, end) in enumerate(shift.continuous_work_periods, 1):
                    duration = (end - start).total_seconds() / 3600
                    print(f"        Period {i}: {start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')} ({duration:.2f} hours)")
            
            print(f"      - Meal Breaks: {len(shift.meal_breaks)}")
            
            for i, (start, end) in enumerate(shift.meal_breaks, 1):
                duration = (end - start).total_seconds() / 60
                start_tz = f" (TZ: {start.tzinfo})" if start.tzinfo else " (naive)"
                end_tz = f" (TZ: {end.tzinfo})" if end.tzinfo else " (naive)"
                print(f"        Break {i}: {start.isoformat()}{start_tz} to {end.isoformat()}{end_tz}")
                print(f"                 Formatted: {start.strftime('%I:%M:%S %p')} to {end.strftime('%I:%M:%S %p')} ({duration:.0f} min)")
                
            # Check for meal break event detection
            has_meal_events = any(
                any(keyword in event.punch_type_as_parsed.lower() for keyword in ['meal', 'lunch', 'break'])
                for event in shift.punch_events
            )
            print(f"      - Has explicit meal break events: {has_meal_events}")
    
    # Step 3: Detect violations and track timestamp handling
    print(f"\n🚨 STEP 3: Detecting violations...")
    violations = detect_meal_break_violations(events)
    
    print(f"Found {len(violations)} violations:")
    for violation in violations:
        print(f"\n❌ VIOLATION: {violation.rule_id}")
        print(f"   📝 Details: {violation.specific_details}")
        
        print(f"\n   🕐 Related Punch Events:")
        if violation.related_punch_events:
            for punch in violation.related_punch_events:
                print(f"      - Timestamp: {punch['timestamp']}")
                print(f"        Formatted: {punch['formatted_time']}")
                print(f"        Type: {punch['punch_type']}")
        
        print(f"\n   📊 Shift Summary:")
        if violation.shift_summary:
            summary = violation.shift_summary
            print(f"      - Clock In: {summary.get('clock_in_time', 'N/A')}")
            print(f"        Formatted: {summary.get('clock_in_formatted', 'N/A')}")
            print(f"      - Clock Out: {summary.get('clock_out_time', 'N/A')}")
            print(f"        Formatted: {summary.get('clock_out_formatted', 'N/A')}")
            print(f"      - Total Hours: {summary.get('total_hours_worked', 0):.2f}")
            print(f"      - Meal Breaks: {summary.get('meal_break_count', 0)}")
            
            if summary.get('meal_breaks'):
                for i, meal_break in enumerate(summary['meal_breaks'], 1):
                    print(f"        Break {i}: {meal_break['start_time']} to {meal_break['end_time']}")
                    print(f"                 Formatted: {meal_break['start_formatted']} to {meal_break['end_formatted']}")

if __name__ == "__main__":
    debug_timezone_discrepancy() 