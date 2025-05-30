#!/usr/bin/env python3
"""
Quick test script to verify the new immediate lead submission flow.
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_new_flow():
    print("Testing new immediate lead submission flow...")
    
    # Create a simple test CSV content
    test_csv_content = """Employee Name,Date,Clock In,Clock Out
John Doe,2023-05-01,08:00,17:00
Jane Smith,2023-05-01,09:00,18:00
"""
    
    # Step 1: Start analysis and get request ID immediately
    print("\n1. Starting analysis...")
    files = {
        'file': ('test.csv', test_csv_content, 'text/csv')
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/start-analysis", files=files)
        print(f"Start analysis response: {response.status_code}")
        
        if response.status_code == 200:
            start_result = response.json()
            print(f"Start result: {json.dumps(start_result, indent=2)}")
            request_id = start_result.get('request_id')
            
            if request_id:
                print(f"✅ Got request ID immediately: {request_id}")
                
                # Step 2: Submit lead data immediately
                print("\n2. Submitting lead data immediately...")
                lead_data = {
                    "analysisId": request_id,
                    "managerName": "Test Manager",
                    "managerEmail": "test@example.com",
                    "managerPhone": "555-1234",
                    "storeName": "Test Store",
                    "storeAddress": "123 Test St"
                }
                
                lead_response = requests.post(f"{BASE_URL}/api/submit-lead", 
                                            json=lead_data,
                                            headers={'Content-Type': 'application/json'})
                print(f"Lead submission response: {lead_response.status_code}")
                
                if lead_response.status_code == 200:
                    lead_result = lead_response.json()
                    print(f"Lead result: {json.dumps(lead_result, indent=2)}")
                    print("✅ Lead submitted successfully before analysis completion!")
                    
                    # Step 3: Wait for analysis to complete and check report
                    print("\n3. Waiting for analysis to complete...")
                    max_attempts = 30
                    for attempt in range(max_attempts):
                        time.sleep(2)
                        try:
                            report_response = requests.get(f"{BASE_URL}/api/reports/{request_id}")
                            if report_response.status_code == 200:
                                report = report_response.json()
                                # Check if report has real data (not placeholder)
                                if (report.get('kpis') and 
                                    report.get('employee_summaries') and 
                                    len(report.get('employee_summaries', [])) > 0):
                                    print(f"✅ Analysis completed! Report has {len(report.get('employee_summaries', []))} employees")
                                    print(f"Status: {report.get('status')}")
                                    return True
                                else:
                                    print(f"Analysis still in progress... (attempt {attempt + 1})")
                            else:
                                print(f"Error checking report: {report_response.status_code}")
                        except Exception as e:
                            print(f"Error checking report: {e}")
                    
                    print("⚠️ Analysis did not complete within expected time")
                    return False
                else:
                    print(f"❌ Lead submission failed: {lead_response.text}")
                    return False
            else:
                print("❌ No request ID received")
                return False
        else:
            print(f"❌ Start analysis failed: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend server. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_new_flow()
    if success:
        print("\n🎉 New immediate lead submission flow works correctly!")
    else:
        print("\n💥 Test failed - check the issues above") 