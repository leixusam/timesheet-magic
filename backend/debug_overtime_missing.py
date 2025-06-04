#!/usr/bin/env python3
"""
Debug script to investigate why overtime violations are not being detected
based on the CSV data that should show OT and double time violations.
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.models.schemas import LLMParsedPunchEvent, ViolationInstance
from app.core.compliance_rules import (
    detect_daily_overtime_violations,
    detect_weekly_overtime_violations,
    parse_shifts_from_punch_events,
    WorkShift,
    _detect_logical_shifts
)

def debug_overtime_detection():
    """Debug overtime detection with actual CSV data"""
    print("🔍 DEBUGGING OVERTIME DETECTION")
    print("=" * 80)
    
    # Based on the CSV screenshot - BB's data should show overtime
    # BB worked 3/25/2025 with two shifts that might be getting combined incorrectly
    
    # First, let's test with the midnight-crossing shift that should work over 8 hours
    print("\n📋 SCENARIO 1: BB's midnight-crossing shift (10:11 PM to 12:28 AM)")
    test_events_midnight = [
        LLMParsedPunchEvent(
            employee_identifier_in_file="BB",
            timestamp=datetime(2025, 3, 24, 22, 11),  # 10:11 PM on 3/24
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cashier",
            hourly_wage_as_parsed=18.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="BB",
            timestamp=datetime(2025, 3, 25, 0, 28),  # 12:28 AM on 3/25
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cashier",
            hourly_wage_as_parsed=18.00
        )
    ]
    
    debug_overtime_for_events(test_events_midnight, "Midnight Crossing")
    
    print("\n" + "=" * 80)
    print("📋 SCENARIO 2: BB's evening shift (5:04 PM to 10:25 PM)")
    test_events_evening = [
        LLMParsedPunchEvent(
            employee_identifier_in_file="BB",
            timestamp=datetime(2025, 3, 25, 17, 4),  # 5:04 PM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cashier",
            hourly_wage_as_parsed=18.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="BB",
            timestamp=datetime(2025, 3, 25, 22, 25),  # 10:25 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cashier",
            hourly_wage_as_parsed=18.00
        )
    ]
    
    debug_overtime_for_events(test_events_evening, "Evening Shift")
    
    print("\n" + "=" * 80)
    print("📋 SCENARIO 3: Combined shifts on same day (should trigger daily OT)")
    test_events_combined = test_events_midnight + test_events_evening
    
    debug_overtime_for_events(test_events_combined, "Combined Daily")
    
    print("\n" + "=" * 80)
    print("📋 SCENARIO 4: Long single shift (should trigger double time)")
    test_events_long = [
        LLMParsedPunchEvent(
            employee_identifier_in_file="TEST",
            timestamp=datetime(2025, 3, 25, 6, 0),  # 6:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cashier",
            hourly_wage_as_parsed=18.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="TEST",
            timestamp=datetime(2025, 3, 25, 21, 0),  # 9:00 PM (15 hours)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cashier",
            hourly_wage_as_parsed=18.00
        )
    ]
    
    debug_overtime_for_events(test_events_long, "Long Single Shift (15 hours)")

def debug_overtime_for_events(events, scenario_name):
    """Debug overtime detection for specific events"""
    print(f"\n🔄 DEBUGGING {scenario_name.upper()}")
    print("-" * 60)
    
    print(f"\n📝 Input Events ({len(events)} events):")
    for i, event in enumerate(events, 1):
        print(f"   {i}. {event.employee_identifier_in_file}: {event.punch_type_as_parsed}")
        print(f"      Time: {event.timestamp.strftime('%Y-%m-%d %I:%M %p')} (day {event.timestamp.day})")
    
    # Step 1: Parse into shifts WITH DEBUGGING
    print(f"\n🔄 STEP 1: Parsing into shifts...")
    
    # Group by employee first (same as in parse_shifts_from_punch_events)
    from collections import defaultdict
    events_by_employee = defaultdict(list)
    for event in events:
        events_by_employee[event.employee_identifier_in_file].append(event)
    
    for employee_id, employee_events in events_by_employee.items():
        print(f"\n🔍 DEBUGGING SHIFT DETECTION for {employee_id}:")
        
        # Sort events by timestamp
        sorted_events = sorted(employee_events, key=lambda x: x.timestamp)
        print(f"   Sorted events:")
        for i, event in enumerate(sorted_events):
            print(f"     {i+1}. {event.punch_type_as_parsed} at {event.timestamp.strftime('%I:%M %p')}")
        
        # Call the shift detection with debugging
        logical_shifts = _detect_logical_shifts(sorted_events)
        print(f"   Detected {len(logical_shifts)} logical shifts:")
        
        for shift_idx, shift_events in enumerate(logical_shifts):
            print(f"     Shift {shift_idx + 1} ({len(shift_events)} events):")
            for event in shift_events:
                print(f"       - {event.punch_type_as_parsed}: {event.timestamp.strftime('%I:%M %p')}")
    
    # Continue with the rest of the original function...
    shifts_by_employee = parse_shifts_from_punch_events(events)
    
    for employee_id, shifts in shifts_by_employee.items():
        print(f"\n👤 Employee: {employee_id} ({len(shifts)} shifts detected)")
        for shift_idx, shift in enumerate(shifts):
            print(f"\n   📅 Shift {shift_idx + 1}:")
            print(f"      Date: {shift.shift_date}")
            print(f"      Clock In: {shift.clock_in_time.strftime('%Y-%m-%d %I:%M %p') if shift.clock_in_time else 'None'}")
            print(f"      Clock Out: {shift.clock_out_time.strftime('%Y-%m-%d %I:%M %p') if shift.clock_out_time else 'None'}")
            print(f"      Total Hours: {shift.total_hours_worked:.2f}")
            
            # Check overtime thresholds
            if shift.total_hours_worked > 8.0:
                overtime_hours = shift.total_hours_worked - 8.0
                print(f"      ⚠️  OVERTIME: {overtime_hours:.2f} hours over 8-hour threshold")
                
                if shift.total_hours_worked > 12.0:
                    double_time_hours = shift.total_hours_worked - 12.0
                    print(f"      🚨 DOUBLE TIME: {double_time_hours:.2f} hours over 12-hour threshold")
            else:
                print(f"      ✅ No overtime (under 8 hours)")
    
    # Step 2: Test daily overtime detection
    print(f"\n🚨 STEP 2: Testing daily overtime detection...")
    daily_overtime_violations = detect_daily_overtime_violations(events)
    
    print(f"Found {len(daily_overtime_violations)} daily overtime violations:")
    for violation in daily_overtime_violations:
        print(f"\n❌ VIOLATION: {violation.rule_id}")
        print(f"   Employee: {violation.employee_identifier}")
        print(f"   Date: {violation.date_of_violation}")
        print(f"   Details: {violation.specific_details}")
    
    # Step 3: Test weekly overtime detection
    print(f"\n🚨 STEP 3: Testing weekly overtime detection...")
    weekly_overtime_violations = detect_weekly_overtime_violations(events)
    
    print(f"Found {len(weekly_overtime_violations)} weekly overtime violations:")
    for violation in weekly_overtime_violations:
        print(f"\n❌ VIOLATION: {violation.rule_id}")
        print(f"   Employee: {violation.employee_identifier}")
        print(f"   Date: {violation.date_of_violation}")
        print(f"   Details: {violation.specific_details}")
    
    # Step 4: Summary
    total_violations = len(daily_overtime_violations) + len(weekly_overtime_violations)
    print(f"\n📊 SUMMARY for {scenario_name}:")
    print(f"   Total Violations: {total_violations}")
    print(f"   Daily Overtime: {len(daily_overtime_violations)}")
    print(f"   Weekly Overtime: {len(weekly_overtime_violations)}")
    
    if total_violations == 0:
        print(f"   🤔 WHY NO VIOLATIONS?")
        # Check if we have valid shifts
        total_shifts = sum(len(shifts) for shifts in shifts_by_employee.values())
        total_hours = sum(
            shift.total_hours_worked 
            for shifts in shifts_by_employee.values() 
            for shift in shifts
        )
        print(f"   - Total shifts: {total_shifts}")
        print(f"   - Total hours across all shifts: {total_hours:.2f}")
        print(f"   - Should have overtime if any shift > 8 hours or total > 8 hours")

if __name__ == "__main__":
    debug_overtime_detection() 