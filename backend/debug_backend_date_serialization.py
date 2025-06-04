#!/usr/bin/env python3
"""
Debug script to check what date format the backend is actually sending to the frontend
"""

import sys
import asyncio
import json
from datetime import datetime, date
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.core.llm_processing import parse_file_to_structured_data
from app.core.compliance_rules import parse_shifts_from_punch_events
from app.core.reporting import compile_general_compliance_violations

async def debug_backend_serialization():
    """Debug what date format is being sent by the backend"""
    print("🔍 DEBUGGING BACKEND DATE SERIALIZATION")
    print("=" * 80)
    
    # Read the actual CSV file
    csv_file_path = Path(__file__).parent.parent / "sample_data" / "8.05-short.csv"
    
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    # Parse with LLM
    file_bytes = file_content.encode('utf-8')
    result = await parse_file_to_structured_data(file_bytes, 'text/csv', '8.05-short.csv')
    
    # Get violations
    violations = compile_general_compliance_violations(result.punch_events)
    
    print(f"\n🎯 BB VIOLATIONS ON MARCH 27:")
    for violation in violations:
        if 'BB' in violation.employee_identifier and violation.date_of_violation.month == 3 and violation.date_of_violation.day == 27:
            print(f"\n   Violation found:")
            print(f"     Rule ID: {violation.rule_id}")
            print(f"     Employee: {violation.employee_identifier}")
            print(f"     Date type: {type(violation.date_of_violation)}")
            print(f"     Date value: {violation.date_of_violation}")
            print(f"     Date ISO format: {violation.date_of_violation.isoformat()}")
            print(f"     Date weekday: {violation.date_of_violation.strftime('%A')}")
            
            # Show what would be serialized to JSON (like the API does)
            serialized_data = {
                "rule_id": violation.rule_id,
                "employee_identifier": violation.employee_identifier,
                "date_of_violation": violation.date_of_violation.isoformat(),  # This is what gets sent to frontend
                "rule_description": violation.rule_description
            }
            
            print(f"\n   🌐 JSON SERIALIZATION (what frontend receives):")
            print(f"     date_of_violation: '{serialized_data['date_of_violation']}'")
            
            # Test frontend parsing simulation
            frontend_date_string = serialized_data['date_of_violation']
            print(f"\n   🖥️  FRONTEND PARSING SIMULATION:")
            print(f"     Input string: '{frontend_date_string}'")
            
            # Method 1: Direct Date constructor (what might be causing the issue)
            try:
                js_date = datetime.fromisoformat(frontend_date_string)
                print(f"     Python datetime.fromisoformat(): {js_date}")
            except Exception as e:
                print(f"     Python datetime.fromisoformat() error: {e}")
            
            # Method 2: Manual parsing (what the frontend does)
            try:
                year, month, day = frontend_date_string.split('-')
                manual_date = date(int(year), int(month), int(day))
                print(f"     Manual parsing (year={year}, month={month}, day={day}): {manual_date}")
                print(f"     Manual parsing weekday: {manual_date.strftime('%A')}")
            except Exception as e:
                print(f"     Manual parsing error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_backend_serialization()) 