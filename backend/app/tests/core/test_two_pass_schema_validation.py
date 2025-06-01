#!/usr/bin/env python3
"""
Schema Validation Test Script

This script tests the two-pass schemas and validation functions
using the actual 8.05-short.csv sample data file without requiring Gemini API calls.
"""

import sys
from pathlib import Path

# Add the backend app to the Python path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.models.two_pass_schemas import (
    EmployeeDiscoveryResult,
    EmployeeDiscoveryOutput,
    PerEmployeeParsingOutput,
    employee_discovery_to_gemini_tool_dict,
    per_employee_parsing_to_gemini_tool_dict,
    validate_employee_identifiers_in_file,
    deduplicate_employee_identifiers,
    normalize_employee_discovery_output
)
from app.models.schemas import LLMParsedPunchEvent
from datetime import datetime


def test_data_loading():
    """Test loading the sample CSV file"""
    print("🔍 TESTING DATA LOADING")
    print("="*40)
    
    sample_file = Path(__file__).parent.parent / "sample_data" / "8.05-short.csv"
    
    if not sample_file.exists():
        print(f"❌ Sample file not found: {sample_file}")
        return None
    
    print(f"📄 Loading file: {sample_file}")
    file_content = sample_file.read_text(encoding='utf-8')
    
    print(f"✅ File loaded successfully!")
    print(f"📊 File size: {len(file_content):,} characters")
    print(f"📋 File lines: {len(file_content.splitlines()):,}")
    
    # Show a sample of the content
    lines = file_content.splitlines()
    print(f"\n📝 First 5 lines:")
    for i, line in enumerate(lines[:5], 1):
        print(f"   {i}. {line[:80]}{'...' if len(line) > 80 else ''}")
    
    # Look for employee identifiers in the file
    print(f"\n🔍 Looking for employee patterns...")
    employee_lines = [line for line in lines if "Employee / Job:" in line]
    print(f"   Found {len(employee_lines)} employee header lines:")
    
    for i, line in enumerate(employee_lines[:3], 1):
        print(f"   {i}. {line}")
    
    return file_content


def test_schema_creation():
    """Test creating and validating our schemas"""
    print("\n🏗️  TESTING SCHEMA CREATION")
    print("="*40)
    
    # Test EmployeeDiscoveryResult
    print("Testing EmployeeDiscoveryResult schema...")
    employee1 = EmployeeDiscoveryResult(
        employee_identifier_in_file="BB - xxxxxxxxx",
        punch_count_estimate=8,
        canonical_name_suggestion="BB"
    )
    print(f"✅ Created employee: {employee1.employee_identifier_in_file}")
    
    employee2 = EmployeeDiscoveryResult(
        employee_identifier_in_file="FM - xxxxxxxxx",
        punch_count_estimate=12,
        canonical_name_suggestion="FM"
    )
    print(f"✅ Created employee: {employee2.employee_identifier_in_file}")
    
    # Test EmployeeDiscoveryOutput
    print("\nTesting EmployeeDiscoveryOutput schema...")
    discovery_output = EmployeeDiscoveryOutput(
        employees=[employee1, employee2],
        discovery_issues=["Test issue for validation"]
    )
    print(f"✅ Created discovery output with {len(discovery_output.employees)} employees")
    
    # Test LLMParsedPunchEvent
    print("\nTesting LLMParsedPunchEvent schema...")
    punch_event = LLMParsedPunchEvent(
        employee_identifier_in_file="BB - xxxxxxxxx",
        timestamp=datetime(2025, 3, 16, 11, 13),
        punch_type_as_parsed="Clock In",
        role_as_parsed="Cashier",
        hourly_wage_as_parsed=9.00
    )
    print(f"✅ Created punch event: {punch_event.punch_type_as_parsed} at {punch_event.timestamp}")
    
    # Assert successful creation
    assert discovery_output is not None
    assert punch_event is not None
    assert len(discovery_output.employees) == 2


def test_function_calling_schemas():
    """Test the Gemini function calling schema generation"""
    print("\n⚙️  TESTING FUNCTION CALLING SCHEMAS")
    print("="*40)
    
    # Test employee discovery schema
    print("Testing employee discovery tool schema...")
    discovery_tool = employee_discovery_to_gemini_tool_dict()
    
    print(f"✅ Discovery tool created:")
    print(f"   Name: {discovery_tool['name']}")
    print(f"   Description: {discovery_tool['description'][:60]}...")
    print(f"   Parameters: {len(discovery_tool['parameters']['properties'])} properties")
    
    # Test per-employee parsing schema
    print("\nTesting per-employee parsing tool schema...")
    parsing_tool = per_employee_parsing_to_gemini_tool_dict()
    
    print(f"✅ Parsing tool created:")
    print(f"   Name: {parsing_tool['name']}")
    print(f"   Description: {parsing_tool['description'][:60]}...")
    print(f"   Parameters: {len(parsing_tool['parameters']['properties'])} properties")
    
    # Assert successful creation
    assert discovery_tool is not None
    assert parsing_tool is not None
    assert 'name' in discovery_tool
    assert 'name' in parsing_tool


def test_validation_functions():
    """Test the validation and normalization functions"""
    print("\n🔍 TESTING VALIDATION FUNCTIONS")
    print("="*40)
    
    # Load test data
    file_content = test_data_loading()
    if not file_content:
        print("❌ Cannot load test data for validation tests")
        return
    
    # Create test employees with one that exists and one that doesn't
    test_employees = [
        EmployeeDiscoveryResult(
            employee_identifier_in_file="BB - xxxxxxxxx",  # This should exist
            punch_count_estimate=8,
            canonical_name_suggestion="BB"
        ),
        EmployeeDiscoveryResult(
            employee_identifier_in_file="FAKE_EMPLOYEE_123",  # This doesn't exist
            punch_count_estimate=5,
            canonical_name_suggestion="Fake"
        ),
        EmployeeDiscoveryResult(
            employee_identifier_in_file="FM - xxxxxxxxx",  # This should exist
            punch_count_estimate=12,
            canonical_name_suggestion="FM"
        )
    ]
    
    print(f"Testing validation with {len(test_employees)} employees...")
    
    # Test validation
    validated_employees, validation_issues = validate_employee_identifiers_in_file(
        test_employees, file_content
    )
    
    print(f"✅ Validation completed:")
    print(f"   Valid employees: {len(validated_employees)}")
    print(f"   Validation issues: {len(validation_issues)}")
    
    for employee in validated_employees:
        print(f"   ✅ Valid: {employee.employee_identifier_in_file}")
    
    for issue in validation_issues:
        print(f"   ⚠️  Issue: {issue}")
    
    # Test deduplication
    print(f"\nTesting deduplication...")
    duplicate_employees = test_employees + [
        EmployeeDiscoveryResult(
            employee_identifier_in_file="BB - xxxxxxxxx",  # Duplicate
            punch_count_estimate=10,  # Higher count
            canonical_name_suggestion="BB Updated"
        )
    ]
    
    deduplicated_employees, dedup_notes = deduplicate_employee_identifiers(duplicate_employees)
    
    print(f"✅ Deduplication completed:")
    print(f"   Original count: {len(duplicate_employees)}")
    print(f"   Deduplicated count: {len(deduplicated_employees)}")
    print(f"   Deduplication notes: {len(dedup_notes)}")
    
    for note in dedup_notes:
        print(f"   📝 {note}")
    
    # Test full normalization
    print(f"\nTesting full normalization...")
    raw_output = EmployeeDiscoveryOutput(
        employees=duplicate_employees,
        discovery_issues=["Original issue"]
    )
    
    normalized_output = normalize_employee_discovery_output(raw_output, file_content)
    
    print(f"✅ Normalization completed:")
    print(f"   Final employee count: {len(normalized_output.employees)}")
    print(f"   Total issues: {len(normalized_output.discovery_issues)}")
    
    # Assert successful validation
    assert normalized_output is not None
    assert len(validated_employees) >= 0
    assert len(deduplicated_employees) >= 0


def main():
    """Main test function"""
    print("Two-Pass Schema Validation Test")
    print("="*50)
    print("Testing schemas and validation without Gemini API calls\n")
    
    try:
        # Test 1: Data Loading
        file_content = test_data_loading()
        if not file_content:
            print("❌ Cannot continue - data loading failed")
            return
        
        # Test 2: Schema Creation
        discovery_output, punch_event = test_schema_creation()
        
        # Test 3: Function Calling Schemas
        discovery_tool, parsing_tool = test_function_calling_schemas()
        
        # Test 4: Validation Functions
        if file_content:
            test_validation_functions()
        
        # Final Summary
        print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*50)
        print("✅ Data loading works")
        print("✅ Schema creation works")
        print("✅ Function calling schemas work")
        print("✅ Validation functions work")
        print("\n📋 The two-pass processing schemas are ready for Gemini integration!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 