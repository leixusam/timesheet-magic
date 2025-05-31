#!/usr/bin/env python3
"""
Simple LLM Test Script
Tests different Google models to find the most reliable one for our use case.
"""

import asyncio
import os
import sys
from pathlib import Path
import json
from datetime import datetime

# Add the backend directory to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.llm_processing import parse_file_to_structured_data

# Test different models
MODELS_TO_TEST = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest", 
    "gemini-1.5-pro",
    "gemini-2.5-flash-preview-05-20",  # Current problematic model
]

async def test_model(model_name, file_bytes, mime_type, filename):
    """Test a specific model"""
    print(f"\n🧪 Testing model: {model_name}")
    print("-" * 30)
    
    debug_dir = current_dir / "debug_runs" / f"simple_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Temporarily override the model configuration
        config_path = backend_dir / "config.json"
        with open(config_path, 'r') as f:
            original_config = json.load(f)
        
        # Create test config with our model
        test_config = original_config.copy()
        test_config["google"]["default_model"] = model_name
        
        with open(config_path, 'w') as f:
            json.dump(test_config, f, indent=2)
        
        print(f"⚙️ Temporarily set default model to: {model_name}")
        
        # Test LLM processing
        result = await parse_file_to_structured_data(
            file_bytes=file_bytes,
            mime_type=mime_type,
            original_filename=filename
        )
        
        print(f"✅ SUCCESS with {model_name}!")
        print(f"   - Extracted {len(result.punch_events)} punch events")
        print(f"   - Parsing issues: {len(result.parsing_issues)}")
        
        if result.parsing_issues:
            print(f"   - Issues: {result.parsing_issues[:2]}")  # Show first 2 issues
        
        # Restore original config
        with open(config_path, 'w') as f:
            json.dump(original_config, f, indent=2)
        
        return True, len(result.punch_events), result.parsing_issues
        
    except Exception as e:
        print(f"❌ FAILED with {model_name}: {e}")
        
        # Restore original config
        with open(config_path, 'w') as f:
            json.dump(original_config, f, indent=2)
        
        return False, 0, [str(e)]

async def main():
    """Test multiple models"""
    print("🚀 Testing Multiple Google Models")
    print("=" * 50)
    
    # Load test file
    csv_file_path = current_dir.parent / "sample_data" / "8.05-short.csv"
    
    if not csv_file_path.exists():
        print(f"❌ Test file not found: {csv_file_path}")
        return
    
    with open(csv_file_path, 'rb') as f:
        file_bytes = f.read()
    
    print(f"📄 Testing with: {csv_file_path.name} ({len(file_bytes)} bytes)")
    
    results = {}
    
    for model in MODELS_TO_TEST:
        try:
            success, events, issues = await test_model(
                model, file_bytes, "text/csv", csv_file_path.name
            )
            results[model] = {
                "success": success,
                "events": events,
                "issues": len(issues)
            }
        except Exception as e:
            print(f"💥 Critical error testing {model}: {e}")
            results[model] = {
                "success": False,
                "events": 0,
                "issues": 1,
                "error": str(e)
            }
    
    # Summary
    print("\n📊 MODEL TEST RESULTS")
    print("=" * 50)
    
    working_models = []
    for model, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        events = result["events"]
        issues = result["issues"]
        
        print(f"{status} {model:30} | Events: {events:2d} | Issues: {issues}")
        
        if result["success"] and events > 0:
            working_models.append((model, events))
    
    if working_models:
        print(f"\n🎉 WORKING MODELS FOUND: {len(working_models)}")
        best_model = max(working_models, key=lambda x: x[1])  # Model with most events
        print(f"🏆 BEST MODEL: {best_model[0]} (extracted {best_model[1]} events)")
        
        print(f"\n💡 RECOMMENDATION:")
        print(f"   Update config.json to use: {best_model[0]}")
        print(f"   This model successfully extracted the most punch events.")
    else:
        print(f"\n⚠️ NO WORKING MODELS FOUND")
        print(f"   This might indicate an API key issue or temporary service problems.")

if __name__ == "__main__":
    asyncio.run(main()) 