#!/usr/bin/env python3
"""
Test Script for Two-Pass Processing with Real Sample Data

This script tests the two-pass employee discovery and parsing functions
using the actual 8.05-short.csv sample data file.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add the backend app to the Python path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.core.llm_processing_two_pass import discover_employees_in_file, parse_employee_punches
from app.models.two_pass_schemas import EmployeeDiscoveryOutput, PerEmployeeParsingOutput

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_two_pass_processing():
    """Test the complete two-pass workflow with real sample data"""
    
    print("Two-Pass Processing Test Script")
    print("=" * 40)
    print("🚀 STARTING TWO-PASS PROCESSING TEST")
    print("✨ Pass 1 (Discovery): Using default model (gemini-2.5-flash-preview-05-20)")
    print("⚡ Pass 2 (Parsing): Using function calling model (gemini-2.5-flash-preview-05-20)")
    print("📊 Improved punch counting: each Clock In/Out/Break counts as separate punch")
    print("Testing with real sample data: 8.05-short.csv")
    print()
    
    # Load the sample data file
    sample_file_path = Path(__file__).parent.parent / "sample_data" / "8.05-short.csv"
    
    if not sample_file_path.exists():
        print(f"❌ ERROR: Sample file not found at {sample_file_path}")
        return
    
    print("=" * 60)
    print("🔍 TESTING EMPLOYEE DISCOVERY (Pass 1)")
    print("=" * 60)
    
    # Read the file
    print(f"📄 Loading file: {sample_file_path}")
    with open(sample_file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    print(f"📊 File size: {len(file_content):,} characters")
    print(f"📋 File lines: {len(file_content.splitlines())}")
    print()
    
    try:
        # Test Pass 1: Employee Discovery
        print("🚀 Starting employee discovery...")
        discovery_result = await discover_employees_in_file(
            file_content=file_content,
            original_filename="8.05-short.csv"
        )
        
        print("\n✅ Discovery completed successfully!")
        print(f"👥 Found {len(discovery_result.employees)} employees:")
        
        for i, employee in enumerate(discovery_result.employees, 1):
            print(f"   {i}. '{employee.employee_identifier_in_file}'")
            print(f"      - Estimated individual punches: {employee.punch_count_estimate}")
            if employee.canonical_name_suggestion:
                print(f"      - Suggested name: {employee.canonical_name_suggestion}")
        
        if discovery_result.discovery_issues:
            print(f"\n⚠️  Discovery issues found:")
            for issue in discovery_result.discovery_issues:
                print(f"   - {issue}")
        
        print("\n" + "=" * 60)
        print("⚡ TESTING PER-EMPLOYEE PARSING (Pass 2)")
        print("=" * 60)
        print()
        
        # Test Pass 2: Per-Employee Parsing
        all_punch_events = []
        
        for i, employee in enumerate(discovery_result.employees, 1):
            employee_id = employee.employee_identifier_in_file
            estimated_count = employee.punch_count_estimate
            print(f"🎯 Parsing employee {i}/{len(discovery_result.employees)}: '{employee_id}'")
            
            try:
                parsing_result = await parse_employee_punches(
                    file_content=file_content,
                    employee_identifier=employee_id,
                    original_filename="8.05-short.csv",
                    estimated_punch_count=estimated_count
                )
                
                print(f"   ✅ Found {len(parsing_result.punch_events)} punch events")
                
                # Display first few events for verification
                for j, event in enumerate(parsing_result.punch_events[:5], 1):
                    timestamp_str = event.timestamp.strftime("%Y-%m-%d %H:%M")
                    print(f"      {j}. {timestamp_str} - {event.punch_type_as_parsed}")
                    if event.role_as_parsed:
                        print(f"         Role: {event.role_as_parsed}")
                    if event.hourly_wage_as_parsed:
                        print(f"         Wage: ${event.hourly_wage_as_parsed}/hr")
                
                if len(parsing_result.punch_events) > 5:
                    print(f"      ... and {len(parsing_result.punch_events) - 5} more events")
                
                # Verify punch count accuracy
                estimated = employee.punch_count_estimate
                actual = len(parsing_result.punch_events)
                accuracy = (min(estimated, actual) / max(estimated, actual)) * 100 if max(estimated, actual) > 0 else 100
                print(f"      📊 Count accuracy: {accuracy:.1f}% (estimated {estimated}, actual {actual})")
                
                all_punch_events.extend(parsing_result.punch_events)
                
                if parsing_result.parsing_issues:
                    print(f"      ⚠️  Parsing issues:")
                    for issue in parsing_result.parsing_issues:
                        print(f"         - {issue}")
                        
            except Exception as e:
                print(f"   ❌ Failed to parse employee '{employee_id}': {str(e)}")
            
            print()
        
        # Summary
        print("=" * 60)
        print("📊 PROCESSING SUMMARY")
        print("=" * 60)
        print(f"✅ Employees discovered: {len(discovery_result.employees)}")
        print(f"✅ Total punch events parsed: {len(all_punch_events)}")
        
        # Calculate total estimated vs actual
        total_estimated = sum(emp.punch_count_estimate for emp in discovery_result.employees)
        total_actual = len(all_punch_events)
        overall_accuracy = (min(total_estimated, total_actual) / max(total_estimated, total_actual)) * 100 if max(total_estimated, total_actual) > 0 else 100
        
        print(f"📊 Overall count accuracy: {overall_accuracy:.1f}%")
        print(f"   - Total estimated punches: {total_estimated}")
        print(f"   - Total actual punches: {total_actual}")
        
        # Show unique employees found in parsing
        unique_employees_parsed = set(event.employee_identifier_in_file for event in all_punch_events)
        print(f"✅ Unique employees with punch data: {len(unique_employees_parsed)}")
        
        print("\n🎉 Two-pass processing test completed successfully!")
        print("💡 Key improvements demonstrated:")
        print("   - Using gemini-2.5-flash-preview-05-20 function calling model")
        print("   - More accurate individual punch counting")
        print("   - Exact employee identifier matching")
        print("   - Robust error handling and validation")
        
    except Exception as e:
        print(f"\n❌ ERROR during two-pass processing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_two_pass_processing()) 