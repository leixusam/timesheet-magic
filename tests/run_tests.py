#!/usr/bin/env python3
"""
Test Runner for Time Sheet Magic

This script provides an easy way to run all integration tests for the Time Sheet Magic
application. It handles dependencies between tests and provides clear output.

Available Tests:
1. test_end_to_end.py      - Full pipeline test (run this first)
2. test_compliance_only.py - Isolated compliance testing  
3. test_kpi_calculation.py - KPI calculation validation (Task 3.5.1)
4. test_real_excel.py      - Excel file processing test
5. test_simple.py          - Basic functionality test
6. test_final.py           - API timeout diagnostic test

Usage:
    python tests/run_tests.py [test_name]
    
    # Run all tests in recommended order
    python tests/run_tests.py all
    
    # Run specific test
    python tests/run_tests.py end_to_end
    python tests/run_tests.py compliance_only
    python tests/run_tests.py kpi_calculation
    
    # Run core pipeline tests only
    python tests/run_tests.py core
"""

import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime


class TestRunner:
    def __init__(self):
        self.tests_dir = Path(__file__).parent
        self.root_dir = self.tests_dir.parent
        
        # Define available tests with descriptions
        self.tests = {
            'end_to_end': {
                'file': 'test_end_to_end.py',
                'description': 'Complete pipeline test (LLM → Compliance → Costs)',
                'dependency': None,
                'priority': 1
            },
            'compliance_only': {
                'file': 'test_compliance_only.py', 
                'description': 'Isolated compliance testing (no LLM dependencies)',
                'dependency': None,
                'priority': 2
            },
            'kpi_calculation': {
                'file': 'test_kpi_calculation.py',
                'description': 'KPI calculation validation (Task 3.5.1)',
                'dependency': 'end_to_end',
                'priority': 3
            },
            'real_excel': {
                'file': 'test_real_excel.py',
                'description': 'Excel file processing test',
                'dependency': None,
                'priority': 4
            },
            'simple': {
                'file': 'test_simple.py',
                'description': 'Basic functionality test',
                'dependency': None,
                'priority': 5
            },
            'final': {
                'file': 'test_final.py',
                'description': 'API timeout diagnostic test',
                'dependency': None,
                'priority': 6
            }
        }
        
        # Test suites
        self.suites = {
            'core': ['end_to_end', 'compliance_only', 'kpi_calculation'],
            'all': list(self.tests.keys())
        }

    def print_header(self):
        print("🧪 Time Sheet Magic - Test Runner")
        print("=" * 60)
        print(f"📁 Tests directory: {self.tests_dir}")
        print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

    def print_available_tests(self):
        print("📋 Available Tests:")
        print("-" * 40)
        
        for test_name, test_info in sorted(self.tests.items(), key=lambda x: x[1]['priority']):
            dependency_note = f" (requires: {test_info['dependency']})" if test_info['dependency'] else ""
            print(f"  {test_info['priority']}. {test_name:<15} - {test_info['description']}{dependency_note}")
        
        print("\n📦 Test Suites:")
        print("-" * 40)
        for suite_name, test_list in self.suites.items():
            print(f"  {suite_name:<15} - {', '.join(test_list)}")
        print()

    def check_environment(self):
        """Check that the environment is properly set up"""
        print("🔧 Checking environment...")
        
        # Check virtual environment
        if not os.getenv('VIRTUAL_ENV'):
            print("⚠️ Warning: No virtual environment detected")
            print("   Consider running: source venv/bin/activate")
        else:
            print(f"✅ Virtual environment: {os.getenv('VIRTUAL_ENV')}")
        
        # Check for required environment variables (these may be optional)
        env_vars = ['GOOGLE_API_KEY', 'OPENAI_API_KEY']
        missing_vars = [var for var in env_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"⚠️ Warning: Missing environment variables: {', '.join(missing_vars)}")
            print("   Some tests may fail if these are required")
        else:
            print("✅ Environment variables found")
        
        print()

    def run_test(self, test_name):
        """Run a specific test"""
        if test_name not in self.tests:
            print(f"❌ Unknown test: {test_name}")
            return False
        
        test_info = self.tests[test_name]
        test_file = self.tests_dir / test_info['file']
        
        if not test_file.exists():
            print(f"❌ Test file not found: {test_file}")
            return False
        
        # Check dependency
        if test_info['dependency']:
            dependency_file = self.tests_dir.parent / "debug_runs"
            if not any(dependency_file.glob(f"{test_info['dependency']}_*")):
                print(f"⚠️ Warning: Test '{test_name}' requires '{test_info['dependency']}' to be run first")
                response = input(f"   Continue anyway? (y/n): ").lower().strip()
                if response != 'y':
                    print(f"⏭️ Skipping {test_name}")
                    return False
        
        print(f"🚀 Running: {test_name}")
        print(f"📄 File: {test_info['file']}")
        print(f"📝 Description: {test_info['description']}")
        print("-" * 40)
        
        try:
            # Change to root directory to run test
            original_cwd = os.getcwd()
            os.chdir(self.root_dir)
            
            # Run the test
            result = subprocess.run([
                sys.executable, str(test_file)
            ], capture_output=False, text=True)
            
            # Restore directory
            os.chdir(original_cwd)
            
            if result.returncode == 0:
                print(f"✅ Test '{test_name}' PASSED")
                return True
            else:
                print(f"❌ Test '{test_name}' FAILED (exit code: {result.returncode})")
                return False
                
        except Exception as e:
            print(f"💥 Error running test '{test_name}': {e}")
            return False
        finally:
            print("-" * 40)
            print()

    def run_suite(self, suite_name):
        """Run a test suite"""
        if suite_name not in self.suites:
            print(f"❌ Unknown test suite: {suite_name}")
            return False
        
        test_list = self.suites[suite_name]
        print(f"📦 Running test suite: {suite_name}")
        print(f"🎯 Tests: {', '.join(test_list)}")
        print()
        
        results = {}
        for test_name in test_list:
            results[test_name] = self.run_test(test_name)
        
        # Summary
        passed = sum(1 for success in results.values() if success)
        total = len(results)
        
        print("📊 Test Suite Summary")
        print("=" * 40)
        for test_name, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"  {test_name:<20} {status}")
        
        print(f"\n🎯 Results: {passed}/{total} tests passed")
        
        return passed == total

    def main(self):
        """Main test runner entry point"""
        self.print_header()
        
        if len(sys.argv) < 2:
            print("Usage: python tests/run_tests.py [test_name|suite_name]")
            print()
            self.print_available_tests()
            return 1
        
        target = sys.argv[1].lower()
        
        self.check_environment()
        
        # Check if it's a suite
        if target in self.suites:
            success = self.run_suite(target)
        # Check if it's a test
        elif target in self.tests:
            success = self.run_test(target)
        else:
            print(f"❌ Unknown test or suite: {target}")
            print()
            self.print_available_tests()
            return 1
        
        if success:
            print("🎉 All tests completed successfully!")
            return 0
        else:
            print("💥 Some tests failed. Check output above for details.")
            return 1


if __name__ == "__main__":
    runner = TestRunner()
    sys.exit(runner.main()) 