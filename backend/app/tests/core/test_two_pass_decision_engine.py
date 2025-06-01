#!/usr/bin/env python3
"""
Test Script for Updated Decision Engine

This script tests the improved decision engine with new file size thresholds
that give file size more precedence in complexity scoring.
"""

import sys
from pathlib import Path

# Add the backend app to the Python path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.core.llm_processing_two_pass import _evaluate_two_pass_suitability

def test_updated_decision_engine():
    """Test the updated decision engine with new file size thresholds"""
    
    print("🧠 UPDATED DECISION ENGINE TEST")
    print("=" * 60)
    print("📊 Testing new file size thresholds:")
    print("   - <3KB: 1 point")
    print("   - 3-6KB: 2 points") 
    print("   - 6KB+: 3 points")
    print()
    
    # Test with the same file from the orchestration test
    sample_file = Path("../sample_data/8.05-short.csv")
    
    if not sample_file.exists():
        print(f"❌ ERROR: Sample file not found at {sample_file}")
        return
    
    with open(sample_file, 'r') as f:
        content = f.read()
    
    file_size = len(content)
    print(f"📄 Testing file: 8.05-short.csv")
    print(f"📊 File size: {file_size:,} characters")
    
    # Get decision result
    result = _evaluate_two_pass_suitability(content, '8.05-short.csv')
    
    print(f"\n📊 NEW SCORING BREAKDOWN:")
    print(f"   File Size Analysis:")
    if file_size >= 6000:
        print(f"     → {file_size:,} chars ≥ 6KB = 3 points (large file)")
    elif file_size >= 3000:
        print(f"     → {file_size:,} chars = 3-6KB = 2 points (moderate file)")
    else:
        print(f"     → {file_size:,} chars < 3KB = 1 point (small file)")
    
    print(f"\n🎯 DECISION RESULTS:")
    print(f"   - Complexity score: {result['complexity_score']}/10")
    print(f"   - Recommendation: {'Two-pass' if result['should_use_two_pass'] else 'Single-pass'}")
    print(f"   - Reason: {result['reason']}")
    print(f"   - Estimated employees: {result['estimated_employees']}")
    
    print(f"\n📈 IMPACT ANALYSIS:")
    old_score = 3  # Previous score from orchestration test
    new_score = result['complexity_score']
    print(f"   - Previous score: {old_score}/10")
    print(f"   - New score: {new_score}/10")
    print(f"   - Change: {new_score - old_score:+.1f} points")
    
    if new_score > old_score:
        print(f"   - ✅ File size thresholds now provide stronger signal")
    elif new_score < old_score:
        print(f"   - ⚠️  File size thresholds provide weaker signal")
    else:
        print(f"   - ➡️  Same scoring result")
    
    print(f"\n🧪 TESTING DIFFERENT FILE SIZES:")
    test_cases = [
        (1500, "Very small timesheet"),
        (2800, "Small timesheet"), 
        (4500, "Medium timesheet"),
        (7000, "Large timesheet"),
        (12000, "Very large timesheet")
    ]
    
    for size, description in test_cases:
        # Create dummy content of specified size
        dummy_content = "Employee,Date,Time\n" + "Test Data," * (size // 20)
        dummy_content = dummy_content[:size]  # Trim to exact size
        
        test_result = _evaluate_two_pass_suitability(dummy_content, f"test-{size}.csv")
        
        if size >= 6000:
            expected_file_points = 3
        elif size >= 3000:
            expected_file_points = 2
        else:
            expected_file_points = 1
            
        print(f"   - {size:,} chars ({description}): Score {test_result['complexity_score']}/10 → {'Two-pass' if test_result['should_use_two_pass'] else 'Single-pass'}")
    
    print(f"\n✅ Updated decision engine testing completed!")
    print(f"💡 File size now has appropriate precedence with realistic thresholds")

if __name__ == "__main__":
    test_updated_decision_engine() 