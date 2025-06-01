#!/usr/bin/env python3
"""
Mock Two-Pass Processing Test

This script simulates the complete two-pass workflow with realistic mock responses
based on the actual patterns found in 8.05-short.csv.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock
from datetime import datetime

# Add the backend app to the Python path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.core.llm_processing_two_pass import discover_employees_in_file, parse_employee_punches
from app.models.two_pass_schemas import EmployeeDiscoveryOutput, PerEmployeeParsingOutput
from app.models.schemas import LLMParsedPunchEvent


def create_realistic_discovery_response():
    """Create a realistic discovery response based on the actual CSV file"""
    return {
        "employees": [
            {
                "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                "punch_count_estimate": 16,  # Based on the actual data we saw
                "canonical_name_suggestion": "BB (Cashier)"
            },
            {
                "employee_identifier_in_file": "BC - xxxxxxxxx / 664690 / Cook", 
                "punch_count_estimate": 12,
                "canonical_name_suggestion": "BC (Cook)"
            },
            {
                "employee_identifier_in_file": "FA - xxxxxxxxx / 557233 / Shift Lead",
                "punch_count_estimate": 8,
                "canonical_name_suggestion": "FA (Shift Lead)"
            },
            {
                "employee_identifier_in_file": "FM - xxxxxxxxx / 584862 / Cook",
                "punch_count_estimate": 14,
                "canonical_name_suggestion": "FM (Cook)"
            }
        ],
        "discovery_issues": [
            "Found one employee section that may be incomplete (FM section appears truncated)",
            "Date range spans multiple weeks (3/16/2025 - 3/29/2025)"
        ]
    }


def create_realistic_parsing_response(employee_id: str):
    """Create realistic per-employee parsing responses based on actual patterns"""
    
    if "BB - xxxxxxxxx" in employee_id:
        # BB (Cashier) - Multiple shifts with clock in/out
        return {
            "punch_events": [
                {
                    "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                    "timestamp": "2025-03-16T11:13:00",
                    "punch_type_as_parsed": "Clock In",
                    "role_as_parsed": "Cashier",
                    "hourly_wage_as_parsed": 9.00
                },
                {
                    "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                    "timestamp": "2025-03-16T16:14:00", 
                    "punch_type_as_parsed": "Clock Out",
                    "role_as_parsed": "Cashier",
                    "hourly_wage_as_parsed": 9.00
                },
                {
                    "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                    "timestamp": "2025-03-16T16:42:00",
                    "punch_type_as_parsed": "Clock In",
                    "role_as_parsed": "Cashier", 
                    "hourly_wage_as_parsed": 9.00
                },
                {
                    "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                    "timestamp": "2025-03-16T17:06:00",
                    "punch_type_as_parsed": "Clock Out",
                    "role_as_parsed": "Cashier",
                    "hourly_wage_as_parsed": 9.00
                },
                {
                    "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                    "timestamp": "2025-03-20T17:02:00",
                    "punch_type_as_parsed": "Clock In",
                    "role_as_parsed": "Cashier",
                    "hourly_wage_as_parsed": 9.00
                },
                {
                    "employee_identifier_in_file": "BB - xxxxxxxxx / 649190 / Cashier",
                    "timestamp": "2025-03-20T22:01:00",
                    "punch_type_as_parsed": "Clock Out",
                    "role_as_parsed": "Cashier",
                    "hourly_wage_as_parsed": 9.00
                }
            ],
            "parsing_issues": []
        }
    
    elif "BC - xxxxxxxxx" in employee_id:
        # BC (Cook) - Day shifts
        return {
            "punch_events": [
                {
                    "employee_identifier_in_file": "BC - xxxxxxxxx / 664690 / Cook",
                    "timestamp": "2025-03-17T10:01:00",
                    "punch_type_as_parsed": "Clock In",
                    "role_as_parsed": "Cook",
                    "hourly_wage_as_parsed": 9.00
                },
                {
                    "employee_identifier_in_file": "BC - xxxxxxxxx / 664690 / Cook",
                    "timestamp": "2025-03-17T14:30:00",
                    "punch_type_as_parsed": "Clock Out",
                    "role_as_parsed": "Cook",
                    "hourly_wage_as_parsed": 9.00
                },
                {
                    "employee_identifier_in_file": "BC - xxxxxxxxx / 664690 / Cook",
                    "timestamp": "2025-03-18T10:03:00",
                    "punch_type_as_parsed": "Clock In",
                    "role_as_parsed": "Cook",
                    "hourly_wage_as_parsed": 9.00
                },
                {
                    "employee_identifier_in_file": "BC - xxxxxxxxx / 664690 / Cook",
                    "timestamp": "2025-03-18T15:14:00",
                    "punch_type_as_parsed": "Clock Out",
                    "role_as_parsed": "Cook",
                    "hourly_wage_as_parsed": 9.00
                }
            ],
            "parsing_issues": []
        }
    
    elif "FA - xxxxxxxxx" in employee_id:
        # FA (Shift Lead) - Mixed shifts including overnight
        return {
            "punch_events": [
                {
                    "employee_identifier_in_file": "FA - xxxxxxxxx / 557233 / Shift Lead",
                    "timestamp": "2025-03-21T21:00:00",
                    "punch_type_as_parsed": "Clock In",
                    "role_as_parsed": "Shift Lead",
                    "hourly_wage_as_parsed": 11.00
                },
                {
                    "employee_identifier_in_file": "FA - xxxxxxxxx / 557233 / Shift Lead",
                    "timestamp": "2025-03-22T01:39:00",
                    "punch_type_as_parsed": "Clock Out", 
                    "role_as_parsed": "Shift Lead",
                    "hourly_wage_as_parsed": 11.00
                },
                {
                    "employee_identifier_in_file": "FA - xxxxxxxxx / 557233 / Shift Lead",
                    "timestamp": "2025-03-22T13:40:00",
                    "punch_type_as_parsed": "Clock In",
                    "role_as_parsed": "Shift Lead",
                    "hourly_wage_as_parsed": 11.00
                },
                {
                    "employee_identifier_in_file": "FA - xxxxxxxxx / 557233 / Shift Lead",
                    "timestamp": "2025-03-23T01:11:00",
                    "punch_type_as_parsed": "Clock Out",
                    "role_as_parsed": "Shift Lead",
                    "hourly_wage_as_parsed": 11.00
                }
            ],
            "parsing_issues": []
        }
    
    elif "FM - xxxxxxxxx" in employee_id:
        # FM (Cook) - Full-time cook with longer hours  
        return {
            "punch_events": [
                {
                    "employee_identifier_in_file": "FM - xxxxxxxxx / 584862 / Cook",
                    "timestamp": "2025-03-17T08:01:00",
                    "punch_type_as_parsed": "Clock In",
                    "role_as_parsed": "Cook",
                    "hourly_wage_as_parsed": 12.00
                },
                {
                    "employee_identifier_in_file": "FM - xxxxxxxxx / 584862 / Cook", 
                    "timestamp": "2025-03-17T17:15:00",
                    "punch_type_as_parsed": "Clock Out",
                    "role_as_parsed": "Cook",
                    "hourly_wage_as_parsed": 12.00
                },
                {
                    "employee_identifier_in_file": "FM - xxxxxxxxx / 584862 / Cook",
                    "timestamp": "2025-03-18T07:42:00",
                    "punch_type_as_parsed": "Clock In", 
                    "role_as_parsed": "Cook",
                    "hourly_wage_as_parsed": 12.00
                },
                {
                    "employee_identifier_in_file": "FM - xxxxxxxxx / 584862 / Cook",
                    "timestamp": "2025-03-18T17:28:00",
                    "punch_type_as_parsed": "Clock Out",
                    "role_as_parsed": "Cook",
                    "hourly_wage_as_parsed": 12.00
                }
            ],
            "parsing_issues": ["Some overtime calculations may be complex due to shift overlaps"]
        }
    
    else:
        # Unknown employee - return empty
        return {
            "punch_events": [],
            "parsing_issues": [f"No punch events found for employee: {employee_id}"]
        }


async def test_mock_two_pass_workflow():
    """Test the complete two-pass workflow with realistic mock data"""
    print("🚀 MOCK TWO-PASS PROCESSING TEST")
    print("="*60)
    print("Testing complete workflow with realistic mock responses based on 8.05-short.csv\n")
    
    # Load the real sample file
    sample_file = Path(__file__).parent.parent / "sample_data" / "8.05-short.csv"
    if not sample_file.exists():
        print(f"❌ Sample file not found: {sample_file}")
        return
    
    file_content = sample_file.read_text(encoding='utf-8')
    print(f"📄 Loaded real sample file: {len(file_content):,} characters")
    
    # Create realistic mock responses
    discovery_response = create_realistic_discovery_response()
    
    def mock_employee_response(employee_id):
        return create_realistic_parsing_response(employee_id)
    
    # Mock the Gemini function
    def create_mock_gemini(*args, **kwargs):
        # Determine which call this is based on the prompt
        prompt_text = kwargs.get("prompt_parts", [""])[0] if kwargs.get("prompt_parts") else ""
        
        if "discover ALL unique employees" in prompt_text or "CRITICAL TASK" in prompt_text:
            # This is a discovery call
            print("🔍 Mock: Employee discovery call detected")
            return discovery_response
        elif "TARGET EMPLOYEE:" in prompt_text:
            # This is a per-employee parsing call
            # Extract the employee identifier from the prompt
            lines = prompt_text.split('\n')
            employee_id = None
            for line in lines:
                if "TARGET EMPLOYEE:" in line:
                    employee_id = line.split("TARGET EMPLOYEE:")[1].strip()
                    break
            
            print(f"⚡ Mock: Per-employee parsing call for '{employee_id}'")
            return mock_employee_response(employee_id)
        else:
            # Fallback
            print(f"❓ Mock: Unknown call type")
            return {"error": "Unknown call type"}
    
    # Test with mock
    with patch('app.core.llm_processing_two_pass.get_gemini_response_with_function_calling', side_effect=create_mock_gemini):
        
        print("Phase 1: Employee Discovery")
        print("-" * 30)
        
        # Test employee discovery
        discovery_result = await discover_employees_in_file(
            file_content=file_content,
            original_filename="8.05-short.csv"
        )
        
        print(f"✅ Discovery completed!")
        print(f"👥 Found {len(discovery_result.employees)} employees:")
        
        for i, employee in enumerate(discovery_result.employees, 1):
            print(f"   {i}. {employee.employee_identifier_in_file}")
            print(f"      📊 Estimated punches: {employee.punch_count_estimate}")
            print(f"      🏷️  Canonical name: {employee.canonical_name_suggestion}")
        
        if discovery_result.discovery_issues:
            print(f"\n⚠️  Discovery issues:")
            for issue in discovery_result.discovery_issues:
                print(f"   - {issue}")
        
        print(f"\nPhase 2: Per-Employee Parsing")
        print("-" * 30)
        
        # Test per-employee parsing for each discovered employee
        all_punch_events = []
        total_parse_time = 0
        
        for i, employee in enumerate(discovery_result.employees, 1):
            employee_id = employee.employee_identifier_in_file
            
            print(f"\n🎯 Parsing {i}/{len(discovery_result.employees)}: {employee_id}")
            
            parsing_result = await parse_employee_punches(
                employee_filter=employee_id,
                file_content=file_content,
                original_filename="8.05-short.csv"
            )
            
            print(f"   ✅ Found {len(parsing_result.punch_events)} punch events")
            
            # Show first few events for this employee
            for j, punch in enumerate(parsing_result.punch_events[:3], 1):
                print(f"      {j}. {punch.timestamp.strftime('%m/%d %H:%M')} - {punch.punch_type_as_parsed}")
                if punch.hourly_wage_as_parsed:
                    print(f"         💰 ${punch.hourly_wage_as_parsed:.2f}/hr")
            
            if len(parsing_result.punch_events) > 3:
                print(f"      ... and {len(parsing_result.punch_events) - 3} more events")
            
            if parsing_result.parsing_issues:
                print(f"   ⚠️  Issues: {len(parsing_result.parsing_issues)}")
                for issue in parsing_result.parsing_issues:
                    print(f"      - {issue}")
            
            all_punch_events.extend(parsing_result.punch_events)
        
        # Final Summary
        print(f"\n" + "="*60)
        print("📊 FINAL WORKFLOW RESULTS")
        print("="*60)
        
        # Employee summary
        print(f"👥 Employees processed: {len(discovery_result.employees)}")
        for employee in discovery_result.employees:
            employee_events = [e for e in all_punch_events if employee.employee_identifier_in_file in e.employee_identifier_in_file]
            print(f"   - {employee.canonical_name_suggestion}: {len(employee_events)} punch events")
        
        # Time range summary
        if all_punch_events:
            timestamps = [event.timestamp for event in all_punch_events]
            min_date = min(timestamps).date()
            max_date = max(timestamps).date()
            print(f"\n📅 Date range: {min_date} to {max_date}")
            
            # Role distribution
            roles = {}
            for event in all_punch_events:
                role = event.role_as_parsed or "Unknown"
                roles[role] = roles.get(role, 0) + 1
            
            print(f"\n👔 Role distribution:")
            for role, count in roles.items():
                print(f"   - {role}: {count} punch events")
            
            # Wage distribution
            wages = set()
            for event in all_punch_events:
                if event.hourly_wage_as_parsed:
                    wages.add(event.hourly_wage_as_parsed)
            
            if wages:
                print(f"\n💰 Hourly wages found: {', '.join(f'${w:.2f}' for w in sorted(wages))}")
        
        print(f"\n⏰ Total punch events parsed: {len(all_punch_events)}")
        print(f"🎉 Two-pass workflow completed successfully!")
        
        # Validate that we got realistic results
        assert len(discovery_result.employees) == 4, f"Expected 4 employees, got {len(discovery_result.employees)}"
        assert len(all_punch_events) > 0, "Should have parsed some punch events"
        
        print(f"\n✅ All validations passed - mock workflow is working correctly!")


async def main():
    """Main test function"""
    try:
        await test_mock_two_pass_workflow()
    except Exception as e:
        print(f"\n❌ Mock test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 