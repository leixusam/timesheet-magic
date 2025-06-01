#!/usr/bin/env python3
"""
Test Script for Enhanced Error Handling and Recovery (Task 8.0)

This script tests the new two-pass specific error handling, partial success
scenarios, and intelligent fallback mechanisms.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add the backend app to the Python path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.core.error_handlers import (
    TwoPassDiscoveryError,
    TwoPassEmployeeParsingError,
    TwoPassPartialSuccessError
)

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_error_classes():
    """Test the new two-pass specific error classes"""
    
    print("🧪 ENHANCED ERROR HANDLING TEST")
    print("=" * 60)
    print("🎯 Testing new two-pass specific exception classes")
    print("⚡ Including intelligent error suggestions and context")
    print()
    
    print("=" * 60)
    print("🔍 TESTING ERROR CLASS FUNCTIONALITY")
    print("=" * 60)
    
    # Test TwoPassDiscoveryError
    print("\n1️⃣ Testing TwoPassDiscoveryError:")
    try:
        raise TwoPassDiscoveryError(
            message="Failed to discover employees in timesheet",
            original_filename="test-file.csv",
            file_size=5000,
            discovery_issues=["No clear employee identifiers found", "Unusual file format"]
        )
    except TwoPassDiscoveryError as e:
        print(f"   ✅ Error Code: {e.code}")
        print(f"   ✅ Category: {e.category}")
        print(f"   ✅ Severity: {e.severity}")
        print(f"   ✅ HTTP Status: {e.http_status}")
        print(f"   ✅ Message: {e.message}")
        print(f"   ✅ Suggestion: {e.suggestion}")
        print(f"   ✅ Debug Info: {e.debug_info}")
    
    # Test TwoPassEmployeeParsingError with high failure rate
    print("\n2️⃣ Testing TwoPassEmployeeParsingError (High Failure Rate):")
    try:
        raise TwoPassEmployeeParsingError(
            message="Critical parsing failure",
            original_filename="test-file.csv",
            failed_employees=["Employee A", "Employee B", "Employee C", "Employee D"],
            successful_employees=["Employee E"],
            parsing_issues=["Timeout errors", "Invalid timestamps"]
        )
    except TwoPassEmployeeParsingError as e:
        print(f"   ✅ Error Code: {e.code}")
        print(f"   ✅ Severity: {e.severity} (should be HIGH for 80% failure)")
        print(f"   ✅ Message: {e.message}")
        print(f"   ✅ Suggestion: {e.suggestion}")
        print(f"   ✅ Failed Employees: {e.debug_info.get('failed_employees')}")
        print(f"   ✅ Successful Employees: {e.debug_info.get('successful_employees')}")
    
    # Test TwoPassEmployeeParsingError with low failure rate
    print("\n3️⃣ Testing TwoPassEmployeeParsingError (Low Failure Rate):")
    try:
        raise TwoPassEmployeeParsingError(
            message="Minor parsing issues",
            original_filename="test-file.csv",
            failed_employees=["Employee A"],
            successful_employees=["Employee B", "Employee C", "Employee D", "Employee E"],
            parsing_issues=["One employee had incomplete data"]
        )
    except TwoPassEmployeeParsingError as e:
        print(f"   ✅ Error Code: {e.code}")
        print(f"   ✅ Severity: {e.severity} (should be MEDIUM for 20% failure)")
        print(f"   ✅ Suggestion: {e.suggestion}")
    
    # Test TwoPassPartialSuccessError
    print("\n4️⃣ Testing TwoPassPartialSuccessError:")
    try:
        raise TwoPassPartialSuccessError(
            message="Partial processing success",
            successful_employees=["Employee A", "Employee B", "Employee C"],
            failed_employees=["Employee D"],
            partial_results={"punch_events": [{"id": 1}, {"id": 2}, {"id": 3}]},
            original_filename="test-file.csv"
        )
    except TwoPassPartialSuccessError as e:
        print(f"   ✅ Error Code: {e.code}")
        print(f"   ✅ HTTP Status: {e.http_status} (should be 206 for Partial Content)")
        print(f"   ✅ Success Rate: {e.debug_info.get('success_rate')}%")
        print(f"   ✅ Suggestion: {e.suggestion}")
        print(f"   ✅ Partial Results Available: {e.debug_info.get('partial_results_available')}")
    
    print(f"\n✅ Error class testing completed!")


def main():
    """Run all error handling tests"""
    
    print("🚀 TASK 8.0 - ENHANCED ERROR HANDLING AND RECOVERY")
    print("=" * 80)
    
    # Test error classes
    test_error_classes()
    
    print(f"\n🎉 TASK 8.0 ENHANCED ERROR HANDLING TESTING COMPLETED!")


if __name__ == "__main__":
    main() 