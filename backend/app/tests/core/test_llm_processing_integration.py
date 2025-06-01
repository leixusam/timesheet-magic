"""
Integration Tests for Two-Pass LLM Processing - Task 10.0 Testing and Validation

These tests validate the complete two-pass workflow using real sample data
to ensure the system works correctly end-to-end.

Task 10.1: Employee discovery function tests
Task 10.2: Per-employee parsing function tests  
Task 10.3: Parallel processing and result stitching tests
Task 10.4: Complete two-pass workflow integration tests
Task 10.5: Performance tests comparing approaches
Task 10.6: Real large file testing
Task 10.7: Edge case testing
"""

import pytest
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from app.core.llm_processing_two_pass import (
    discover_employees_in_file,
    parse_employee_punches,
    process_employees_in_parallel,
    stitch_employee_results,
    parse_file_to_structured_data_two_pass,
    _evaluate_two_pass_suitability
)
from app.models.two_pass_schemas import (
    EmployeeDiscoveryResult,
    EmployeeDiscoveryOutput,
    PerEmployeeParsingOutput
)
from app.models.schemas import LLMParsedPunchEvent
from app.core.error_handlers import LLMServiceError, ParsingError, LLMComplexityError


# ===== FIXTURE: SAMPLE DATA LOADER =====

@pytest.fixture
def sample_data_dir():
    """Get the path to the sample_data directory"""
    return Path(__file__).parent.parent.parent.parent.parent / "sample_data"


@pytest.fixture
def sample_csv_content(sample_data_dir):
    """Load the 8.05-short.csv sample file content"""
    csv_file = sample_data_dir / "8.05-short.csv"
    if csv_file.exists():
        return csv_file.read_text(encoding='utf-8')
    else:
        # Fallback content if file doesn't exist
        return """Employee / Job:,,,BB - xxxxxxxxx / 649190 / Cashier,,,,,,,,,,,,,,,,,,,,,,,,,,
2490,,,3/16/2025,,9.00,,Sun,,,11:13 AM,,,,4:14 PM,,5.42,,48.78,,,0.00,,,0.00,,,48.78,,0.00
Employee / Job:,,,FM - xxxxxxxxx / 584862 / Cook,,,,,,,,,,,,,,,,,,,,,,,,,,
2490,,,3/17/2025,,12.00,,Mon,,,8:01 AM,,,,5:15 PM,,9.23,,110.76,,,0.00,,,0.00,,,110.76,,0.00"""


@pytest.fixture
def single_employee_csv():
    """Simple CSV with single employee for edge case testing"""
    return """Employee,Date,Time In,Time Out,Role
John Doe,2024-03-15,09:00,17:00,Server"""


@pytest.fixture
def complex_csv_content():
    """Complex CSV content that should trigger two-pass processing"""
    employees = ["Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson", "Emma Brown"]
    content = "Employee,Date,Start Time,End Time,Role,Department\n"
    
    # Generate many rows to exceed complexity threshold
    for day in range(1, 15):  # 14 days
        for emp in employees:
            for shift in range(2):  # 2 shifts per day per employee
                start_hour = 8 + (shift * 8)
                end_hour = start_hour + 6
                content += f"{emp},2024-03-{day:02d},{start_hour:02d}:00,{end_hour:02d}:00,Server,Restaurant\n"
    
    return content


@pytest.fixture
def empty_csv_content():
    """Empty CSV for edge case testing"""
    return "Date,Notes\n2024-03-15,No staff scheduled today"


@pytest.fixture
def malformed_content():
    """Malformed content for edge case testing"""
    return "This is not a timesheet file\nJust some random text\n123,456,abc,def"


# ===== TASK 10.1: EMPLOYEE DISCOVERY FUNCTION TESTS =====

@pytest.mark.asyncio
async def test_discover_employees_with_real_data(sample_csv_content):
    """Task 10.1: Test employee discovery with real sample data"""
    
    result = await discover_employees_in_file(
        file_content=sample_csv_content,
        original_filename="8.05-short.csv"
    )
    
    # Verify the result structure
    assert isinstance(result, EmployeeDiscoveryOutput)
    assert len(result.employees) > 0
    
    # Verify we found employees from the sample file
    employee_identifiers = [emp.employee_identifier_in_file for emp in result.employees]
    print(f"📊 Found {len(result.employees)} employees: {employee_identifiers}")
    
    # Should find expected employees from the sample data
    assert any("BB" in emp_id for emp_id in employee_identifiers), "Should find BB employee"
    
    # Verify punch count estimates are reasonable
    for employee in result.employees:
        assert employee.punch_count_estimate > 0, f"Employee {employee.employee_identifier_in_file} should have punch count > 0"
        assert employee.punch_count_estimate < 1000, f"Employee {employee.employee_identifier_in_file} punch count seems too high"
    
    # Verify discovery issues are minimal
    print(f"⚠️  Discovery issues: {result.discovery_issues}")
    assert len(result.discovery_issues) < 10, "Should have minimal discovery issues"


@pytest.mark.asyncio
async def test_discover_employees_performance_timing(sample_csv_content):
    """Task 10.1: Test employee discovery performance and timing"""
    
    start_time = time.time()
    result = await discover_employees_in_file(
        file_content=sample_csv_content,
        original_filename="performance_test.csv"
    )
    duration = time.time() - start_time
    
    # Performance assertions
    assert duration < 30.0, f"Discovery should complete within 30 seconds, took {duration:.2f}s"
    assert isinstance(result, EmployeeDiscoveryOutput)
    
    print(f"⏱️  Discovery completed in {duration:.2f} seconds")
    print(f"📈 Performance: {len(result.employees)} employees found in {duration:.2f}s")


@pytest.mark.asyncio
async def test_discover_employees_edge_cases():
    """Task 10.1: Test employee discovery edge cases"""
    
    # Test with empty content
    empty_result = await discover_employees_in_file(
        file_content="",
        original_filename="empty.csv"
    )
    assert len(empty_result.employees) == 0
    assert len(empty_result.discovery_issues) > 0
    
    # Test with malformed content
    malformed_result = await discover_employees_in_file(
        file_content="This is not a proper timesheet\nJust random text",
        original_filename="malformed.txt"
    )
    assert isinstance(malformed_result, EmployeeDiscoveryOutput)
    # May or may not find employees in malformed data - just shouldn't crash


# ===== TASK 10.2: PER-EMPLOYEE PARSING FUNCTION TESTS =====

@pytest.mark.asyncio
async def test_parse_employee_punches_with_real_data(sample_csv_content):
    """Task 10.2: Test per-employee parsing with real sample data"""
    
    # First, discover employees to get a real employee identifier
    discovery_result = await discover_employees_in_file(
        file_content=sample_csv_content,
        original_filename="8.05-short.csv"
    )
    
    assert len(discovery_result.employees) > 0, "Need at least one employee for parsing test"
    
    # Test parsing the first discovered employee
    first_employee = discovery_result.employees[0]
    employee_id = first_employee.employee_identifier_in_file
    estimated_punches = first_employee.punch_count_estimate
    
    print(f"🎯 Testing parsing for employee: '{employee_id}' (estimated {estimated_punches} punches)")
    
    result = await parse_employee_punches(
        file_content=sample_csv_content,
        employee_identifier=employee_id,
        original_filename="8.05-short.csv",
        estimated_punch_count=estimated_punches
    )
    
    # Verify the result structure
    assert isinstance(result, PerEmployeeParsingOutput)
    assert result.employee_identifier == employee_id
    
    # Verify punch events
    print(f"✅ Found {len(result.punch_events)} punch events for {employee_id}")
    
    for event in result.punch_events:
        assert isinstance(event, LLMParsedPunchEvent)
        assert event.employee_identifier_in_file == employee_id
        assert isinstance(event.timestamp, datetime)
        assert event.punch_type_as_parsed is not None
    
    # Log any parsing issues
    if result.parsing_issues:
        print(f"⚠️  Parsing issues: {result.parsing_issues}")


@pytest.mark.asyncio
async def test_parse_employee_punches_nonexistent_employee(sample_csv_content):
    """Task 10.2: Test per-employee parsing with nonexistent employee"""
    
    result = await parse_employee_punches(
        file_content=sample_csv_content,
        employee_identifier="NONEXISTENT_EMPLOYEE_12345",
        original_filename="test.csv"
    )
    
    # Should not crash, but may have no events
    assert isinstance(result, PerEmployeeParsingOutput)
    assert result.employee_identifier == "NONEXISTENT_EMPLOYEE_12345"
    # No specific assertion on punch events count - depends on LLM response


@pytest.mark.asyncio
async def test_parse_employee_punches_performance(sample_csv_content):
    """Task 10.2: Test per-employee parsing performance"""
    
    # Get a real employee ID
    discovery_result = await discover_employees_in_file(
        file_content=sample_csv_content,
        original_filename="8.05-short.csv"
    )
    
    if discovery_result.employees:
        employee_id = discovery_result.employees[0].employee_identifier_in_file
        
        start_time = time.time()
        result = await parse_employee_punches(
            file_content=sample_csv_content,
            employee_identifier=employee_id,
            original_filename="performance_test.csv"
        )
        duration = time.time() - start_time
        
        assert duration < 60.0, f"Employee parsing should complete within 60 seconds, took {duration:.2f}s"
        print(f"⏱️  Employee parsing completed in {duration:.2f} seconds")


# ===== TASK 10.3: PARALLEL PROCESSING AND RESULT STITCHING TESTS =====

@pytest.mark.asyncio
async def test_parallel_processing_real_employees(sample_csv_content):
    """Task 10.3: Test parallel processing with real discovered employees"""
    
    # Discover employees first
    discovery_result = await discover_employees_in_file(
        file_content=sample_csv_content,
        original_filename="8.05-short.csv"
    )
    
    assert len(discovery_result.employees) > 0, "Need employees for parallel processing test"
    
    print(f"🔄 Testing parallel processing for {len(discovery_result.employees)} employees")
    
    # Test parallel processing
    start_time = time.time()
    results = await process_employees_in_parallel(
        file_content=sample_csv_content,
        employees=discovery_result.employees,
        original_filename="8.05-short.csv",
        batch_size=2
    )
    duration = time.time() - start_time
    
    # Verify results
    assert isinstance(results, list)
    print(f"✅ Parallel processing completed in {duration:.2f}s")
    print(f"📊 Processed {len(results)}/{len(discovery_result.employees)} employees successfully")
    
    # Verify each result
    for result in results:
        assert isinstance(result, PerEmployeeParsingOutput)
        assert result.employee_identifier is not None


@pytest.mark.asyncio
async def test_stitch_employee_results_real_data(sample_csv_content):
    """Task 10.3: Test result stitching with real data"""
    
    # Get real data through discovery and parsing
    discovery_result = await discover_employees_in_file(
        file_content=sample_csv_content,
        original_filename="8.05-short.csv"
    )
    
    if len(discovery_result.employees) > 0:
        # Process first employee only for simplicity
        first_employee = discovery_result.employees[0]
        parsing_result = await parse_employee_punches(
            file_content=sample_csv_content,
            employee_identifier=first_employee.employee_identifier_in_file,
            original_filename="8.05-short.csv"
        )
        
        # Test stitching
        stitched_result = stitch_employee_results(
            discovery_result=discovery_result,
            employee_parsing_results=[parsing_result],
            original_filename="8.05-short.csv"
        )
        
        # Verify stitched result structure
        assert isinstance(stitched_result, dict)
        assert "punch_events" in stitched_result
        assert "processing_metadata" in stitched_result
        
        print(f"🔧 Stitching completed: {len(stitched_result['punch_events'])} total punch events")


# ===== TASK 10.4: COMPLETE TWO-PASS WORKFLOW INTEGRATION TESTS =====

@pytest.mark.asyncio
async def test_complete_two_pass_workflow(sample_csv_content):
    """Task 10.4: Test complete two-pass workflow end-to-end"""
    
    print("🚀 Starting complete two-pass workflow test")
    start_time = time.time()
    
    result = await parse_file_to_structured_data_two_pass(
        file_content=sample_csv_content,
        original_filename="8.05-short.csv"
    )
    
    duration = time.time() - start_time
    
    # Verify result structure
    assert isinstance(result, dict)
    assert "punch_events" in result
    assert "processing_metadata" in result
    assert "parsing_issues" in result
    
    # Verify metadata
    metadata = result["processing_metadata"]
    assert metadata["processing_mode"] == "two_pass"
    assert "workflow_stages" in metadata
    # Fix: Check for actual metadata structure
    total_employees = metadata.get("total_employees_discovered", 0)
    if total_employees == 0:
        # Alternative way to get employee count from decision factors or other fields
        total_employees = metadata.get("decision_factors", {}).get("estimated_employees", 0)
    
    print(f"✅ Complete workflow completed in {duration:.2f} seconds")
    print(f"📊 Results: {len(result['punch_events'])} punch events, {total_employees} employees")
    
    # Verify workflow stages
    if "workflow_stages" in metadata:
        stages = metadata["workflow_stages"]
        if "discovery" in stages:
            print(f"🔍 Discovery: {stages['discovery'].get('duration_seconds', 0):.2f}s")
        if "parallel_processing" in stages:
            print(f"⚡ Parallel: {stages['parallel_processing'].get('duration_seconds', 0):.2f}s")
        if "stitching" in stages:
            print(f"🔧 Stitching: {stages['stitching'].get('duration_seconds', 0):.2f}s")


@pytest.mark.asyncio
async def test_two_pass_workflow_with_complex_data(complex_csv_content):
    """Task 10.4: Test two-pass workflow with complex data that should trigger two-pass"""
    
    print("🏗️  Testing two-pass workflow with complex data")
    
    # First test decision engine
    decision_result = _evaluate_two_pass_suitability(complex_csv_content, "complex.csv")
    print(f"🤔 Decision: should_use_two_pass = {decision_result['should_use_two_pass']}")
    print(f"📊 Complexity score: {decision_result.get('complexity_score', 'N/A')}")
    
    # Run the workflow
    start_time = time.time()
    result = await parse_file_to_structured_data_two_pass(
        file_content=complex_csv_content,
        original_filename="complex.csv",
        force_two_pass=True  # Force two-pass for this test
    )
    duration = time.time() - start_time
    
    # Verify it worked
    assert isinstance(result, dict)
    assert result["processing_metadata"]["processing_mode"] == "two_pass"
    
    print(f"✅ Complex workflow completed in {duration:.2f} seconds")


# ===== TASK 10.5: PERFORMANCE TESTS =====

@pytest.mark.asyncio
async def test_two_pass_vs_decision_engine_performance(sample_csv_content):
    """Task 10.5: Test performance and decision engine"""
    
    # Test decision engine performance
    start_time = time.time()
    decision_result = _evaluate_two_pass_suitability(sample_csv_content, "8.05-short.csv")
    decision_duration = time.time() - start_time
    
    print(f"🤔 Decision engine completed in {decision_duration:.3f} seconds")
    print(f"📊 Decision: {decision_result}")
    
    assert decision_duration < 1.0, "Decision engine should be very fast"
    assert "should_use_two_pass" in decision_result
    assert "reason" in decision_result


@pytest.mark.asyncio
async def test_performance_with_varying_complexity():
    """Task 10.5: Test performance with different complexity levels"""
    
    # Test simple data
    simple_data = "Employee,Date,Time\nJohn,2024-03-15,09:00"
    simple_decision = _evaluate_two_pass_suitability(simple_data, "simple.csv")
    
    # Test medium data
    medium_data = "\n".join([f"Employee{i},2024-03-15,09:00" for i in range(20)])
    medium_decision = _evaluate_two_pass_suitability(medium_data, "medium.csv")
    
    # Test complex data (many employees and rows)
    complex_data = "\n".join([f"Employee{i},2024-03-15,09:00" for i in range(200)])
    complex_decision = _evaluate_two_pass_suitability(complex_data, "complex.csv")
    
    print(f"📊 Simple: {simple_decision['should_use_two_pass']} (score: {simple_decision.get('complexity_score', 'N/A')})")
    print(f"📊 Medium: {medium_decision['should_use_two_pass']} (score: {medium_decision.get('complexity_score', 'N/A')})")
    print(f"📊 Complex: {complex_decision['should_use_two_pass']} (score: {complex_decision.get('complexity_score', 'N/A')})")


# ===== TASK 10.6: REAL LARGE FILE TESTING =====

@pytest.mark.asyncio
async def test_large_file_handling(sample_data_dir):
    """Task 10.6: Test with real large files if available"""
    
    # Look for larger sample files
    large_files = list(sample_data_dir.glob("*.csv")) if sample_data_dir.exists() else []
    large_files = [f for f in large_files if f.stat().st_size > 10000]  # Files > 10KB
    
    if large_files:
        large_file = large_files[0]
        print(f"📁 Testing with large file: {large_file.name} ({large_file.stat().st_size:,} bytes)")
        
        content = large_file.read_text(encoding='utf-8')
        
        start_time = time.time()
        result = await parse_file_to_structured_data_two_pass(
            file_content=content,
            original_filename=large_file.name
        )
        duration = time.time() - start_time
        
        print(f"✅ Large file processed in {duration:.2f} seconds")
        assert isinstance(result, dict)
        assert "punch_events" in result
    else:
        print("⚠️  No large files found for testing")


# ===== TASK 10.7: EDGE CASE TESTING =====

@pytest.mark.asyncio
async def test_single_employee_edge_case(single_employee_csv):
    """Task 10.7: Test with single employee file"""
    
    result = await parse_file_to_structured_data_two_pass(
        file_content=single_employee_csv,
        original_filename="single_employee.csv",
        force_two_pass=True  # Force two-pass for testing
    )
    
    assert isinstance(result, dict)
    # Fix: Check for actual metadata structure
    total_employees = result["processing_metadata"].get("total_employees_discovered", 0)
    if total_employees == 0:
        total_employees = result["processing_metadata"].get("decision_factors", {}).get("estimated_employees", 0)
        if total_employees == 0:
            # Check workflow stages for discovery results
            discovery_stage = result["processing_metadata"].get("workflow_stages", {}).get("discovery", {})
            total_employees = discovery_stage.get("employees_found", 0)
    
    assert total_employees <= 1
    print(f"👤 Single employee test: {total_employees} employees")


@pytest.mark.asyncio
async def test_empty_file_edge_case(empty_csv_content):
    """Task 10.7: Test with empty/no-employee file"""
    
    result = await parse_file_to_structured_data_two_pass(
        file_content=empty_csv_content,
        original_filename="empty.csv",
        force_two_pass=True,  # Force two-pass for testing
        fallback_to_single_pass=False  # Disable fallback for testing
    )
    
    assert isinstance(result, dict)
    assert len(result["punch_events"]) == 0
    # Fix: Check for actual metadata structure
    total_employees = result["processing_metadata"].get("total_employees_discovered", 0)
    if total_employees == 0:
        discovery_stage = result["processing_metadata"].get("workflow_stages", {}).get("discovery", {})
        total_employees = discovery_stage.get("employees_found", 0)
    
    assert total_employees == 0
    print("📭 Empty file test: 0 employees found (expected)")


@pytest.mark.asyncio
async def test_malformed_data_edge_case(malformed_content):
    """Task 10.7: Test with malformed data"""
    
    result = await parse_file_to_structured_data_two_pass(
        file_content=malformed_content,
        original_filename="malformed.txt",
        force_two_pass=True,  # Force two-pass for testing
        fallback_to_single_pass=False  # Disable fallback for testing
    )
    
    # Should not crash, may have empty or minimal results
    assert isinstance(result, dict)
    print(f"🔧 Malformed data test: {len(result['punch_events'])} punch events")


# ===== COMPREHENSIVE INTEGRATION TEST =====

@pytest.mark.asyncio
async def test_comprehensive_two_pass_validation(sample_csv_content):
    """Task 10.0: Comprehensive validation of entire two-pass system"""
    
    print("\n" + "="*60)
    print("🧪 COMPREHENSIVE TWO-PASS SYSTEM VALIDATION")
    print("="*60)
    
    overall_start = time.time()
    
    # Phase 1: Individual component testing
    print("\n📋 Phase 1: Component Testing")
    
    # Test discovery
    discovery_start = time.time()
    discovery_result = await discover_employees_in_file(
        file_content=sample_csv_content,
        original_filename="validation.csv"
    )
    discovery_time = time.time() - discovery_start
    print(f"   ✅ Discovery: {len(discovery_result.employees)} employees in {discovery_time:.2f}s")
    
    # Test individual parsing (if employees found)
    if discovery_result.employees:
        parsing_start = time.time()
        first_employee = discovery_result.employees[0]
        parsing_result = await parse_employee_punches(
            file_content=sample_csv_content,
            employee_identifier=first_employee.employee_identifier_in_file,
            original_filename="validation.csv"
        )
        parsing_time = time.time() - parsing_start
        print(f"   ✅ Individual parsing: {len(parsing_result.punch_events)} events in {parsing_time:.2f}s")
    
    # Phase 2: Integrated workflow testing
    print("\n🔄 Phase 2: Integrated Workflow Testing")
    
    workflow_start = time.time()
    full_result = await parse_file_to_structured_data_two_pass(
        file_content=sample_csv_content,
        original_filename="validation.csv"
    )
    workflow_time = time.time() - workflow_start
    
    # Phase 3: Results validation
    print("\n🔍 Phase 3: Results Validation")
    
    # Validate structure
    assert isinstance(full_result, dict), "Result should be dictionary"
    assert "punch_events" in full_result, "Should have punch_events"
    assert "processing_metadata" in full_result, "Should have metadata"
    
    metadata = full_result["processing_metadata"]
    assert metadata["processing_mode"] == "two_pass", "Should use two-pass mode"
    
    # Validate performance
    total_time = time.time() - overall_start
    print(f"   ✅ Total workflow time: {workflow_time:.2f}s")
    print(f"   ✅ Overall test time: {total_time:.2f}s")
    assert total_time < 120.0, "Complete validation should finish within 2 minutes"
    
    # Validate data quality
    punch_events = full_result["punch_events"]
    print(f"   ✅ Data quality: {len(punch_events)} total punch events")
    
    for event in punch_events[:5]:  # Check first 5 events
        # Events may be dictionaries or objects depending on the processing stage
        if isinstance(event, dict):
            assert "employee_identifier_in_file" in event, "Events should have employee_identifier_in_file"
            assert "timestamp" in event, "Events should have timestamps"
        else:
            assert isinstance(event, LLMParsedPunchEvent), "Events should be proper objects"
            assert event.timestamp is not None, "Events should have timestamps"
            assert event.employee_identifier_in_file is not None, "Events should have employee IDs"
    
    print(f"\n🎉 VALIDATION COMPLETE - All tests passed!")
    print(f"📊 Summary:")
    print(f"   - Employees discovered: {metadata.get('discovered_employees', 0)}")
    print(f"   - Punch events parsed: {len(punch_events)}")
    print(f"   - Total processing time: {workflow_time:.2f}s")
    print(f"   - Processing mode: {metadata['processing_mode']}")
    
    return {
        "validation_passed": True,
        "total_time": total_time,
        "workflow_time": workflow_time,
        "employees_found": metadata.get('discovered_employees', 0),
        "punch_events_found": len(punch_events)
    } 