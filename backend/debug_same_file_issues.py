#!/usr/bin/env python3
"""
Debug script to test the exact same file that previously had overtime violations
to understand why they're missing now and why the date is wrong.
"""

import sys
import asyncio
import aiohttp
import json
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent))

async def test_file_upload():
    """Test uploading the actual Excel file to see current behavior"""
    
    # The file path from the CSV screenshot
    test_file_path = Path(__file__).parent / "sample_data" / "8.05-short.xlsx"
    
    print(f"🔍 TESTING FILE UPLOAD: {test_file_path}")
    print("=" * 80)
    
    if not test_file_path.exists():
        print(f"❌ File not found: {test_file_path}")
        print("Looking for alternative paths...")
        
        # Try alternative paths
        alternative_paths = [
            Path(__file__).parent.parent / "sample_data" / "8.05-short.xlsx",
            Path(__file__).parent / "8.05-short.xlsx",
            Path(__file__).parent / "sample_data" / "8.05 - Time Clock Detail.xlsx",
            Path(__file__).parent.parent / "sample_data" / "8.05 - Time Clock Detail.xlsx",
        ]
        
        for alt_path in alternative_paths:
            if alt_path.exists():
                test_file_path = alt_path
                print(f"✅ Found file at: {test_file_path}")
                break
        else:
            print("❌ No file found in any expected location")
            return
    
    try:
        # Test with local backend
        base_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # Step 1: Start analysis
            print(f"\n🚀 STEP 1: Starting analysis...")
            
            with open(test_file_path, 'rb') as f:
                file_data = aiohttp.FormData()
                file_data.add_field('file', f, filename=test_file_path.name)
                
                async with session.post(f"{base_url}/api/start-analysis", data=file_data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ Start analysis failed: {response.status} - {error_text}")
                        return
                    
                    start_result = await response.json()
                    request_id = start_result.get('request_id')
                    print(f"✅ Analysis started with request_id: {request_id}")
            
            # Step 2: Get analysis results
            print(f"\n📊 STEP 2: Getting analysis results...")
            
            # Wait a bit for processing
            await asyncio.sleep(5)
            
            async with session.get(f"{base_url}/api/analyze?request_id={request_id}") as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ Analysis failed: {response.status} - {error_text}")
                    return
                
                analysis_result = await response.json()
                
                print(f"✅ Analysis completed!")
                print(f"📝 Status: {analysis_result.get('status')}")
                
                # Extract key information
                violations = analysis_result.get('analysis_results', {}).get('violations', [])
                daily_ot = analysis_result.get('analysis_results', {}).get('daily_overtime_violations', [])
                weekly_ot = analysis_result.get('analysis_results', {}).get('weekly_overtime_violations', [])
                
                print(f"\n📊 VIOLATION SUMMARY:")
                print(f"   Total violations: {len(violations)}")
                print(f"   Daily overtime violations: {len(daily_ot)}")
                print(f"   Weekly overtime violations: {len(weekly_ot)}")
                
                # Check dates in violations
                print(f"\n📅 DATE ANALYSIS:")
                dates_found = set()
                for violation in violations:
                    date_str = str(violation.get('date_of_violation', 'Unknown'))
                    dates_found.add(date_str)
                    print(f"   Violation date: {date_str}")
                
                print(f"   Unique dates: {list(dates_found)}")
                
                # Look for BB specifically
                print(f"\n👤 BB EMPLOYEE ANALYSIS:")
                bb_violations = [v for v in violations if 'BB' in str(v.get('employee_identifier', ''))]
                bb_daily_ot = [v for v in daily_ot if 'BB' in str(v.get('employee_identifier', ''))]
                bb_weekly_ot = [v for v in weekly_ot if 'BB' in str(v.get('employee_identifier', ''))]
                
                print(f"   BB total violations: {len(bb_violations)}")
                print(f"   BB daily overtime: {len(bb_daily_ot)}")
                print(f"   BB weekly overtime: {len(bb_weekly_ot)}")
                
                for violation in bb_violations:
                    print(f"   BB Violation: {violation.get('rule_id')} on {violation.get('date_of_violation')}")
                
                # Look at shifts/punch events for BB
                punch_events = analysis_result.get('analysis_results', {}).get('punch_events', [])
                bb_punches = [p for p in punch_events if 'BB' in str(p.get('employee_identifier_in_file', ''))]
                
                print(f"\n🕐 BB PUNCH EVENTS:")
                print(f"   Total BB punches: {len(bb_punches)}")
                
                for i, punch in enumerate(bb_punches, 1):
                    timestamp = punch.get('timestamp', 'Unknown')
                    punch_type = punch.get('punch_type_as_parsed', 'Unknown')
                    print(f"   {i}. {punch_type}: {timestamp}")
                
                # Check for any overtime violations at all
                print(f"\n⚡ OVERTIME VIOLATIONS DETAIL:")
                all_ot_violations = daily_ot + weekly_ot
                
                if all_ot_violations:
                    for ot_violation in all_ot_violations:
                        print(f"   OT: {ot_violation.get('rule_id')} - {ot_violation.get('employee_identifier')} on {ot_violation.get('date_of_violation')}")
                        print(f"       Details: {ot_violation.get('specific_details', 'No details')}")
                else:
                    print(f"   ❌ NO OVERTIME VIOLATIONS FOUND")
                    print(f"   This suggests either:")
                    print(f"   1. The shift parsing is incorrect")
                    print(f"   2. The LLM is parsing times incorrectly")
                    print(f"   3. The overtime detection logic has an issue")
                
                # Save full response for debugging
                debug_file = Path(__file__).parent / "debug_api_response.json"
                with open(debug_file, 'w') as f:
                    json.dump(analysis_result, f, indent=2, default=str)
                print(f"\n💾 Full response saved to: {debug_file}")
                
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_file_upload()) 