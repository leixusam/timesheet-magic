#!/usr/bin/env python3
"""
End-to-End Test for Backend Processing Pipeline
Tests the complete flow from file upload through LLM processing to compliance checking.
"""

import asyncio
import os
import sys
from pathlib import Path
import json
from datetime import datetime

# Add the backend app to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir / "backend" / "app"
sys.path.insert(0, str(backend_dir))

from core.llm_processing import parse_file_to_structured_data
from core.compliance_rules import get_all_compliance_violations, detect_compliance_violations_with_costs
from models.schemas import LLMProcessingOutput

async def test_csv_end_to_end():
    """Test the complete pipeline with the 8.05-short.csv file"""
    
    print("🚀 Starting End-to-End Backend Test")
    print("=" * 50)
    
    # Path to test file
    csv_file_path = backend_dir / "tests" / "core" / "8.05-short.csv"
    
    if not csv_file_path.exists():
        print(f"❌ Test file not found: {csv_file_path}")
        return
    
    # Create debug directory for this run
    debug_dir = current_dir / "debug_runs" / f"end_to_end_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Debug output will be saved to: {debug_dir}")
    
    try:
        # Step 1: Load the CSV file
        print("\n📄 Step 1: Loading CSV file...")
        with open(csv_file_path, 'rb') as f:
            file_bytes = f.read()
        
        print(f"✅ Loaded {len(file_bytes)} bytes from {csv_file_path.name}")
        
        # Step 2: Process through LLM
        print("\n🤖 Step 2: Processing through LLM...")
        llm_result = await parse_file_to_structured_data(
            file_bytes=file_bytes,
            mime_type="text/csv",
            original_filename=csv_file_path.name,
            debug_dir=str(debug_dir)
        )
        
        print(f"✅ LLM Processing Complete!")
        print(f"   - Found {len(llm_result.punch_events)} punch events")
        print(f"   - Parsing issues: {len(llm_result.parsing_issues)}")
        
        # Save LLM results
        llm_output_file = debug_dir / "llm_output.json"
        with open(llm_output_file, 'w') as f:
            json.dump(llm_result.model_dump(), f, indent=2, default=str)
        print(f"💾 LLM output saved to: {llm_output_file}")
        
        # Step 3: Analyze punch events
        print("\n📊 Step 3: Analyzing punch events...")
        if llm_result.punch_events:
            print("Sample punch events:")
            for i, event in enumerate(llm_result.punch_events[:3]):
                print(f"   {i+1}. {event.employee_identifier_in_file} - {event.punch_type_as_parsed} at {event.timestamp}")
            if len(llm_result.punch_events) > 3:
                print(f"   ... and {len(llm_result.punch_events) - 3} more events")
        
        # Step 4: Run compliance checks
        print("\n⚖️ Step 4: Running compliance checks...")
        compliance_results = get_all_compliance_violations(llm_result.punch_events)
        
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
        
        # Step 5: Run comprehensive analysis with costs
        print("\n💰 Step 5: Running cost analysis...")
        cost_analysis = detect_compliance_violations_with_costs(llm_result.punch_events)
        
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
        
        # Step 6: Display detailed findings
        print("\n📋 Step 6: Detailed Findings Summary")
        print("-" * 40)
        
        if compliance_results.get('meal_break_violations'):
            print("\n🍽️ Meal Break Violations:")
            for violation in compliance_results['meal_break_violations'][:3]:
                print(f"   - {violation.employee_identifier} on {violation.date_of_violation}")
                print(f"     {violation.specific_details}")
        
        if compliance_results.get('daily_overtime_violations'):
            print("\n⏰ Daily Overtime Violations:")
            for violation in compliance_results['daily_overtime_violations'][:3]:
                print(f"   - {violation.employee_identifier} on {violation.date_of_violation}")
                print(f"     {violation.specific_details}")
        
        if compliance_results.get('duplicate_groups'):
            print("\n👥 Potential Duplicate Employees:")
            for canonical, duplicates in compliance_results['duplicate_groups'].items():
                print(f"   - {canonical} (may be same as: {', '.join(duplicates)})")
        
        # Step 7: Summary report
        print("\n📊 Final Summary")
        print("=" * 50)
        print(f"✅ Successfully processed {csv_file_path.name}")
        print(f"📈 Extracted {len(llm_result.punch_events)} punch events")
        print(f"⚠️ Found {sum(len(v) for v in compliance_results.values() if isinstance(v, list))} total violations")
        
        if cost_analysis.get('cost_breakdown'):
            total_cost = cost_analysis['cost_breakdown'].get('total_violation_cost', 0)
            print(f"💰 Estimated violation cost: ${total_cost:.2f}")
        
        print(f"🗂️ All debug files saved to: {debug_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during end-to-end test: {e}")
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
    print("Time Sheet Magic - Backend End-to-End Test")
    print("=" * 50)
    
    # Verify environment
    print("🔧 Checking environment...")
    
    required_env_vars = ['OPENAI_API_KEY', 'GOOGLE_API_KEY']
    missing_vars = []
    
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️ Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("   The test may fail if these are required for LLM processing.")
    else:
        print("✅ Environment variables found")
    
    # Run the test
    result = asyncio.run(test_csv_end_to_end())
    
    if result:
        print("\n🎉 End-to-End Test PASSED!")
        return 0
    else:
        print("\n💥 End-to-End Test FAILED!")
        return 1

if __name__ == "__main__":
    exit(main()) 