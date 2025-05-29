#!/usr/bin/env python3
"""
Actionable Advice Generation Test (Task 3.5.5 Validation)

This script validates the newly implemented generic actionable advice functions from the reporting module.
It demonstrates completion of task 3.5.5: "Function to provide generic actionable advice text for each violation type".

What this test validates:
- ✅ Comprehensive actionable advice mapping for all violation types
- ✅ Convenient single-violation advice retrieval
- ✅ Categorized violation display for frontend organization
- ✅ Quality and actionability of advice content
- ✅ Integration with existing violation detection system

Test Strategy:
- Demonstrates the public API for actionable advice generation
- Shows how frontend can display categorized violation guidance
- Validates advice quality and comprehensiveness
- No LLM API calls required - pure logic testing

Prerequisites:
- Backend reporting module with task 3.5.5 functions implemented
- Valid virtual environment with dependencies installed

Usage:
    cd backend && python ../tests/test_actionable_advice_validation.py

Related Files:
- backend/app/core/reporting.py - Contains the actionable advice functions
- backend/app/tests/core/test_reporting.py - Unit tests for reporting module
- tasks/tasks-prd-timesheet-magic-mvp.md - Task tracking document
"""

import sys
import json
from pathlib import Path

# Add current directory to Python path for imports
sys.path.insert(0, '.')

from app.core.reporting import (
    provide_generic_actionable_advice_for_violation_types,
    get_actionable_advice_for_violation,
    get_all_violation_types_with_advice
)


def test_actionable_advice_comprehensive_functionality():
    """Test comprehensive actionable advice functionality for task 3.5.5"""
    
    print("💡 Testing Generic Actionable Advice Generation (Task 3.5.5)")
    print("=" * 70)
    
    # Step 1: Test comprehensive advice mapping
    print("\n📚 Step 1: Testing comprehensive advice mapping...")
    
    advice_mapping = provide_generic_actionable_advice_for_violation_types()
    
    print(f"✅ Generated advice for {len(advice_mapping)} violation types")
    
    # Check coverage of key violation categories
    violation_categories = {
        "Meal Breaks": [k for k in advice_mapping.keys() if "MEAL_BREAK" in k],
        "Rest Breaks": [k for k in advice_mapping.keys() if "REST_BREAK" in k],
        "Daily Overtime": [k for k in advice_mapping.keys() if "DAILY_OVERTIME" in k],
        "Weekly Overtime": [k for k in advice_mapping.keys() if "WEEKLY_OVERTIME" in k],
        "Employee Records": [k for k in advice_mapping.keys() if "DUPLICATE" in k],
        "Management": [k for k in advice_mapping.keys() if any(word in k for word in ["SCHEDULING", "TRAINING", "COVERAGE"])]
    }
    
    print(f"\n📋 Violation category coverage:")
    for category, violations in violation_categories.items():
        print(f"   {category}: {len(violations)} violation types")
        if violations:
            print(f"      Examples: {', '.join(violations[:3])}")
    
    # Step 2: Test single violation advice retrieval
    print(f"\n🎯 Step 2: Testing single violation advice retrieval...")
    
    test_violations = [
        "MEAL_BREAK_MISSING",
        "DAILY_OVERTIME", 
        "REST_BREAK_MISSING",
        "WEEKLY_OVERTIME",
        "DUPLICATE_EMPLOYEE_DETECTED",
        "UNKNOWN_VIOLATION_TYPE"  # Test fallback
    ]
    
    for violation in test_violations:
        advice = get_actionable_advice_for_violation(violation)
        status = "✅" if len(advice) > 50 else "⚠️"
        print(f"   {status} {violation}: {advice[:80]}{'...' if len(advice) > 80 else ''}")
    
    # Step 3: Test categorized violation display
    print(f"\n📂 Step 3: Testing categorized violation display...")
    
    all_violations = get_all_violation_types_with_advice()
    
    print(f"✅ Retrieved {len(all_violations)} violation entries with categories")
    
    # Group by category for display
    by_category = {}
    for violation_info in all_violations:
        category = violation_info["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(violation_info)
    
    print(f"\n📊 Violations grouped by category:")
    for category, violations in sorted(by_category.items()):
        print(f"\n   📁 {category} ({len(violations)} violations):")
        for violation in violations[:3]:  # Show first 3 as examples
            rule_id = violation["rule_id"]
            advice_preview = violation["advice"][:60] + "..." if len(violation["advice"]) > 60 else violation["advice"]
            print(f"      • {rule_id}: {advice_preview}")
        if len(violations) > 3:
            print(f"      ... and {len(violations) - 3} more")
    
    # Step 4: Validate advice quality
    print(f"\n✨ Step 4: Validating advice quality...")
    
    quality_checks = {
        "All advice non-empty": all(len(advice.strip()) > 0 for advice in advice_mapping.values()),
        "Most advice detailed (>80 chars)": sum(1 for advice in advice_mapping.values() if len(advice) > 80) >= len(advice_mapping) * 0.7,
        "Contains action words": all(any(word in advice.lower() for word in ["ensure", "schedule", "provide", "monitor", "review", "consider", "must", "should", "implement", "train", "avoid", "apply", "create", "use", "track", "set", "analyze", "adjust"]) for advice in advice_mapping.values()),
        "Meal break advice mentions timing": any("5th hour" in advice or "5 hour" in advice for k, advice in advice_mapping.items() if "MEAL_BREAK" in k),
        "Overtime advice mentions pay rates": any("time-and-a-half" in advice or "double pay" in advice for k, advice in advice_mapping.items() if "OVERTIME" in k),
        "Rest break advice mentions duration": any("10-minute" in advice or "10 minute" in advice for k, advice in advice_mapping.items() if "REST_BREAK" in k)
    }
    
    for check, passed in quality_checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
    
    all_quality_passed = all(quality_checks.values())
    
    # Step 5: Demonstrate practical usage examples
    print(f"\n🔧 Step 5: Practical usage examples for frontend integration...")
    
    print(f"\n   Example 1: Getting advice for a specific violation")
    meal_advice = get_actionable_advice_for_violation("MEAL_BREAK_MISSING")
    print(f"   Rule: MEAL_BREAK_MISSING")
    print(f"   Advice: {meal_advice}")
    
    print(f"\n   Example 2: Frontend dropdown/help text structure")
    sample_violations = [info for info in all_violations if info["category"] == "Meal Breaks"][:2]
    for violation in sample_violations:
        print(f"   Category: {violation['category']}")
        print(f"   Rule ID: {violation['rule_id']}")
        print(f"   Help Text: {violation['advice']}")
        print()
    
    # Step 6: Export for frontend reference
    print(f"\n💾 Step 6: Exporting reference data for frontend...")
    
    export_data = {
        "violation_advice_mapping": advice_mapping,
        "violations_by_category": by_category,
        "quality_validation": quality_checks,
        "usage_examples": {
            "single_violation_lookup": {
                "function": "get_actionable_advice_for_violation",
                "example": {
                    "input": "MEAL_BREAK_MISSING",
                    "output": get_actionable_advice_for_violation("MEAL_BREAK_MISSING")
                }
            },
            "all_violations_with_categories": {
                "function": "get_all_violation_types_with_advice",
                "sample_output": all_violations[:3]
            }
        },
        "metadata": {
            "total_violation_types": len(advice_mapping),
            "categories_count": len(by_category),
            "task_completed": "3.5.5",
            "test_timestamp": "2025-01-28T21:35:00Z"
        }
    }
    
    output_file = Path("../debug_runs") / "actionable_advice_validation.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"✅ Reference data exported to: {output_file}")
    
    # Final summary
    print(f"\n" + "=" * 70)
    print(f"🎉 Task 3.5.5 Validation Complete!")
    print(f"=" * 70)
    
    if all_quality_passed:
        print(f"✅ All quality checks passed")
        print(f"📊 Generated comprehensive advice for {len(advice_mapping)} violation types")
        print(f"📂 Organized into {len(by_category)} categories for frontend display")
        print(f"🔧 Public API ready for frontend integration:")
        print(f"   - provide_generic_actionable_advice_for_violation_types()")
        print(f"   - get_actionable_advice_for_violation(rule_id)")
        print(f"   - get_all_violation_types_with_advice()")
        print(f"💡 Task 3.5.5: Generic actionable advice generation is complete and functional!")
        return True
    else:
        print(f"❌ Some quality checks failed - review implementation")
        failed_checks = [check for check, passed in quality_checks.items() if not passed]
        print(f"Failed checks: {', '.join(failed_checks)}")
        return False


if __name__ == "__main__":
    success = test_actionable_advice_comprehensive_functionality()
    sys.exit(0 if success else 1) 