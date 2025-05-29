#!/usr/bin/env python3
"""
Final LLM Test with Timeout Protection
Tests the LLM with timeout to prevent hanging.
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

async def test_with_timeout():
    """Test LLM processing with timeout protection"""
    print("🚀 Testing LLM Processing with Timeout Protection")
    print("=" * 60)
    
    # Load test file
    csv_file_path = backend_dir / "tests" / "core" / "8.05-short.csv"
    
    if not csv_file_path.exists():
        print(f"❌ Test file not found: {csv_file_path}")
        return False
    
    with open(csv_file_path, 'rb') as f:
        file_bytes = f.read()
    
    print(f"📄 Testing with: {csv_file_path.name} ({len(file_bytes)} bytes)")
    
    debug_dir = current_dir / "debug_runs" / f"final_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    # Test with 60-second timeout
    timeout_seconds = 60
    print(f"⏱️ Setting timeout: {timeout_seconds} seconds")
    
    try:
        print(f"\n🤖 Starting LLM processing with timeout protection...")
        start_time = datetime.now()
        
        # Wrap the LLM call with asyncio timeout
        result = await asyncio.wait_for(
            parse_file_to_structured_data(
                file_bytes=file_bytes,
                mime_type="text/csv",
                original_filename=csv_file_path.name,
                debug_dir=str(debug_dir)
            ),
            timeout=timeout_seconds
        )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"✅ SUCCESS! Processing completed in {processing_time:.2f} seconds")
        print(f"📊 Results:")
        print(f"   - Extracted {len(result.punch_events)} punch events")
        print(f"   - Parsing issues: {len(result.parsing_issues)}")
        
        if result.punch_events:
            print(f"\n📋 Sample punch events:")
            for i, event in enumerate(result.punch_events[:3], 1):
                print(f"   {i}. {event.employee_identifier_in_file} - {event.punch_type_as_parsed}")
        
        if result.parsing_issues:
            print(f"\n⚠️ Parsing issues:")
            for issue in result.parsing_issues[:2]:
                print(f"   - {issue}")
        
        # Save results
        output_data = {
            "success": True,
            "processing_time_seconds": processing_time,
            "events_count": len(result.punch_events),
            "issues_count": len(result.parsing_issues),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(debug_dir / "test_results.json", 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"💾 Results saved to: {debug_dir}")
        return True
        
    except asyncio.TimeoutError:
        print(f"❌ TIMEOUT: LLM processing exceeded {timeout_seconds} seconds")
        print(f"   This indicates the API call is hanging/stuck")
        print(f"   The issue is likely in the Google API client or model availability")
        
        # Save timeout info
        timeout_data = {
            "error": "timeout",
            "timeout_seconds": timeout_seconds,
            "timestamp": datetime.now().isoformat(),
            "recommendation": "Use a more stable model or add timeout to google_utils.py"
        }
        
        with open(debug_dir / "timeout_error.json", 'w') as f:
            json.dump(timeout_data, f, indent=2)
        
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        # Save error info
        error_data = {
            "error": str(e),
            "error_type": e.__class__.__name__,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(debug_dir / "error_log.json", 'w') as f:
            json.dump(error_data, f, indent=2)
        
        return False

async def test_stable_model():
    """Test with a known stable model"""
    print("\n🔧 Testing with Stable Model (gemini-1.5-flash)")
    print("=" * 60)
    
    # Temporarily change config to use stable model
    config_path = current_dir / "config.json"
    with open(config_path, 'r') as f:
        original_config = json.load(f)
    
    # Set stable model
    stable_config = original_config.copy()
    stable_config["google"]["default_model"] = "gemini-1.5-flash"
    
    with open(config_path, 'w') as f:
        json.dump(stable_config, f, indent=2)
    
    print(f"⚙️ Temporarily using stable model: gemini-1.5-flash")
    
    try:
        result = await test_with_timeout()
        return result
    finally:
        # Restore original config
        with open(config_path, 'w') as f:
            json.dump(original_config, f, indent=2)
        print(f"🔄 Restored original model configuration")

async def main():
    """Run all tests"""
    print("🧪 Final LLM Hanging Issue Diagnosis")
    print("=" * 60)
    
    # Test 1: Current model with timeout
    print("\n📋 Test 1: Current Model with Timeout Protection")
    success1 = await test_with_timeout()
    
    if not success1:
        # Test 2: Stable model with timeout
        print("\n📋 Test 2: Stable Model with Timeout Protection")
        success2 = await test_stable_model()
        
        if success2:
            print("\n💡 DIAGNOSIS: The issue is with the unstable preview model")
            print("   SOLUTION: Update config.json to use 'gemini-1.5-flash'")
        else:
            print("\n💡 DIAGNOSIS: The issue is deeper - likely timeout or API problems")
            print("   SOLUTION: Add timeout protection to google_utils.py")
    else:
        print("\n🎉 SUCCESS: No hanging issues detected!")
    
    print(f"\n📊 Final Recommendation:")
    if success1:
        print("   ✅ Current setup works - no changes needed")
    else:
        print("   🔧 Implement timeout protection in google_utils.py")
        print("   🔄 Switch to stable model: gemini-1.5-flash")

if __name__ == "__main__":
    asyncio.run(main()) 