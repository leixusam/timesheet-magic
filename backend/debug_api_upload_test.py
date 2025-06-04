#!/usr/bin/env python3
"""
Test the actual API upload to see what violations are returned with their dates
"""

import asyncio
import aiohttp
import json
from pathlib import Path

async def test_api_upload():
    """Test the actual API endpoint to see what violations are returned"""
    print("🔍 TESTING ACTUAL API UPLOAD")
    print("=" * 80)
    
    # Read the actual CSV file
    csv_file_path = Path(__file__).parent.parent / "sample_data" / "8.05-short.csv"
    
    if not csv_file_path.exists():
        print(f"❌ File not found: {csv_file_path}")
        return
    
    print(f"✅ Found file: {csv_file_path}")
    
    async with aiohttp.ClientSession() as session:
        # Prepare the file for upload
        with open(csv_file_path, 'rb') as f:
            file_content = f.read()
        
        data = aiohttp.FormData()
        data.add_field('file', 
                      file_content, 
                      filename='8.05-short.csv',
                      content_type='text/csv')
        
        print(f"\n📤 Uploading file to API...")
        
        try:
            async with session.post('http://localhost:8000/api/analyze', data=data) as response:
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    response_data = await response.json()
                    
                    # Extract violations from response
                    violations = response_data.get('violations', [])
                    print(f"\n✅ API Response received:")
                    print(f"   Total violations: {len(violations)}")
                    
                    # Focus on BB employee violations around March 26-27
                    print(f"\n🎯 BB EMPLOYEE VIOLATIONS (March 26-27):")
                    bb_violations = []
                    
                    for violation in violations:
                        if 'BB' in violation.get('employee_identifier', ''):
                            date_str = violation.get('date_of_violation', '')
                            if '2025-03-26' in date_str or '2025-03-27' in date_str:
                                bb_violations.append(violation)
                                print(f"\n   📍 Found BB violation:")
                                print(f"      Rule ID: {violation.get('rule_id')}")
                                print(f"      Date: {date_str}")
                                print(f"      Employee: {violation.get('employee_identifier')}")
                                print(f"      Description: {violation.get('rule_description', '')[:100]}...")
                    
                    if not bb_violations:
                        print(f"\n   ❌ No BB violations found for March 26-27")
                        print(f"   Let's check all BB violations:")
                        
                        for violation in violations:
                            if 'BB' in violation.get('employee_identifier', ''):
                                print(f"      {violation.get('date_of_violation')} - {violation.get('rule_id')}")
                    
                    # Save full response for debugging
                    debug_file = Path(__file__).parent / "api_response_debug.json"
                    with open(debug_file, 'w') as f:
                        json.dump(response_data, f, indent=2, default=str)
                    print(f"\n💾 Full API response saved to: {debug_file}")
                    
                else:
                    error_text = await response.text()
                    print(f"❌ API Error: {response.status}")
                    print(f"   Response: {error_text}")
                    
        except aiohttp.ClientConnectorError:
            print(f"❌ Could not connect to API. Is the backend running on localhost:8000?")
        except Exception as e:
            print(f"❌ Error during API call: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_upload()) 