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
import re
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict
import json
from difflib import SequenceMatcher

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

def detect_rest_break_violations(punch_events: List[LLMParsedPunchEvent]) -> List[ViolationInstance]:
    """
    Detect rest break violations based on California Labor Law:
    
    California Requirements:
    - Employees must receive a 10-minute paid rest break for every 4 hours worked (or major fraction thereof)
    - "Major fraction" is defined as more than 2 hours (DLSE considers anything more than 2 hours to be major fraction of 4)
    - No rest break required for shifts less than 3.5 hours
    - Rest breaks should be given as close to the middle of each 4-hour work period as practicable
    - Rest breaks must be uninterrupted and duty-free
    - Employer must pay 1 hour premium for each workday rest break is not provided
    
    NOTE: This detection has caveats due to data availability:
    - We can only detect missing rest breaks, not short/interrupted ones
    - We cannot detect if breaks were taken at inappropriate times without detailed punch data
    - Many timekeeping systems don't track rest breaks as they are paid time
    
    Args:
        punch_events: List of parsed punch events from LLM processing
        
    Returns:
        List of ViolationInstance objects representing rest break violations
    """
    violations = []
    
    # Parse punch events into shifts
    shifts_by_employee = parse_shifts_from_punch_events(punch_events)
    
    for employee_id, shifts in shifts_by_employee.items():
        for shift in shifts:
            # Skip shifts with insufficient data or very short shifts
            if shift.total_hours_worked <= 0 or not shift.clock_in_time:
                continue
                
            violations.extend(_check_shift_rest_breaks(shift))
    
    return violations

def _check_shift_rest_breaks(shift: WorkShift) -> List[ViolationInstance]:
    """Check a single shift for rest break violations"""
    violations = []
    
    # California rest break requirements
    MINIMUM_HOURS_FOR_REST_BREAK = 3.5  # No break required under 3.5 hours
    HOURS_PER_REST_BREAK = 4.0  # One 10-minute break per 4 hours
    MAJOR_FRACTION_THRESHOLD = 2.0  # More than 2 hours = major fraction of 4
    
    total_hours = shift.total_hours_worked
    
    # No rest break required for very short shifts
    if total_hours < MINIMUM_HOURS_FOR_REST_BREAK:
        return violations
    
    # Calculate expected number of rest breaks
    expected_breaks = _calculate_expected_rest_breaks(total_hours)
    
    # Check for missing rest breaks
    # NOTE: This is limited by data availability - we can only detect completely missing breaks
    # Most timekeeping systems don't track 10-minute paid rest breaks separately
    missing_break_violation = _check_missing_rest_breaks(shift, expected_breaks)
    if missing_break_violation:
        violations.append(missing_break_violation)
        
    return violations

def _calculate_expected_rest_breaks(total_hours: float) -> int:
    """
    Calculate expected number of rest breaks based on hours worked
    
    California law: 10 minutes for every 4 hours or major fraction thereof
    Major fraction = more than 2 hours
    """
    if total_hours < 3.5:
        return 0
    elif total_hours <= 6.0:  # 3.5 to 6 hours = 1 break
        return 1
    elif total_hours <= 10.0:  # 6+ to 10 hours = 2 breaks  
        return 2
    elif total_hours <= 14.0:  # 10+ to 14 hours = 3 breaks
        return 3
    else:  # 14+ hours = 4 breaks
        return 4

def _check_missing_rest_breaks(shift: WorkShift, expected_breaks: int) -> Optional[ViolationInstance]:
    """
    Check for missing rest breaks
    
    NOTE: This function has significant limitations due to data availability:
    - Most timekeeping systems don't track paid 10-minute rest breaks
    - We cannot distinguish between rest breaks and other short interruptions
    - This detection is conservative and may miss violations
    """
    
    # Count potential rest breaks (gaps between work periods that are too short to be meal breaks)
    potential_rest_breaks = 0
    
    # Look for short gaps that might be rest breaks (5-15 minutes)
    # This is heuristic and not definitive
    if len(shift.punch_events) >= 4:  # Need multiple punch events to detect patterns
        sorted_events = sorted(shift.punch_events, key=lambda x: x.timestamp)
        
        for i in range(len(sorted_events) - 1):
            current_event = sorted_events[i]
            next_event = sorted_events[i + 1]
            
            # Look for OUT followed by IN
            if ("out" in current_event.punch_type_as_parsed.lower() and 
                "in" in next_event.punch_type_as_parsed.lower()):
                
                gap_duration = (next_event.timestamp - current_event.timestamp).total_seconds() / 60
                
                # Count gaps that look like rest breaks (5-19 minutes)
                # Longer gaps are likely meal breaks or role changes
                if 5 <= gap_duration < 20:
                    potential_rest_breaks += 1
    
    # If we found significantly fewer potential breaks than expected, flag as violation
    # Use conservative threshold due to data limitations
    if potential_rest_breaks < max(1, expected_breaks - 1):  # Allow for some uncertainty
        
        roles_worked = _get_roles_from_shift(shift)
        roles_text = f" across roles: {', '.join(roles_worked)}" if len(roles_worked) > 1 else ""
        
        # Create a caveat-heavy violation description
        return ViolationInstance(
            rule_id="REST_BREAK_POTENTIALLY_MISSING",
            rule_description="Potentially missing rest breaks (limited data confidence)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"Worked {shift.total_hours_worked:.1f} hours but only detected {potential_rest_breaks} "
                           f"potential rest break(s){roles_text}. California law requires {expected_breaks} rest break(s) "
                           f"(10 minutes per 4 hours worked). "
                           f"⚠️ CAVEAT: This detection has limited confidence due to data availability. "
                           f"Many timekeeping systems don't track paid rest breaks separately from work time. "
                           f"Manual review recommended.",
            suggested_action_generic="Ensure employees receive 10-minute paid rest breaks for every 4 hours worked "
                                   "across all roles. Review timekeeping practices to better track rest break compliance. "
                                   "⚠️ Note: This flagging may have false positives due to data limitations."
        )
    
    return None

def detect_daily_overtime_violations(punch_events: List[LLMParsedPunchEvent]) -> List[ViolationInstance]:
    """
    Detect daily overtime violations based on California Labor Law:
    
    California Requirements:
    - Time and a half (1.5x) for hours worked over 8 in a day
    - Double time (2x) for hours worked over 12 in a day
    
    Args:
        punch_events: List of parsed punch events from LLM processing
        
    Returns:
        List of ViolationInstance objects representing daily overtime violations
    """
    violations = []
    
    # Parse punch events into shifts
    shifts_by_employee = parse_shifts_from_punch_events(punch_events)
    
    for employee_id, shifts in shifts_by_employee.items():
        for shift in shifts:
            # Skip shifts with insufficient data
            if shift.total_hours_worked <= 0 or not shift.clock_in_time:
                continue
                
            violations.extend(_check_shift_daily_overtime(shift))
    
    return violations

def _check_shift_daily_overtime(shift: WorkShift) -> List[ViolationInstance]:
    """Check a single shift for daily overtime violations"""
    violations = []
    
    # California daily overtime thresholds
    DAILY_OVERTIME_THRESHOLD = 8.0  # hours - time and a half after 8 hours
    DAILY_DOUBLE_TIME_THRESHOLD = 12.0  # hours - double time after 12 hours
    
    total_hours = shift.total_hours_worked
    
    # Check for daily overtime (over 8 hours)
    if total_hours > DAILY_OVERTIME_THRESHOLD:
        overtime_hours = total_hours - DAILY_OVERTIME_THRESHOLD
        
        # Determine if this crosses into double time territory
        double_time_hours = 0.0
        time_and_half_hours = overtime_hours
        
        if total_hours > DAILY_DOUBLE_TIME_THRESHOLD:
            double_time_hours = total_hours - DAILY_DOUBLE_TIME_THRESHOLD
            time_and_half_hours = DAILY_DOUBLE_TIME_THRESHOLD - DAILY_OVERTIME_THRESHOLD  # 4 hours
        
        # Create violation for time and a half
        if time_and_half_hours > 0:
            time_and_half_violation = ViolationInstance(
                rule_id="DAILY_OVERTIME_TIME_AND_HALF",
                rule_description="Daily overtime exceeds 8 hours (California Labor Code Section 510)",
                employee_identifier=shift.employee_identifier,
                date_of_violation=shift.shift_date,
                specific_details=f"Employee: {shift.employee_identifier} | "
                               f"Date: {shift.shift_date} | "
                               f"Total Hours: {total_hours:.2f} | "
                               f"Time-and-a-half Hours: {time_and_half_hours:.2f} | "
                               f"Shift: {shift.clock_in_time.strftime('%I:%M %p') if shift.clock_in_time else 'N/A'} - "
                               f"{shift.clock_out_time.strftime('%I:%M %p') if shift.clock_out_time else 'N/A'}",
                suggested_action_generic="California law requires time-and-a-half pay for hours worked over 8 in a day. "
                                       "Review employee scheduling and consider additional staffing to reduce overtime costs."
            )
            violations.append(time_and_half_violation)
        
        # Create separate violation for double time if applicable
        if double_time_hours > 0:
            double_time_violation = ViolationInstance(
                rule_id="DAILY_OVERTIME_DOUBLE_TIME",
                rule_description="Daily overtime exceeds 12 hours (California Labor Code Section 510)",
                employee_identifier=shift.employee_identifier,
                date_of_violation=shift.shift_date,
                specific_details=f"Employee: {shift.employee_identifier} | "
                               f"Date: {shift.shift_date} | "
                               f"Total Hours: {total_hours:.2f} | "
                               f"Double-time Hours: {double_time_hours:.2f} | "
                               f"Shift: {shift.clock_in_time.strftime('%I:%M %p') if shift.clock_in_time else 'N/A'} - "
                               f"{shift.clock_out_time.strftime('%I:%M %p') if shift.clock_out_time else 'N/A'}",
                suggested_action_generic="California law requires double-time pay for hours worked over 12 in a day. "
                                       "Long shifts increase fatigue and safety risks. Consider mandatory shift limits."
            )
            violations.append(double_time_violation)
    
    return violations

def detect_weekly_overtime_violations(punch_events: List[LLMParsedPunchEvent]) -> List[ViolationInstance]:
    """
    Detect weekly overtime violations based on California Labor Law:
    
    California Requirements:
    - Time and a half (1.5x) for hours worked over 40 in a workweek
    - Workweek is defined as any seven consecutive 24-hour periods
    - For this implementation, we'll use Sunday-Saturday as the workweek
    
    Args:
        punch_events: List of parsed punch events from LLM processing
        
    Returns:
        List of ViolationInstance objects representing weekly overtime violations
    """
    violations = []
    
    # Parse punch events into shifts
    shifts_by_employee = parse_shifts_from_punch_events(punch_events)
    
    for employee_id, shifts in shifts_by_employee.items():
        # Group shifts by workweek (Sunday-Saturday)
        workweeks = _group_shifts_by_workweek(shifts)
        
        for week_start_date, week_shifts in workweeks.items():
            # Check for weekly overtime violations
            weekly_violation = _check_weekly_overtime(employee_id, week_start_date, week_shifts)
            if weekly_violation:
                violations.append(weekly_violation)
    
    return violations

def _group_shifts_by_workweek(shifts: List[WorkShift]) -> Dict[date, List[WorkShift]]:
    """
    Group shifts by workweek (Sunday-Saturday)
    
    Returns:
        Dict mapping week start date (Sunday) to list of shifts in that week
    """
    workweeks = defaultdict(list)
    
    for shift in shifts:
        # Calculate the Sunday of the week this shift belongs to
        days_since_sunday = shift.shift_date.weekday() + 1  # Monday=0, Sunday=6 -> Monday=1, Sunday=0
        if days_since_sunday == 7:  # Sunday
            days_since_sunday = 0
        
        week_start = shift.shift_date - timedelta(days=days_since_sunday)
        workweeks[week_start].append(shift)
    
    return workweeks

def _check_weekly_overtime(employee_id: str, week_start_date: date, week_shifts: List[WorkShift]) -> Optional[ViolationInstance]:
    """Check a single workweek for overtime violations"""
    
    # California weekly overtime threshold
    WEEKLY_OVERTIME_THRESHOLD = 40.0  # hours
    
    # Calculate total hours worked in the week
    total_weekly_hours = sum(shift.total_hours_worked for shift in week_shifts)
    
    # Skip weeks with no significant hours
    if total_weekly_hours <= 0:
        return None
    
    # Check for weekly overtime (over 40 hours)
    if total_weekly_hours > WEEKLY_OVERTIME_THRESHOLD:
        overtime_hours = total_weekly_hours - WEEKLY_OVERTIME_THRESHOLD
        week_end_date = week_start_date + timedelta(days=6)
        
        # Create detailed shift breakdown for the violation
        shift_details = []
        for shift in sorted(week_shifts, key=lambda s: s.shift_date):
            shift_details.append(
                f"{shift.shift_date.strftime('%a %m/%d')}: {shift.total_hours_worked:.2f}h"
            )
        
        shift_breakdown = " | ".join(shift_details)
        
        return ViolationInstance(
            rule_id="WEEKLY_OVERTIME",
            rule_description="Weekly overtime exceeds 40 hours (California Labor Code Section 510)",
            employee_identifier=employee_id,
            date_of_violation=week_end_date,  # Use week end date as violation date
            specific_details=f"Employee: {employee_id} | "
                           f"Week: {week_start_date.strftime('%m/%d/%Y')} - {week_end_date.strftime('%m/%d/%Y')} | "
                           f"Total Hours: {total_weekly_hours:.2f} | "
                           f"Overtime Hours: {overtime_hours:.2f} | "
                           f"Daily Breakdown: {shift_breakdown}",
            suggested_action_generic="California law requires time-and-a-half pay for hours worked over 40 in a workweek. "
                                   "Review employee scheduling to distribute hours more evenly across the workforce."
        )
    
    return None

def detect_duplicate_employees(punch_events: List[LLMParsedPunchEvent]) -> Dict[str, List[str]]:
    """
    Detect potential duplicate employee names from the punch events.
    
    This function looks for employees who might be the same person but listed
    with different identifiers (e.g., different roles, name variations).
    
    Returns:
        Dict mapping normalized employee name to list of original identifiers
        that might represent the same person
    """
    # Get all unique employee identifiers
    employee_identifiers = list(set(event.employee_identifier_in_file for event in punch_events))
    
    # Dictionary to store potential duplicates
    potential_duplicates = defaultdict(list)
    
    # Normalize employee names for comparison
    def normalize_name(name: str) -> str:
        """Normalize employee name for comparison"""
        # Remove common separators and extra info
        name = name.lower().strip()
        
        # Remove common role/department indicators
        role_indicators = [' - cook', ' - server', ' - cashier', ' - manager', ' - host', 
                          ' - kitchen', ' - foh', ' - boh', '(cook)', '(server)', '(cashier)']
        for indicator in role_indicators:
            name = name.replace(indicator, '')
        
        # Remove employee IDs (numbers at the end)
        name = re.sub(r'\s*[/#]\s*\d+\s*$', '', name)  # Remove " / 12345" or "# 12345"
        name = re.sub(r'\s*\d{3,}\s*$', '', name)      # Remove trailing employee numbers
        
        # Standardize name format
        name = re.sub(r'[^\w\s]', ' ', name)  # Replace punctuation with spaces
        name = ' '.join(name.split())         # Normalize whitespace
        
        return name
    
    def names_likely_same_person(name1: str, name2: str) -> bool:
        """Determine if two names likely represent the same person"""
        norm1 = normalize_name(name1)
        norm2 = normalize_name(name2)
        
        # Exact match after normalization
        if norm1 == norm2:
            return True
        
        # Check for initials vs full names (e.g., "J. Smith" vs "John Smith")
        parts1 = norm1.split()
        parts2 = norm2.split()
        
        if len(parts1) == len(parts2) == 2:  # Both have first and last name
            first1, last1 = parts1
            first2, last2 = parts2
            
            # Same last name and first name initial match
            if (last1 == last2 and 
                ((len(first1) == 1 and first1 == first2[0]) or 
                 (len(first2) == 1 and first2 == first1[0]))):
                return True
        
        # High similarity score (for typos, abbreviations)
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        if similarity >= 0.85:  # 85% similarity threshold
            return True
        
        return False
    
    # Group similar names
    processed = set()
    
    for i, emp1 in enumerate(employee_identifiers):
        if emp1 in processed:
            continue
            
        similar_group = [emp1]
        processed.add(emp1)
        
        for j, emp2 in enumerate(employee_identifiers[i+1:], i+1):
            if emp2 in processed:
                continue
                
            if names_likely_same_person(emp1, emp2):
                similar_group.append(emp2)
                processed.add(emp2)
        
        # Only flag if we found potential duplicates
        if len(similar_group) > 1:
            normalized_key = normalize_name(similar_group[0])
            potential_duplicates[normalized_key] = similar_group
    
    return dict(potential_duplicates)

def consolidate_employee_shifts_for_duplicates(
    punch_events: List[LLMParsedPunchEvent], 
    duplicate_groups: Dict[str, List[str]]
) -> Tuple[Dict[str, List[WorkShift]], Dict[str, List[str]]]:
    """
    Consolidate shifts for employees who might be the same person working multiple roles.
    
    Args:
        punch_events: List of parsed punch events
        duplicate_groups: Dict from detect_duplicate_employees
        
    Returns:
        Tuple of (consolidated_shifts_by_employee, employee_mapping)
        where employee_mapping shows which original IDs were consolidated
    """
    # Create mapping from original ID to consolidated ID
    id_mapping = {}
    employee_mapping = {}
    
    # First, map duplicate groups to a single consolidated ID
    for normalized_name, original_ids in duplicate_groups.items():
        # Use the first (or most complete) name as the consolidated ID
        consolidated_id = max(original_ids, key=len)  # Longest name is often most complete
        employee_mapping[consolidated_id] = original_ids
        
        for original_id in original_ids:
            id_mapping[original_id] = consolidated_id
    
    # For non-duplicates, map to themselves
    all_employee_ids = set(event.employee_identifier_in_file for event in punch_events)
    for emp_id in all_employee_ids:
        if emp_id not in id_mapping:
            id_mapping[emp_id] = emp_id
    
    # Create new punch events with consolidated IDs
    consolidated_events = []
    for event in punch_events:
        consolidated_id = id_mapping[event.employee_identifier_in_file]
        
        # Create new event with consolidated ID but preserve original data
        consolidated_event = LLMParsedPunchEvent(
            employee_identifier_in_file=consolidated_id,
            timestamp=event.timestamp,
            punch_type_as_parsed=event.punch_type_as_parsed,
            role_as_parsed=event.role_as_parsed,
            department_as_parsed=event.department_as_parsed,
            location_note_as_parsed=event.location_note_as_parsed,
            notes_as_parsed=event.notes_as_parsed
        )
        consolidated_events.append(consolidated_event)
    
    # Parse consolidated events into shifts
    consolidated_shifts = parse_shifts_from_punch_events(consolidated_events)
    
    return consolidated_shifts, employee_mapping

def detect_compliance_violations_with_duplicate_handling(punch_events: List[LLMParsedPunchEvent]) -> Dict[str, any]:
    """
    Enhanced compliance violation detection that accounts for employees working multiple jobs/roles.
    
    This function:
    1. Detects potential duplicate employee names
    2. Consolidates hours for likely duplicate employees
    3. Runs compliance checks on consolidated data
    4. Reports both violations and duplicate warnings
    """
    # Step 1: Detect potential duplicates
    duplicate_groups = detect_duplicate_employees(punch_events)
    
    # Step 2: Get consolidated shifts (combining hours for potential duplicates)
    consolidated_shifts, employee_mapping = consolidate_employee_shifts_for_duplicates(
        punch_events, duplicate_groups
    )
    
    # Step 3: Run compliance checks on consolidated data
    # Create consolidated punch events for compliance checking
    consolidated_punch_events = []
    for employee_id, shifts in consolidated_shifts.items():
        for shift in shifts:
            consolidated_punch_events.extend(shift.punch_events)
    
    # Run compliance checks with consolidated break detection
    meal_break_violations = detect_consolidated_meal_break_violations(consolidated_shifts)
    rest_break_violations = detect_consolidated_rest_break_violations(consolidated_shifts)
    daily_overtime_violations = detect_daily_overtime_violations(consolidated_punch_events)
    weekly_overtime_violations = detect_weekly_overtime_violations(consolidated_punch_events)
    
    all_violations = meal_break_violations + rest_break_violations + daily_overtime_violations + weekly_overtime_violations
    
    # Count violations by type
    violation_counts = defaultdict(int)
    for violation in all_violations:
        violation_counts[violation.rule_id] += 1
    
    # Step 4: Create duplicate warnings
    duplicate_warnings = []
    for normalized_name, original_ids in duplicate_groups.items():
        warning = (f"Potential duplicate employee detected: {', '.join(original_ids)}. "
                  f"Hours have been consolidated for compliance calculations. "
                  f"Please verify if these represent the same person working multiple roles.")
        duplicate_warnings.append(warning)
    
    return {
        "meal_break_violations": meal_break_violations,
        "rest_break_violations": rest_break_violations,
        "daily_overtime_violations": daily_overtime_violations,
        "weekly_overtime_violations": weekly_overtime_violations,
        "all_violations": all_violations,
        "violation_counts": dict(violation_counts),
        "total_violations": len(all_violations),
        "affected_employees": len(set(v.employee_identifier for v in all_violations)),
        "violation_dates": len(set(v.date_of_violation for v in all_violations)),
        "violation_summary": {
            "meal_breaks": len(meal_break_violations),
            "rest_breaks": len(rest_break_violations),
            "daily_overtime": len(daily_overtime_violations),
            "weekly_overtime": len(weekly_overtime_violations),
        },
        "duplicate_employee_groups": duplicate_groups,
        "employee_consolidation_mapping": employee_mapping,
        "duplicate_warnings": duplicate_warnings,
        "consolidation_applied": len(duplicate_groups) > 0,
        "enhanced_break_detection": True  # Flag to indicate consolidated break detection was used
    }

def get_all_compliance_violations(punch_events: List[LLMParsedPunchEvent]) -> Dict[str, any]:
    """
    Get a comprehensive summary of all compliance violations
    
    Returns:
        Dictionary with all violation types and summary statistics
    """
    meal_break_violations = detect_meal_break_violations(punch_events)
    rest_break_violations = detect_rest_break_violations(punch_events)
    daily_overtime_violations = detect_daily_overtime_violations(punch_events)
    weekly_overtime_violations = detect_weekly_overtime_violations(punch_events)
    
    all_violations = meal_break_violations + rest_break_violations + daily_overtime_violations + weekly_overtime_violations
    
    # Count violations by type
    violation_counts = defaultdict(int)
    for violation in all_violations:
        violation_counts[violation.rule_id] += 1
    
    return {
        "meal_break_violations": meal_break_violations,
        "rest_break_violations": rest_break_violations,
        "daily_overtime_violations": daily_overtime_violations,
        "weekly_overtime_violations": weekly_overtime_violations,
        "all_violations": all_violations,
        "violation_counts": dict(violation_counts),
        "total_violations": len(all_violations),
        "affected_employees": len(set(v.employee_identifier for v in all_violations)),
        "violation_dates": len(set(v.date_of_violation for v in all_violations)),
        "violation_summary": {
            "meal_breaks": len(meal_break_violations),
            "rest_breaks": len(rest_break_violations),
            "daily_overtime": len(daily_overtime_violations),
            "weekly_overtime": len(weekly_overtime_violations),
        }
    }

# Update the existing get_compliance_violations_summary function to include rest breaks
def get_compliance_violations_summary(punch_events: List[LLMParsedPunchEvent]) -> Dict[str, any]:
    """
    Get a summary of all compliance violations (updated to include rest breaks)
    
    Returns:
        Dictionary with violation counts and details
    """
    return get_all_compliance_violations(punch_events)

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

def test_rest_break_detection():
    """Test function to verify rest break detection logic"""
    
    # Create sample punch events for testing rest breaks
    test_events = [
        # Employee working 8 hours with no visible rest breaks - should flag potential violation
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 3",
            timestamp=datetime(2025, 1, 15, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cashier"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 3",
            timestamp=datetime(2025, 1, 15, 12, 0),  # 12:00 PM - Meal break start
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cashier"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 3",
            timestamp=datetime(2025, 1, 15, 12, 30),  # 12:30 PM - Meal break end
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cashier"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 3",
            timestamp=datetime(2025, 1, 15, 16, 0),  # 4:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cashier"
        ),
        
        # Employee working 8 hours with some short breaks - should have fewer violations
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 4",
            timestamp=datetime(2025, 1, 15, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Host"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 4",
            timestamp=datetime(2025, 1, 15, 10, 30),  # 10:30 AM - Short break start
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Host"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 4",
            timestamp=datetime(2025, 1, 15, 10, 40),  # 10:40 AM - Short break end (10 min)
            punch_type_as_parsed="Clock In",
            role_as_parsed="Host"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 4",
            timestamp=datetime(2025, 1, 15, 13, 0),  # 1:00 PM - Meal break start
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Host"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 4",
            timestamp=datetime(2025, 1, 15, 13, 30),  # 1:30 PM - Meal break end
            punch_type_as_parsed="Clock In",
            role_as_parsed="Host"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 4",
            timestamp=datetime(2025, 1, 15, 15, 0),  # 3:00 PM - Another short break
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Host"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 4",
            timestamp=datetime(2025, 1, 15, 15, 10),  # 3:10 PM - Back from break (10 min)
            punch_type_as_parsed="Clock In",
            role_as_parsed="Host"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 4",
            timestamp=datetime(2025, 1, 15, 17, 0),  # 5:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Host"
        ),
    ]
    
    rest_violations = detect_rest_break_violations(test_events)
    
    print(f"\nFound {len(rest_violations)} rest break violations:")
    for violation in rest_violations:
        print(f"- {violation.rule_id}: {violation.specific_details}")
    
    return rest_violations

def test_daily_overtime_detection():
    """Test function to verify daily overtime detection logic"""
    
    # Create sample punch events for testing daily overtime
    test_events = [
        # Employee working exactly 8 hours - no overtime
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 5",
            timestamp=datetime(2025, 1, 15, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Manager"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 5",
            timestamp=datetime(2025, 1, 15, 17, 0),  # 5:00 PM (8 hours)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Manager"
        ),
        
        # Employee working 10 hours - time and a half overtime
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 6",
            timestamp=datetime(2025, 1, 15, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 6",
            timestamp=datetime(2025, 1, 15, 12, 0),  # 12:00 PM - Meal break start
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 6",
            timestamp=datetime(2025, 1, 15, 12, 30),  # 12:30 PM - Meal break end
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 6",
            timestamp=datetime(2025, 1, 15, 18, 30),  # 6:30 PM (10 hours worked)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
        
        # Employee working 13 hours - time and a half + double time
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 7",
            timestamp=datetime(2025, 1, 15, 7, 0),  # 7:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 7",
            timestamp=datetime(2025, 1, 15, 11, 30),  # 11:30 AM - Meal break start
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 7",
            timestamp=datetime(2025, 1, 15, 12, 0),  # 12:00 PM - Meal break end
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 7",
            timestamp=datetime(2025, 1, 15, 20, 30),  # 8:30 PM (13 hours worked)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
    ]
    
    overtime_violations = detect_daily_overtime_violations(test_events)
    
    print(f"\nFound {len(overtime_violations)} daily overtime violations:")
    for violation in overtime_violations:
        print(f"- {violation.rule_id}: {violation.specific_details}")
    
    return overtime_violations

def test_weekly_overtime_detection():
    """Test function to verify weekly overtime detection logic"""
    
    # Create sample punch events for testing weekly overtime
    # Week 1: Sunday 1/12 - Saturday 1/18, 2025
    test_events = [
        # Employee working 45 hours in a week - should trigger weekly overtime
        
        # Monday 1/13/2025 - 8 hours
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 8",
            timestamp=datetime(2025, 1, 13, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 8",
            timestamp=datetime(2025, 1, 13, 17, 0),  # 5:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
        
        # Tuesday 1/14/2025 - 8 hours
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 8",
            timestamp=datetime(2025, 1, 14, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 8",
            timestamp=datetime(2025, 1, 14, 17, 0),  # 5:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
        
        # Wednesday 1/15/2025 - 8 hours
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 8",
            timestamp=datetime(2025, 1, 15, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 8",
            timestamp=datetime(2025, 1, 15, 17, 0),  # 5:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
        
        # Thursday 1/16/2025 - 8 hours
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 8",
            timestamp=datetime(2025, 1, 16, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 8",
            timestamp=datetime(2025, 1, 16, 17, 0),  # 5:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
        
        # Friday 1/17/2025 - 8 hours
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 8",
            timestamp=datetime(2025, 1, 17, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 8",
            timestamp=datetime(2025, 1, 17, 17, 0),  # 5:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
        
        # Saturday 1/18/2025 - 5 hours (total = 45 hours)
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 8",
            timestamp=datetime(2025, 1, 18, 10, 0),  # 10:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 8",
            timestamp=datetime(2025, 1, 18, 15, 0),  # 3:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
        
        # Employee working exactly 40 hours - no weekly overtime
        
        # Monday 1/13/2025 - 8 hours
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 9",
            timestamp=datetime(2025, 1, 13, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 9",
            timestamp=datetime(2025, 1, 13, 16, 0),  # 4:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
        
        # Tuesday 1/14/2025 - 8 hours
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 9",
            timestamp=datetime(2025, 1, 14, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 9",
            timestamp=datetime(2025, 1, 14, 16, 0),  # 4:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
        
        # Wednesday 1/15/2025 - 8 hours
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 9",
            timestamp=datetime(2025, 1, 15, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 9",
            timestamp=datetime(2025, 1, 15, 16, 0),  # 4:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
        
        # Thursday 1/16/2025 - 8 hours
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 9",
            timestamp=datetime(2025, 1, 16, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 9",
            timestamp=datetime(2025, 1, 16, 16, 0),  # 4:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
        
        # Friday 1/17/2025 - 8 hours (total = 40 hours exactly)
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 9",
            timestamp=datetime(2025, 1, 17, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 9",
            timestamp=datetime(2025, 1, 17, 16, 0),  # 4:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
    ]
    
    weekly_violations = detect_weekly_overtime_violations(test_events)
    
    print(f"\nFound {len(weekly_violations)} weekly overtime violations:")
    for violation in weekly_violations:
        print(f"- {violation.rule_id}: {violation.specific_details}")
    
    return weekly_violations

def test_multiple_jobs_duplicate_detection():
    """Test function to verify duplicate employee detection and consolidation logic"""
    
    # Create sample punch events for testing multiple jobs/duplicate detection
    test_events = [
        # Same employee working as both Cook and Server (should be consolidated)
        
        # Monday as Cook
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Cook",
            timestamp=datetime(2025, 1, 13, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Cook",
            timestamp=datetime(2025, 1, 13, 16, 0),  # 4:00 PM (8 hours)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
        
        # Tuesday as Server (same person, different role)
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Server",
            timestamp=datetime(2025, 1, 14, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Server",
            timestamp=datetime(2025, 1, 14, 18, 0),  # 6:00 PM (9 hours)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
        
        # Wednesday as Cook again
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Cook",
            timestamp=datetime(2025, 1, 15, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Cook",
            timestamp=datetime(2025, 1, 15, 17, 0),  # 5:00 PM (9 hours)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
        
        # Thursday as Server
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Server",
            timestamp=datetime(2025, 1, 16, 10, 0),  # 10:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Server",
            timestamp=datetime(2025, 1, 16, 19, 0),  # 7:00 PM (9 hours)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
        
        # Friday as Cook
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Cook",
            timestamp=datetime(2025, 1, 17, 7, 0),  # 7:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Cook",
            timestamp=datetime(2025, 1, 17, 16, 0),  # 4:00 PM (9 hours)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
        # Total for John Smith: 8+9+9+9+9 = 44 hours (should trigger weekly OT)
        
        # Another employee with name variations (should be detected as duplicate)
        LLMParsedPunchEvent(
            employee_identifier_in_file="Jane Doe / 12345",
            timestamp=datetime(2025, 1, 13, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Manager"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Jane Doe / 12345",
            timestamp=datetime(2025, 1, 13, 17, 0),  # 5:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Manager"
        ),
        
        LLMParsedPunchEvent(
            employee_identifier_in_file="J. Doe",
            timestamp=datetime(2025, 1, 14, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Assistant Manager"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="J. Doe",
            timestamp=datetime(2025, 1, 14, 16, 0),  # 4:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Assistant Manager"
        ),
        
        # Regular employee (no duplicates)
        LLMParsedPunchEvent(
            employee_identifier_in_file="Mike Johnson",
            timestamp=datetime(2025, 1, 13, 10, 0),  # 10:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Host"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Mike Johnson",
            timestamp=datetime(2025, 1, 13, 18, 0),  # 6:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Host"
        ),
    ]
    
    print(f"\n=== MULTIPLE JOBS / DUPLICATE DETECTION TEST ===")
    
    # Test duplicate detection
    duplicate_groups = detect_duplicate_employees(test_events)
    print(f"Detected {len(duplicate_groups)} potential duplicate groups:")
    for normalized_name, original_ids in duplicate_groups.items():
        print(f"- '{normalized_name}': {original_ids}")
    
    # Test enhanced compliance detection with duplicate handling
    enhanced_results = detect_compliance_violations_with_duplicate_handling(test_events)
    
    print(f"\nEnhanced compliance results:")
    print(f"Consolidation applied: {enhanced_results['consolidation_applied']}")
    print(f"Enhanced break detection: {enhanced_results['enhanced_break_detection']}")
    print(f"Total violations: {enhanced_results['total_violations']}")
    print(f"Weekly overtime violations: {enhanced_results['violation_summary']['weekly_overtime']}")
    print(f"Daily overtime violations: {enhanced_results['violation_summary']['daily_overtime']}")
    print(f"Meal break violations: {enhanced_results['violation_summary']['meal_breaks']}")
    print(f"Rest break violations: {enhanced_results['violation_summary']['rest_breaks']}")
    
    print(f"\nDuplicate warnings ({len(enhanced_results['duplicate_warnings'])}):")
    for warning in enhanced_results['duplicate_warnings']:
        print(f"- {warning}")
    
    print(f"\nEmployee consolidation mapping:")
    for consolidated_id, original_ids in enhanced_results['employee_consolidation_mapping'].items():
        print(f"- '{consolidated_id}' consolidates: {original_ids}")
    
    # Compare with non-consolidated results
    print(f"\n--- Comparison: Standard vs Enhanced Detection ---")
    standard_results = get_all_compliance_violations(test_events)
    
    print(f"Standard detection:")
    print(f"  Weekly overtime violations: {standard_results['violation_summary']['weekly_overtime']}")
    print(f"  Daily overtime violations: {standard_results['violation_summary']['daily_overtime']}")
    print(f"  Meal break violations: {standard_results['violation_summary']['meal_breaks']}")
    print(f"  Rest break violations: {standard_results['violation_summary']['rest_breaks']}")
    print(f"  Total violations: {standard_results['total_violations']}")
    
    print(f"Enhanced detection (with consolidation):")
    print(f"  Weekly overtime violations: {enhanced_results['violation_summary']['weekly_overtime']}")
    print(f"  Daily overtime violations: {enhanced_results['violation_summary']['daily_overtime']}")
    print(f"  Meal break violations: {enhanced_results['violation_summary']['meal_breaks']}")
    print(f"  Rest break violations: {enhanced_results['violation_summary']['rest_breaks']}")
    print(f"  Total violations: {enhanced_results['total_violations']}")
    
    return enhanced_results

def test_consolidated_break_detection():
    """Test function specifically for consolidated break detection across multiple roles"""
    
    print(f"\n=== CONSOLIDATED BREAK DETECTION TEST ===")
    
    # Create test scenario: Employee working two roles in same day with inadequate breaks
    test_events = [
        # Sarah working as Cook from 8am-12pm (4 hours)
        LLMParsedPunchEvent(
            employee_identifier_in_file="Sarah Wilson - Cook",
            timestamp=datetime(2025, 1, 15, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Sarah Wilson - Cook",
            timestamp=datetime(2025, 1, 15, 12, 0),  # 12:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook"
        ),
        
        # Sarah working as Server from 12:15pm-6pm (5.75 hours) - only 15 minute break!
        LLMParsedPunchEvent(
            employee_identifier_in_file="Sarah Wilson - Server",
            timestamp=datetime(2025, 1, 15, 12, 15),  # 12:15 PM (15-minute break)
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Sarah Wilson - Server",
            timestamp=datetime(2025, 1, 15, 18, 0),  # 6:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
        # Total: 9.75 hours with only 15-minute break - should violate meal break rules
        
        # Another employee: Tom working split shift with proper breaks
        LLMParsedPunchEvent(
            employee_identifier_in_file="Tom Brown - Host",
            timestamp=datetime(2025, 1, 15, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Host"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Tom Brown - Host",
            timestamp=datetime(2025, 1, 15, 13, 0),  # 1:00 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Host"
        ),
        
        # Tom's meal break: 1pm-1:30pm
        LLMParsedPunchEvent(
            employee_identifier_in_file="Tom Brown - Cashier",
            timestamp=datetime(2025, 1, 15, 13, 30),  # 1:30 PM (30-minute break)
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cashier"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Tom Brown - Cashier",
            timestamp=datetime(2025, 1, 15, 18, 30),  # 6:30 PM
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cashier"
        ),
        # Total: 9 hours with proper 30-minute meal break - should be compliant
    ]
    
    # Test enhanced detection
    enhanced_results = detect_compliance_violations_with_duplicate_handling(test_events)
    
    print(f"Enhanced break detection results:")
    print(f"Total violations: {enhanced_results['total_violations']}")
    print(f"Meal break violations: {enhanced_results['violation_summary']['meal_breaks']}")
    
    print(f"\nDetailed meal break violations:")
    for violation in enhanced_results['meal_break_violations']:
        print(f"- {violation.rule_id}: {violation.employee_identifier}")
        print(f"  Details: {violation.specific_details}")
        print()
    
    # Test standard detection for comparison
    standard_results = get_all_compliance_violations(test_events)
    
    print(f"--- Comparison ---")
    print(f"Standard detection meal break violations: {standard_results['violation_summary']['meal_breaks']}")
    print(f"Enhanced detection meal break violations: {enhanced_results['violation_summary']['meal_breaks']}")
    
    print(f"\nKey difference: Enhanced detection consolidates hours across roles")
    print(f"to properly calculate break requirements based on total daily work time.")
    
    return enhanced_results

def test_all_compliance_detection():
    """Test function to verify all compliance detection logic"""
    
    # Combine test events for comprehensive testing
    all_test_events = [
        # Long shift with minimal breaks - multiple violations expected
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 5",
            timestamp=datetime(2025, 1, 15, 7, 0),  # 7:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Manager"
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Test Employee 5",
            timestamp=datetime(2025, 1, 15, 19, 0),  # 7:00 PM - 12 hour shift, no breaks
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Manager"
        ),
    ]
    
    print("\n=== COMPREHENSIVE COMPLIANCE TEST ===")
    
    # Get all violations
    summary = get_all_compliance_violations(all_test_events)
    
    print(f"Total violations found: {summary['total_violations']}")
    print(f"Affected employees: {summary['affected_employees']}")
    print(f"Meal break violations: {summary['violation_summary']['meal_breaks']}")
    print(f"Rest break violations: {summary['violation_summary']['rest_breaks']}")
    print(f"Daily overtime violations: {summary['violation_summary']['daily_overtime']}")
    
    print("\nViolation breakdown:")
    for rule_id, count in summary['violation_counts'].items():
        print(f"- {rule_id}: {count}")
    
    return summary

def detect_consolidated_meal_break_violations(consolidated_shifts: Dict[str, List[WorkShift]]) -> List[ViolationInstance]:
    """
    Detect meal break violations considering consolidated shifts for employees working multiple roles.
    
    This function analyzes an employee's entire workday across all roles to determine
    if proper meal breaks were taken based on total hours worked.
    
    Args:
        consolidated_shifts: Dict mapping employee_identifier to list of WorkShift objects
        
    Returns:
        List of ViolationInstance objects representing meal break violations
    """
    violations = []
    
    for employee_id, shifts in consolidated_shifts.items():
        # Group shifts by date
        shifts_by_date = defaultdict(list)
        for shift in shifts:
            shifts_by_date[shift.shift_date].append(shift)
        
        # Check each day's consolidated work
        for shift_date, daily_shifts in shifts_by_date.items():
            if not daily_shifts:
                continue
                
            # Create a consolidated daily shift
            consolidated_daily_shift = _create_consolidated_daily_shift(employee_id, shift_date, daily_shifts)
            
            # Check for meal break violations on the consolidated shift
            violations.extend(_check_consolidated_shift_meal_breaks(consolidated_daily_shift))
    
    return violations

def _create_consolidated_daily_shift(employee_id: str, shift_date: date, daily_shifts: List[WorkShift]) -> WorkShift:
    """
    Create a single consolidated shift from multiple shifts on the same day.
    
    This combines all punch events from different roles into a single timeline
    to properly analyze breaks and work periods.
    """
    consolidated_shift = WorkShift(employee_id, shift_date)
    
    # Combine all punch events from all shifts on this date
    all_punch_events = []
    for shift in daily_shifts:
        all_punch_events.extend(shift.punch_events)
    
    # Sort by timestamp to create proper timeline
    all_punch_events.sort(key=lambda x: x.timestamp)
    
    # Add all events to consolidated shift
    for event in all_punch_events:
        consolidated_shift.add_punch_event(event)
    
    # Analyze the consolidated shift
    consolidated_shift.analyze_shift()
    
    return consolidated_shift

def _check_consolidated_shift_meal_breaks(shift: WorkShift) -> List[ViolationInstance]:
    """
    Check meal breaks for a consolidated shift (across multiple roles/jobs).
    
    This is similar to _check_shift_meal_breaks but considers that gaps between
    different role shifts might represent meal breaks.
    """
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
        first_meal_violation = _check_consolidated_first_meal_break_violation(shift, MEAL_BREAK_TIMING_LIMIT, MINIMUM_MEAL_BREAK_DURATION)
        if first_meal_violation:
            violations.append(first_meal_violation)
    
    # Check for second meal break violation (> 10 hours worked)
    if total_hours > SECOND_MEAL_BREAK_THRESHOLD:
        second_meal_violation = _check_consolidated_second_meal_break_violation(shift, SECOND_MEAL_BREAK_TIMING_LIMIT, MINIMUM_MEAL_BREAK_DURATION)
        if second_meal_violation:
            violations.append(second_meal_violation)
            
    return violations

def _check_consolidated_first_meal_break_violation(shift: WorkShift, timing_limit_hours: float, min_duration_minutes: int) -> Optional[ViolationInstance]:
    """Check for first meal break violation in consolidated shift"""
    
    # Calculate the latest time the meal break should have started
    latest_meal_start = shift.clock_in_time + timedelta(hours=timing_limit_hours)
    
    # Check if there are any meal breaks
    if not shift.meal_breaks:
        # No meal breaks found - violation
        roles_worked = _get_roles_from_shift(shift)
        roles_text = f" across roles: {', '.join(roles_worked)}" if len(roles_worked) > 1 else ""
        
        return ViolationInstance(
            rule_id="MEAL_BREAK_MISSING_FIRST_CONSOLIDATED",
            rule_description="Missing required first meal break across multiple roles (California Labor Code Section 512)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"Worked {shift.total_hours_worked:.1f} hours with no meal breaks detected{roles_text}. "
                           f"California law requires a 30-minute meal break for shifts over 5 hours, "
                           f"starting no later than {latest_meal_start.strftime('%I:%M %p')}.",
            suggested_action_generic="Ensure employees working more than 5 hours across multiple roles receive an uninterrupted "
                                   "30-minute meal break that starts before the end of their 5th hour of work."
        )
    
    # Check if the first meal break started too late
    first_meal_start, first_meal_end = shift.meal_breaks[0]
    meal_duration_minutes = (first_meal_end - first_meal_start).total_seconds() / 60
    
    if first_meal_start > latest_meal_start:
        roles_worked = _get_roles_from_shift(shift)
        roles_text = f" across roles: {', '.join(roles_worked)}" if len(roles_worked) > 1 else ""
        
        return ViolationInstance(
            rule_id="MEAL_BREAK_LATE_FIRST_CONSOLIDATED",
            rule_description="First meal break started too late across multiple roles (California Labor Code Section 512)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"First meal break started at {first_meal_start.strftime('%I:%M %p')}, "
                           f"but should have started by {latest_meal_start.strftime('%I:%M %p')}. "
                           f"Worked {shift.total_hours_worked:.1f} hours total{roles_text}.",
            suggested_action_generic="Schedule meal breaks to start before the end of the 5th hour of work, "
                                   "even when employees work multiple roles."
        )
    
    # Check if the meal break was too short
    if meal_duration_minutes < min_duration_minutes:
        return ViolationInstance(
            rule_id="MEAL_BREAK_TOO_SHORT_CONSOLIDATED",
            rule_description="Meal break duration insufficient across multiple roles (California Labor Code Section 512)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"Meal break was only {meal_duration_minutes:.0f} minutes "
                           f"({first_meal_start.strftime('%I:%M %p')} to {first_meal_end.strftime('%I:%M %p')}). "
                           f"California law requires at least 30 minutes.",
            suggested_action_generic="Ensure all meal breaks are at least 30 minutes long and uninterrupted, "
                                   "regardless of role changes."
        )
    
    return None

def _check_consolidated_second_meal_break_violation(shift: WorkShift, timing_limit_hours: float, min_duration_minutes: int) -> Optional[ViolationInstance]:
    """Check for second meal break violation in consolidated shift"""
    
    # Calculate the latest time the second meal break should have started
    latest_second_meal_start = shift.clock_in_time + timedelta(hours=timing_limit_hours)
    
    # Check if there's a second meal break
    if len(shift.meal_breaks) < 2:
        roles_worked = _get_roles_from_shift(shift)
        roles_text = f" across roles: {', '.join(roles_worked)}" if len(roles_worked) > 1 else ""
        
        return ViolationInstance(
            rule_id="MEAL_BREAK_MISSING_SECOND_CONSOLIDATED",
            rule_description="Missing required second meal break across multiple roles (California Labor Code Section 512)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"Worked {shift.total_hours_worked:.1f} hours with only "
                           f"{len(shift.meal_breaks)} meal break(s){roles_text}. California law requires a second "
                           f"30-minute meal break for shifts over 10 hours, starting no later than "
                           f"{latest_second_meal_start.strftime('%I:%M %p')}.",
            suggested_action_generic="Provide a second 30-minute meal break for employees working more than "
                                   "10 hours across multiple roles, starting before the end of their 10th hour of work."
        )
    
    # Check timing and duration of second meal break
    second_meal_start, second_meal_end = shift.meal_breaks[1]
    meal_duration_minutes = (second_meal_end - second_meal_start).total_seconds() / 60
    
    if second_meal_start > latest_second_meal_start:
        roles_worked = _get_roles_from_shift(shift)
        roles_text = f" across roles: {', '.join(roles_worked)}" if len(roles_worked) > 1 else ""
        
        return ViolationInstance(
            rule_id="MEAL_BREAK_LATE_SECOND_CONSOLIDATED",
            rule_description="Second meal break started too late across multiple roles (California Labor Code Section 512)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"Second meal break started at {second_meal_start.strftime('%I:%M %p')}, "
                           f"but should have started by {latest_second_meal_start.strftime('%I:%M %p')}. "
                           f"Worked {shift.total_hours_worked:.1f} hours total{roles_text}.",
            suggested_action_generic="Schedule second meal breaks to start before the end of the 10th hour of work "
                                   "across all roles."
        )
    
    if meal_duration_minutes < min_duration_minutes:
        return ViolationInstance(
            rule_id="MEAL_BREAK_TOO_SHORT_SECOND_CONSOLIDATED",
            rule_description="Second meal break duration insufficient across multiple roles (California Labor Code Section 512)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"Second meal break was only {meal_duration_minutes:.0f} minutes "
                           f"({second_meal_start.strftime('%I:%M %p')} to {second_meal_end.strftime('%I:%M %p')}). "
                           f"California law requires at least 30 minutes.",
            suggested_action_generic="Ensure all meal breaks are at least 30 minutes long and uninterrupted."
        )
    
    return None

def _get_roles_from_shift(shift: WorkShift) -> List[str]:
    """Extract unique roles from a shift's punch events"""
    roles = set()
    for event in shift.punch_events:
        if event.role_as_parsed:
            roles.add(event.role_as_parsed)
    return list(roles)

def detect_consolidated_rest_break_violations(consolidated_shifts: Dict[str, List[WorkShift]]) -> List[ViolationInstance]:
    """
    Detect rest break violations considering consolidated shifts for employees working multiple roles.
    
    Args:
        consolidated_shifts: Dict mapping employee_identifier to list of WorkShift objects
        
    Returns:
        List of ViolationInstance objects representing rest break violations
    """
    violations = []
    
    for employee_id, shifts in consolidated_shifts.items():
        # Group shifts by date
        shifts_by_date = defaultdict(list)
        for shift in shifts:
            shifts_by_date[shift.shift_date].append(shift)
        
        # Check each day's consolidated work
        for shift_date, daily_shifts in shifts_by_date.items():
            if not daily_shifts:
                continue
                
            # Create a consolidated daily shift
            consolidated_daily_shift = _create_consolidated_daily_shift(employee_id, shift_date, daily_shifts)
            
            # Check for rest break violations on the consolidated shift
            violations.extend(_check_consolidated_shift_rest_breaks(consolidated_daily_shift))
    
    return violations

def _check_consolidated_shift_rest_breaks(shift: WorkShift) -> List[ViolationInstance]:
    """Check rest breaks for a consolidated shift (across multiple roles/jobs)"""
    violations = []
    
    # California rest break requirements
    MINIMUM_HOURS_FOR_REST_BREAK = 3.5  # No break required under 3.5 hours
    
    total_hours = shift.total_hours_worked
    
    # No rest break required for very short shifts
    if total_hours < MINIMUM_HOURS_FOR_REST_BREAK:
        return violations
    
    # Calculate expected number of rest breaks
    expected_breaks = _calculate_expected_rest_breaks(total_hours)
    
    # Check for missing rest breaks with enhanced detection for multiple roles
    missing_break_violation = _check_consolidated_missing_rest_breaks(shift, expected_breaks)
    if missing_break_violation:
        violations.append(missing_break_violation)
        
    return violations

def _check_consolidated_missing_rest_breaks(shift: WorkShift, expected_breaks: int) -> Optional[ViolationInstance]:
    """Check for missing rest breaks in consolidated shift"""
    
    # Count potential rest breaks (gaps between work periods that are too short to be meal breaks)
    potential_rest_breaks = 0
    
    # Look for short gaps that might be rest breaks (5-15 minutes)
    # This is heuristic and not definitive
    if len(shift.punch_events) >= 4:  # Need multiple punch events to detect patterns
        sorted_events = sorted(shift.punch_events, key=lambda x: x.timestamp)
        
        for i in range(len(sorted_events) - 1):
            current_event = sorted_events[i]
            next_event = sorted_events[i + 1]
            
            # Look for OUT followed by IN
            if ("out" in current_event.punch_type_as_parsed.lower() and 
                "in" in next_event.punch_type_as_parsed.lower()):
                
                gap_minutes = (next_event.timestamp - current_event.timestamp).total_seconds() / 60
                
                # Count gaps that might be rest breaks (5-15 minutes)
                # Exclude longer gaps that are likely meal breaks
                if 5 <= gap_minutes <= 15:
                    potential_rest_breaks += 1
    
    # If we found significantly fewer potential breaks than expected, flag as violation
    # Use conservative threshold due to data limitations
    if potential_rest_breaks < max(1, expected_breaks - 1):  # Allow for some uncertainty
        
        roles_worked = _get_roles_from_shift(shift)
        roles_text = f" across roles: {', '.join(roles_worked)}" if len(roles_worked) > 1 else ""
        
        # Create a caveat-heavy violation description
        return ViolationInstance(
            rule_id="REST_BREAK_POTENTIALLY_MISSING_CONSOLIDATED",
            rule_description="Potentially missing rest breaks across multiple roles (limited data confidence)",
            employee_identifier=shift.employee_identifier,
            date_of_violation=shift.shift_date,
            specific_details=f"Worked {shift.total_hours_worked:.1f} hours but only detected {potential_rest_breaks} "
                           f"potential rest break(s){roles_text}. California law requires {expected_breaks} rest break(s) "
                           f"(10 minutes per 4 hours worked). "
                           f"⚠️ CAVEAT: This detection has limited confidence due to data availability. "
                           f"Many timekeeping systems don't track paid rest breaks separately from work time. "
                           f"Manual review recommended.",
            suggested_action_generic="Ensure employees receive 10-minute paid rest breaks for every 4 hours worked "
                                   "across all roles. Review timekeeping practices to better track rest break compliance. "
                                   "⚠️ Note: This flagging may have false positives due to data limitations."
        )
    
    return None

# ===== WAGE DETERMINATION FUNCTIONS =====

def extract_wage_data_from_punch_events(punch_events: List[LLMParsedPunchEvent]) -> Dict[str, float]:
    """
    Extract hourly wage data from punch events.
    
    Returns a dictionary mapping employee_identifier to their hourly wage.
    Only includes employees where wage data was successfully parsed.
    
    Args:
        punch_events: List of parsed punch events from LLM processing
        
    Returns:
        Dict mapping employee_identifier to hourly wage (float)
    """
    wage_data = {}
    
    for event in punch_events:
        if event.hourly_wage_as_parsed is not None and event.hourly_wage_as_parsed > 0:
            employee_id = event.employee_identifier_in_file
            # Use the wage from any event for this employee
            # (wages should be consistent across events for the same employee)
            wage_data[employee_id] = event.hourly_wage_as_parsed
    
    return wage_data

def determine_employee_hourly_wages(
    punch_events: List[LLMParsedPunchEvent], 
    default_wage: float = 18.00
) -> Tuple[Dict[str, float], Dict[str, str]]:
    """
    Determine hourly wages for all employees, using parsed data when available
    and falling back to default wage when not available.
    
    Args:
        punch_events: List of parsed punch events from LLM processing
        default_wage: Default hourly wage to use when wage data is not available
        
    Returns:
        Tuple of (employee_wages, wage_sources)
        - employee_wages: Dict mapping employee_identifier to hourly wage
        - wage_sources: Dict mapping employee_identifier to source description
    """
    # Extract wage data from punch events
    parsed_wages = extract_wage_data_from_punch_events(punch_events)
    
    # Get all unique employees
    all_employees = set(event.employee_identifier_in_file for event in punch_events)
    
    employee_wages = {}
    wage_sources = {}
    
    for employee_id in all_employees:
        if employee_id in parsed_wages:
            # Use parsed wage data
            employee_wages[employee_id] = parsed_wages[employee_id]
            wage_sources[employee_id] = f"Parsed from timesheet: ${parsed_wages[employee_id]:.2f}/hr"
        else:
            # Fall back to default wage
            employee_wages[employee_id] = default_wage
            wage_sources[employee_id] = f"Default assumption: ${default_wage:.2f}/hr (no wage data in timesheet)"
    
    return employee_wages, wage_sources

def calculate_violation_costs(
    violations: List[ViolationInstance],
    employee_wages: Dict[str, float],
    overtime_multiplier: float = 1.5,
    double_time_multiplier: float = 2.0
) -> Dict[str, any]:
    """
    Calculate the estimated costs associated with labor compliance violations.
    
    Args:
        violations: List of ViolationInstance objects
        employee_wages: Dict mapping employee_identifier to hourly wage
        overtime_multiplier: Multiplier for overtime pay (default 1.5x)
        double_time_multiplier: Multiplier for double time pay (default 2.0x)
        
    Returns:
        Dict containing cost breakdown and totals
    """
    cost_breakdown = {
        "meal_break_penalty_cost": 0.0,
        "rest_break_penalty_cost": 0.0,
        "overtime_cost": 0.0,
        "double_time_cost": 0.0,
        "total_penalty_cost": 0.0,
        "total_overtime_cost": 0.0,
        "total_estimated_cost": 0.0,
        "violation_details": []
    }
    
    for violation in violations:
        employee_id = violation.employee_identifier
        base_wage = employee_wages.get(employee_id, 18.00)  # Default fallback
        
        violation_cost = 0.0
        cost_description = ""
        
        if violation.rule_id.startswith("MEAL_BREAK"):
            # California meal break penalty: 1 hour of pay per violation
            violation_cost = base_wage
            cost_breakdown["meal_break_penalty_cost"] += violation_cost
            cost_description = f"Meal break penalty: 1 hour at ${base_wage:.2f}/hr = ${violation_cost:.2f}"
            
        elif violation.rule_id.startswith("REST_BREAK"):
            # California rest break penalty: 1 hour of pay per violation
            violation_cost = base_wage
            cost_breakdown["rest_break_penalty_cost"] += violation_cost
            cost_description = f"Rest break penalty: 1 hour at ${base_wage:.2f}/hr = ${violation_cost:.2f}"
            
        elif violation.rule_id == "DAILY_OVERTIME_TIME_AND_HALF":
            # Extract overtime hours from violation details
            overtime_hours = _extract_overtime_hours_from_violation(violation, "time-and-a-half")
            if overtime_hours > 0:
                overtime_premium = base_wage * (overtime_multiplier - 1.0)  # Additional 0.5x
                violation_cost = overtime_hours * overtime_premium
                cost_breakdown["overtime_cost"] += violation_cost
                cost_description = f"Overtime premium: {overtime_hours:.2f} hrs × ${overtime_premium:.2f}/hr = ${violation_cost:.2f}"
            
        elif violation.rule_id == "DAILY_OVERTIME_DOUBLE_TIME":
            # Extract double time hours from violation details
            double_time_hours = _extract_overtime_hours_from_violation(violation, "double-time")
            if double_time_hours > 0:
                double_time_premium = base_wage * (double_time_multiplier - 1.0)  # Additional 1.0x
                violation_cost = double_time_hours * double_time_premium
                cost_breakdown["double_time_cost"] += violation_cost
                cost_description = f"Double time premium: {double_time_hours:.2f} hrs × ${double_time_premium:.2f}/hr = ${violation_cost:.2f}"
            
        elif violation.rule_id == "WEEKLY_OVERTIME":
            # Extract weekly overtime hours from violation details
            weekly_overtime_hours = _extract_overtime_hours_from_violation(violation, "overtime")
            if weekly_overtime_hours > 0:
                overtime_premium = base_wage * (overtime_multiplier - 1.0)  # Additional 0.5x
                violation_cost = weekly_overtime_hours * overtime_premium
                cost_breakdown["overtime_cost"] += violation_cost
                cost_description = f"Weekly overtime premium: {weekly_overtime_hours:.2f} hrs × ${overtime_premium:.2f}/hr = ${violation_cost:.2f}"
        
        # Record violation cost details
        if violation_cost > 0:
            cost_breakdown["violation_details"].append({
                "rule_id": violation.rule_id,
                "employee_identifier": employee_id,
                "date_of_violation": violation.date_of_violation,
                "estimated_cost": violation_cost,
                "cost_description": cost_description
            })
    
    # Calculate totals
    cost_breakdown["total_penalty_cost"] = (
        cost_breakdown["meal_break_penalty_cost"] + 
        cost_breakdown["rest_break_penalty_cost"]
    )
    cost_breakdown["total_overtime_cost"] = (
        cost_breakdown["overtime_cost"] + 
        cost_breakdown["double_time_cost"]
    )
    cost_breakdown["total_estimated_cost"] = (
        cost_breakdown["total_penalty_cost"] + 
        cost_breakdown["total_overtime_cost"]
    )
    
    return cost_breakdown

def _extract_overtime_hours_from_violation(violation: ViolationInstance, overtime_type: str) -> float:
    """
    Extract overtime hours from violation specific_details.
    
    This is a helper function to parse hours from violation descriptions.
    """
    details = violation.specific_details
    
    try:
        if overtime_type == "time-and-a-half":
            # Look for pattern like "Time-and-a-half Hours: 2.00"
            match = re.search(r"Time-and-a-half Hours:\s*(\d+\.?\d*)", details)
            if match:
                return float(match.group(1))
        
        elif overtime_type == "double-time":
            # Look for pattern like "Double-time Hours: 1.00"
            match = re.search(r"Double-time Hours:\s*(\d+\.?\d*)", details)
            if match:
                return float(match.group(1))
        
        elif overtime_type == "overtime":
            # Look for pattern like "Overtime Hours: 5.00"
            match = re.search(r"Overtime Hours:\s*(\d+\.?\d*)", details)
            if match:
                return float(match.group(1))
    
    except (ValueError, AttributeError):
        pass
    
    return 0.0

def generate_wage_data_source_note(
    wage_sources: Dict[str, str],
    default_wage: float = 18.00
) -> str:
    """
    Generate a note explaining how wage data was sourced for the report.
    
    Args:
        wage_sources: Dict mapping employee_identifier to wage source description
        default_wage: Default wage used for fallback
        
    Returns:
        String describing wage data sources
    """
    if not wage_sources:
        return f"Default V1 assumption of ${default_wage:.2f}/hr used for all cost estimates (no wage data available)."
    
    # Count how many employees had parsed vs. default wages
    parsed_count = sum(1 for source in wage_sources.values() if "Parsed from timesheet" in source)
    default_count = sum(1 for source in wage_sources.values() if "Default assumption" in source)
    total_count = len(wage_sources)
    
    if parsed_count == total_count:
        return f"Wage rates parsed from timesheet data for all {total_count} employees."
    elif default_count == total_count:
        return f"Default V1 assumption of ${default_wage:.2f}/hr used for all {total_count} employees (no wage data in timesheet)."
    else:
        return (f"Mixed wage data sources: {parsed_count} employees with rates from timesheet, "
                f"{default_count} employees using default ${default_wage:.2f}/hr assumption.")

def calculate_total_labor_costs(
    punch_events: List[LLMParsedPunchEvent],
    employee_wages: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate total labor costs including regular, overtime, and double time hours.
    
    Args:
        punch_events: List of parsed punch events
        employee_wages: Dict mapping employee_identifier to hourly wage
        
    Returns:
        Dict with labor hour and cost breakdowns
    """
    # Parse shifts to get hour breakdowns
    shifts_by_employee = parse_shifts_from_punch_events(punch_events)
    
    labor_totals = {
        "total_regular_hours": 0.0,
        "total_overtime_hours": 0.0,
        "total_double_time_hours": 0.0,
        "total_regular_cost": 0.0,
        "total_overtime_cost": 0.0,
        "total_double_time_cost": 0.0,
        "total_labor_hours": 0.0,
        "total_labor_cost": 0.0
    }
    
    # Constants for overtime calculations
    DAILY_OVERTIME_THRESHOLD = 8.0
    DAILY_DOUBLE_TIME_THRESHOLD = 12.0
    OVERTIME_MULTIPLIER = 1.5
    DOUBLE_TIME_MULTIPLIER = 2.0
    
    for employee_id, shifts in shifts_by_employee.items():
        base_wage = employee_wages.get(employee_id, 18.00)
        
        for shift in shifts:
            total_hours = shift.total_hours_worked
            
            if total_hours <= 0:
                continue
            
            # Calculate hour breakdowns for this shift
            regular_hours = min(total_hours, DAILY_OVERTIME_THRESHOLD)
            overtime_hours = 0.0
            double_time_hours = 0.0
            
            if total_hours > DAILY_OVERTIME_THRESHOLD:
                if total_hours <= DAILY_DOUBLE_TIME_THRESHOLD:
                    overtime_hours = total_hours - DAILY_OVERTIME_THRESHOLD
                else:
                    overtime_hours = DAILY_DOUBLE_TIME_THRESHOLD - DAILY_OVERTIME_THRESHOLD  # 4 hours
                    double_time_hours = total_hours - DAILY_DOUBLE_TIME_THRESHOLD
            
            # Add to totals
            labor_totals["total_regular_hours"] += regular_hours
            labor_totals["total_overtime_hours"] += overtime_hours
            labor_totals["total_double_time_hours"] += double_time_hours
            
            # Calculate costs
            labor_totals["total_regular_cost"] += regular_hours * base_wage
            labor_totals["total_overtime_cost"] += overtime_hours * base_wage * OVERTIME_MULTIPLIER
            labor_totals["total_double_time_cost"] += double_time_hours * base_wage * DOUBLE_TIME_MULTIPLIER
    
    # Calculate final totals
    labor_totals["total_labor_hours"] = (
        labor_totals["total_regular_hours"] + 
        labor_totals["total_overtime_hours"] + 
        labor_totals["total_double_time_hours"]
    )
    labor_totals["total_labor_cost"] = (
        labor_totals["total_regular_cost"] + 
        labor_totals["total_overtime_cost"] + 
        labor_totals["total_double_time_cost"]
    )
    
    return labor_totals

# ===== TEST FUNCTIONS =====

if __name__ == "__main__":
    # Run tests when script is executed directly
    print("=== MEAL BREAK DETECTION TEST ===")
    test_meal_break_detection()
    
    print("\n=== REST BREAK DETECTION TEST ===")
    test_rest_break_detection()
    
    print("\n=== DAILY OVERTIME DETECTION TEST ===")
    test_daily_overtime_detection()
    
    print("\n=== WEEKLY OVERTIME DETECTION TEST ===")
    test_weekly_overtime_detection()
    
    print("\n=== MULTIPLE JOBS / DUPLICATE DETECTION TEST ===")
    test_multiple_jobs_duplicate_detection()
    
    print("\n=== CONSOLIDATED BREAK DETECTION TEST ===")
    test_consolidated_break_detection()
    
    print("\n=== COMPREHENSIVE TEST ===")
    test_all_compliance_detection() 

def test_wage_determination():
    """Test function to verify wage determination and cost calculation logic"""
    
    print(f"\n=== WAGE DETERMINATION TEST ===")
    
    # Create test data with mixed wage information
    test_events = [
        # Employee with wage data in timesheet
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Cook",
            timestamp=datetime(2025, 1, 15, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=15.50  # Wage data available
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Cook",
            timestamp=datetime(2025, 1, 15, 18, 0),  # 6:00 PM (10 hours - overtime)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=15.50
        ),
        
        # Employee without wage data (will use default)
        LLMParsedPunchEvent(
            employee_identifier_in_file="Jane Doe - Server",
            timestamp=datetime(2025, 1, 15, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server"
            # No hourly_wage_as_parsed - will use default
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Jane Doe - Server",
            timestamp=datetime(2025, 1, 15, 20, 0),  # 8:00 PM (11 hours - overtime)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server"
        ),
        
        # Employee with higher wage and meal break violation
        LLMParsedPunchEvent(
            employee_identifier_in_file="Manager Bob",
            timestamp=datetime(2025, 1, 15, 7, 0),  # 7:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Manager",
            hourly_wage_as_parsed=22.00  # Higher wage
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Manager Bob",
            timestamp=datetime(2025, 1, 15, 13, 0),  # 1:00 PM (6 hours no break)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Manager",
            hourly_wage_as_parsed=22.00
        ),
    ]
    
    print("1. Testing wage determination:")
    employee_wages, wage_sources = determine_employee_hourly_wages(test_events)
    
    for employee_id, wage in employee_wages.items():
        source = wage_sources[employee_id]
        print(f"  {employee_id}: ${wage:.2f}/hr ({source})")
    
    print(f"\n2. Testing wage data source note:")
    wage_note = generate_wage_data_source_note(wage_sources)
    print(f"  {wage_note}")
    
    print(f"\n3. Testing labor cost calculations:")
    labor_costs = calculate_total_labor_costs(test_events, employee_wages)
    print(f"  Total Regular Hours: {labor_costs['total_regular_hours']:.2f}")
    print(f"  Total Overtime Hours: {labor_costs['total_overtime_hours']:.2f}")
    print(f"  Total Labor Cost: ${labor_costs['total_labor_cost']:.2f}")
    print(f"  - Regular Cost: ${labor_costs['total_regular_cost']:.2f}")
    print(f"  - Overtime Cost: ${labor_costs['total_overtime_cost']:.2f}")
    
    print(f"\n4. Testing violation cost calculations:")
    # Generate some violations to test cost calculations
    meal_violations = detect_meal_break_violations(test_events)
    overtime_violations = detect_daily_overtime_violations(test_events)
    all_violations = meal_violations + overtime_violations
    
    violation_costs = calculate_violation_costs(all_violations, employee_wages)
    print(f"  Total Estimated Cost: ${violation_costs['total_estimated_cost']:.2f}")
    print(f"  - Penalty Costs: ${violation_costs['total_penalty_cost']:.2f}")
    print(f"  - Overtime Premiums: ${violation_costs['total_overtime_cost']:.2f}")
    
    print(f"\n5. Violation cost breakdown:")
    for detail in violation_costs['violation_details']:
        print(f"  {detail['rule_id']}: ${detail['estimated_cost']:.2f} - {detail['cost_description']}")
    
    return {
        "employee_wages": employee_wages,
        "wage_sources": wage_sources,
        "labor_costs": labor_costs,
        "violation_costs": violation_costs,
        "violations": all_violations
    } 

def detect_compliance_violations_with_costs(punch_events: List[LLMParsedPunchEvent], default_wage: float = 18.00) -> Dict[str, any]:
    """
    Comprehensive compliance violation detection with cost calculations and wage determination.
    
    This function:
    1. Determines employee wages (parsed or default)
    2. Detects all compliance violations (including duplicate handling)
    3. Calculates violation costs
    4. Calculates total labor costs
    5. Provides comprehensive cost and violation analysis
    
    Args:
        punch_events: List of parsed punch events from LLM processing
        default_wage: Default hourly wage to use when not available in data
        
    Returns:
        Dict containing comprehensive analysis results
    """
    # Step 1: Determine employee wages
    employee_wages, wage_sources = determine_employee_hourly_wages(punch_events, default_wage)
    wage_data_note = generate_wage_data_source_note(wage_sources, default_wage)
    
    # Step 2: Run comprehensive compliance detection (including duplicate handling)
    compliance_results = detect_compliance_violations_with_duplicate_handling(punch_events)
    
    # Step 3: Calculate violation costs
    all_violations = compliance_results["all_violations"]
    violation_costs = calculate_violation_costs(all_violations, employee_wages)
    
    # Step 4: Calculate total labor costs
    labor_costs = calculate_total_labor_costs(punch_events, employee_wages)
    
    # Step 5: Combine all results
    comprehensive_results = {
        # Wage determination results
        "employee_wages": employee_wages,
        "wage_sources": wage_sources,
        "wage_data_source_note": wage_data_note,
        
        # Labor cost analysis
        "labor_costs": labor_costs,
        
        # Compliance violation results (from existing function)
        **compliance_results,
        
        # Violation cost analysis
        "violation_costs": violation_costs,
        
        # Summary metrics
        "cost_summary": {
            "total_labor_cost": labor_costs["total_labor_cost"],
            "total_violation_cost": violation_costs["total_estimated_cost"],
            "violation_cost_percentage": (
                violation_costs["total_estimated_cost"] / labor_costs["total_labor_cost"] * 100
                if labor_costs["total_labor_cost"] > 0 else 0.0
            ),
            "penalty_cost": violation_costs["total_penalty_cost"],
            "overtime_premium_cost": violation_costs["total_overtime_cost"]
        }
    }
    
    return comprehensive_results

def test_comprehensive_wage_and_cost_analysis():
    """Test function to verify comprehensive wage determination and cost analysis"""
    
    print(f"\n=== COMPREHENSIVE WAGE & COST ANALYSIS TEST ===")
    
    # Create comprehensive test scenario with multiple violation types and wage scenarios
    test_events = [
        # Employee 1: John Smith working multiple roles with parsed wage
        # Monday - Cook role, 10 hours (overtime + meal break violation)
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Cook",
            timestamp=datetime(2025, 1, 13, 7, 0),  # 7:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=16.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Cook",
            timestamp=datetime(2025, 1, 13, 17, 0),  # 5:00 PM (10 hours, no meal break)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=16.00
        ),
        
        # Tuesday - Server role (should be consolidated as same person)
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Server",
            timestamp=datetime(2025, 1, 14, 8, 0),  # 8:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Server",
            hourly_wage_as_parsed=16.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="John Smith - Server",
            timestamp=datetime(2025, 1, 14, 18, 0),  # 6:00 PM (10 hours)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Server",
            hourly_wage_as_parsed=16.00
        ),
        
        # Employee 2: Manager with high wage and various violations
        LLMParsedPunchEvent(
            employee_identifier_in_file="Manager Sarah",
            timestamp=datetime(2025, 1, 13, 6, 0),  # 6:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Manager",
            hourly_wage_as_parsed=28.00  # High wage
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Manager Sarah",
            timestamp=datetime(2025, 1, 13, 20, 0),  # 8:00 PM (14 hours - double time + meal violations)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Manager",
            hourly_wage_as_parsed=28.00
        ),
        
        # Employee 3: No wage data (will use default)
        LLMParsedPunchEvent(
            employee_identifier_in_file="Temp Worker - Host",
            timestamp=datetime(2025, 1, 13, 9, 0),  # 9:00 AM
            punch_type_as_parsed="Clock In",
            role_as_parsed="Host"
            # No wage data - will use default $18/hr
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="Temp Worker - Host",
            timestamp=datetime(2025, 1, 13, 15, 0),  # 3:00 PM (6 hours - meal violation)
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Host"
        ),
    ]
    
    print("Testing comprehensive wage determination and cost analysis...")
    
    # Run comprehensive analysis
    results = detect_compliance_violations_with_costs(test_events)
    
    print(f"\n1. WAGE DETERMINATION:")
    print(f"   Data Source Note: {results['wage_data_source_note']}")
    for emp_id, wage in results['employee_wages'].items():
        source = results['wage_sources'][emp_id]
        print(f"   {emp_id}: ${wage:.2f}/hr - {source}")
    
    print(f"\n2. LABOR COST ANALYSIS:")
    labor = results['labor_costs']
    print(f"   Total Labor Hours: {labor['total_labor_hours']:.2f}")
    print(f"   - Regular: {labor['total_regular_hours']:.2f} hrs")
    print(f"   - Overtime: {labor['total_overtime_hours']:.2f} hrs")
    print(f"   - Double Time: {labor['total_double_time_hours']:.2f} hrs")
    print(f"   Total Labor Cost: ${labor['total_labor_cost']:.2f}")
    print(f"   - Regular Cost: ${labor['total_regular_cost']:.2f}")
    print(f"   - Overtime Cost: ${labor['total_overtime_cost']:.2f}")
    print(f"   - Double Time Cost: ${labor['total_double_time_cost']:.2f}")
    
    print(f"\n3. COMPLIANCE VIOLATIONS:")
    violations = results['violation_summary']
    print(f"   Total Violations: {results['total_violations']}")
    print(f"   - Meal Breaks: {violations['meal_breaks']}")
    print(f"   - Rest Breaks: {violations['rest_breaks']}")
    print(f"   - Daily Overtime: {violations['daily_overtime']}")
    print(f"   - Weekly Overtime: {violations['weekly_overtime']}")
    
    print(f"\n4. VIOLATION COST ANALYSIS:")
    costs = results['violation_costs']
    print(f"   Total Violation Cost: ${costs['total_estimated_cost']:.2f}")
    print(f"   - Penalty Costs: ${costs['total_penalty_cost']:.2f}")
    print(f"   - Overtime Premiums: ${costs['total_overtime_cost']:.2f}")
    
    print(f"\n5. COST SUMMARY:")
    summary = results['cost_summary']
    print(f"   Total Labor Cost: ${summary['total_labor_cost']:.2f}")
    print(f"   Total Violation Cost: ${summary['total_violation_cost']:.2f}")
    print(f"   Violation Cost as % of Labor: {summary['violation_cost_percentage']:.1f}%")
    
    print(f"\n6. DUPLICATE EMPLOYEE HANDLING:")
    if results['duplicate_employee_groups']:
        for norm_name, original_ids in results['duplicate_employee_groups'].items():
            print(f"   Detected duplicate: {original_ids}")
    else:
        print(f"   No duplicate employees detected")
    
    print(f"\n7. TOP VIOLATION COSTS:")
    for detail in sorted(costs['violation_details'], key=lambda x: x['estimated_cost'], reverse=True)[:5]:
        print(f"   ${detail['estimated_cost']:.2f} - {detail['rule_id']}: {detail['employee_identifier']}")
    
    return results