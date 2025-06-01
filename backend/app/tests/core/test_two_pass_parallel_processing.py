#!/usr/bin/env python3
"""
Test Script for Parallel Processing Engine

This script tests the async parallel processing functionality
with the 8.05-short.csv sample data using small batch sizes
to demonstrate the batching and retry logic.
"""

import asyncio
import sys
import logging
from pathlib import Path
import time

# Add the backend app to the Python path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.core.llm_processing_two_pass import (
    discover_employees_in_file, 
    process_employees_in_parallel,
    stitch_employee_results
)

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_parallel_processing():
    """Test the parallel processing engine with real sample data"""
    
    print("Parallel Processing Engine Test")
    print("=" * 50)
    print("🚀 Testing batch processing with small batch sizes")
    print("⚡ Using retry logic and timeout handling")
    print("📊 Monitoring success rates and performance")
    print()
    
    # Load the sample data file (Short CSV - 4 employees - testing due to API issues with larger file)
    sample_file_path = Path(__file__).parent.parent / "sample_data" / "8.05-short.csv"
    
    if not sample_file_path.exists():
        print(f"❌ ERROR: Sample file not found at {sample_file_path}")
        return
    
    # Read the file
    print(f"📄 Loading file: {sample_file_path}")
    with open(sample_file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    print(f"📊 File size: {len(file_content):,} characters")
    print()
    
    # ⏱️ START TIMING THE COMPLETE TWO-PASS WORKFLOW
    total_workflow_start_time = time.time()
    
    print("=" * 60)
    print("🔍 STEP 1: EMPLOYEE DISCOVERY (Pass 1)")
    print("=" * 60)
    
    try:
        # Step 1: Discover employees
        print("🚀 Starting employee discovery...")
        discovery_start_time = time.time()
        
        discovery_result = await discover_employees_in_file(
            file_content=file_content,
            original_filename="8.05-short.csv"
        )
        
        discovery_end_time = time.time()
        discovery_duration = discovery_end_time - discovery_start_time
        
        print(f"✅ Discovery completed in {discovery_duration:.2f}s")
        print(f"✅ Found {len(discovery_result.employees)} employees:")
        
        # Calculate total estimated punches from Pass 1
        total_estimated_punches = sum(emp.punch_count_estimate for emp in discovery_result.employees)
        
        for i, employee in enumerate(discovery_result.employees, 1):
            print(f"   {i:2d}. '{employee.employee_identifier_in_file}' ({employee.punch_count_estimate} punches)")
        
        print(f"\n📊 Pass 1 Summary:")
        print(f"   - Total employees discovered: {len(discovery_result.employees)}")
        print(f"   - Total estimated punch events: {total_estimated_punches}")
        print(f"   - Discovery time: {discovery_duration:.2f}s")
        
        print("\n" + "=" * 60)
        print("⚡ STEP 2: PARALLEL PROCESSING (Pass 2)")
        print("=" * 60)
        print()
        
        # Step 2: Parallel Processing (Pass 2) - High Throughput Configuration
        print("🚀 Starting parallel employee parsing with high throughput (batch_size=50)...")
        parsing_start_time = time.time()
        
        employee_results = await process_employees_in_parallel(
            file_content=file_content,
            employees=discovery_result.employees,
            original_filename=sample_file_path.name,
            batch_size=50,  # High throughput: process 50 employees simultaneously
            timeout_per_employee=120.0
        )
        
        parsing_end_time = time.time()
        parsing_duration = parsing_end_time - parsing_start_time
        
        # ⏱️ END TIMING THE COMPLETE TWO-PASS WORKFLOW
        total_workflow_end_time = time.time()
        total_workflow_duration = total_workflow_end_time - total_workflow_start_time
        
        print(f"✅ Parallel processing completed in {parsing_duration:.2f}s")
        
        # Calculate actual results from Pass 2
        total_actual_punches = sum(len(result.punch_events) for result in employee_results)
        success_rate = len(employee_results) / len(discovery_result.employees) * 100
        
        print(f"\n📊 Pass 2 Summary:")
        print(f"   - Employees successfully processed: {len(employee_results)}/{len(discovery_result.employees)}")
        print(f"   - Success rate: {success_rate:.1f}%")
        print(f"   - Total actual punch events found: {total_actual_punches}")
        print(f"   - Parallel processing time: {parsing_duration:.2f}s")
        
        print("\n" + "=" * 60)
        print("🎯 TWO-PASS WORKFLOW ANALYSIS")
        print("=" * 60)
        
        # Overall accuracy comparison
        if total_estimated_punches > 0:
            accuracy_percentage = (total_actual_punches / total_estimated_punches) * 100
            difference = total_actual_punches - total_estimated_punches
            difference_sign = "+" if difference >= 0 else ""
        else:
            accuracy_percentage = 0
            difference = 0
            difference_sign = ""
        
        print(f"📈 Accuracy Analysis:")
        print(f"   - Pass 1 Estimated Total: {total_estimated_punches} punch events")
        print(f"   - Pass 2 Actual Total: {total_actual_punches} punch events")
        print(f"   - Difference: {difference_sign}{difference} punch events")
        print(f"   - Accuracy: {accuracy_percentage:.1f}%")
        
        if accuracy_percentage >= 95:
            print(f"   - ✅ Excellent accuracy!")
        elif accuracy_percentage >= 85:
            print(f"   - ⚠️  Good accuracy, minor discrepancies")
        else:
            print(f"   - ❌ Accuracy needs improvement")
        
        print(f"\n⏱️  Performance Analysis:")
        print(f"   - Pass 1 (Discovery) Time: {discovery_duration:.2f}s")
        print(f"   - Pass 2 (Parallel Parsing) Time: {parsing_duration:.2f}s")
        print(f"   - Total End-to-End Time: {total_workflow_duration:.2f}s")
        print(f"   - Pass 2 vs Pass 1 Ratio: {parsing_duration/discovery_duration:.1f}x")
        
        # Performance per employee
        avg_time_per_employee = parsing_duration / len(discovery_result.employees) if len(discovery_result.employees) > 0 else 0
        print(f"   - Average time per employee (Pass 2): {avg_time_per_employee:.2f}s")
        
        # Throughput analysis
        throughput_employees_per_sec = len(discovery_result.employees) / total_workflow_duration if total_workflow_duration > 0 else 0
        throughput_punches_per_sec = total_actual_punches / total_workflow_duration if total_workflow_duration > 0 else 0
        
        print(f"   - Overall throughput: {throughput_employees_per_sec:.1f} employees/sec")
        print(f"   - Punch event throughput: {throughput_punches_per_sec:.1f} punches/sec")
        
        print(f"\n📋 Detailed Employee Results:")
        for i, result in enumerate(employee_results, 1):
            employee_id = result.employee_identifier
            actual_punches = len(result.punch_events)
            
            # Find the corresponding estimated count
            estimated_punches = next(
                (emp.punch_count_estimate for emp in discovery_result.employees 
                 if emp.employee_identifier_in_file == employee_id), 
                0
            )
            
            employee_accuracy = (actual_punches / estimated_punches * 100) if estimated_punches > 0 else 100
            difference = actual_punches - estimated_punches
            difference_sign = "+" if difference >= 0 else ""
            
            print(f"   {i:2d}. '{employee_id}':")
            print(f"       Estimated: {estimated_punches} | Actual: {actual_punches} | "
                  f"Diff: {difference_sign}{difference} | Accuracy: {employee_accuracy:.1f}%")
        
        print("\n" + "=" * 60)
        print("🔧 STEP 3: RESULT STITCHING & VALIDATION")
        print("=" * 60)
        
        # Step 3: Result Stitching with comprehensive validation
        print("🧩 Starting result stitching and validation...")
        stitching_start_time = time.time()
        
        stitched_result = stitch_employee_results(
            discovery_result=discovery_result,
            employee_parsing_results=employee_results,
            original_filename=sample_file_path.name,
            enable_deduplication=True,
            strict_validation=True
        )
        
        stitching_end_time = time.time()
        stitching_duration = stitching_end_time - stitching_start_time
        
        print(f"✅ Result stitching completed in {stitching_duration:.2f}s")
        
        # Display comprehensive stitching results
        metadata = stitched_result['processing_metadata']
        integrity = metadata['data_integrity_report']
        dedup_stats = metadata['deduplication_stats']
        
        print(f"\n📊 Stitching Summary:")
        print(f"   - Final punch events: {len(stitched_result['punch_events'])}")
        print(f"   - Quality score: {metadata['quality_score']:.1f}% ({metadata.get('quality_assessment', 'Unknown')})")
        print(f"   - Employee coverage: {metadata['processed_employees']}/{metadata['discovered_employees']} ({(metadata['processed_employees']/metadata['discovered_employees']*100):.1f}%)")
        print(f"   - Stitching time: {stitching_duration:.2f}s")
        
        print(f"\n🔍 Data Integrity Report:")
        print(f"   - Overall accuracy: {integrity['overall_accuracy']:.1f}%")
        print(f"   - Average employee accuracy: {integrity['average_employee_accuracy']:.1f}%")
        print(f"   - Low accuracy employees: {len(integrity['low_accuracy_employees'])}")
        
        if dedup_stats.get('enabled', True):
            print(f"\n🧹 Deduplication Statistics:")
            print(f"   - Original events: {dedup_stats['original_count']}")
            print(f"   - Final events: {dedup_stats['final_count']}")
            print(f"   - Duplicates removed: {dedup_stats['duplicates_removed']}")
            print(f"   - Deduplication rate: {dedup_stats['deduplication_rate']:.1f}%")
        
        if metadata['validation_issues']:
            print(f"\n⚠️  Validation Issues:")
            for issue in metadata['validation_issues']:
                print(f"   - {issue}")
        
        if stitched_result['parsing_issues']:
            print(f"\n🐛 Parsing Issues:")
            for issue in stitched_result['parsing_issues'][:5]:  # Show first 5
                print(f"   - {issue}")
            if len(stitched_result['parsing_issues']) > 5:
                print(f"   - ... and {len(stitched_result['parsing_issues']) - 5} more")
        
        # Update the final summary to include stitching
        total_workflow_duration = stitching_end_time - total_workflow_start_time
        
        print(f"\n⏱️  Updated Performance Analysis:")
        print(f"   - Pass 1 (Discovery) Time: {discovery_duration:.2f}s")
        print(f"   - Pass 2 (Parallel Parsing) Time: {parsing_duration:.2f}s")
        print(f"   - Pass 3 (Result Stitching) Time: {stitching_duration:.2f}s")
        print(f"   - Total End-to-End Time: {total_workflow_duration:.2f}s")
        print(f"   - Final Quality Score: {metadata['quality_score']:.1f}%")
        
        print("\n🎉 Complete two-pass workflow with stitching analysis completed successfully!")
        print("💡 Key insights:")
        print("   - ✅ End-to-end timing measurement")
        print("   - ✅ Pass 1 vs Pass 2 accuracy comparison")
        print("   - ✅ Individual employee accuracy analysis")
        print("   - ✅ Comprehensive result stitching and validation")
        print("   - ✅ Data integrity checks and quality scoring")
        print("   - ✅ Deduplication and error reporting")
        print("   - ✅ Throughput and performance metrics")
        print("   - ✅ Comprehensive debugging information")
        
    except Exception as e:
        print(f"\n❌ ERROR during parallel processing test: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_parallel_processing()) 