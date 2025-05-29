#!/usr/bin/env python3
"""
Integration tests for the complete timesheet analysis pipeline.

This module provides comprehensive end-to-end testing for the analysis endpoint,
including parsing, compliance checking, and report generation. It can be used
with different input files and configurations for thorough testing.

Usage:
    python -m app.tests.test_integration_analysis
    python -m app.tests.test_integration_analysis --file custom_file.csv
    python -m app.tests.test_integration_analysis --detailed
"""

import asyncio
import json
import sys
import os
import argparse
from io import BytesIO
from typing import Optional, Dict, Any

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app.api.endpoints.analysis import analyze_timesheet
from app.models.schemas import FinalAnalysisReport
from fastapi import UploadFile


class AnalysisIntegrationTester:
    """
    Comprehensive integration tester for the timesheet analysis pipeline.
    
    This class provides methods to test different aspects of the analysis
    system with various input formats and configurations.
    """
    
    def __init__(self, verbose: bool = True, detailed: bool = False):
        """
        Initialize the integration tester.
        
        Args:
            verbose: Whether to print detailed output during testing
            detailed: Whether to show detailed violation and employee data
        """
        self.verbose = verbose
        self.detailed = detailed
        self.test_results = []
    
    def get_default_lead_data(self, store_name: str = "Test Store") -> Dict[str, str]:
        """Get default lead data for testing."""
        return {
            "manager_name": "Test Manager",
            "manager_email": "test@restaurant.com", 
            "manager_phone": "555-123-4567",
            "store_name": store_name,
            "store_address": "123 Main St, Test City, CA 90210"
        }
    
    async def test_csv_file(self, 
                           file_path: str, 
                           lead_data: Optional[Dict[str, str]] = None,
                           expected_employees: Optional[int] = None) -> FinalAnalysisReport:
        """
        Test analysis with a CSV timesheet file.
        
        Args:
            file_path: Path to the CSV file to test
            lead_data: Optional lead data (uses default if not provided)
            expected_employees: Expected number of employees (for validation)
            
        Returns:
            FinalAnalysisReport object with analysis results
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Test file not found: {file_path}")
        
        # Use default lead data if not provided
        if lead_data is None:
            # Extract store name from file path if possible
            filename = os.path.basename(file_path)
            store_name = filename.replace('.csv', '').replace('-', ' - ')
            lead_data = self.get_default_lead_data(store_name)
        
        # Read the CSV file
        with open(file_path, "rb") as f:
            csv_bytes = f.read()
        
        # Create UploadFile object
        csv_file = UploadFile(
            file=BytesIO(csv_bytes),
            filename=os.path.basename(file_path),
            headers={"content-type": "text/csv"}
        )
        
        if self.verbose:
            print(f"🚀 Testing analysis with: {os.path.basename(file_path)}")
            print(f"📄 File size: {len(csv_bytes)} bytes")
            print(f"📍 Store: {lead_data['store_name']}")
            print("=" * 80)
        
        # Run the analysis
        result = await analyze_timesheet(
            lead_data_json=json.dumps(lead_data),
            file=csv_file
        )
        
        # Validate results if expected values provided
        if expected_employees and result.employee_summaries:
            actual_employees = len(result.employee_summaries)
            if actual_employees != expected_employees:
                print(f"⚠️  Expected {expected_employees} employees, found {actual_employees}")
        
        # Display results
        if self.verbose:
            self._display_results(result)
        
        # Store test result
        test_result = {
            "file": file_path,
            "status": result.status,
            "employees": len(result.employee_summaries) if result.employee_summaries else 0,
            "violations": len(result.all_identified_violations) if result.all_identified_violations else 0,
            "total_hours": result.kpis.total_scheduled_labor_hours if result.kpis else 0
        }
        self.test_results.append(test_result)
        
        return result
    
    def _display_results(self, result: FinalAnalysisReport):
        """Display comprehensive analysis results."""
        print("✅ Analysis completed!")
        print("=" * 80)
        
        # Request info
        print(f"📋 REQUEST INFO:")
        print(f"   Request ID: {result.request_id}")
        print(f"   Status: {result.status}")
        print(f"   File: {result.original_filename}")
        if result.status_message:
            print(f"   Message: {result.status_message}")
        
        # KPIs
        if result.kpis:
            print(f"\n📊 KPI SUMMARY:")
            kpis = result.kpis
            print(f"   Total Labor Hours: {kpis.total_scheduled_labor_hours:.1f}")
            print(f"   Regular Hours: {kpis.total_regular_hours:.1f}")
            print(f"   Overtime Hours: {kpis.total_overtime_hours:.1f}")
            print(f"   Double OT Hours: {kpis.total_double_overtime_hours:.1f}")
            print(f"   Estimated OT Cost: ${kpis.estimated_overtime_cost:.2f}")
            print(f"   Estimated Double OT Cost: ${kpis.estimated_double_overtime_cost:.2f}")
            print(f"   Risk Assessment: {kpis.compliance_risk_assessment}")
        
        # Violations summary
        if result.all_identified_violations:
            print(f"\n⚠️  COMPLIANCE VIOLATIONS ({len(result.all_identified_violations)} found):")
            
            # Count violations by type
            violation_counts = {}
            for violation in result.all_identified_violations:
                rule_type = violation.rule_id.split('_')[0] if '_' in violation.rule_id else 'OTHER'
                violation_counts[rule_type] = violation_counts.get(rule_type, 0) + 1
            
            for rule_type, count in sorted(violation_counts.items()):
                print(f"   • {rule_type.title()}: {count} violations")
            
            # Show detailed violations if requested
            if self.detailed:
                print(f"\n   📋 DETAILED VIOLATIONS (first 10):")
                for i, violation in enumerate(result.all_identified_violations[:10], 1):
                    print(f"   {i}. {violation.rule_description}")
                    print(f"      Employee: {violation.employee_identifier}")
                    print(f"      Date: {violation.date_of_violation}")
                    print(f"      Details: {violation.specific_details}")
                    if violation.suggested_action_generic:
                        print(f"      Action: {violation.suggested_action_generic[:100]}...")
                    print()
                if len(result.all_identified_violations) > 10:
                    print(f"   ... and {len(result.all_identified_violations) - 10} more violations")
        
        # Employee summaries
        if result.employee_summaries:
            print(f"\n👥 EMPLOYEE SUMMARIES ({len(result.employee_summaries)} employees):")
            for emp in result.employee_summaries:
                print(f"   • {emp.employee_identifier}")
                if self.detailed:
                    print(f"     Roles: {', '.join(emp.roles_observed)}")
                    print(f"     Departments: {', '.join(emp.departments_observed)}")
                print(f"     Hours: {emp.total_hours_worked:.1f} total " +
                      f"({emp.regular_hours:.1f} reg, {emp.overtime_hours:.1f} OT, {emp.double_overtime_hours:.1f} 2xOT)")
                print(f"     Violations: {len(emp.violations_for_employee)}")
                print()
        
        # Heatmap data
        if result.staffing_density_heatmap:
            print(f"\n🔥 STAFFING HEATMAP ({len(result.staffing_density_heatmap)} data points):")
            if self.detailed:
                # Show sample of heatmap data
                for i, point in enumerate(result.staffing_density_heatmap[:5]):
                    print(f"   {point.hour_timestamp.strftime('%Y-%m-%d %H:00')}: {point.employee_count} employees")
                if len(result.staffing_density_heatmap) > 5:
                    print(f"   ... and {len(result.staffing_density_heatmap) - 5} more time points")
            else:
                # Just show range
                first_point = result.staffing_density_heatmap[0]
                last_point = result.staffing_density_heatmap[-1]
                print(f"   Time range: {first_point.hour_timestamp.strftime('%Y-%m-%d %H:00')} to " +
                      f"{last_point.hour_timestamp.strftime('%Y-%m-%d %H:00')}")
        
        # Warnings
        if result.duplicate_name_warnings:
            print(f"\n🔍 DUPLICATE NAME WARNINGS:")
            for warning in result.duplicate_name_warnings:
                print(f"   ⚠️  {warning}")
        
        if result.parsing_issues_summary:
            print(f"\n📝 PARSING ISSUES:")
            for issue in result.parsing_issues_summary:
                print(f"   ⚠️  {issue}")
        
        # Overall summary
        if result.overall_report_summary_text:
            print(f"\n📝 OVERALL SUMMARY:")
            print(f"   {result.overall_report_summary_text}")
        
        print("\n" + "=" * 80)
    
    def print_test_summary(self):
        """Print a summary of all test results."""
        if not self.test_results:
            print("No tests run.")
            return
        
        print(f"\n🎯 TEST SUMMARY ({len(self.test_results)} tests run):")
        print("=" * 80)
        
        total_employees = sum(t["employees"] for t in self.test_results)
        total_violations = sum(t["violations"] for t in self.test_results)
        total_hours = sum(t["total_hours"] for t in self.test_results)
        
        for test in self.test_results:
            filename = os.path.basename(test["file"])
            status_emoji = "✅" if test["status"] == "success" else "⚠️" if "warning" in test["status"] else "❌"
            print(f"   {status_emoji} {filename}: {test['employees']} employees, " +
                  f"{test['violations']} violations, {test['total_hours']:.1f} hours")
        
        print(f"\n   📊 TOTALS: {total_employees} employees, {total_violations} violations, {total_hours:.1f} hours")
        print("=" * 80)


async def run_default_tests(detailed: bool = False):
    """Run the default test suite with the available test files."""
    tester = AnalysisIntegrationTester(verbose=True, detailed=detailed)
    
    # Test with the 8.05-short.csv file
    csv_path = "app/tests/core/8.05-short.csv"
    
    try:
        print("🧪 Running Integration Test Suite")
        print("=" * 80)
        
        if os.path.exists(csv_path):
            await tester.test_csv_file(
                file_path=csv_path,
                lead_data=tester.get_default_lead_data("LA - Carencro - NE"),
                expected_employees=4  # Based on the CSV data
            )
        else:
            print(f"⚠️  Test file not found: {csv_path}")
            print("Please ensure test data files are available.")
        
        # Add more test files here as they become available
        # await tester.test_csv_file("app/tests/core/another_test.csv")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        tester.print_test_summary()


async def run_custom_test(file_path: str, detailed: bool = False):
    """Run a test with a custom file."""
    tester = AnalysisIntegrationTester(verbose=True, detailed=detailed)
    
    try:
        await tester.test_csv_file(file_path)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        tester.print_test_summary()


def main():
    """Main entry point for running integration tests."""
    parser = argparse.ArgumentParser(description="Run integration tests for timesheet analysis")
    parser.add_argument("--file", help="Path to a specific test file")
    parser.add_argument("--detailed", action="store_true", help="Show detailed output including violations and employee data")
    
    args = parser.parse_args()
    
    if args.file:
        asyncio.run(run_custom_test(args.file, args.detailed))
    else:
        asyncio.run(run_default_tests(args.detailed))


if __name__ == "__main__":
    main() 