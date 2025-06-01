## Relevant Files

- `backend/app/core/llm_processing.py` - Main file containing the current single-pass parsing logic that needs refactoring
- `backend/app/core/llm_processing_two_pass.py` - New module for two-pass processing implementation
- `backend/app/models/schemas.py` - Contains current LLM schemas that need extension for employee discovery
- `backend/app/models/two_pass_schemas.py` - New schemas for two-pass approach (employee discovery and per-employee parsing)
- `backend/llm_utils/google_utils.py` - Contains Gemini API interaction code that needs enhancement
- `backend/app/core/error_handlers.py` - Error handling that may need updates for two-pass failures
- `backend/app/api/endpoints/analyze.py` - API endpoint that calls the parsing logic
- `backend/app/tests/core/test_llm_processing_two_pass.py` - Unit tests for new two-pass functionality
- `backend/app/tests/core/test_llm_processing_integration.py` - Integration tests for the complete two-pass workflow with real data validation
- `backend/config.json` - Configuration file that may need updates for two-pass settings

### Notes

- Unit tests should typically be placed alongside the code files they are testing (e.g., `llm_processing_two_pass.py` and `test_llm_processing_two_pass.py` in the same directory).
- Use `npx jest [optional/path/to/test/file]` to run tests. Running without a path executes all tests found by the Jest configuration.
- The implementation should maintain backward compatibility with the current single-pass approach as a fallback option.

## Tasks

- [x] 1.0 Design and Implement Employee Discovery Schema (Pass 1)
  - [x] 1.1 Create new Pydantic models for employee discovery response in `backend/app/models/two_pass_schemas.py`
  - [x] 1.2 Define `EmployeeDiscoveryResult` schema with fields: employee_identifier_in_file, punch_count_estimate, canonical_name_suggestion
  - [x] 1.3 Define `EmployeeDiscoveryOutput` schema containing list of employees and any discovery issues
  - [x] 1.4 Create function calling schema converter for employee discovery tools
  - [x] 1.5 Add validation logic to ensure employee identifiers are exact substrings from file

- [x] 2.0 Implement Employee Discovery Function (Pass 1)
  - [x] 2.1 Create `discover_employees_in_file()` function in `backend/app/core/llm_processing_two_pass.py`
  - [x] 2.2 Design optimized prompt for employee discovery that emphasizes exact string matching
  - [x] 2.3 Implement Gemini function calling for employee discovery with appropriate tool schema
  - [x] 2.4 Add post-processing to deduplicate and normalize employee identifiers
  - [x] 2.5 Handle edge cases like employees with no time punches or malformed entries
  - [x] 2.6 Add comprehensive logging for discovery phase

- [x] 3.0 Design and Implement Per-Employee Parsing Schema (Pass 2)
  - [x] 3.1 Extend existing `LLMParsedPunchEvent` schema to include employee filter context
  - [x] 3.2 Create `PerEmployeeParsingInput` schema with employee_filter and file_content
  - [x] 3.3 Create `PerEmployeeParsingOutput` schema for individual employee results
  - [x] 3.4 Design function calling schema for per-employee parsing with employee filter parameter
  - [x] 3.5 Add validation to ensure returned punch events match the requested employee

- [x] 4.0 Implement Per-Employee Parsing Function (Pass 2)
  - [x] 4.1 Create `parse_employee_punches()` function in `backend/app/core/llm_processing_two_pass.py`
  - [x] 4.2 Design targeted prompt for individual employee parsing with explicit filtering instructions
  - [x] 4.3 Implement Gemini function calling for per-employee parsing
  - [x] 4.4 Add validation to filter out punch events that don't match the target employee
  - [x] 4.5 Handle cases where employee has no valid punch events
  - [x] 4.6 Add detailed logging for each employee parsing operation

- [x] 5.0 Implement Async Parallel Processing Engine
  - [x] 5.1 Create `process_employees_in_parallel()` function using asyncio.gather()
  - [x] 5.2 Implement configurable batch processing (default 10-20 simultaneous calls)
  - [x] 5.3 Add retry logic with exponential backoff for failed employee parsing
  - [x] 5.4 Implement progress tracking and partial result handling
  - [x] 5.5 Add timeout handling for individual employee parsing operations
  - [x] 5.6 Create result aggregation logic to combine all employee results

- [x] 6.0 Implement Result Stitching and Validation
  - [x] 6.1 Create `stitch_employee_results()` function to combine all parsed data
  - [x] 6.2 Implement deduplication logic for overlapping punch events
  - [x] 6.3 Add validation to ensure all discovered employees have been processed
  - [x] 6.4 Create comprehensive error reporting for failed employee parsing
  - [x] 6.5 Add data integrity checks comparing discovery results with final parsed data
  - [x] 6.6 Implement fallback to single-pass parsing if two-pass fails

- [x] 7.0 Create Main Two-Pass Orchestration Function
  - [x] 7.1 Create `parse_file_to_structured_data_two_pass()` main entry point
  - [x] 7.2 Implement decision logic for when to use two-pass vs single-pass approach
  - [x] 7.3 Add comprehensive error handling and fallback mechanisms
  - [x] 7.4 Implement performance monitoring and timing metrics
  - [x] 7.5 Add detailed logging for the entire two-pass workflow
  - [x] 7.6 Create configuration options for batch size, timeouts, and retry limits
  - [x] 7.7 Enhanced decision engine with improved file size thresholds (<3KB=1pt, 3-6KB=2pts, 6KB+=3pts)

- [x] 8.0 Enhance Error Handling and Recovery
  - [x] 8.1 Create new exception classes for two-pass specific errors in `backend/app/core/error_handlers.py`
  - [x] 8.2 Implement `TwoPassDiscoveryError` for employee discovery failures
  - [x] 8.3 Implement `TwoPassEmployeeParsingError` for individual employee parsing failures
  - [x] 8.4 Add partial success handling (some employees parsed, others failed)
  - [x] 8.5 Implement intelligent fallback to single-pass when two-pass is not suitable
  - [x] 8.6 Add detailed error context and recovery suggestions

- [x] 9.0 Integration with Existing System
  - [x] 9.1 Update `backend/app/core/llm_processing.py` to integrate two-pass option
  - [x] 9.2 Add configuration flag to enable/disable two-pass processing
  - [x] 9.3 Implement automatic detection of when two-pass is needed (file size, complexity)
  - [x] 9.4 Update API endpoints to support two-pass processing parameters
  - [x] 9.5 Ensure backward compatibility with existing single-pass functionality
  - [x] 9.6 Add two-pass processing status to API responses

- [x] 10.0 Testing and Validation
  - [x] 10.1 Create unit tests for employee discovery function in `backend/app/tests/core/test_llm_processing_two_pass.py`
  - [x] 10.2 Create unit tests for per-employee parsing function
  - [x] 10.3 Create unit tests for parallel processing and result stitching
  - [x] 10.4 Create integration tests for complete two-pass workflow in `backend/app/tests/core/test_llm_processing_integration.py`
  - [x] 10.5 Create performance tests comparing single-pass vs two-pass approaches
  - [x] 10.6 Test with real large files that previously failed with token limits
  - [x] 10.7 Test edge cases like files with single employee, no employees, or malformed data

- [x] 11.0 Configuration and Documentation
  - [x] 11.1 Add two-pass configuration options to `backend/config.json`
  - [x] 11.2 Document two-pass vs single-pass decision criteria
  - [x] 11.3 Add monitoring and metrics for two-pass processing performance
  - [x] 11.4 Create developer documentation for extending two-pass functionality
  - [x] 11.5 Add operational documentation for troubleshooting two-pass issues
  - [x] 11.6 Update API documentation to include two-pass processing options

- [ ] 99.0 Miscellaneous Tasks
  - [x] 99.1 Remove Excel preprocessing row limit, convert Excel to CSV first, use first sheet only for multi-sheet files 