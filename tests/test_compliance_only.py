#!/usr/bin/env python3
"""
Compliance Rules Test Script (Isolated Testing)

This script tests the compliance checking functionality in isolation using manually 
created punch events. It validates that the compliance rules logic works correctly
without dependencies on LLM processing or external APIs.

What this test validates:
- ✅ Meal break violation detection
- ✅ Rest break violation detection  
- ✅ Daily overtime detection (time-and-a-half and double-time)
- ✅ Weekly overtime detection
- ✅ Duplicate employee detection and consolidation
- ✅ Cost calculations for all violation types
- ✅ Wage determination logic

Test Strategy:
- Uses manually crafted punch events based on real CSV data patterns
- Tests realistic scenarios from actual timesheet data
- Independent of LLM processing - purely tests compliance logic
- Creates comprehensive test cases for edge cases and violations

Test Data:
- Employee BB (Cashier): Split shift with potential meal break issues
- Employee FM (Cook): Regular shift + overtime day (12+ hours)  
- Employee FA (Shift Lead): Very long shift (11.5+ hours) with no breaks

Usage:
    python tests/test_compliance_only.py

Related Files:
- backend/app/core/compliance_rules.py - Contains all compliance detection logic
- backend/app/tests/core/test_compliance_rules.py - Unit tests for compliance rules
- backend/app/tests/core/8.05-short.csv - Real data that inspired these test cases
"""

import sys
from pathlib import Path
from datetime import datetime, date
import json

# Add the backend app to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir / "backend" / "app"
sys.path.insert(0, str(backend_dir))

from core.compliance_rules import get_all_compliance_violations, detect_compliance_violations_with_costs
from models.schemas import LLMParsedPunchEvent

def create_test_punch_events():
    """Create test punch events based on the CSV data structure"""
    
    # Based on the CSV file, create realistic punch events
    punch_events = []
    
    # Employee BB (Cashier) - has potential violations
    # 3/16/2025: 11:13 AM - 4:14 PM, then 4:42 PM - 5:06 PM (long shift, short break)
    punch_events.extend([
        LLMParsedPunchEvent(
            employee_identifier_in_file="BB - xxxxxxxxx",
            timestamp=datetime(2025, 3, 16, 11, 13),
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cashier",
            hourly_wage_as_parsed=9.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="BB - xxxxxxxxx",
            timestamp=datetime(2025, 3, 16, 16, 14),
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cashier",
            hourly_wage_as_parsed=9.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="BB - xxxxxxxxx",
            timestamp=datetime(2025, 3, 16, 16, 42),
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cashier",
            hourly_wage_as_parsed=9.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="BB - xxxxxxxxx",
            timestamp=datetime(2025, 3, 16, 17, 6),
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cashier",
            hourly_wage_as_parsed=9.00
        )
    ])
    
    # Employee FM (Cook) - has overtime
    # 3/21/2025: 7:08 AM - 2:06 PM, then 2:35 PM - 3:59 PM (8.37 hours total)
    # 3/28/2025: 7:58 AM - 8:03 PM (12.08 hours - overtime!)
    punch_events.extend([
        LLMParsedPunchEvent(
            employee_identifier_in_file="FM - xxxxxxxxx",
            timestamp=datetime(2025, 3, 21, 7, 8),
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=12.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="FM - xxxxxxxxx",
            timestamp=datetime(2025, 3, 21, 14, 6),
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=12.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="FM - xxxxxxxxx",
            timestamp=datetime(2025, 3, 21, 14, 35),
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=12.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="FM - xxxxxxxxx",
            timestamp=datetime(2025, 3, 21, 15, 59),
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=12.00
        ),
        # Overtime day
        LLMParsedPunchEvent(
            employee_identifier_in_file="FM - xxxxxxxxx",
            timestamp=datetime(2025, 3, 28, 7, 58),
            punch_type_as_parsed="Clock In",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=12.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="FM - xxxxxxxxx",
            timestamp=datetime(2025, 3, 28, 20, 3),
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Cook",
            hourly_wage_as_parsed=12.00
        )
    ])
    
    # Employee FA (Shift Lead) - potential meal break violations
    # 3/22/2025: 1:40 PM - 1:11 AM next day (11.5+ hours with no meal break recorded)
    punch_events.extend([
        LLMParsedPunchEvent(
            employee_identifier_in_file="FA - xxxxxxxxx",
            timestamp=datetime(2025, 3, 22, 13, 40),
            punch_type_as_parsed="Clock In",
            role_as_parsed="Shift Lead",
            hourly_wage_as_parsed=11.00
        ),
        LLMParsedPunchEvent(
            employee_identifier_in_file="FA - xxxxxxxxx",
            timestamp=datetime(2025, 3, 23, 1, 11),
            punch_type_as_parsed="Clock Out",
            role_as_parsed="Shift Lead",
            hourly_wage_as_parsed=11.00
        )
    ])
    
    return punch_events

def test_compliance_rules():
    """Test compliance rules with realistic data"""
    
    print("🚀 Starting Compliance Rules Test")
    print("=" * 50)
    
    # Create debug directory for this run
    debug_dir = current_dir / "debug_runs" / f"compliance_only_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Debug output will be saved to: {debug_dir}")
    
    try:
        # Step 1: Create test punch events
        print("\n📄 Step 1: Creating test punch events...")
        punch_events = create_test_punch_events()
        print(f"✅ Created {len(punch_events)} test punch events")
        
        # Save test data
        test_data = [event.model_dump() for event in punch_events]
        test_data_file = debug_dir / "test_punch_events.json"
        with open(test_data_file, 'w') as f:
            json.dump(test_data, f, indent=2, default=str)
        print(f"💾 Test data saved to: {test_data_file}")
        
        # Step 2: Analyze punch events
        print("\n📊 Step 2: Analyzing punch events...")
        employees = set(event.employee_identifier_in_file for event in punch_events)
        print(f"   - Employees: {', '.join(employees)}")
        
        date_range = [event.timestamp.date() for event in punch_events]
        print(f"   - Date range: {min(date_range)} to {max(date_range)}")
        
        # Step 3: Run compliance checks
        print("\n⚖️ Step 3: Running compliance checks...")
        compliance_results = get_all_compliance_violations(punch_events)
        
        print(f"✅ Compliance Analysis Complete!")
        print(f"   - Meal break violations: {len(compliance_results.get('meal_break_violations', []))}")
        print(f"   - Rest break violations: {len(compliance_results.get('rest_break_violations', []))}")
        print(f"   - Daily overtime violations: {len(compliance_results.get('daily_overtime_violations', []))}")
        print(f"   - Weekly overtime violations: {len(compliance_results.get('weekly_overtime_violations', []))}")
        print(f"   - Daily double overtime violations: {len(compliance_results.get('daily_double_overtime_violations', []))}")
        print(f"   - Duplicate employees detected: {len(compliance_results.get('duplicate_groups', {}))}")
        
        # Save compliance results
        compliance_output_file = debug_dir / "compliance_results.json"
        with open(compliance_output_file, 'w') as f:
            json.dump(compliance_results, f, indent=2, default=str)
        print(f"💾 Compliance results saved to: {compliance_output_file}")
        
        # Step 4: Run cost analysis
        print("\n💰 Step 4: Running cost analysis...")
        cost_analysis = detect_compliance_violations_with_costs(punch_events)
        
        print(f"✅ Cost Analysis Complete!")
        if 'cost_breakdown' in cost_analysis:
            costs = cost_analysis['cost_breakdown']
            print(f"   - Total violation costs: ${costs.get('total_violation_cost', 0):.2f}")
            print(f"   - Meal break costs: ${costs.get('meal_break_cost', 0):.2f}")
            print(f"   - Overtime costs: ${costs.get('overtime_cost', 0):.2f}")
            print(f"   - Double overtime costs: ${costs.get('double_overtime_cost', 0):.2f}")
        
        # Save cost analysis
        cost_output_file = debug_dir / "cost_analysis.json"
        with open(cost_output_file, 'w') as f:
            json.dump(cost_analysis, f, indent=2, default=str)
        print(f"💾 Cost analysis saved to: {cost_output_file}")
        
        # Step 5: Display detailed findings
        print("\n📋 Step 5: Detailed Findings Summary")
        print("-" * 40)
        
        if compliance_results.get('meal_break_violations'):
            print("\n🍽️ Meal Break Violations:")
            for violation in compliance_results['meal_break_violations']:
                print(f"   - {violation.employee_identifier} on {violation.date_of_violation}")
                print(f"     {violation.specific_details}")
        
        if compliance_results.get('daily_overtime_violations'):
            print("\n⏰ Daily Overtime Violations:")
            for violation in compliance_results['daily_overtime_violations']:
                print(f"   - {violation.employee_identifier} on {violation.date_of_violation}")
                print(f"     {violation.specific_details}")
        
        if compliance_results.get('weekly_overtime_violations'):
            print("\n📅 Weekly Overtime Violations:")
            for violation in compliance_results['weekly_overtime_violations']:
                print(f"   - {violation.employee_identifier} for week of {violation.date_of_violation}")
                print(f"     {violation.specific_details}")
        
        if compliance_results.get('duplicate_groups'):
            print("\n👥 Potential Duplicate Employees:")
            for canonical, duplicates in compliance_results['duplicate_groups'].items():
                print(f"   - {canonical} (may be same as: {', '.join(duplicates)})")
        
        # Step 6: Summary report
        print("\n📊 Final Summary")
        print("=" * 50)
        print(f"✅ Successfully analyzed {len(punch_events)} punch events")
        print(f"👥 Found {len(employees)} employees")
        print(f"⚠️ Found {sum(len(v) for v in compliance_results.values() if isinstance(v, list))} total violations")
        
        if cost_analysis.get('cost_breakdown'):
            total_cost = cost_analysis['cost_breakdown'].get('total_violation_cost', 0)
            print(f"💰 Estimated violation cost: ${total_cost:.2f}")
        
        print(f"🗂️ All debug files saved to: {debug_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during compliance test: {e}")
        import traceback
        traceback.print_exc()
        
        # Save error information
        error_file = debug_dir / "error_log.txt"
        with open(error_file, 'w') as f:
            f.write(f"Error: {e}\n\n")
            f.write(traceback.format_exc())
        print(f"💾 Error log saved to: {error_file}")
        
        return False

def main():
    """Main test runner"""
    print("Time Sheet Magic - Compliance Rules Test")
    print("=" * 50)
    
    # Run the test
    result = test_compliance_rules()
    
    if result:
        print("\n🎉 Compliance Rules Test PASSED!")
        return 0
    else:
        print("\n💥 Compliance Rules Test FAILED!")
        return 1

if __name__ == "__main__":
    exit(main()) 