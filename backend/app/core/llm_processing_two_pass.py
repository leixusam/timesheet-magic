"""
Two-Pass LLM Processing Module

This module implements the two-pass approach to timesheet processing that solves
Gemini's output token limits by separating employee discovery from individual parsing.

Pass 1: Employee Discovery - Fast identification of all employees
Pass 2: Per-Employee Parsing - Parallel processing of individual employees
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.models.two_pass_schemas import (
    EmployeeDiscoveryResult, 
    EmployeeDiscoveryOutput,
    PerEmployeeParsingInput,
    PerEmployeeParsingOutput,
    TwoPassProcessingResult,
    employee_discovery_to_gemini_tool_dict,
    per_employee_parsing_to_gemini_tool_dict,
    normalize_employee_discovery_output
)
from app.models.schemas import LLMParsedPunchEvent
from app.core.error_handlers import (
    LLMServiceError, 
    ParsingError, 
    LLMComplexityError,
    TwoPassDiscoveryError,
    TwoPassEmployeeParsingError,
    TwoPassPartialSuccessError
)

# Import LLM utilities
try:
    from llm_utils.google_utils import get_gemini_response_with_function_calling, get_gemini_response_with_function_calling_async
except ImportError:
    # Fallback for testing environment
    from backend.llm_utils.google_utils import get_gemini_response_with_function_calling, get_gemini_response_with_function_calling_async

# Load configuration
import json
from pathlib import Path

# Import metrics collection for Task 11.3
from app.core.metrics_collector import collect_two_pass_metrics

def load_config():
    """Load configuration from config.json"""
    config_path = Path(__file__).parent.parent.parent / "config.json"
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback for testing environment
        config_path = Path(__file__).parent.parent.parent.parent / "backend" / "config.json" 
        with open(config_path, 'r') as f:
            return json.load(f)

config = load_config()

logger = logging.getLogger(__name__)


async def discover_employees_in_file(
    file_content: str,
    original_filename: str
) -> EmployeeDiscoveryOutput:
    """
    Pass 1: Discover all unique employees in the timesheet file with accurate punch counts.
    
    This function performs the first pass of the two-pass approach by identifying
    all employees in the file and providing accurate estimates of their individual
    punch event counts (Clock In, Clock Out, Break Start, Break End all count as separate punches).
    
    Args:
        file_content: The raw content of the timesheet file
        original_filename: Name of the original file for logging
        
    Returns:
        EmployeeDiscoveryOutput containing list of discovered employees and any issues
        
    Raises:
        LLMServiceError: If the LLM service fails
        ParsingError: If the response cannot be parsed
        LLMComplexityError: If the file is too complex for discovery
    """
    start_time = time.time()
    logger.info(f"Starting employee discovery for '{original_filename}'")
    
    try:
        # Create the discovery prompt with emphasis on accurate punch counting
        discovery_prompt = f"""
You are analyzing a timesheet file to discover all unique employees and count their individual punch events.

CRITICAL PUNCH COUNTING RULES - READ CAREFULLY:
- Count EVERY individual punch action as a separate punch event. 
- Each timestamp = 1 punch event. 
- Even if a row has multiple timestamps, count each one as a separate punch event.
- For example: Clock In = 1 punch
- For example: Clock Out = 1 punch  
- For example: Break Start = 1 punch
- For example: Break End = 1 punch
- For example: Meal Start = 1 punch
- For example: Meal End = 1 punch
- For example: Any other time recording action = 1 punch

IMPORTANT: DO NOT count "pairs" - count each individual action!

COUNTING EXAMPLES:
Example 1 - If you see these 6 timestamp entries for an employee:
- 9:00 AM Clock In
- 12:00 PM Break Start  
- 12:30 PM Break End
- 3:00 PM Break Start
- 3:15 PM Break End
- 5:00 PM Clock Out
That's 6 individual punches, NOT 3 pairs!

Example 2 - A typical workday might have:
- Clock In (1)
- Break Start (2) 
- Break End (3)
- Lunch Start (4)
- Lunch End (5)
- Break Start (6)
- Break End (7)
- Clock Out (8)
= 8 individual punch events for ONE day

ESTIMATION STRATEGY:
- Look for ALL timestamp entries for each employee
- Count each timestamp as 1 punch event
- A full workday typically has 4-8+ individual punch events
- Employees working multiple days will have many more punches
- Be accurate in your counting - count every individual timestamp entry
- Provide the actual count of timestamp entries you find

INSTRUCTIONS:
1. Scan the entire file and identify all unique employees
2. For each employee, find ALL their timestamp entries
3. Count each timestamp as one individual punch event
4. Use the EXACT employee identifier as it appears in the file
5. Provide accurate punch count estimates by counting EVERY individual timestamp
6. MUST use the function call format - do not provide explanatory text

File to analyze:
```
{file_content}
```

Please discover all employees and provide accurate individual punch event counts for each.
Use the discover_employees function call format.
"""
        
        # Get the function calling tool schema
        tool_schema = employee_discovery_to_gemini_tool_dict()
        
        # Call Gemini with function calling to discover employees
        response = await get_gemini_response_with_function_calling_async(
            prompt_parts=[discovery_prompt],
            tools=[tool_schema],
            model_name_override=config["google"]["default_model"],
            temperature=0.1
        )
        
        # Handle string response (error or text with JSON)
        if isinstance(response, str):
            if "Error:" in response:
                raise Exception(response)
            else:
                # Try to extract JSON from text response
                import re
                import json as json_module
                
                # Look for JSON block in the response
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group(1)
                        response = json_module.loads(json_str)
                        logger.info("Successfully extracted JSON from text response")
                    except json_module.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON from text response: {e}")
                        raise Exception(f"Text response contained invalid JSON: {e}")
                else:
                    raise Exception(f"Text response without valid JSON block: {response[:500]}...")
        
        # Parse the response into our schema
        discovery_output = EmployeeDiscoveryOutput(**response)
        
        # Normalize and validate the output
        normalized_output = normalize_employee_discovery_output(
            discovery_output, file_content
        )
        
        execution_time = time.time() - start_time
        logger.info(
            f"Employee discovery completed for '{original_filename}' in {execution_time:.2f}s - "
            f"Found {len(normalized_output.employees)} employees"
        )
        
        return normalized_output
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            f"Employee discovery failed for '{original_filename}' after {execution_time:.2f}s: {str(e)}"
        )
        
        if "complexity" in str(e).lower() or "token" in str(e).lower():
            raise LLMComplexityError(
                message=f"File too complex for employee discovery: {str(e)}",
                original_filename=original_filename,
                llm_call_details=str(e)
            )
        elif "service" in str(e).lower() or "api" in str(e).lower():
            raise LLMServiceError(
                message=f"LLM service error during discovery: {str(e)}",
                service_name="Google Gemini"
            )
        else:
            raise TwoPassDiscoveryError(
                message=f"Failed to discover employees in timesheet: {str(e)}",
                original_filename=original_filename,
                file_size=len(file_content),
                discovery_issues=[str(e)]
            )


def log_punch_count_mismatch(
    employee_identifier: str,
    estimated_count: int,
    actual_count: int,
    original_filename: str,
    accuracy_threshold: float = 90.0
) -> None:
    """
    Log when there's a significant mismatch between estimated and actual punch counts.
    
    Args:
        employee_identifier: The employee identifier
        estimated_count: Count estimated during discovery phase
        actual_count: Actual count found during parsing phase
        original_filename: Name of the original file
        accuracy_threshold: Minimum accuracy percentage to avoid logging (default 90%)
    """
    if max(estimated_count, actual_count) == 0:
        return  # No data to compare
    
    accuracy = (min(estimated_count, actual_count) / max(estimated_count, actual_count)) * 100
    
    if accuracy < accuracy_threshold:
        difference = abs(estimated_count - actual_count)
        direction = "overestimated" if estimated_count > actual_count else "underestimated"
        
        logger.warning(
            f"PUNCH_COUNT_MISMATCH - File: '{original_filename}' | "
            f"Employee: '{employee_identifier}' | "
            f"Estimated: {estimated_count} | Actual: {actual_count} | "
            f"Accuracy: {accuracy:.1f}% | Direction: {direction} by {difference} punches | "
            f"RETRY_CANDIDATE: True"
        )
        
        # Log with a specific tag for easy filtering/searching
        logger.info(
            f"MISMATCH_DETAILS - Employee='{employee_identifier}' "
            f"EstimatedVsActual={estimated_count}vs{actual_count} "
            f"File='{original_filename}' "
            f"Accuracy={accuracy:.1f}%"
        )


async def parse_employee_punches(
    file_content: str,
    employee_identifier: str,
    original_filename: str,
    estimated_punch_count: Optional[int] = None
) -> PerEmployeeParsingOutput:
    """
    Pass 2: Parse punch events for a specific employee.
    
    This function performs the second pass by focusing on a single employee
    and extracting all their punch events with full detail.
    
    Args:
        file_content: The raw content of the timesheet file
        employee_identifier: The exact identifier of the employee to parse
        original_filename: Name of the original file for logging
        estimated_punch_count: Optional estimated punch count from discovery phase for mismatch logging
        
    Returns:
        PerEmployeeParsingOutput containing the employee's punch events
        
    Raises:
        LLMServiceError: If the LLM service fails
        ParsingError: If the response cannot be parsed
        LLMComplexityError: If the employee data is too complex to parse
    """
    start_time = time.time()
    logger.debug(f"Starting individual parsing for employee '{employee_identifier}' in '{original_filename}'")
    
    try:
        # Create the per-employee parsing prompt
        parsing_prompt = f"""
You are an expert timesheet analyst parsing punch events for ONE specific employee. Your goal is to find EVERY single time recording event for this employee with 100% accuracy.

TARGET EMPLOYEE: "{employee_identifier}"

🎯 CRITICAL SUCCESS CRITERIA:
1. ONLY return punch events for the EXACT employee identifier: "{employee_identifier}"
2. Find EVERY timestamp entry for this employee - missing events causes compliance violations
3. The employee_identifier_in_file field must EXACTLY match: "{employee_identifier}"
4. Ignore all other employees completely

🔍 SYSTEMATIC SCANNING INSTRUCTIONS:
1. First, scan the ENTIRE file for any mention of: "{employee_identifier}"
2. For each mention, look for associated timestamp data (times, dates)
3. Every time entry = one punch event (Clock In, Clock Out, Break Start, Break End, etc.)
4. Look in ALL sections: headers, data rows, totals, notes, anywhere timestamps appear
5. Check for multiple date ranges - employees may work across several days/weeks

📋 PUNCH EVENT TYPES TO EXTRACT (each timestamp = 1 event):
✅ Clock In / Clock Out (start/end of shift)
✅ Break Start / Break End (any break or rest period)  
✅ Meal Start / Meal End (lunch breaks, meal periods)
✅ Department transfers (if timestamped)
✅ Overtime start/end (if timestamped separately)
✅ Holiday/vacation punch adjustments
✅ Manual time corrections (if timestamped)
✅ ANY other time recording events with timestamps

⚠️ COMMON MISTAKES TO AVOID:
- Missing partial days or split shifts
- Overlooking break periods between main work hours
- Missing timestamps in unusual file sections (headers, footers, notes)
- Confusing similar employee identifiers (only extract for EXACT match)
- Missing weekend or holiday work
- Overlooking manual adjustments or corrections

📅 TIMESTAMP PROCESSING:
- Convert timestamps to ISO 8601 format (e.g., "2025-03-16T11:13:00")
- CRITICAL: Do NOT add timezone suffixes like 'Z' to timestamps - this causes 7-hour time shifts
- If the original timesheet shows times like "8:00 AM" or "14:30", treat them as local time (no 'Z' suffix)
- Only add timezone information if it was explicitly present in the source data
- IMPORTANT: Correctly handle AM/PM times. PM times must be converted to 24-hour format (e.g., 5:04 PM = 17:04, 10:25 PM = 22:25, 10:11 PM = 22:11)
- For AM times, keep as-is (e.g., 10:11 AM = 10:11, 5:04 AM = 05:04)
- For dates: use YYYY-MM-DD format consistently

💡 ACCURACY CHECK:
Expected punch count for this employee: {estimated_punch_count if estimated_punch_count else "Unknown"}
Double-check your work - scan the file twice if needed to ensure no timestamps are missed.

📄 FILE CONTENT TO ANALYZE:
```
{file_content}
```

🎯 FINAL INSTRUCTION: Extract ALL punch events for employee "{employee_identifier}". 
Be thorough and systematic - compliance depends on finding every single timestamp entry.
Use the parse_employee_punches function to return your structured findings."""
        
        # Get the function calling tool schema
        tool_schema = per_employee_parsing_to_gemini_tool_dict()
        
        # Make the LLM API call using the async version for true parallel processing
        response = await get_gemini_response_with_function_calling_async(
            prompt_parts=[parsing_prompt],  # Must be a list
            tools=[tool_schema],
            model_name_override=config["google"]["function_calling_model"],
            temperature=0.1
        )
        
        # Handle string response (error or text with JSON)
        if isinstance(response, str):
            if "Error:" in response:
                raise Exception(response)
            else:
                # Try to extract JSON from text response
                import re
                import json as json_module
                
                # Look for JSON block in the response
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group(1)
                        response = json_module.loads(json_str)
                        logger.info("Successfully extracted JSON from text response")
                    except json_module.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON from text response: {e}")
                        raise Exception(f"Text response contained invalid JSON: {e}")
                else:
                    raise Exception(f"Text response without valid JSON block: {response[:500]}...")
        
        # Add employee_identifier to response since Gemini doesn't include it in function calls
        response["employee_identifier"] = employee_identifier
        
        # Parse the response into our schema
        parsing_output = PerEmployeeParsingOutput(**response)
        
        # Validate that all punch events are for the correct employee
        filtered_events = []
        for event_data in parsing_output.punch_events:
            # Convert dict to LLMParsedPunchEvent if needed
            if isinstance(event_data, dict):
                try:
                    # Parse timestamp if it's a string
                    if isinstance(event_data.get("timestamp"), str):
                        timestamp_str = event_data["timestamp"]
                        if timestamp_str.endswith('Z'):
                            import pytz
                            # BUGFIX: MISC-001 - Date parsing off by one day
                            # Convert UTC timestamp to local timezone before creating datetime object
                            # to prevent off-by-one date errors in compliance rules
                            utc_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            
                            # Convert to Pacific Time (California timezone) since this is for restaurant compliance
                            # Restaurant shifts typically occur in local time, not UTC
                            pacific_tz = pytz.timezone('America/Los_Angeles')
                            local_timestamp = utc_timestamp.replace(tzinfo=pytz.UTC).astimezone(pacific_tz)
                            
                            # Use the local timestamp so .date() calls get the correct local date
                            timestamp = local_timestamp
                        else:
                            timestamp = datetime.fromisoformat(timestamp_str)
                        event_data["timestamp"] = timestamp
                    
                    event = LLMParsedPunchEvent(**event_data)
                except Exception as e:
                    logger.warning(f"Failed to parse punch event: {event_data} - Error: {e}")
                    continue
            else:
                event = event_data
            
            # Validate employee identifier
            if event.employee_identifier_in_file == employee_identifier:
                filtered_events.append(event)
            else:
                logger.warning(
                    f"Filtered out punch event for wrong employee: "
                    f"expected '{employee_identifier}', got '{event.employee_identifier_in_file}'"
                )
        
        # Create the final output with filtered events
        final_output = PerEmployeeParsingOutput(
            punch_events=filtered_events,
            employee_identifier=employee_identifier,
            parsing_issues=parsing_output.parsing_issues
        )
        
        # Handle edge case: employee with no punch events
        if len(filtered_events) == 0:
            if estimated_punch_count and estimated_punch_count > 0:
                # Expected punches but found none - this is concerning
                logger.warning(
                    f"ZERO_PUNCH_EVENTS - Employee '{employee_identifier}' had no punch events found, "
                    f"but discovery estimated {estimated_punch_count} punches. "
                    f"File: '{original_filename}' - INVESTIGATE_REQUIRED"
                )
                final_output.parsing_issues.append(
                    f"No punch events found despite estimated count of {estimated_punch_count}"
                )
            else:
                # No punches expected or found - normal case
                logger.info(
                    f"Employee '{employee_identifier}' has no punch events in file '{original_filename}' "
                    f"(expected based on discovery phase)"
                )
        
        execution_time = time.time() - start_time
        logger.debug(
            f"Individual parsing completed for '{employee_identifier}' in {execution_time:.2f}s - "
            f"Found {len(final_output.punch_events)} punch events"
        )
        
        # Log punch count mismatch if estimated_punch_count is provided
        if estimated_punch_count is not None:
            actual_count = len(final_output.punch_events)
            log_punch_count_mismatch(employee_identifier, estimated_punch_count, actual_count, original_filename)
        
        return final_output
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            f"Individual parsing failed for '{employee_identifier}' after {execution_time:.2f}s: {str(e)}"
        )
        
        if "complexity" in str(e).lower() or "token" in str(e).lower():
            raise LLMComplexityError(
                message=f"Employee data too complex for parsing: {str(e)}",
                original_filename=original_filename,
                llm_call_details=str(e)
            )
        elif "service" in str(e).lower() or "api" in str(e).lower():
            raise LLMServiceError(
                message=f"LLM service error during employee parsing: {str(e)}",
                service_name="Google Gemini"
            )
        else:
            raise ParsingError(
                message=f"Failed to parse employee response: {str(e)}",
                filename=original_filename,
                parsing_issues=[str(e)]
            )


# Additional helper functions for the two-pass workflow would go here
# These will be implemented in subsequent tasks (5.0-7.0)

async def process_employees_in_parallel(
    file_content: str,
    employees: List[EmployeeDiscoveryResult],
    original_filename: str,
    batch_size: int = 50,
    max_retries: int = 3,
    timeout_per_employee: float = 120.0,
    retry_delay_base: float = 1.0
) -> List[PerEmployeeParsingOutput]:
    """
    Process multiple employees in parallel batches with retry logic and progress tracking.
    
    This function implements the parallel processing engine for Pass 2, handling
    multiple employees concurrently while managing resources and failures gracefully.
    
    Args:
        file_content: The raw content of the timesheet file
        employees: List of discovered employees from Pass 1
        original_filename: Name of the original file for logging
        batch_size: Number of employees to process simultaneously (default 50)
        max_retries: Maximum retry attempts for failed employees (default 3)
        timeout_per_employee: Timeout in seconds for individual employee parsing (default 120s)
        retry_delay_base: Base delay for exponential backoff (default 1s)
        
    Returns:
        List of PerEmployeeParsingOutput for all successfully processed employees
        
    Raises:
        LLMServiceError: If too many employees fail processing
        TimeoutError: If processing takes too long overall
    """
    start_time = time.time()
    total_employees = len(employees)
    
    logger.info(
        f"Starting parallel processing for {total_employees} employees in '{original_filename}' "
        f"(batch_size={batch_size}, max_retries={max_retries}, timeout={timeout_per_employee}s)"
    )
    
    successful_results = []
    failed_employees = []
    retry_queue = []
    
    # Split employees into batches
    batches = [employees[i:i + batch_size] for i in range(0, total_employees, batch_size)]
    
    for batch_num, batch in enumerate(batches, 1):
        batch_start_time = time.time()
        logger.info(f"Processing batch {batch_num}/{len(batches)} ({len(batch)} employees)")
        
        # Process batch with timeout
        batch_results = await _process_employee_batch(
            file_content=file_content,
            employee_batch=batch,
            original_filename=original_filename,
            timeout_per_employee=timeout_per_employee
        )
        
        # Separate successful and failed results
        for employee, result in zip(batch, batch_results):
            if result is not None:
                successful_results.append(result)
                logger.debug(f"✅ Batch {batch_num}: '{employee.employee_identifier_in_file}' completed successfully")
            else:
                failed_employees.append(employee)
                retry_queue.append((employee, 1))  # (employee, attempt_number)
                logger.warning(f"❌ Batch {batch_num}: '{employee.employee_identifier_in_file}' failed, will retry")
        
        batch_duration = time.time() - batch_start_time
        success_rate = len([r for r in batch_results if r is not None]) / len(batch) * 100
        logger.info(
            f"Batch {batch_num} completed in {batch_duration:.2f}s - "
            f"Success rate: {success_rate:.1f}% ({len([r for r in batch_results if r is not None])}/{len(batch)})"
        )
    
    # Process retry queue with exponential backoff
    if retry_queue:
        logger.info(f"Processing {len(retry_queue)} failed employees with retry logic")
        retry_results = await _process_retry_queue(
            file_content=file_content,
            retry_queue=retry_queue,
            original_filename=original_filename,
            max_retries=max_retries,
            timeout_per_employee=timeout_per_employee,
            retry_delay_base=retry_delay_base
        )
        
        successful_results.extend(retry_results['successful'])
        failed_employees = retry_results['failed']
    
    # Final summary
    total_duration = time.time() - start_time
    success_count = len(successful_results)
    failure_count = len(failed_employees)
    overall_success_rate = success_count / total_employees * 100 if total_employees > 0 else 100
    
    logger.info(
        f"Parallel processing completed in {total_duration:.2f}s - "
        f"Overall success rate: {overall_success_rate:.1f}% ({success_count}/{total_employees})"
    )
    
    if failed_employees:
        failed_ids = [emp.employee_identifier_in_file for emp in failed_employees]
        successful_ids = [result.employee_identifier for result in successful_results]
        
        logger.error(
            f"PARALLEL_PROCESSING_FAILURES - {failure_count} employees failed after all retries: {failed_ids}"
        )
        
        # Determine appropriate error handling based on failure rate
        if failure_count > total_employees * 0.8:  # More than 80% failed - critical failure
            raise TwoPassEmployeeParsingError(
                message=f"Critical parallel processing failure: {failure_count}/{total_employees} employees failed",
                original_filename=original_filename,
                failed_employees=failed_ids,
                successful_employees=successful_ids,
                parsing_issues=[f"High failure rate: {overall_success_rate:.1f}% success"]
            )
        elif failure_count > total_employees * 0.5:  # More than 50% failed - major failure
            raise TwoPassEmployeeParsingError(
                message=f"Major parallel processing failure: {failure_count}/{total_employees} employees failed",
                original_filename=original_filename,
                failed_employees=failed_ids,
                successful_employees=successful_ids,
                parsing_issues=[f"Moderate failure rate: {overall_success_rate:.1f}% success"]
            )
        elif failure_count > 0:  # Some failures - partial success
            # Log the partial success but don't raise an exception
            # The caller can decide how to handle partial results
            logger.warning(
                f"PARTIAL_SUCCESS - {success_count}/{total_employees} employees processed successfully. "
                f"Failed employees: {failed_ids}"
            )
    
    return successful_results


async def _process_employee_batch(
    file_content: str,
    employee_batch: List[EmployeeDiscoveryResult],
    original_filename: str,
    timeout_per_employee: float
) -> List[Optional[PerEmployeeParsingOutput]]:
    """
    Process a single batch of employees in parallel with timeout handling.
    
    Returns a list where each element is either a PerEmployeeParsingOutput or None (for failures).
    """
    
    async def _parse_single_employee_with_timeout(employee: EmployeeDiscoveryResult) -> Optional[PerEmployeeParsingOutput]:
        """Parse a single employee with timeout protection."""
        try:
            # Use asyncio.wait_for to add timeout protection
            result = await asyncio.wait_for(
                parse_employee_punches(
                    file_content=file_content,
                    employee_identifier=employee.employee_identifier_in_file,
                    original_filename=original_filename,
                    estimated_punch_count=employee.punch_count_estimate
                ),
                timeout=timeout_per_employee
            )
            return result
            
        except asyncio.TimeoutError:
            logger.error(
                f"TIMEOUT - Employee '{employee.employee_identifier_in_file}' "
                f"exceeded {timeout_per_employee}s timeout"
            )
            return None
            
        except Exception as e:
            logger.error(
                f"ERROR - Employee '{employee.employee_identifier_in_file}' "
                f"failed with exception: {str(e)}"
            )
            return None
    
    # Process all employees in the batch concurrently
    tasks = [_parse_single_employee_with_timeout(employee) for employee in employee_batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Convert exceptions to None for consistency
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(
                f"EXCEPTION - Employee '{employee_batch[i].employee_identifier_in_file}' "
                f"raised exception: {str(result)}"
            )
            processed_results.append(None)
        else:
            processed_results.append(result)
    
    return processed_results


async def _process_retry_queue(
    file_content: str,
    retry_queue: List[tuple],  # List of (employee, attempt_number)
    original_filename: str,
    max_retries: int,
    timeout_per_employee: float,
    retry_delay_base: float
) -> Dict[str, List]:
    """
    Process failed employees with exponential backoff retry logic.
    
    Returns dict with 'successful' and 'failed' lists.
    """
    successful_results = []
    current_queue = retry_queue.copy()
    
    while current_queue:
        next_queue = []
        
        for employee, attempt_num in current_queue:
            if attempt_num > max_retries:
                continue  # Skip employees that exceeded max retries
            
            # Exponential backoff delay
            if attempt_num > 1:
                delay = retry_delay_base * (2 ** (attempt_num - 2))  # 1s, 2s, 4s, 8s...
                logger.debug(f"Retry attempt {attempt_num} for '{employee.employee_identifier_in_file}' after {delay}s delay")
                await asyncio.sleep(delay)
            
            try:
                result = await asyncio.wait_for(
                    parse_employee_punches(
                        file_content=file_content,
                        employee_identifier=employee.employee_identifier_in_file,
                        original_filename=original_filename,
                        estimated_punch_count=employee.punch_count_estimate
                    ),
                    timeout=timeout_per_employee
                )
                
                successful_results.append(result)
                logger.info(f"✅ Retry success: '{employee.employee_identifier_in_file}' on attempt {attempt_num}")
                
            except Exception as e:
                logger.warning(
                    f"🔄 Retry {attempt_num} failed for '{employee.employee_identifier_in_file}': {str(e)}"
                )
                if attempt_num < max_retries:
                    next_queue.append((employee, attempt_num + 1))
        
        current_queue = next_queue
    
    # Collect final failures
    failed_employees = [emp for emp, _ in current_queue]
    
    return {
        'successful': successful_results,
        'failed': failed_employees
    }


async def parse_file_to_structured_data_two_pass(
    file_content: str,
    original_filename: str,
    enable_two_pass: bool = True,
    force_two_pass: bool = False,
    batch_size: Optional[int] = None,
    timeout_per_employee: Optional[float] = None,
    max_retries: Optional[int] = None,
    enable_deduplication: bool = True,
    strict_validation: bool = True,
    fallback_to_single_pass: bool = True
) -> Dict[str, Any]:
    """
    Main orchestration function for two-pass timesheet processing.
    
    This function coordinates the complete two-pass workflow:
    1. Employee discovery (Pass 1)
    2. Parallel per-employee parsing (Pass 2) 
    3. Result stitching and validation (Pass 3)
    
    Includes intelligent decision logic, comprehensive error handling,
    performance monitoring, and fallback mechanisms.
    
    Args:
        file_content: Raw content of the timesheet file
        original_filename: Name of the original file for logging
        enable_two_pass: Whether to enable two-pass processing (default: True)
        force_two_pass: Force two-pass even if single-pass seems better (default: False)
        batch_size: Number of employees to process in parallel (default: from config)
        timeout_per_employee: Timeout per employee in seconds (default: from config)
        max_retries: Maximum retries for failed operations (default: from config)
        enable_deduplication: Whether to deduplicate results (default: True)
        strict_validation: Whether to enforce strict validation (default: True)
        fallback_to_single_pass: Whether to fallback on failures (default: True)
        
    Returns:
        Dictionary containing parsed results, metadata, and performance metrics
        
    Raises:
        LLMServiceError: If the entire workflow fails
        ParsingError: If validation fails critically
        LLMComplexityError: If the file is too complex to process
    """
    
    workflow_start_time = time.time()
    logger.info(f"Starting two-pass workflow for '{original_filename}' (file_size={len(file_content):,} chars)")
    
    # Load configuration and set defaults
    config = load_config()
    batch_size = batch_size or config.get("two_pass", {}).get("default_batch_size", 50)
    timeout_per_employee = timeout_per_employee or config.get("two_pass", {}).get("timeout_per_employee", 120.0)
    max_retries = max_retries or config.get("two_pass", {}).get("max_retries", 3)
    
    # Initialize result structure
    workflow_result = {
        'punch_events': [],
        'processing_metadata': {
            'original_filename': original_filename,
            'file_size_chars': len(file_content),
            'processing_mode': 'two_pass',
            'workflow_version': '2.0',
            'timestamp': datetime.now().isoformat(),
            'performance_metrics': {},
            'decision_factors': {},
            'workflow_stages': {},
            'configuration': {
                'batch_size': batch_size,
                'timeout_per_employee': timeout_per_employee,
                'max_retries': max_retries,
                'enable_deduplication': enable_deduplication,
                'strict_validation': strict_validation
            }
        },
        'parsing_issues': [],
        'workflow_success': False
    }
    
    try:
        # DECISION PHASE: Determine if two-pass is appropriate
        if enable_two_pass and not force_two_pass:
            decision_result = _evaluate_two_pass_suitability(file_content, original_filename)
            workflow_result['processing_metadata']['decision_factors'] = decision_result
            
            if not decision_result['should_use_two_pass'] and not force_two_pass:
                logger.info(f"Decision engine recommends single-pass for '{original_filename}': {decision_result['reason']}")
                
                if fallback_to_single_pass:
                    # BUGFIX: Implement single-pass fallback
                    logger.info(f"🔄 Using single-pass processing as recommended by decision engine for '{original_filename}'")
                    fallback_result = await _fallback_to_single_pass(
                        file_content=file_content,
                        original_filename=original_filename,
                        failure_reason=f"Decision engine recommendation: {decision_result['reason']}",
                        failure_context=decision_result
                    )
                    return fallback_result
                else:
                    logger.warning(f"Proceeding with two-pass despite recommendation for '{original_filename}'")
        
        # PHASE 1: EMPLOYEE DISCOVERY
        logger.info(f"🔍 PHASE 1: Starting employee discovery for '{original_filename}'")
        discovery_start_time = time.time()
        
        discovery_result = await discover_employees_in_file(
            file_content=file_content,
            original_filename=original_filename
        )
        
        discovery_duration = time.time() - discovery_start_time
        workflow_result['processing_metadata']['workflow_stages']['discovery'] = {
            'duration_seconds': discovery_duration,
            'employees_found': len(discovery_result.employees),
            'total_estimated_punches': sum(emp.punch_count_estimate for emp in discovery_result.employees),
            'success': True
        }
        
        logger.info(f"✅ Discovery completed: {len(discovery_result.employees)} employees, {sum(emp.punch_count_estimate for emp in discovery_result.employees)} estimated punches")
        
        # Check if we found any employees
        if not discovery_result.employees:
            workflow_result['processing_metadata']['workflow_stages']['discovery']['success'] = False
            if fallback_to_single_pass:
                logger.warning(f"No employees discovered for '{original_filename}', falling back to single-pass")
                fallback_result = await _fallback_to_single_pass(
                    file_content=file_content,
                    original_filename=original_filename,
                    failure_reason="No employees discovered in two-pass processing",
                    failure_context={'discovery_result': discovery_result}
                )
                return fallback_result
            else:
                raise ParsingError(
                    message="No employees found in timesheet file",
                    filename=original_filename,
                    parsing_issues=["Employee discovery returned no results"]
                )
        
        # PHASE 2: PARALLEL EMPLOYEE PARSING
        logger.info(f"⚡ PHASE 2: Starting parallel processing for {len(discovery_result.employees)} employees")
        parallel_start_time = time.time()
        
        employee_results = await process_employees_in_parallel(
            file_content=file_content,
            employees=discovery_result.employees,
            original_filename=original_filename,
            batch_size=batch_size,
            max_retries=max_retries,
            timeout_per_employee=timeout_per_employee
        )
        
        parallel_duration = time.time() - parallel_start_time
        workflow_result['processing_metadata']['workflow_stages']['parallel_processing'] = {
            'duration_seconds': parallel_duration,
            'employees_processed': len(employee_results),
            'employees_target': len(discovery_result.employees),
            'success_rate': len(employee_results) / len(discovery_result.employees) * 100 if discovery_result.employees else 0,
            'total_actual_punches': sum(len(result.punch_events) for result in employee_results),
            'success': len(employee_results) > 0
        }
        
        logger.info(f"✅ Parallel processing completed: {len(employee_results)}/{len(discovery_result.employees)} employees processed")
        
        # Check parallel processing success rate
        success_rate = len(employee_results) / len(discovery_result.employees) * 100 if discovery_result.employees else 0
        if success_rate < 50.0:  # Less than 50% success rate
            workflow_result['processing_metadata']['workflow_stages']['parallel_processing']['success'] = False
            if fallback_to_single_pass:
                logger.error(f"Parallel processing success rate too low ({success_rate:.1f}%) for '{original_filename}', falling back to single-pass")
                fallback_result = await _fallback_to_single_pass(
                    file_content=file_content,
                    original_filename=original_filename,
                    failure_reason=f"Parallel processing success rate too low ({success_rate:.1f}%)",
                    failure_context={'employee_results': employee_results, 'success_rate': success_rate}
                )
                return fallback_result
            else:
                raise LLMServiceError(
                    message=f"Parallel processing failed with {success_rate:.1f}% success rate",
                    service_name="Two-Pass Parallel Processing"
                )
        
        # PHASE 3: RESULT STITCHING AND VALIDATION
        logger.info(f"🔧 PHASE 3: Starting result stitching and validation")
        stitching_start_time = time.time()
        
        stitched_result = stitch_employee_results(
            discovery_result=discovery_result,
            employee_parsing_results=employee_results,
            original_filename=original_filename,
            enable_deduplication=enable_deduplication,
            strict_validation=strict_validation
        )
        
        stitching_duration = time.time() - stitching_start_time
        workflow_result['processing_metadata']['workflow_stages']['stitching'] = {
            'duration_seconds': stitching_duration,
            'final_punch_events': len(stitched_result['punch_events']),
            'duplicates_removed': stitched_result['processing_metadata']['deduplication_stats'].get('duplicates_removed', 0),
            'quality_score': stitched_result['processing_metadata']['quality_score'],
            'success': stitched_result['processing_metadata']['quality_score'] >= 50.0
        }
        
        logger.info(f"✅ Result stitching completed: {len(stitched_result['punch_events'])} final punch events, quality score {stitched_result['processing_metadata']['quality_score']:.1f}%")
        
        # FINAL ASSEMBLY: Combine all results
        workflow_result['punch_events'] = stitched_result['punch_events']
        workflow_result['parsing_issues'].extend(stitched_result['parsing_issues'])
        
        # Add comprehensive performance metrics
        total_duration = time.time() - workflow_start_time
        
        # Calculate decision engine metrics
        decision_factors = workflow_result['processing_metadata'].get('decision_factors', {})
        decision_metrics = {
            'complexity_score': decision_factors.get('complexity_score', 0),
            'complexity_threshold': decision_factors.get('complexity_threshold', 0),
            'file_size_category': decision_factors.get('file_size_category', 'unknown'),
            'estimated_employees': decision_factors.get('estimated_employees', 0),
            'content_factors': decision_factors.get('content_factors', []),
            'decision_confidence': min(100, max(0, (decision_factors.get('complexity_score', 0) / max(1, decision_factors.get('complexity_threshold', 1))) * 100))
        }
        
        # Calculate advanced throughput and efficiency metrics
        total_employees = len(discovery_result.employees)
        total_punch_events = len(stitched_result['punch_events'])
        successful_employees = len(employee_results)
        failed_employees = total_employees - successful_employees
        
        # Calculate batch efficiency metrics
        estimated_total_punches = sum(emp.punch_count_estimate for emp in discovery_result.employees)
        actual_total_punches = total_punch_events
        punch_estimation_accuracy = (min(estimated_total_punches, actual_total_punches) / max(1, max(estimated_total_punches, actual_total_punches))) * 100
        
        # Phase efficiency analysis
        phase_efficiency = {
            'discovery_efficiency': (discovery_duration / total_duration) * 100,
            'parallel_processing_efficiency': (parallel_duration / total_duration) * 100,
            'stitching_efficiency': (stitching_duration / total_duration) * 100,
            'discovery_employees_per_second': total_employees / max(0.1, discovery_duration),
            'parallel_processing_success_rate': (successful_employees / max(1, total_employees)) * 100,
            'stitching_events_per_second': total_punch_events / max(0.1, stitching_duration)
        }
        
        # Resource utilization metrics
        resource_metrics = {
            'batch_size_used': batch_size,
            'max_retries_configured': max_retries,
            'timeout_per_employee_configured': timeout_per_employee,
            'average_employee_processing_time': parallel_duration / max(1, total_employees),
            'batch_utilization_percentage': min(100, (total_employees / batch_size) * 100),
            'retry_rate_percentage': 0  # Will be enhanced when retry tracking is added
        }
        
        # Quality and accuracy metrics
        quality_metrics = {
            'final_quality_score': stitched_result['processing_metadata']['quality_score'],
            'punch_estimation_accuracy_percentage': punch_estimation_accuracy,
            'employee_success_rate_percentage': phase_efficiency['parallel_processing_success_rate'],
            'data_integrity_score': 100,  # From data integrity checks - will be enhanced
            'deduplication_effectiveness': stitched_result['processing_metadata']['deduplication_stats'].get('duplicates_removed', 0)
        }
        
        # Error and issue tracking
        error_metrics = {
            'discovery_issues_count': len(discovery_result.discovery_issues) if hasattr(discovery_result, 'discovery_issues') else 0,
            'parsing_issues_count': len(stitched_result['parsing_issues']),
            'failed_employees_count': failed_employees,
            'validation_issues_count': len(stitched_result['processing_metadata'].get('validation_issues', [])),
            'fallback_attempted': False,
            'workflow_success': True
        }
        
        # Comprehensive performance metrics structure
        workflow_result['processing_metadata']['performance_metrics'] = {
            # Original basic metrics
            'total_workflow_duration_seconds': total_duration,
            'discovery_duration_seconds': discovery_duration,
            'parallel_processing_duration_seconds': parallel_duration,
            'stitching_duration_seconds': stitching_duration,
            'discovery_percentage': (discovery_duration / total_duration) * 100,
            'parallel_percentage': (parallel_duration / total_duration) * 100,
            'stitching_percentage': (stitching_duration / total_duration) * 100,
            'throughput_employees_per_second': total_employees / total_duration,
            'throughput_punches_per_second': total_punch_events / total_duration,
            'average_time_per_employee': parallel_duration / max(1, total_employees),
            
            # Enhanced monitoring metrics
            'decision_engine_metrics': decision_metrics,
            'phase_efficiency_metrics': phase_efficiency,
            'resource_utilization_metrics': resource_metrics,
            'quality_and_accuracy_metrics': quality_metrics,
            'error_and_issue_metrics': error_metrics,
            
            # Summary metrics for monitoring dashboards
            'monitoring_summary': {
                'total_employees_processed': total_employees,
                'total_punch_events_extracted': total_punch_events,
                'success_rate_percentage': phase_efficiency['parallel_processing_success_rate'],
                'overall_efficiency_score': min(100, (total_punch_events / max(1, total_duration)) * 10),  # Events per second * 10
                'complexity_handled': decision_factors.get('file_size_category', 'unknown'),
                'processing_mode': 'two_pass_success',
                'quality_grade': 'A' if quality_metrics['final_quality_score'] >= 90 else 'B' if quality_metrics['final_quality_score'] >= 75 else 'C',
                'estimated_cost_savings_hours': parallel_duration * 0.8 if total_employees > 10 else 0  # Estimated time saved vs sequential processing
            }
        }
        
        # Mark workflow as successful
        workflow_result['workflow_success'] = True
        final_quality = stitched_result['processing_metadata']['quality_score']
        
        logger.info(
            f"🎉 Two-pass workflow completed successfully for '{original_filename}' in {total_duration:.2f}s - "
            f"Final: {len(stitched_result['punch_events'])} punch events, Quality: {final_quality:.1f}%"
        )
        
        # Collect metrics for monitoring and analysis (Task 11.3)
        collect_two_pass_metrics(workflow_result)
        
        return workflow_result
        
    except Exception as e:
        total_duration = time.time() - workflow_start_time
        failure_point = _determine_failure_point(workflow_result)
        
        # Enhanced failure metrics with detailed analysis
        error_type = type(e).__name__
        error_message = str(e)
        
        # Analyze failure characteristics
        failure_analysis = {
            'failure_point': failure_point,
            'error_type': error_type,
            'error_message': error_message,
            'time_to_failure_seconds': total_duration,
            'stages_completed': list(workflow_result['processing_metadata']['workflow_stages'].keys()),
            'last_successful_stage': None,
            'failure_category': 'unknown'
        }
        
        # Determine last successful stage and failure category
        stages = workflow_result['processing_metadata']['workflow_stages']
        for stage_name, stage_data in stages.items():
            if stage_data.get('success', False):
                failure_analysis['last_successful_stage'] = stage_name
        
        # Categorize failure types for better monitoring
        if isinstance(e, TwoPassDiscoveryError):
            failure_analysis['failure_category'] = 'discovery_error'
        elif isinstance(e, TwoPassEmployeeParsingError):
            failure_analysis['failure_category'] = 'employee_parsing_error'
        elif isinstance(e, TwoPassPartialSuccessError):
            failure_analysis['failure_category'] = 'partial_success_error'
        elif isinstance(e, LLMComplexityError):
            failure_analysis['failure_category'] = 'complexity_error'
        elif isinstance(e, LLMServiceError):
            failure_analysis['failure_category'] = 'llm_service_error'
        elif isinstance(e, ParsingError):
            failure_analysis['failure_category'] = 'parsing_error'
        else:
            failure_analysis['failure_category'] = 'unexpected_error'
        
        # Calculate partial metrics if any stages completed
        partial_metrics = {
            'discovery_attempted': 'discovery' in stages,
            'discovery_success': stages.get('discovery', {}).get('success', False),
            'parallel_processing_attempted': 'parallel_processing' in stages,
            'parallel_processing_success': stages.get('parallel_processing', {}).get('success', False),
            'stitching_attempted': 'stitching' in stages,
            'stitching_success': stages.get('stitching', {}).get('success', False)
        }
        
        # Decision engine metrics (if available)
        decision_factors = workflow_result['processing_metadata'].get('decision_factors', {})
        decision_metrics = {
            'complexity_score': decision_factors.get('complexity_score', 0),
            'file_size_category': decision_factors.get('file_size_category', 'unknown'),
            'estimated_employees': decision_factors.get('estimated_employees', 0),
            'should_use_two_pass': decision_factors.get('should_use_two_pass', True),
            'decision_available': bool(decision_factors)
        }
        
        # Resource utilization at time of failure
        resource_metrics = {
            'batch_size_configured': batch_size,
            'timeout_configured': timeout_per_employee,
            'max_retries_configured': max_retries,
            'fallback_enabled': fallback_to_single_pass,
            'force_two_pass': force_two_pass
        }
        
        workflow_result['processing_metadata']['performance_metrics'] = {
            # Basic failure metrics
            'total_workflow_duration_seconds': total_duration,
            'failure_point': failure_point,
            'error_type': error_type,
            'error_message': error_message,
            'workflow_success': False,
            
            # Enhanced failure analysis
            'failure_analysis': failure_analysis,
            'partial_completion_metrics': partial_metrics,
            'decision_engine_metrics': decision_metrics,
            'resource_utilization_metrics': resource_metrics,
            
            # Monitoring summary for failed processing
            'monitoring_summary': {
                'processing_mode': 'two_pass_failure',
                'failure_category': failure_analysis['failure_category'],
                'time_to_failure_seconds': total_duration,
                'completion_percentage': len([s for s in partial_metrics.values() if s]) / len(partial_metrics) * 100,
                'complexity_handled': decision_metrics.get('file_size_category', 'unknown'),
                'fallback_available': fallback_to_single_pass and not force_two_pass,
                'estimated_employees': decision_metrics.get('estimated_employees', 0),
                'diagnostic_info': {
                    'last_successful_stage': failure_analysis['last_successful_stage'],
                    'stages_completed': len(failure_analysis['stages_completed']),
                    'error_severity': 'high' if failure_point in ['discovery', 'pre_discovery'] else 'medium'
                }
            }
        }
        
        logger.error(f"❌ Two-pass workflow failed for '{original_filename}' after {total_duration:.2f}s: {str(e)}")
        
        # Collect failure metrics for monitoring and analysis (Task 11.3)
        collect_two_pass_metrics(workflow_result)
        
        # Determine if fallback is appropriate based on the type of error and failure point
        should_attempt_fallback = (
            fallback_to_single_pass and 
            not force_two_pass and 
            "single-pass" not in str(e).lower()
        )
        
        # Specific fallback logic based on error type and failure point
        if should_attempt_fallback:
            try:
                logger.info(f"🔄 Attempting intelligent fallback to single-pass for '{original_filename}'")
                workflow_result['processing_metadata']['attempted_fallback'] = True
                
                # Determine fallback reason based on error type
                if isinstance(e, TwoPassDiscoveryError):
                    fallback_reason = f"Employee discovery failed: {str(e)}"
                elif isinstance(e, TwoPassEmployeeParsingError):
                    fallback_reason = f"Employee parsing failed: {str(e)}"
                elif isinstance(e, TwoPassPartialSuccessError):
                    fallback_reason = f"Partial success with low quality: {str(e)}"
                elif isinstance(e, LLMComplexityError):
                    fallback_reason = f"File too complex for two-pass: {str(e)}"
                else:
                    fallback_reason = f"Two-pass workflow error: {str(e)}"
                
                # Attempt fallback
                fallback_result = await _fallback_to_single_pass(
                    file_content=file_content,
                    original_filename=original_filename,
                    failure_reason=fallback_reason,
                    failure_context={
                        'original_error_type': type(e).__name__,
                        'failure_point': failure_point,
                        'two_pass_duration': total_duration,
                        'workflow_stages': workflow_result['processing_metadata']['workflow_stages']
                    }
                )
                
                # If fallback succeeds, return the fallback result
                logger.info(f"✅ Fallback to single-pass succeeded for '{original_filename}'")
                return fallback_result
                
            except Exception as fallback_error:
                # Fallback also failed
                logger.error(f"❌ Fallback to single-pass also failed for '{original_filename}': {str(fallback_error)}")
                workflow_result['processing_metadata']['fallback_error'] = str(fallback_error)
        
        # Re-raise the original exception with enhanced context
        if isinstance(e, (TwoPassDiscoveryError, TwoPassEmployeeParsingError, TwoPassPartialSuccessError)):
            # These are already well-structured two-pass errors
            raise e
        elif isinstance(e, (LLMServiceError, ParsingError, LLMComplexityError)):
            # These are existing well-structured errors
            raise e
        else:
            # If it's a new error type, raise a generic error
            raise Exception(f"Two-pass workflow failed with unexpected error: {str(e)}")


def _evaluate_two_pass_suitability(file_content: str, original_filename: str) -> Dict[str, Any]:
    """
    Evaluate whether two-pass processing is suitable for the given file.
    
    Args:
        file_content: Raw content of the timesheet file
        original_filename: Name of the file for logging
        
    Returns:
        Dictionary with decision factors and recommendation
    """
    
    # Load configuration
    config = load_config()
    decision_config = config.get("two_pass", {}).get("decision_engine", {})
    
    # Get thresholds from config
    file_size_thresholds = decision_config.get("file_size_thresholds", {})
    small_file_kb = file_size_thresholds.get("small_file_kb", 3) * 1000  # Convert to bytes
    medium_file_kb = file_size_thresholds.get("medium_file_kb", 6) * 1000
    
    # Get scoring values from config
    complexity_scoring = decision_config.get("complexity_scoring", {})
    small_file_points = complexity_scoring.get("small_file_points", 1)
    medium_file_points = complexity_scoring.get("medium_file_points", 2)
    large_file_points = complexity_scoring.get("large_file_points", 3)
    employee_multiplier = complexity_scoring.get("employee_count_multiplier", 0.5)
    
    # Get complexity threshold from config
    complexity_threshold = decision_config.get("complexity_threshold", 3)
    
    # Calculate basic file metrics
    file_size = len(file_content)
    line_count = file_content.count('\n')
    
    # Estimate complexity factors
    # Simple heuristics - can be enhanced with ML models later
    estimated_employees = min(50, max(1, line_count // 10))  # Rough estimate
    complexity_score = 0
    
    # File size factor (larger files benefit more from two-pass) - NOW FROM CONFIG
    if file_size >= medium_file_kb:   # Large file
        complexity_score += large_file_points
        file_size_category = "large"
    elif file_size >= small_file_kb:  # Medium file
        complexity_score += medium_file_points
        file_size_category = "medium"
    else:  # Small file
        complexity_score += small_file_points
        file_size_category = "small"
    
    # Employee count factor (more employees benefit from parallel processing) - NOW USES MULTIPLIER
    base_employee_score = 0
    if estimated_employees > 15:
        base_employee_score = 3
    elif estimated_employees > 8:
        base_employee_score = 2
    elif estimated_employees > 3:
        base_employee_score = 1
    
    employee_score = base_employee_score * employee_multiplier
    complexity_score += employee_score
    
    # Content complexity factors
    content_factors = []
    if 'break' in file_content.lower():
        complexity_score += 1  # Break punches add complexity
        content_factors.append("break_punches")
    
    if file_content.count(',') > file_content.count('\n') * 3:
        complexity_score += 1  # Many columns suggest complexity
        content_factors.append("many_columns")
    
    # Decision logic - NOW USES CONFIG THRESHOLD
    should_use_two_pass = complexity_score >= complexity_threshold
    
    decision_result = {
        'should_use_two_pass': should_use_two_pass,
        'complexity_score': complexity_score,
        'complexity_threshold': complexity_threshold,
        'file_size_chars': file_size,
        'file_size_category': file_size_category,
        'estimated_line_count': line_count,
        'estimated_employees': estimated_employees,
        'content_factors': content_factors,
        'config_used': {
            'file_size_thresholds_kb': {
                'small': small_file_kb // 1000,
                'medium': medium_file_kb // 1000
            },
            'scoring_points': {
                'small_file': small_file_points,
                'medium_file': medium_file_points,
                'large_file': large_file_points,
                'employee_multiplier': employee_multiplier
            }
        },
        'reason': _generate_decision_reason(complexity_score, should_use_two_pass, file_size, estimated_employees, complexity_threshold)
    }
    
    logger.info(
        f"DECISION_ENGINE - File: '{original_filename}' | "
        f"Complexity: {complexity_score:.1f}/{complexity_threshold} | "
        f"Size: {file_size:,} chars ({file_size_category}) | "
        f"Est. employees: {estimated_employees} | "
        f"Recommendation: {'Two-pass' if should_use_two_pass else 'Single-pass'}"
    )
    
    return decision_result


def _generate_decision_reason(complexity_score: float, should_use_two_pass: bool, file_size: int, estimated_employees: int, complexity_threshold: float) -> str:
    """Generate human-readable reason for the processing decision."""
    
    if should_use_two_pass:
        reasons = []
        if file_size >= 6000:  # 6KB
            reasons.append("large file size")
        elif file_size >= 3000:  # 3KB
            reasons.append("moderate file size")
        
        if estimated_employees > 15:
            reasons.append("many employees")
        elif estimated_employees > 8:
            reasons.append("moderate employee count")
        
        if reasons:
            return f"Two-pass recommended due to {' and '.join(reasons)} (complexity score: {complexity_score:.1f} ≥ {complexity_threshold})"
        else:
            return f"Two-pass recommended (complexity score: {complexity_score:.1f} ≥ {complexity_threshold})"
    else:
        return f"Single-pass sufficient for small/simple file (complexity score: {complexity_score:.1f} < {complexity_threshold})"


def _determine_failure_point(workflow_result: Dict[str, Any]) -> str:
    """Determine at which stage the workflow failed."""
    
    stages = workflow_result['processing_metadata']['workflow_stages']
    
    if 'discovery' not in stages:
        return 'pre_discovery'
    elif not stages['discovery'].get('success', False):
        return 'discovery'
    elif 'parallel_processing' not in stages:
        return 'pre_parallel_processing'
    elif not stages['parallel_processing'].get('success', False):
        return 'parallel_processing'
    elif 'stitching' not in stages:
        return 'pre_stitching'
    elif not stages['stitching'].get('success', False):
        return 'stitching'
    else:
        return 'post_stitching'


def stitch_employee_results(
    discovery_result: EmployeeDiscoveryOutput,
    employee_parsing_results: List[PerEmployeeParsingOutput],
    original_filename: str,
    enable_deduplication: bool = True,
    strict_validation: bool = True
) -> Dict[str, Any]:
    """
    Stitch together all employee parsing results into a comprehensive final output.
    
    This function combines all individual employee results, performs validation,
    deduplication, and creates comprehensive error reporting.
    
    Args:
        discovery_result: Results from Pass 1 employee discovery
        employee_parsing_results: List of results from Pass 2 employee parsing
        original_filename: Name of the original file for logging
        enable_deduplication: Whether to deduplicate overlapping punch events
        strict_validation: Whether to enforce strict validation rules
        
    Returns:
        Dictionary containing stitched results, validation report, and metadata
        
    Raises:
        ParsingError: If critical validation fails
        LLMServiceError: If too many employees failed processing
    """
    start_time = time.time()
    logger.info(f"Starting result stitching for '{original_filename}' with {len(employee_parsing_results)} employee results")
    
    # Initialize result structure
    stitched_result = {
        'punch_events': [],
        'processing_metadata': {
            'original_filename': original_filename,
            'discovered_employees': len(discovery_result.employees),
            'processed_employees': len(employee_parsing_results),
            'failed_employees': [],
            'validation_issues': [],
            'deduplication_stats': {},
            'data_integrity_report': {}
        },
        'parsing_issues': []
    }
    
    try:
        # Step 1: Validate employee coverage
        coverage_validation = _validate_employee_coverage(discovery_result, employee_parsing_results, strict_validation)
        stitched_result['processing_metadata']['failed_employees'] = coverage_validation['failed_employees']
        stitched_result['processing_metadata']['validation_issues'].extend(coverage_validation['issues'])
        
        # Step 2: Collect all punch events
        all_punch_events = []
        employee_punch_counts = {}
        
        for employee_result in employee_parsing_results:
            employee_id = employee_result.employee_identifier
            punch_count = len(employee_result.punch_events)
            employee_punch_counts[employee_id] = punch_count
            
            # Add punch events with metadata
            for punch_event in employee_result.punch_events:
                # Ensure punch event has source metadata
                if hasattr(punch_event, '__dict__'):
                    punch_dict = punch_event.__dict__.copy()
                else:
                    punch_dict = punch_event.model_dump() if hasattr(punch_event, 'model_dump') else dict(punch_event)
                
                punch_dict['_source_employee'] = employee_id
                punch_dict['_processing_pass'] = 'two_pass'
                all_punch_events.append(punch_dict)
            
            # Collect parsing issues
            if employee_result.parsing_issues:
                stitched_result['parsing_issues'].extend([
                    f"Employee '{employee_id}': {issue}" for issue in employee_result.parsing_issues
                ])
        
        logger.info(f"Collected {len(all_punch_events)} punch events from {len(employee_parsing_results)} employees")
        
        # Step 3: Deduplication (if enabled)
        if enable_deduplication:
            deduplicated_events, dedup_stats = _deduplicate_punch_events(all_punch_events, original_filename)
            stitched_result['punch_events'] = deduplicated_events
            stitched_result['processing_metadata']['deduplication_stats'] = dedup_stats
            logger.info(f"Deduplication removed {dedup_stats['duplicates_removed']} duplicate events")
        else:
            stitched_result['punch_events'] = all_punch_events
            stitched_result['processing_metadata']['deduplication_stats'] = {'enabled': False}
        
        # Step 4: Data integrity checks
        integrity_report = _perform_data_integrity_checks(
            discovery_result, employee_parsing_results, stitched_result['punch_events'], original_filename
        )
        stitched_result['processing_metadata']['data_integrity_report'] = integrity_report
        
        # Step 5: Final validation and quality assessment
        final_validation = _perform_final_validation(stitched_result, strict_validation)
        stitched_result['processing_metadata']['validation_issues'].extend(final_validation['issues'])
        stitched_result['processing_metadata']['quality_score'] = final_validation['quality_score']
        
        execution_time = time.time() - start_time
        stitched_result['processing_metadata']['stitching_time_seconds'] = execution_time
        
        logger.info(
            f"Result stitching completed for '{original_filename}' in {execution_time:.2f}s - "
            f"Final: {len(stitched_result['punch_events'])} punch events, "
            f"Quality score: {final_validation['quality_score']:.1f}%"
        )
        
        # Raise error if critical validation failed
        if strict_validation and final_validation['quality_score'] < 50.0:
            raise ParsingError(
                message=f"Critical validation failure: Quality score {final_validation['quality_score']:.1f}% too low",
                filename=original_filename,
                parsing_issues=stitched_result['processing_metadata']['validation_issues']
            )
        
        return stitched_result
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Result stitching failed for '{original_filename}' after {execution_time:.2f}s: {str(e)}")
        
        if "validation" in str(e).lower():
            raise ParsingError(
                message=f"Validation error during result stitching: {str(e)}",
                filename=original_filename,
                parsing_issues=[str(e)]
            )
        else:
            raise LLMServiceError(
                message=f"Service error during result stitching: {str(e)}",
                service_name="Two-Pass Result Stitching"
            )


def _validate_employee_coverage(
    discovery_result: EmployeeDiscoveryOutput,
    employee_parsing_results: List[PerEmployeeParsingOutput],
    strict_validation: bool
) -> Dict[str, Any]:
    """
    Validate that all discovered employees have been processed.
    
    Returns:
        Dictionary with failed employees and validation issues
    """
    discovered_employees = {emp.employee_identifier_in_file for emp in discovery_result.employees}
    processed_employees = {result.employee_identifier for result in employee_parsing_results}
    
    failed_employees = discovered_employees - processed_employees
    extra_employees = processed_employees - discovered_employees
    
    issues = []
    
    if failed_employees:
        issues.append(f"Missing results for {len(failed_employees)} employees: {list(failed_employees)}")
        logger.warning(f"EMPLOYEE_COVERAGE_ISSUE - Missing results for employees: {failed_employees}")
    
    if extra_employees:
        issues.append(f"Unexpected results for {len(extra_employees)} employees: {list(extra_employees)}")
        logger.warning(f"EMPLOYEE_COVERAGE_ISSUE - Extra results for employees: {extra_employees}")
    
    coverage_percentage = (len(processed_employees & discovered_employees) / len(discovered_employees)) * 100 if discovered_employees else 100
    
    if strict_validation and coverage_percentage < 100.0:
        issues.append(f"Employee coverage only {coverage_percentage:.1f}% (strict validation requires 100%)")
    
    return {
        'failed_employees': list(failed_employees),
        'extra_employees': list(extra_employees),
        'coverage_percentage': coverage_percentage,
        'issues': issues
    }


def _deduplicate_punch_events(punch_events: List[Dict], original_filename: str) -> Tuple[List[Dict], Dict[str, Any]]:
    """
    Remove duplicate punch events based on employee, timestamp, and punch type.
    
    Returns:
        Tuple of (deduplicated_events, deduplication_stats)
    """
    original_count = len(punch_events)
    seen_events = set()
    deduplicated_events = []
    duplicate_count = 0
    
    for event in punch_events:
        # Create a unique key for the punch event
        event_key = (
            event.get('employee_identifier_in_file', ''),
            str(event.get('timestamp', '')),
            event.get('punch_type', ''),
            event.get('location', '')
        )
        
        if event_key not in seen_events:
            seen_events.add(event_key)
            deduplicated_events.append(event)
        else:
            duplicate_count += 1
            logger.debug(f"Removed duplicate punch event: {event_key}")
    
    dedup_stats = {
        'original_count': original_count,
        'final_count': len(deduplicated_events),
        'duplicates_removed': duplicate_count,
        'deduplication_rate': (duplicate_count / original_count * 100) if original_count > 0 else 0.0
    }
    
    if duplicate_count > 0:
        logger.info(f"DEDUPLICATION - Removed {duplicate_count} duplicates from {original_count} events ({dedup_stats['deduplication_rate']:.1f}%)")
    
    return deduplicated_events, dedup_stats


def _perform_data_integrity_checks(
    discovery_result: EmployeeDiscoveryOutput,
    employee_parsing_results: List[PerEmployeeParsingOutput],
    final_punch_events: List[Dict],
    original_filename: str
) -> Dict[str, Any]:
    """
    Perform comprehensive data integrity checks comparing discovery vs final results.
    
    Returns:
        Dictionary with integrity check results
    """
    # Calculate total estimated vs actual punch counts
    total_estimated = sum(emp.punch_count_estimate for emp in discovery_result.employees)
    total_actual = len(final_punch_events)
    
    # Calculate per-employee accuracy
    employee_accuracies = []
    for discovery_emp in discovery_result.employees:
        emp_id = discovery_emp.employee_identifier_in_file
        estimated = discovery_emp.punch_count_estimate
        
        # Find actual count from parsing results
        actual = 0
        for parsing_result in employee_parsing_results:
            if parsing_result.employee_identifier == emp_id:
                actual = len(parsing_result.punch_events)
                break
        
        if estimated > 0:
            accuracy = (min(estimated, actual) / max(estimated, actual)) * 100
        else:
            accuracy = 100.0 if actual == 0 else 0.0
        
        employee_accuracies.append({
            'employee_id': emp_id,
            'estimated': estimated,
            'actual': actual,
            'accuracy': accuracy
        })
    
    # Calculate overall accuracy
    overall_accuracy = (min(total_estimated, total_actual) / max(total_estimated, total_actual) * 100) if max(total_estimated, total_actual) > 0 else 100.0
    
    # Identify accuracy outliers
    low_accuracy_employees = [emp for emp in employee_accuracies if emp['accuracy'] < 85.0]
    
    integrity_report = {
        'total_estimated_punches': total_estimated,
        'total_actual_punches': total_actual,
        'overall_accuracy': overall_accuracy,
        'employee_count_accuracy': len([emp for emp in employee_accuracies if emp['accuracy'] >= 95.0]) / len(employee_accuracies) * 100 if employee_accuracies else 100.0,
        'low_accuracy_employees': low_accuracy_employees,
        'average_employee_accuracy': sum(emp['accuracy'] for emp in employee_accuracies) / len(employee_accuracies) if employee_accuracies else 100.0
    }
    
    logger.info(
        f"DATA_INTEGRITY - Overall accuracy: {overall_accuracy:.1f}%, "
        f"Employee accuracy: {integrity_report['average_employee_accuracy']:.1f}%, "
        f"Low accuracy employees: {len(low_accuracy_employees)}"
    )
    
    return integrity_report


def _perform_final_validation(stitched_result: Dict[str, Any], strict_validation: bool) -> Dict[str, Any]:
    """
    Perform final validation and calculate quality score.
    
    Returns:
        Dictionary with validation results and quality score
    """
    issues = []
    quality_factors = []
    
    # Check if we have any punch events
    punch_count = len(stitched_result['punch_events'])
    if punch_count == 0:
        issues.append("No punch events found in final result")
        quality_factors.append(0.0)
    else:
        quality_factors.append(100.0)
    
    # Check data integrity metrics
    integrity = stitched_result['processing_metadata']['data_integrity_report']
    overall_accuracy = integrity.get('overall_accuracy', 0.0)
    employee_accuracy = integrity.get('average_employee_accuracy', 0.0)
    
    quality_factors.extend([overall_accuracy, employee_accuracy])
    
    # Check employee coverage
    discovered = stitched_result['processing_metadata']['discovered_employees']
    processed = stitched_result['processing_metadata']['processed_employees']
    failed = len(stitched_result['processing_metadata']['failed_employees'])
    
    if failed > 0:
        coverage_score = ((processed - failed) / discovered * 100) if discovered > 0 else 100.0
        if coverage_score < 90.0:
            issues.append(f"Poor employee coverage: {coverage_score:.1f}% ({failed} failed)")
        quality_factors.append(coverage_score)
    else:
        quality_factors.append(100.0)
    
    # Check for excessive parsing issues
    parsing_issues = len(stitched_result['parsing_issues'])
    if parsing_issues > 10:
        issues.append(f"High number of parsing issues: {parsing_issues}")
        issue_penalty = max(0, 100 - (parsing_issues * 2))  # Penalize 2% per issue
        quality_factors.append(issue_penalty)
    else:
        quality_factors.append(100.0)
    
    # Calculate overall quality score (average of all factors)
    quality_score = sum(quality_factors) / len(quality_factors) if quality_factors else 0.0
    
    # Add quality assessment
    if quality_score >= 95.0:
        quality_assessment = "Excellent"
    elif quality_score >= 85.0:
        quality_assessment = "Good"
    elif quality_score >= 70.0:
        quality_assessment = "Fair"
    else:
        quality_assessment = "Poor"
    
    validation_result = {
        'quality_score': quality_score,
        'quality_assessment': quality_assessment,
        'quality_factors': quality_factors,
        'issues': issues
    }
    
    logger.info(f"FINAL_VALIDATION - Quality score: {quality_score:.1f}% ({quality_assessment})")
    
    return validation_result


async def _fallback_to_single_pass(
    file_content: str,
    original_filename: str,
    failure_reason: str,
    failure_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Intelligent fallback to single-pass processing when two-pass fails.
    
    This function implements a fallback to the existing single-pass approach that can handle
    cases where two-pass processing is not suitable or has failed.
    
    Args:
        file_content: Raw content of the timesheet file
        original_filename: Name of the original file for logging
        failure_reason: Reason why two-pass failed
        failure_context: Additional context about the failure
        
    Returns:
        Dictionary containing parsed results from single-pass processing
        
    Raises:
        LLMServiceError: If single-pass also fails
        ParsingError: If the file cannot be parsed at all
    """
    start_time = time.time()
    logger.info(f"🔄 FALLBACK: Starting single-pass processing for '{original_filename}' due to: {failure_reason}")
    
    try:
        # Import the existing single-pass function
        from .llm_processing import parse_file_to_structured_data
        
        # Convert file content to bytes for the single-pass function
        file_bytes = file_content.encode('utf-8')
        
        # Determine MIME type based on filename
        if original_filename.lower().endswith('.csv'):
            mime_type = 'text/csv'
        elif original_filename.lower().endswith('.txt'):
            mime_type = 'text/plain'
        elif original_filename.lower().endswith('.xlsx'):
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif original_filename.lower().endswith('.xls'):
            mime_type = 'application/vnd.ms-excel'
        else:
            mime_type = 'text/plain'
        
        logger.info(f"🔄 Calling existing single-pass system with MIME type: {mime_type}")
        
        # Call the existing single-pass processing function
        single_pass_result = await parse_file_to_structured_data(
            file_bytes=file_bytes,
            mime_type=mime_type,
            original_filename=original_filename,
            debug_dir=None
        )
        
        # Convert single-pass result to two-pass format for compatibility
        fallback_result = {
            'punch_events': [event.model_dump() if hasattr(event, 'model_dump') else event.__dict__ for event in single_pass_result.punch_events],
            'processing_metadata': {
                'original_filename': original_filename,
                'file_size_chars': len(file_content),
                'processing_mode': 'single_pass_fallback',
                'workflow_version': '1.0',
                'timestamp': datetime.now().isoformat(),
                'fallback_reason': failure_reason,
                'fallback_context': failure_context,
                'performance_metrics': {
                    'total_workflow_duration_seconds': time.time() - start_time,
                    'fallback_triggered': True,
                    'original_processing_mode': 'two_pass_failed'
                }
            },
            'parsing_issues': single_pass_result.parsing_issues or [],
            'workflow_success': True
        }
        
        # Add note about fallback to parsing issues
        fallback_result['parsing_issues'].append(f"Note: Fallback to single-pass processing triggered due to: {failure_reason}")
        
        execution_time = time.time() - start_time
        punch_count = len(fallback_result['punch_events'])
        
        logger.info(
            f"✅ Single-pass fallback completed successfully for '{original_filename}' in {execution_time:.2f}s - "
            f"Extracted {punch_count} punch events"
        )
        
        return fallback_result
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"❌ Single-pass fallback also failed for '{original_filename}' after {execution_time:.2f}s: {str(e)}")
        
        # If fallback also fails, raise a comprehensive error
        raise LLMServiceError(
            message=f"Both two-pass and single-pass processing failed. Two-pass failure: {failure_reason}. Single-pass failure: {str(e)}",
            service_name="Timesheet Processing Fallback System"
        )