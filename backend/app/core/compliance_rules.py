"""
Compliance Rules Module for Timesheet Analysis

This module implements various labor law compliance checks including:
- Meal break violations
- Rest break violations (future)
- Overtime violations (future)
- Other compliance rules

Based on California Labor Law (can be extended for other jurisdictions)
"""

import os
import sys
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict
import json

# Add the parent directory to sys.path to import from models
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from models.schemas import (
    LLMParsedPunchEvent, 
    ViolationInstance, 
    EmployeeReportDetails,
    LLMProcessingOutput
)

class WorkShift:
    """Represents a single work shift for an employee on a specific date"""
    
    def __init__(self, employee_identifier: str, shift_date: date):
        self.employee_identifier = employee_identifier
        self.shift_date = shift_date
        self.punch_events: List[LLMParsedPunchEvent] = []
        self.clock_in_time: Optional[datetime] = None
        self.clock_out_time: Optional[datetime] = None
        self.total_hours_worked: float = 0.0
        self.meal_breaks: List[Tuple[datetime, datetime]] = []  # (start, end) times
        self.continuous_work_periods: List[Tuple[datetime, datetime]] = []  # Periods without meal breaks
        
    def add_punch_event(self, event: LLMParsedPunchEvent):
        """Add a punch event to this shift"""
        self.punch_events.append(event)
        
    def analyze_shift(self) -> None:
        """Analyze the punch events to determine work periods and breaks"""
        if not self.punch_events:
            return
            
        # Sort events by timestamp
        sorted_events = sorted(self.punch_events, key=lambda x: x.timestamp)
        
        # Track the work periods and breaks
        current_work_start = None
        work_periods = []
        
        for event in sorted_events:
            punch_type = event.punch_type_as_parsed.lower()
            
            if "in" in punch_type or "start" in punch_type:
                if current_work_start is None:
                    current_work_start = event.timestamp
                    if self.clock_in_time is None:
                        self.clock_in_time = event.timestamp
                        
            elif "out" in punch_type or "end" in punch_type:
                if current_work_start is not None:
                    work_periods.append((current_work_start, event.timestamp))
                    self.clock_out_time = event.timestamp
                    current_work_start = None
        
        # If there's an unmatched clock in, assume they're still working
        if current_work_start is not None and self.clock_out_time is not None:
            work_periods.append((current_work_start, self.clock_out_time))
        
        # Calculate total hours and identify meal breaks
        self.total_hours_worked = 0.0
        self.continuous_work_periods = []
        
        for i, (start, end) in enumerate(work_periods):
            period_hours = (end - start).total_seconds() / 3600
            self.total_hours_worked += period_hours
            
            # If there's a gap between work periods > 20 minutes, it's likely a meal break
            if i < len(work_periods) - 1:
                gap_start = end
                gap_end = work_periods[i + 1][0]
                gap_duration = (gap_end - gap_start).total_seconds() / 60  # minutes
                
                if gap_duration >= 20:  # Assume breaks >= 20 minutes are meal breaks
                    self.meal_breaks.append((gap_start, gap_end))
                    
            # Track continuous work periods (for meal break analysis)
            if i == 0:
                continuous_start = start
            else:
                # Check if previous gap was a meal break
                prev_gap_start = work_periods[i-1][1]
                prev_gap_end = start
                prev_gap_duration = (prev_gap_end - prev_gap_start).total_seconds() / 60
                
                if prev_gap_duration >= 20:  # Previous gap was a meal break
                    # Close previous continuous period and start new one
                    self.continuous_work_periods.append((continuous_start, prev_gap_start))
                    continuous_start = start
                    
            # If this is the last period, close the continuous work period
            if i == len(work_periods) - 1:
                self.continuous_work_periods.append((continuous_start, end))

def parse_shifts_from_punch_events(punch_events: List[LLMParsedPunchEvent]) -> Dict[str, List[WorkShift]]:
    """
    Parse punch events into organized work shifts by employee and date
    
    Returns:
        Dict mapping employee_identifier to list of WorkShift objects
    """
    shifts_by_employee = defaultdict(lambda: defaultdict(lambda: None))
    
    for event in punch_events:
        # Extract date from timestamp
        shift_date = event.timestamp.date()
        employee_id = event.employee_identifier_in_file
        
        # Get or create shift for this employee and date
        if shifts_by_employee[employee_id][shift_date] is None:
            shifts_by_employee[employee_id][shift_date] = WorkShift(employee_id, shift_date)
            
        shifts_by_employee[employee_id][shift_date].add_punch_event(event)
    
    # Analyze all shifts and convert to simple dict
    result = {}
    for employee_id, date_shifts in shifts_by_employee.items():
        shifts_list = []
        for shift_date, shift in date_shifts.items():
            shift.analyze_shift()
            shifts_list.append(shift)
        result[employee_id] = sorted(shifts_list, key=lambda s: s.shift_date)
        
    return result

def detect_meal_break_violations(punch_events: List[LLMParsedPunchEvent]) -> List[ViolationInstance]:
    """
    Detect meal break violations based on California Labor Law:
    
    California Requirements:
    - Employees working more than 5 hours must get a 30-minute meal break
    - The meal break must start before the end of the 5th hour of work
    - If working more than 10 hours, a second 30-minute meal break is required
    - The second meal break must start before the end of the 10th hour of work
    
    Args:
        punch_events: List of parsed punch events from LLM processing
        
    Returns:
        List of ViolationInstance objects representing meal break violations
    """
    violations = []
    
    # Parse punch events into shifts
    shifts_by_employee = parse_shifts_from_punch_events(punch_events)
    
    for employee_id, shifts in shifts_by_employee.items():
        for shift in shifts:
            # Skip shifts with insufficient data or very short shifts
            if shift.total_hours_worked <= 0 or not shift.clock_in_time:
                continue
                
            violations.extend(_check_shift_meal_breaks(shift))
    
    return violations

def _check_shift_meal_breaks(shift: WorkShift) -> List[ViolationInstance]:
    """Check a single shift for meal break violations"""
    violations = []
    
    # California meal break requirements
    FIRST_MEAL_BREAK_THRESHOLD = 5.0  # hours
    SECOND_MEAL_BREAK_THRESHOLD = 10.0  # hours
    MINIMUM_MEAL_BREAK_DURATION = 30  # minutes
    MEAL_BREAK_TIMING_LIMIT = 5.0  # Must start before end of 5th hour for first break
    SECOND_MEAL_BREAK_TIMING_LIMIT = 10.0  # Must start before end of 10th hour for second break
    
    total_hours = shift.total_hours_worked
    
    # Check for first meal break violation (> 5 hours worked)
    if total_hours > FIRST_MEAL_BREAK_THRESHOLD:
        first_meal_violation = _check_first_meal_break_violation(shift, MEAL_BREAK_TIMING_LIMIT, MINIMUM_MEAL_BREAK_DURATION)
        if first_meal_violation:
            violations.append(first_meal_violation)
    
    # Check for second meal break violation (> 10 hours worked)
    if total_hours > SECOND_MEAL_BREAK_THRESHOLD:
        second_meal_violation = _check_second_meal_break_violation(shift, SECOND_MEAL_BREAK_TIMING_LIMIT, MINIMUM_MEAL_BREAK_DURATION)
        if second_meal_violation:
            violations.append(second_meal_violation)
            
    return violations

def _check_first_meal_break_violation(shift: WorkShift, timing_limit_hours: float, min_duration_minutes: int) -> Optional[ViolationInstance]:
    """Check for first meal break violation"""
    
    # Calculate the latest time the meal break should have started
    latest_meal_start = shift.clock_in_time + timedelta(hours=timing_limit_hours)
    
    # Check if there are any meal breaks
    if not shift.meal_breaks:
        # No meal breaks found - violation
        return ViolationInstance(
            rule_id="MEAL_BREAK_MISSING_FIRST",
            rule_description="Missing required first meal break (California Labor Code Section 512)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"Worked {shift.total_hours_worked:.1f} hours with no meal breaks detected. "
                           f"California law requires a 30-minute meal break for shifts over 5 hours, "
                           f"starting no later than {latest_meal_start.strftime('%I:%M %p')}.",
            suggested_action_generic="Ensure employees working more than 5 hours receive an uninterrupted "
                                   "30-minute meal break that starts before the end of their 5th hour of work."
        )
    
    # Check if the first meal break started too late
    first_meal_start, first_meal_end = shift.meal_breaks[0]
    meal_duration_minutes = (first_meal_end - first_meal_start).total_seconds() / 60
    
    if first_meal_start > latest_meal_start:
        return ViolationInstance(
            rule_id="MEAL_BREAK_LATE_FIRST",
            rule_description="First meal break started too late (California Labor Code Section 512)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"First meal break started at {first_meal_start.strftime('%I:%M %p')}, "
                           f"but should have started by {latest_meal_start.strftime('%I:%M %p')}. "
                           f"Worked {shift.total_hours_worked:.1f} hours total.",
            suggested_action_generic="Schedule meal breaks to start before the end of the 5th hour of work. "
                                   "Consider implementing automated reminders or scheduling systems."
        )
    
    # Check if the meal break was too short
    if meal_duration_minutes < min_duration_minutes:
        return ViolationInstance(
            rule_id="MEAL_BREAK_TOO_SHORT",
            rule_description="Meal break duration insufficient (California Labor Code Section 512)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"Meal break was only {meal_duration_minutes:.0f} minutes "
                           f"({first_meal_start.strftime('%I:%M %p')} to {first_meal_end.strftime('%I:%M %p')}). "
                           f"California law requires at least 30 minutes.",
            suggested_action_generic="Ensure all meal breaks are at least 30 minutes long and uninterrupted. "
                                   "Train managers to protect employee break time."
        )
    
    return None

def _check_second_meal_break_violation(shift: WorkShift, timing_limit_hours: float, min_duration_minutes: int) -> Optional[ViolationInstance]:
    """Check for second meal break violation for shifts over 10 hours"""
    
    # Calculate the latest time the second meal break should have started
    latest_second_meal_start = shift.clock_in_time + timedelta(hours=timing_limit_hours)
    
    # Check if there's a second meal break
    if len(shift.meal_breaks) < 2:
        return ViolationInstance(
            rule_id="MEAL_BREAK_MISSING_SECOND",
            rule_description="Missing required second meal break (California Labor Code Section 512)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"Worked {shift.total_hours_worked:.1f} hours with only "
                           f"{len(shift.meal_breaks)} meal break(s). California law requires a second "
                           f"30-minute meal break for shifts over 10 hours, starting no later than "
                           f"{latest_second_meal_start.strftime('%I:%M %p')}.",
            suggested_action_generic="Provide a second 30-minute meal break for employees working more than "
                                   "10 hours, starting before the end of their 10th hour of work."
        )
    
    # Check timing and duration of second meal break
    second_meal_start, second_meal_end = shift.meal_breaks[1]
    meal_duration_minutes = (second_meal_end - second_meal_start).total_seconds() / 60
    
    if second_meal_start > latest_second_meal_start:
        return ViolationInstance(
            rule_id="MEAL_BREAK_LATE_SECOND",
            rule_description="Second meal break started too late (California Labor Code Section 512)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"Second meal break started at {second_meal_start.strftime('%I:%M %p')}, "
                           f"but should have started by {latest_second_meal_start.strftime('%I:%M %p')}. "
                           f"Worked {shift.total_hours_worked:.1f} hours total.",
            suggested_action_generic="Schedule second meal breaks to start before the end of the 10th hour of work."
        )
    
    if meal_duration_minutes < min_duration_minutes:
        return ViolationInstance(
            rule_id="MEAL_BREAK_TOO_SHORT_SECOND",
            rule_description="Second meal break duration insufficient (California Labor Code Section 512)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"Second meal break was only {meal_duration_minutes:.0f} minutes "
                           f"({second_meal_start.strftime('%I:%M %p')} to {second_meal_end.strftime('%I:%M %p')}). "
                           f"California law requires at least 30 minutes.",
            suggested_action_generic="Ensure all meal breaks are at least 30 minutes long and uninterrupted."
        )
    
    return None

def get_compliance_violations_summary(punch_events: List[LLMParsedPunchEvent]) -> Dict[str, any]:
    """
    Get a summary of all compliance violations
    
    Returns:
        Dictionary with violation counts and details
    """
    meal_break_violations = detect_meal_break_violations(punch_events)
    
    # Count violations by type
    violation_counts = defaultdict(int)
    for violation in meal_break_violations:
        violation_counts[violation.rule_id] += 1
    
    return {
        "meal_break_violations": meal_break_violations,
        "violation_counts": dict(violation_counts),
        "total_violations": len(meal_break_violations),
        "affected_employees": len(set(v.employee_identifier for v in meal_break_violations)),
        "violation_dates": len(set(v.date_of_violation for v in meal_break_violations))
    }

# Test function for development
def test_meal_break_detection():
    """Test function to verify meal break detection logic"""
    
    # Create sample punch events for testing
    test_events = [
        # Employee working 6 hours with no meal break - should be violation
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 1",
            timestamp=datetime(2025, 1, 15, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 1", 
            timestamp=datetime(2025, 1, 15, 14, 0),  # 2:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
        
        # Employee working 8 hours with proper meal break - should be OK
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 2",
            timestamp=datetime(2025, 1, 15, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 2",
            timestamp=datetime(2025, 1, 15, 13, 0),  # 1:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 2",
            timestamp=datetime(2025, 1, 15, 13, 30),  # 1:30 PM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 2",
            timestamp=datetime(2025, 1, 15, 17, 0),  # 5:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
    ]
    
    violations = detect_meal_break_violations(test_events)
    
    print(f"Found {len(violations)} meal break violations:")
    for violation in violations:
        print(f"- {violation.rule_id}: {violation.specific_details}")
    
    return violations

if __name__ == "__main__":
    # Run test when script is executed directly
    test_meal_break_detection() 