#!/usr/bin/env python3
"""
Unified Test Runner for TimeSheet Magic
Runs both unit tests (pytest) and integration tests
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def get_python_executable():
    """Get the appropriate Python executable (prefer venv)"""
    script_dir = Path(__file__).parent
    
    # Check for virtual environments in order of preference
    venv_paths = [
        script_dir / "venv" / "bin" / "python",
        script_dir / "backend" / "venv_local" / "bin" / "python",
        script_dir / "venv" / "Scripts" / "python.exe",  # Windows
        script_dir / "backend" / "venv_local" / "Scripts" / "python.exe",  # Windows
    ]
    
    for venv_python in venv_paths:
        if venv_python.exists():
            print(f"✅ Using virtual environment: {venv_python}")
            return str(venv_python)
    
    # Fall back to system Python
    print("⚠️  No virtual environment found, using system Python")
    print("   Consider running: source venv/bin/activate")
    return sys.executable

def run_command(cmd, cwd=None, env=None):
    """Run a command and return success status"""
    print(f"🚀 Running: {' '.join(cmd)}")
    if cwd:
        print(f"   Working directory: {cwd}")
    try:
        result = subprocess.run(cmd, cwd=cwd, env=env, check=True, capture_output=True, text=True)
        print(f"✅ Success: {' '.join(cmd)}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {' '.join(cmd)}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def setup_python_env():
    """Set up Python environment variables for imports"""
    script_dir = Path(__file__).parent
    backend_dir = script_dir / "backend"
    
    # Set up environment variables
    env = os.environ.copy()
    
    # Add backend directory to Python path
    python_path = str(backend_dir)
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{python_path}:{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = python_path
    
    return env

def run_unit_tests():
    """Run backend unit tests with pytest"""
    print("\n🧪 Running Unit Tests (pytest)")
    print("=" * 50)
    
    python_exe = get_python_executable()
    backend_path = Path(__file__).parent / "backend"
    env = setup_python_env()
    
    cmd = [python_exe, "-m", "pytest", "app/tests/", "-v", "--tb=short"]
    return run_command(cmd, cwd=backend_path, env=env)

def run_integration_tests():
    """Run integration tests from tests/ directory"""
    print("\n🔗 Running Integration Tests")
    print("=" * 50)
    
    python_exe = get_python_executable()
    script_dir = Path(__file__).parent
    env = setup_python_env()
    
    test_files = [
        "test_end_to_end.py",
        "test_kpi_calculation.py", 
        "test_compliance_only.py",
        "test_real_excel.py",
        "test_immediate_flow.py"
    ]
    
    success_count = 0
    total_count = len(test_files)
    
    for test_file in test_files:
        test_path = script_dir / "tests" / test_file
        if test_path.exists():
            print(f"\n📋 Running {test_file}...")
            cmd = [python_exe, str(test_path)]
            if run_command(cmd, cwd=script_dir, env=env):
                success_count += 1
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    print(f"\n📊 Integration Tests Complete: {success_count}/{total_count} passed")
    return success_count == total_count

def run_quick_tests():
    """Run a subset of fast tests for quick validation"""
    print("\n⚡ Running Quick Tests")
    print("=" * 50)
    
    python_exe = get_python_executable()
    script_dir = Path(__file__).parent
    backend_path = script_dir / "backend"
    env = setup_python_env()
    
    # Run unit tests (excluding slow ones)
    print("\n🧪 Running Quick Unit Tests...")
    cmd = [python_exe, "-m", "pytest", "app/tests/", "-v", "--tb=short", "-k", "not slow"]
    unit_success = run_command(cmd, cwd=backend_path, env=env)
    
    # Run simple integration test
    print("\n🔗 Running Simple Integration Test...")
    simple_test = script_dir / "tests" / "test_simple.py"
    integration_success = True
    if simple_test.exists():
        cmd = [python_exe, str(simple_test)]
        integration_success = run_command(cmd, cwd=script_dir, env=env)
    else:
        print("⚠️  test_simple.py not found, skipping")
    
    return unit_success and integration_success

def main():
    parser = argparse.ArgumentParser(description="TimeSheet Magic Test Runner")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "all", "quick"],
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    print("🧪 TimeSheet Magic Test Suite")
    print("=" * 60)
    
    success = True
    
    if args.type in ["unit", "all"]:
        if not run_unit_tests():
            success = False
    
    if args.type in ["integration", "all"]:
        if not run_integration_tests():
            success = False
    
    if args.type == "quick":
        if not run_quick_tests():
            success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 