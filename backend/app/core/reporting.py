"""
Reporting module for generating structured report data from compliance analysis.

This module provides functions to transform the comprehensive compliance analysis results
into the specific data structures required for frontend report display, including:
- KPI tiles data
- Staffing density heat-map data  
- Violation summaries
- Employee-specific reports
- Actionable advice text

Task 3.5.1: Function to calculate KPI tiles data (cost of violations, OT costs, total hours by type)
Task 3.5.2: Function to generate data for Staffing Density Heat-Map (dynamic period, hourly counts)
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter
from app.models.schemas import (
    LLMParsedPunchEvent, 
    ReportKPIs, 
    ViolationInstance,
    EmployeeReportDetails,
    HeatMapDatapoint
)
from app.core.compliance_rules import (
    detect_compliance_violations_with_costs,
    detect_compliance_violations_with_duplicate_handling,
    determine_employee_hourly_wages,
    calculate_total_labor_costs,
    calculate_violation_costs,
    generate_wage_data_source_note,
    get_all_compliance_violations
)
from app.core.logging_config import get_logger
import re

# Initialize logger for this module
logger = get_logger("reporting")


def _calculate_aggregated_premium_hours(violations: List[ViolationInstance]) -> Dict[str, float]:
    """
    Calculate aggregated premium hours from all violations.
    
    Args:
        violations: List of ViolationInstance objects with penalty_hours and overtime_hours
        
    Returns:
        Dict with aggregated premium hour totals
    """
    total_penalty_hours = 0.0
    total_overtime_premium_hours = 0.0
    total_double_time_premium_hours = 0.0
    
    for violation in violations:
        penalty_hours = getattr(violation, 'penalty_hours', 0.0) or 0.0
        overtime_hours = getattr(violation, 'overtime_hours', 0.0) or 0.0
        
        # Add penalty hours (from meal break violations)
        total_penalty_hours += penalty_hours
        
        # Add overtime premium hours (categorize by violation type)
        if "DOUBLE_TIME" in violation.rule_id:
            total_double_time_premium_hours += overtime_hours
        elif any(keyword in violation.rule_id for keyword in ["OVERTIME", "DAILY_OT", "WEEKLY_OT"]):
            total_overtime_premium_hours += overtime_hours
    
    total_premium_hours = total_penalty_hours + total_overtime_premium_hours + total_double_time_premium_hours
    
    return {
        "total_premium_hours": total_premium_hours,
        "total_penalty_hours": total_penalty_hours,
        "total_overtime_premium_hours": total_overtime_premium_hours,
        "total_double_time_premium_hours": total_double_time_premium_hours
    }


def calculate_kpi_tiles_data(
    punch_events: List[LLMParsedPunchEvent], 
    default_wage: float = 18.00
) -> ReportKPIs:
    """
    Calculate KPI tiles data including cost of violations, overtime costs, and total hours by type.
    
    This function implements task 3.5.1 by:
    1. Running comprehensive compliance analysis with cost calculations
    2. Extracting labor hour breakdowns (regular, overtime, double overtime)
    3. Calculating violation costs and overtime cost premiums
    4. Determining wage data sources and creating appropriate notes
    5. Counting violations by type for compliance risk assessment
    
    Args:
        punch_events: List of parsed punch events from LLM processing
        default_wage: Default hourly wage to use when wage data not available in timesheet
        
    Returns:
        ReportKPIs object containing all KPI tile data for frontend display
    """
    # Run comprehensive compliance analysis with costs
    analysis_results = detect_compliance_violations_with_costs(punch_events, default_wage)
    
    # Extract labor cost breakdown
    labor_costs = analysis_results["labor_costs"]
    violation_costs = analysis_results["violation_costs"]
    violation_summary = analysis_results["violation_summary"]
    wage_data_note = analysis_results["wage_data_source_note"]
    
    # Get enriched violations for premium hour calculation
    enriched_violations = compile_compliance_violations_with_costs(punch_events)
    premium_hours = _calculate_aggregated_premium_hours(enriched_violations)
    
    # Calculate compliance risk assessment text (updated to use premium hours)
    total_violations = analysis_results["total_violations"]
    risk_assessment = _generate_compliance_risk_assessment(
        total_violations=total_violations,
        violation_summary=violation_summary,
        premium_hours=premium_hours
    )
    
    # Create and return KPI data structure
    return ReportKPIs(
        # Total labor hours breakdown
        total_scheduled_labor_hours=labor_costs["total_labor_hours"],
        total_regular_hours=labor_costs["total_regular_hours"],
        total_overtime_hours=labor_costs["total_overtime_hours"],
        total_double_overtime_hours=labor_costs["total_double_time_hours"],
        
        # Keep old cost fields for backward compatibility (but may be deprecated)
        estimated_overtime_cost=violation_costs["overtime_cost"],  # Premium above regular rate
        estimated_double_overtime_cost=violation_costs["double_time_cost"],  # Premium above regular rate
        
        # New aggregated premium hours fields
        total_premium_hours=premium_hours["total_premium_hours"],
        total_penalty_hours=premium_hours["total_penalty_hours"],
        total_overtime_premium_hours=premium_hours["total_overtime_premium_hours"],
        total_double_time_premium_hours=premium_hours["total_double_time_premium_hours"],
        
        # Compliance violation counts
        count_meal_break_violations=violation_summary["meal_breaks"],
        count_rest_break_violations=violation_summary["rest_breaks"],
        count_daily_overtime_violations=violation_summary["daily_overtime"],
        count_weekly_overtime_violations=violation_summary["weekly_overtime"],
        # NOTE: Double overtime violations are already included in the daily_overtime count above.
        # This field provides the breakdown for reporting but should NOT be added to total violation counts
        # to avoid double counting (daily_overtime already includes both regular and double overtime violations)
        count_daily_double_overtime_violations=_count_daily_double_overtime_violations(analysis_results),
        
        # Risk assessment and notes
        compliance_risk_assessment=risk_assessment,
        wage_data_source_note=wage_data_note
    )


def _generate_compliance_risk_assessment(
    total_violations: int,
    violation_summary: Dict[str, int],
    premium_hours: Dict[str, float]
) -> str:
    """
    Generate qualitative compliance risk assessment text for KPI display.
    
    Args:
        total_violations: Total number of violations detected
        violation_summary: Breakdown of violations by type
        premium_hours: Premium hours breakdown
        
    Returns:
        Human-readable risk assessment string
    """
    if total_violations == 0:
        return "Low: No compliance violations detected"
    
    # Calculate impact level based on premium hours
    total_premium_hours = premium_hours.get("total_premium_hours", 0)
    impact_level = "Low"
    if total_premium_hours > 20:
        impact_level = "High"
    elif total_premium_hours > 10:
        impact_level = "Medium"
    
    # Identify most critical violation types
    critical_violations = []
    if violation_summary.get("meal_breaks", 0) > 0:
        critical_violations.append(f"{violation_summary['meal_breaks']} meal break")
    if violation_summary.get("daily_overtime", 0) > 0:
        critical_violations.append(f"{violation_summary['daily_overtime']} daily overtime")
    if violation_summary.get("weekly_overtime", 0) > 0:
        critical_violations.append(f"{violation_summary['weekly_overtime']} weekly overtime")
    if violation_summary.get("rest_breaks", 0) > 0:
        critical_violations.append(f"{violation_summary['rest_breaks']} rest break")
    
    # Build risk assessment string with premium hours
    risk_level = "Medium"
    if total_violations >= 10 or total_premium_hours > 20:
        risk_level = "High"
    elif total_violations <= 2 and total_premium_hours < 5:
        risk_level = "Low"
    
    violation_text = " & ".join(critical_violations[:3])  # Limit to top 3 types
    if len(critical_violations) > 3:
        violation_text += " & others"
    
    return f"{risk_level}: {total_violations} violations including {violation_text} ({total_premium_hours:.1f}hr premium cost)"


def _count_daily_double_overtime_violations(analysis_results: Dict[str, Any]) -> int:
    """
    Count daily double overtime violations from the comprehensive analysis results.
    
    Daily double overtime violations are tracked as part of daily_overtime_violations
    with rule_id "DAILY_OVERTIME_DOUBLE_TIME".
    
    Args:
        analysis_results: Results from detect_compliance_violations_with_costs
        
    Returns:
        Count of daily double overtime violations
    """
    daily_overtime_violations = analysis_results.get("daily_overtime_violations", [])
    
    # Count violations with double time rule ID
    double_overtime_count = 0
    for violation in daily_overtime_violations:
        if violation.rule_id == "DAILY_OVERTIME_DOUBLE_TIME":
            double_overtime_count += 1
    
    return double_overtime_count


# Additional helper functions for future reporting tasks

def get_violation_cost_breakdown(punch_events: List[LLMParsedPunchEvent]) -> Dict[str, float]:
    """
    Get detailed breakdown of violation costs by category.
    Helper function for future reporting tasks.
    
    Returns:
        Dict with violation cost categories and amounts
    """
    analysis_results = detect_compliance_violations_with_costs(punch_events)
    violation_costs = analysis_results["violation_costs"]
    
    return {
        "meal_break_penalty_cost": violation_costs.get("meal_break_penalty_cost", 0.0),
        "rest_break_penalty_cost": violation_costs.get("rest_break_penalty_cost", 0.0), 
        "overtime_premium_cost": violation_costs.get("overtime_cost", 0.0),
        "double_time_premium_cost": violation_costs.get("double_time_cost", 0.0),
        "total_penalty_cost": violation_costs.get("total_penalty_cost", 0.0),
        "total_overtime_cost": violation_costs.get("total_overtime_cost", 0.0),
        "total_estimated_cost": violation_costs.get("total_estimated_cost", 0.0)
    }


def get_labor_cost_summary(punch_events: List[LLMParsedPunchEvent]) -> Dict[str, float]:
    """
    Get labor cost summary for KPI display.
    Helper function for future reporting tasks.
    
    Returns:
        Dict with labor cost totals by category
    """
    analysis_results = detect_compliance_violations_with_costs(punch_events)
    labor_costs = analysis_results["labor_costs"]
    
    return {
        "total_regular_cost": labor_costs.get("total_regular_cost", 0.0),
        "total_overtime_cost": labor_costs.get("total_overtime_cost", 0.0),
        "total_double_time_cost": labor_costs.get("total_double_time_cost", 0.0),
        "total_labor_cost": labor_costs.get("total_labor_cost", 0.0)
    }


def generate_staffing_density_heatmap_data(
    punch_events: List[LLMParsedPunchEvent],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    hour_start: int = 6,  # Start at 6 AM
    hour_end: int = 23    # End at 11 PM
) -> List[HeatMapDatapoint]:
    """
    Generate data for Staffing Density Heat-Map with dynamic period and hourly counts.
    
    This function implements task 3.5.2 by:
    1. Analyzing punch events to determine when employees are working
    2. Creating hourly time blocks for the specified date range
    3. Counting how many employees are working during each hour
    4. Handling overlapping shifts and break periods
    5. Returning structured data for heat-map visualization
    
    Args:
        punch_events: List of parsed punch events from LLM processing
        start_date: Start date for heat-map analysis (defaults to earliest punch date)
        end_date: End date for heat-map analysis (defaults to latest punch date)
        hour_start: Starting hour of day for heat-map (0-23, default 6 AM)
        hour_end: Ending hour of day for heat-map (0-23, default 11 PM)
        
    Returns:
        List of HeatMapDatapoint objects for frontend heat-map visualization
    """
    if not punch_events:
        return []
    
    # Determine date range from punch events if not specified
    all_dates = [event.timestamp.date() for event in punch_events]
    if start_date is None:
        start_date = min(all_dates)
    if end_date is None:
        end_date = max(all_dates)
    
    # Get timezone from first punch event to ensure consistency
    sample_tz = punch_events[0].timestamp.tzinfo
    
    # Group punch events by employee and date for shift reconstruction
    employee_shifts = _reconstruct_employee_shifts(punch_events)
    
    # Generate all hourly time blocks in the date range
    heatmap_data = []
    current_date = start_date
    
    while current_date <= end_date:
        for hour in range(hour_start, hour_end + 1):
            # Create timezone-aware hour timestamp to match punch events
            hour_timestamp = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=hour)
            if sample_tz:
                hour_timestamp = hour_timestamp.replace(tzinfo=sample_tz)
            
            # Count employees working during this hour
            employee_count = _count_employees_working_at_hour(employee_shifts, hour_timestamp)
            
            heatmap_data.append(HeatMapDatapoint(
                hour_timestamp=hour_timestamp,
                employee_count=employee_count
            ))
        
        current_date += timedelta(days=1)
    
    return heatmap_data


def _reconstruct_employee_shifts(punch_events: List[LLMParsedPunchEvent]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Reconstruct employee shifts from punch events for heat-map analysis.
    
    Args:
        punch_events: List of punch events
        
    Returns:
        Dict mapping employee identifiers to lists of shift periods
    """
    # Group punch events by employee
    employee_punches = defaultdict(list)
    for event in punch_events:
        employee_punches[event.employee_identifier_in_file].append(event)
    
    # Sort punches by timestamp for each employee
    for employee in employee_punches:
        employee_punches[employee].sort(key=lambda x: x.timestamp)
    
    # Reconstruct shifts for each employee
    employee_shifts = {}
    for employee, punches in employee_punches.items():
        shifts = _parse_employee_shifts_from_punches(punches)
        employee_shifts[employee] = shifts
    
    return employee_shifts


def _parse_employee_shifts_from_punches(punches: List[LLMParsedPunchEvent]) -> List[Dict[str, Any]]:
    """
    Parse individual employee punches into shift periods.
    
    Handles various punch types (Clock In/Out, Lunch Start/End, Break Start/End)
    and reconstructs continuous work periods.
    
    Args:
        punches: List of punch events for a single employee, sorted by timestamp
        
    Returns:
        List of shift dictionaries with start_time, end_time, and work_periods
    """
    shifts = []
    current_shift_start = None
    work_periods = []  # List of (start, end) tuples for actual work time
    current_work_start = None
    
    for punch in punches:
        punch_type = punch.punch_type_as_parsed.lower()
        
        # Handle shift start (Clock In)
        if any(keyword in punch_type for keyword in ['clock in', 'in']):
            if 'lunch' not in punch_type and 'break' not in punch_type and 'meal' not in punch_type:
                # Starting a new shift
                current_shift_start = punch.timestamp
                current_work_start = punch.timestamp
        
        # Handle break/lunch start (stop working)
        elif any(keyword in punch_type for keyword in ['lunch start', 'break start', 'meal start']):
            if current_work_start is not None:
                # End current work period (from clock in to lunch start)
                work_periods.append((current_work_start, punch.timestamp))
                current_work_start = None
        
        # Handle break/lunch end (resume working)
        elif any(keyword in punch_type for keyword in ['lunch end', 'break end', 'meal end']):
            if current_shift_start is not None:
                # Resume work (lunch end to next event)
                current_work_start = punch.timestamp
        
        # Handle shift end (Clock Out)
        elif any(keyword in punch_type for keyword in ['clock out', 'out']):
            if 'lunch' not in punch_type and 'break' not in punch_type and 'meal' not in punch_type:
                # Ending the shift
                if current_work_start is not None:
                    # End current work period (from lunch end to clock out, or from clock in to clock out if no lunch)
                    work_periods.append((current_work_start, punch.timestamp))
                    current_work_start = None
                
                if current_shift_start is not None:
                    # Complete the shift
                    shifts.append({
                        'shift_start': current_shift_start,
                        'shift_end': punch.timestamp,
                        'work_periods': work_periods.copy()
                    })
                    current_shift_start = None
                    work_periods = []
        
        # Handle generic "start" and "end" punches if specific ones didn't match
        elif 'start' in punch_type and current_shift_start is None:
            # Generic start - begin shift
            current_shift_start = punch.timestamp
            current_work_start = punch.timestamp
        elif 'end' in punch_type and current_shift_start is not None:
            # Generic end - finish shift
            if current_work_start is not None:
                work_periods.append((current_work_start, punch.timestamp))
                current_work_start = None
            
            shifts.append({
                'shift_start': current_shift_start,
                'shift_end': punch.timestamp,
                'work_periods': work_periods.copy()
            })
            current_shift_start = None
            work_periods = []
    
    # Handle case where shift doesn't have a proper end punch
    if current_shift_start is not None and current_work_start is not None:
        # Assume shift ended shortly after last punch
        estimated_end = punches[-1].timestamp + timedelta(minutes=5)
        work_periods.append((current_work_start, estimated_end))
        shifts.append({
            'shift_start': current_shift_start,
            'shift_end': estimated_end,
            'work_periods': work_periods.copy()
        })
    
    return shifts


def _count_employees_working_at_hour(
    employee_shifts: Dict[str, List[Dict[str, Any]]], 
    hour_timestamp: datetime
) -> int:
    """
    Count how many employees are working during a specific hour.
    
    Args:
        employee_shifts: Dict of employee shifts from _reconstruct_employee_shifts
        hour_timestamp: The specific hour to check (datetime object)
        
    Returns:
        Number of employees working during that hour
    """
    working_count = 0
    
    for employee, shifts in employee_shifts.items():
        is_working_this_hour = False
        
        for shift in shifts:
            # Check if any work period includes this specific hour
            for work_start, work_end in shift['work_periods']:
                # Check if the hour timestamp falls within this work period
                # Employee is working if: work_start <= hour_timestamp < work_end
                if work_start <= hour_timestamp < work_end:
                    is_working_this_hour = True
                    break
            
            if is_working_this_hour:
                break
        
        if is_working_this_hour:
            working_count += 1
    
    return working_count


def compile_general_compliance_violations(punch_events: List[LLMParsedPunchEvent]) -> List[ViolationInstance]:
    """
    Compile all compliance violations for the given punch events.
    
    Args:
        punch_events: List of parsed punch events from LLM
        
    Returns:
        List of all violations found across all employees
    """
    try:
        # Get violations from the comprehensive compliance checking function
        violations_data = get_all_compliance_violations(punch_events)
        all_violations = violations_data["all_violations"]
        
        # Log compliance checking results
        logger.info(f"Compliance check completed | Violations found: {len(all_violations)}")
        
        return all_violations
        
    except Exception as e:
        logger.error(f"Error in compliance violation compilation: {str(e)}")
        return []


def compile_compliance_violations_with_costs(punch_events: List[LLMParsedPunchEvent]) -> List[ViolationInstance]:
    """
    Compile all compliance violations and enrich them with cost information.
    
    Args:
        punch_events: List of parsed punch events from LLM
        
    Returns:
        List of all violations found across all employees, enriched with cost data
    """
    try:
        # FIXED: Use the same violation detection method as KPIs (with duplicate handling)
        # This ensures the detailed violations list matches the KPI counts
        violations_data = detect_compliance_violations_with_duplicate_handling(punch_events)
        all_violations = violations_data.get("all_violations", [])
        
        if not all_violations:
            logger.info("No violations found to enrich with cost data")
            return []
        
        # Get cost breakdown separately for enrichment
        cost_violations_data = detect_compliance_violations_with_costs(punch_events)
        violation_costs = cost_violations_data.get("violation_costs", {})
        violation_details = violation_costs.get("violation_details", [])
        
        # Create a lookup map for cost data by violation key
        cost_lookup = {}
        for detail in violation_details:
            key = (detail["rule_id"], detail["employee_identifier"], detail["date_of_violation"])
            cost_lookup[key] = detail
        
        # Enrich each violation with cost information
        enriched_violations = []
        
        for violation in all_violations:
            # Create a copy of the violation data, preserving ALL original fields
            enriched_violation_data = {
                "rule_id": violation.rule_id,
                "rule_description": violation.rule_description,
                "employee_identifier": violation.employee_identifier,
                "date_of_violation": violation.date_of_violation,
                "specific_details": violation.specific_details,
                "suggested_action_generic": violation.suggested_action_generic,
                "related_punch_events": getattr(violation, 'related_punch_events', []),
                "shift_summary": getattr(violation, 'shift_summary', None),
            }
            
            # Look up cost information for this specific violation
            violation_key = (violation.rule_id, violation.employee_identifier, violation.date_of_violation)
            cost_detail = cost_lookup.get(violation_key)
            
            # Debug logging for cost enrichment
            logger.info(f"Cost enrichment debug - Rule: {violation.rule_id}, Employee: {violation.employee_identifier}, Cost detail found: {cost_detail is not None}, Shift summary present: {enriched_violation_data['shift_summary'] is not None}")
            
            if cost_detail:
                # Always show hours instead of dollar costs to avoid misleading wage assumptions
                # Managers can calculate their own costs using actual wage data
                enriched_violation_data["estimated_cost"] = None
                enriched_violation_data["cost_description"] = None
                
                # Calculate penalty and overtime hours based on violation type
                if "MEAL_BREAK" in violation.rule_id:
                    # All meal break violations get penalty hours (1 hour each)
                    enriched_violation_data["penalty_hours"] = 1.0
                    enriched_violation_data["overtime_hours"] = 0.0
                elif "DAILY_OVERTIME" in violation.rule_id or "WEEKLY_OVERTIME" in violation.rule_id or "DAILY_OT" in violation.rule_id:
                    # Extract actual overtime hours from cost detail or violation details
                    actual_overtime_hours = cost_detail.get("overtime_hours", 0.0)
                    if actual_overtime_hours == 0.0:
                        # Try to extract from cost description first (format: "Overtime premium: 2.00 hrs × $9.00/hr = $18.00")
                        cost_desc = cost_detail.get("cost_description", "")
                        hours_match = re.search(r'(\d+\.?\d*)\s*hrs?\s*×', cost_desc)
                        if hours_match:
                            actual_overtime_hours = float(hours_match.group(1))
                        else:
                            # Fallback: try to extract from violation details
                            details = violation.specific_details
                            hours_match = re.search(r'(\d+\.?\d*)\s*hours?', details.lower())
                            actual_overtime_hours = float(hours_match.group(1)) if hours_match else 0.0
                    
                    # Calculate premium hours based on violation type
                    if "DOUBLE_TIME" in violation.rule_id:
                        # Double time: 100% premium (each hour costs 1 extra hour)
                        premium_hours = actual_overtime_hours * 1.0
                    else:
                        # Regular overtime: 50% premium (each hour costs 0.5 extra hour)
                        premium_hours = actual_overtime_hours * 0.5
                    
                    enriched_violation_data["penalty_hours"] = 0.0
                    enriched_violation_data["overtime_hours"] = premium_hours
                elif "REST_BREAK" in violation.rule_id:
                    # Rest break violations are information-level only, no cost impact
                    enriched_violation_data["penalty_hours"] = 0.0
                    enriched_violation_data["overtime_hours"] = 0.0
                else:
                    # Other violations get no penalty hours
                    enriched_violation_data["penalty_hours"] = 0.0
                    enriched_violation_data["overtime_hours"] = 0.0
            else:
                # No cost data available - just set hours without dollar costs
                enriched_violation_data["estimated_cost"] = None
                enriched_violation_data["cost_description"] = None
                
                # Set penalty/overtime hours based on violation type
                if "MEAL_BREAK" in violation.rule_id:
                    enriched_violation_data["penalty_hours"] = 1.0
                    enriched_violation_data["overtime_hours"] = 0.0
                elif "DAILY_OVERTIME" in violation.rule_id or "WEEKLY_OVERTIME" in violation.rule_id:
                    # Extract actual overtime hours from violation details
                    details = violation.specific_details
                    hours_match = re.search(r'(\d+\.?\d*)\s*hours?', details.lower())
                    actual_overtime_hours = float(hours_match.group(1)) if hours_match else 0.0
                    
                    # Calculate premium hours based on violation type
                    if "DOUBLE_TIME" in violation.rule_id:
                        # Double time: 100% premium (each hour costs 1 extra hour)
                        premium_hours = actual_overtime_hours * 1.0
                    else:
                        # Regular overtime: 50% premium (each hour costs 0.5 extra hour)
                        premium_hours = actual_overtime_hours * 0.5
                    
                    enriched_violation_data["penalty_hours"] = 0.0
                    enriched_violation_data["overtime_hours"] = premium_hours
                elif "REST_BREAK" in violation.rule_id:
                    # Rest break violations are information-level only, no cost impact
                    enriched_violation_data["penalty_hours"] = 0.0
                    enriched_violation_data["overtime_hours"] = 0.0
                else:
                    enriched_violation_data["penalty_hours"] = 0.0
                    enriched_violation_data["overtime_hours"] = 0.0
            
            # Debug logging for enriched violation data
            logger.info(f"Enriched violation debug - Rule: {violation.rule_id}, "
                       f"penalty_hours: {enriched_violation_data.get('penalty_hours')}, "
                       f"overtime_hours: {enriched_violation_data.get('overtime_hours')}, "
                       f"estimated_cost: {enriched_violation_data.get('estimated_cost')}, "
                       f"shift_summary: {enriched_violation_data.get('shift_summary') is not None}")
            
            # Create enriched ViolationInstance
            enriched_violation = ViolationInstance(**enriched_violation_data)
            enriched_violations.append(enriched_violation)
        
        # Log enrichment results
        total_estimated_cost = sum(v.estimated_cost for v in enriched_violations if v.estimated_cost)
        logger.info(f"Enriched violations compiled | Total: {len(enriched_violations)} | Est. cost: ${total_estimated_cost:.2f}")
        
        return enriched_violations
        
    except Exception as e:
        logger.error(f"Error in cost-enriched violation compilation: {str(e)}")
        import traceback
        traceback.print_exc()
        # Fall back to basic violations if enrichment fails
        return compile_general_compliance_violations(punch_events)


def detect_individual_violation_cost(violation: ViolationInstance, base_wage: float = 18.0) -> dict:
    """
    Calculate cost information for an individual violation.
    
    Args:
        violation: The violation instance to calculate cost for
        base_wage: Base hourly wage (default $18/hr)
        
    Returns:
        Dict with estimated_cost and cost_description, or None if no cost applies
    """
    try:
        violation_cost = 0.0
        cost_description = ""
        
        if violation.rule_id.startswith("MEAL_BREAK"):
            # California meal break penalty: 1 hour of pay per violation
            violation_cost = base_wage
            cost_description = f"Meal break penalty: 1 hour at ${base_wage:.2f}/hr = ${violation_cost:.2f}"
            
        elif violation.rule_id.startswith("REST_BREAK"):
            # California rest break penalty: 1 hour of pay per violation
            violation_cost = base_wage
            cost_description = f"Rest break penalty: 1 hour at ${base_wage:.2f}/hr = ${violation_cost:.2f}"
            
        elif "DAILY_OVERTIME" in violation.rule_id:
            # Extract overtime hours from violation details
            details = violation.specific_details
            hours_match = re.search(r'(\d+\.?\d*)\s*hours?', details.lower())
            if hours_match:
                overtime_hours = float(hours_match.group(1))
                # Daily overtime is typically 1.5x rate for hours over 8
                if "DOUBLE_TIME" in violation.rule_id:
                    # Double time for over 12 hours
                    violation_cost = overtime_hours * base_wage * 2.0
                    cost_description = f"Double time: {overtime_hours}hr at ${base_wage * 2.0:.2f}/hr = ${violation_cost:.2f}"
                else:
                    # Time and a half
                    violation_cost = overtime_hours * base_wage * 1.5
                    cost_description = f"Time and a half: {overtime_hours}hr at ${base_wage * 1.5:.2f}/hr = ${violation_cost:.2f}"
            
        elif "WEEKLY_OVERTIME" in violation.rule_id:
            # Extract overtime hours from violation details
            details = violation.specific_details
            hours_match = re.search(r'Overtime Hours: (\d+\.?\d*)', details)
            if hours_match:
                overtime_hours = float(hours_match.group(1))
                # Weekly overtime is typically 1.5x rate for hours over 40
                violation_cost = overtime_hours * base_wage * 1.5
                cost_description = f"Weekly overtime: {overtime_hours}hr at ${base_wage * 1.5:.2f}/hr = ${violation_cost:.2f}"
        
        if violation_cost > 0:
            return {
                "estimated_cost": violation_cost,
                "cost_description": cost_description
            }
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error calculating individual violation cost: {str(e)}")
        return None


def generate_employee_summary_table_data(
    punch_events: List[LLMParsedPunchEvent],
    default_wage: float = 18.00
) -> List[EmployeeReportDetails]:
    """
    Generate employee-specific summary table data with hours breakdown and violations.
    
    This function implements task 3.5.4 by:
    1. Calculating individual employee hours breakdown (regular, overtime, double overtime)
    2. Identifying roles and departments observed for each employee
    3. Associating compliance violations with each employee
    4. Handling duplicate employee detection and consolidation
    5. Returning structured EmployeeReportDetails objects for table display
    
    Args:
        punch_events: List of parsed punch events from LLM processing
        default_wage: Default hourly wage for cost calculations
        
    Returns:
        List of EmployeeReportDetails objects for frontend table display
    """
    from app.core.compliance_rules import (
        detect_duplicate_employees,
        consolidate_employee_shifts_for_duplicates,
        calculate_total_labor_costs,
        determine_employee_hourly_wages
    )
    
    if not punch_events:
        return []
    
    try:
        # Step 1: Handle duplicate employee detection and consolidation
        duplicate_groups = detect_duplicate_employees(punch_events)
        consolidated_shifts = None
        employee_mapping = {}
        
        if duplicate_groups:
            # Use consolidated employee data
            consolidated_shifts, employee_mapping = consolidate_employee_shifts_for_duplicates(punch_events, duplicate_groups)
        
        # Step 2: Get all violations associated with employees
        all_violations = compile_general_compliance_violations(punch_events)
        
        # Step 3: Calculate hours and costs for employees
        employee_wages, wage_sources = determine_employee_hourly_wages(punch_events, default_wage)
        labor_costs = calculate_total_labor_costs(punch_events, employee_wages)
        
        # Step 4: Group data by employee
        employee_summaries = {}
        
        # Process each punch event to gather employee data
        for event in punch_events:
            emp_id = event.employee_identifier_in_file
            
            # Handle consolidated employee mapping
            if employee_mapping and emp_id in employee_mapping:
                # Use the consolidated employee identifier
                normalized_emp_id = employee_mapping[emp_id]
                # Ensure it's a string (might be a list from consolidation)
                if isinstance(normalized_emp_id, list):
                    normalized_emp_id = normalized_emp_id[0] if normalized_emp_id else emp_id
                normalized_emp_id = str(normalized_emp_id)
            else:
                normalized_emp_id = str(emp_id)
            
            # Initialize employee summary if not exists
            if normalized_emp_id not in employee_summaries:
                employee_summaries[normalized_emp_id] = {
                    'employee_identifier': normalized_emp_id,
                    'roles_observed': set(),
                    'departments_observed': set(),
                    'punch_events': [],
                    'violations': []
                }
            
            # Collect roles and departments (ensure they are strings)
            if event.role_as_parsed:
                role_str = str(event.role_as_parsed) if not isinstance(event.role_as_parsed, str) else event.role_as_parsed
                employee_summaries[normalized_emp_id]['roles_observed'].add(role_str)
            if event.department_as_parsed:
                dept_str = str(event.department_as_parsed) if not isinstance(event.department_as_parsed, str) else event.department_as_parsed
                employee_summaries[normalized_emp_id]['departments_observed'].add(dept_str)
            
            # Store punch events for hours calculation
            employee_summaries[normalized_emp_id]['punch_events'].append(event)
        
        # Step 5: Associate violations with employees
        for violation in all_violations:
            emp_id = violation.employee_identifier
            if emp_id in employee_summaries:
                employee_summaries[emp_id]['violations'].append(violation)
        
        # Step 6: Calculate hours breakdown for each employee
        result_summaries = []
        
        for emp_id, emp_data in employee_summaries.items():
            # Calculate hours for this employee
            emp_hours = _calculate_employee_hours_breakdown(emp_data['punch_events'])
            
            # Convert violations to proper format if needed
            violations_list = []
            for violation in emp_data['violations']:
                # Ensure violations are proper ViolationInstance objects
                if hasattr(violation, 'rule_id'):
                    violations_list.append(ViolationInstance(
                        rule_id=violation.rule_id,
                        rule_description=violation.rule_description,
                        employee_identifier=violation.employee_identifier,
                        date_of_violation=violation.date_of_violation,
                        specific_details=violation.specific_details,
                        suggested_action_generic=violation.suggested_action_generic
                    ))
                else:
                    violations_list.append(violation)
            
            # Create EmployeeReportDetails object
            employee_summary = EmployeeReportDetails(
                employee_identifier=emp_id,
                roles_observed=sorted(list(emp_data['roles_observed'])),
                departments_observed=sorted(list(emp_data['departments_observed'])),
                total_hours_worked=emp_hours['total_hours'],
                regular_hours=emp_hours['regular_hours'],
                overtime_hours=emp_hours['overtime_hours'],
                double_overtime_hours=emp_hours['double_overtime_hours'],
                violations_for_employee=violations_list
            )
            
            result_summaries.append(employee_summary)
        
        # Step 7: Sort by employee identifier for consistent ordering
        result_summaries.sort(key=lambda x: x.employee_identifier)
        
        return result_summaries
        
    except Exception as e:
        # If summary generation fails, return empty list with error logged
        print(f"Error generating employee summaries: {e}")
        import traceback
        traceback.print_exc()
        return []


def provide_generic_actionable_advice_for_violation_types() -> Dict[str, str]:
    """
    Provide generic actionable advice text for each violation type.
    
    This function implements task 3.5.5 by returning a comprehensive mapping
    of violation rule IDs to human-readable actionable advice text. This is
    useful for frontend displays where violation-specific guidance needs to
    be shown to users.
    
    The advice provided is generic and applicable across different restaurant
    types and employee situations. It focuses on practical steps managers
    can take to prevent future violations of the same type.
    
    Returns:
        Dict mapping violation rule IDs to actionable advice strings
    """
    return {
        # Meal Break Violations
        "MEAL_BREAK_MISSING": "Ensure employees working more than 5 hours receive a 30-minute uninterrupted meal break before the end of their 5th hour of work. Schedule meal breaks proactively when creating shifts.",
        "MEAL_BREAK_LATE": "Schedule meal breaks to start before the end of the 5th hour of work to comply with California labor regulations. Consider setting up automatic reminders for managers.",
        "MEAL_BREAK_TOO_SHORT": "Meal breaks must be at least 30 minutes long and completely uninterrupted for compliance. Train supervisors to ensure employees are not called back early from breaks.",
        "SECOND_MEAL_BREAK_MISSING": "Employees working more than 10 hours require a second 30-minute meal break before the end of their 10th hour. Monitor long shifts carefully and schedule accordingly.",
        "SECOND_MEAL_BREAK_LATE": "Schedule the second meal break to start before the end of the 10th hour of work. Use scheduling software to track cumulative hours and trigger break reminders.",
        "SECOND_MEAL_BREAK_TOO_SHORT": "The second meal break must also be at least 30 minutes long and uninterrupted. Apply the same standards to all meal breaks regardless of order.",
        
        # Rest Break Violations  
        "REST_BREAK_MISSING": "Provide 10-minute paid rest breaks for every 4 hours worked, scheduled as close to the middle of each work period as possible. Create break rotation schedules to ensure coverage.",
        "REST_BREAK_INSUFFICIENT": "Rest breaks must be at least 10 minutes long. Brief moments between tasks do not constitute proper rest breaks under labor law.",
        "REST_BREAK_TIMING": "Schedule rest breaks near the middle of work periods for optimal compliance. Avoid clustering breaks at the beginning or end of shifts.",
        
        # Daily Overtime Violations
        "DAILY_OVERTIME": "Daily overtime (over 8 hours) requires time-and-a-half pay. Consider scheduling adjustments, additional staff, or shift limits to minimize overtime costs while ensuring adequate coverage.",
        "DAILY_OVERTIME_DOUBLE_TIME": "Daily double-time (over 12 hours) requires double pay. Review scheduling practices to avoid excessive daily hours. Consider splitting long shifts between multiple employees.",
        
        # Weekly Overtime Violations
        "WEEKLY_OVERTIME": "Weekly overtime (over 40 hours) requires time-and-a-half pay. Monitor weekly schedules proactively and redistribute hours across employees to control labor costs.",
        "WEEKLY_OVERTIME_PATTERN": "Consistent weekly overtime may indicate understaffing. Consider hiring additional part-time employees or adjusting service hours to match staffing capacity.",
        
        # Consolidated Violations (for employees working multiple roles)
        "MEAL_BREAK_MISSING_CONSOLIDATED": "When employees work multiple roles in a day, ensure total daily hours still comply with meal break requirements across all positions. Track cumulative hours, not individual role hours.",
        "REST_BREAK_MISSING_CONSOLIDATED": "Rest break requirements apply to total daily hours worked across all roles and departments. Coordinate between managers to ensure breaks are provided based on total work time.",
        "DAILY_OVERTIME_CONSOLIDATED": "When employees work multiple roles, daily overtime calculations are based on total hours across all positions. Monitor cumulative daily hours to prevent unintended overtime.",
        
        # Duplicate Employee Issues
        "DUPLICATE_EMPLOYEE_DETECTED": "Multiple employee entries detected for the same person. Standardize employee naming conventions and review payroll system entries to ensure accurate record-keeping.",
        "DUPLICATE_EMPLOYEE_HOURS": "Hours may be split across duplicate employee records. Consolidate employee records and verify total hours worked to ensure proper overtime and break compliance.",
        
        # Scheduling and Management Advice
        "INSUFFICIENT_BREAK_COVERAGE": "Ensure adequate staffing levels to provide break coverage. Consider cross-training employees or adjusting service levels during break periods.",
        "SCHEDULING_PATTERN_RISK": "Review recurring scheduling patterns that lead to violations. Consider implementing scheduling software with compliance checks built in.",
        "MANAGER_TRAINING_NEEDED": "Ensure all managers and supervisors understand California labor law requirements for breaks and overtime. Provide regular training updates on compliance requirements.",
        
        # Cost Management Advice
        "HIGH_OVERTIME_COSTS": "Excessive overtime indicates potential understaffing or inefficient scheduling. Analyze peak demand periods and consider adjusting staffing models or operating procedures.",
        "BREAK_PENALTY_COSTS": "Break violation penalties can be avoided through better scheduling and supervisor training. Implement systems to track and remind about required breaks.",
        "COMPLIANCE_MONITORING": "Regular compliance monitoring can prevent violations before they occur. Consider implementing automated tracking systems or regular compliance audits.",
        
        # General Fallback Advice
        "GENERAL_COMPLIANCE": "Review scheduling practices and ensure compliance with applicable California labor regulations. When in doubt, consult with labor law experts or HR professionals.",
        "UNKNOWN_VIOLATION": "Review the specific violation details and consult California labor law guidelines. Consider seeking guidance from labor law professionals for complex compliance issues."
    }


def get_actionable_advice_for_violation(rule_id: str) -> str:
    """
    Get specific actionable advice for a single violation type.
    
    This is a convenience function that wraps provide_generic_actionable_advice_for_violation_types()
    to return advice for a single rule ID.
    
    Args:
        rule_id: The violation rule identifier
        
    Returns:
        Human-readable actionable advice string for the specific violation type
    """
    advice_mapping = provide_generic_actionable_advice_for_violation_types()
    return advice_mapping.get(rule_id, advice_mapping.get("GENERAL_COMPLIANCE", "Review scheduling and ensure compliance with applicable labor regulations."))


def get_all_violation_types_with_advice() -> List[Dict[str, str]]:
    """
    Get all available violation types with their corresponding advice.
    
    Useful for frontend displays that need to show all possible violation
    categories and their associated guidance.
    
    Returns:
        List of dictionaries containing rule_id and advice for each violation type
    """
    advice_mapping = provide_generic_actionable_advice_for_violation_types()
    
    return [
        {
            "rule_id": rule_id,
            "advice": advice,
            "category": _categorize_violation_type(rule_id)
        }
        for rule_id, advice in advice_mapping.items()
    ]


def _categorize_violation_type(rule_id: str) -> str:
    """
    Categorize violation types for better organization in frontend displays.
    
    Args:
        rule_id: The violation rule identifier
        
    Returns:
        Category name for the violation type
    """
    if "MEAL_BREAK" in rule_id:
        return "Meal Breaks"
    elif "REST_BREAK" in rule_id:
        return "Rest Breaks"
    elif "DAILY_OVERTIME" in rule_id:
        return "Daily Overtime"
    elif "WEEKLY_OVERTIME" in rule_id:
        return "Weekly Overtime"
    elif "DUPLICATE" in rule_id:
        return "Employee Records"
    elif any(keyword in rule_id for keyword in ["SCHEDULING", "COVERAGE", "TRAINING"]):
        return "Management & Training"
    elif any(keyword in rule_id for keyword in ["COST", "PENALTY"]):
        return "Cost Management"
    else:
        return "General Compliance"


def _calculate_employee_hours_breakdown(punch_events: List[LLMParsedPunchEvent]) -> Dict[str, float]:
    """
    Calculate hours breakdown for a single employee.
    
    Args:
        punch_events: List of punch events for a single employee
        
    Returns:
        Dict with hours breakdown (total, regular, overtime, double_overtime)
    """
    from app.core.compliance_rules import parse_shifts_from_punch_events
    
    if not punch_events:
        return {
            'total_hours': 0.0,
            'regular_hours': 0.0,
            'overtime_hours': 0.0,
            'double_overtime_hours': 0.0
        }
    
    # Parse punch events into shifts
    shifts_by_employee = parse_shifts_from_punch_events(punch_events)
    
    total_hours = 0.0
    total_regular_hours = 0.0
    total_overtime_hours = 0.0
    total_double_overtime_hours = 0.0
    
    # Calculate hours for each shift
    for employee_id, shifts in shifts_by_employee.items():
        for shift in shifts:
            shift_hours = shift.total_hours_worked
            total_hours += shift_hours
            
            # Apply California overtime rules (8+ hours = OT, 12+ hours = double time)
            if shift_hours <= 8.0:
                # All regular time
                total_regular_hours += shift_hours
            elif shift_hours <= 12.0:
                # 8 hours regular + overtime
                total_regular_hours += 8.0
                total_overtime_hours += (shift_hours - 8.0)
            else:
                # 8 hours regular + 4 hours overtime + double time
                total_regular_hours += 8.0
                total_overtime_hours += 4.0
                total_double_overtime_hours += (shift_hours - 12.0)
    
    return {
        'total_hours': total_hours,
        'regular_hours': total_regular_hours,
        'overtime_hours': total_overtime_hours,
        'double_overtime_hours': total_double_overtime_hours
    }


def _get_generic_actionable_advice(rule_id: str) -> str:
    """
    Generate generic actionable advice for different violation types.
    
    Args:
        rule_id: The rule identifier from the violation
        
    Returns:
        Human-readable actionable advice string
    """
    # Use the public function to get advice and avoid code duplication
    return get_actionable_advice_for_violation(rule_id) 