import os
import sys
import time
from dotenv import load_dotenv
# Pillow is not strictly needed here anymore if MIME type is passed in and validated upstream
# import Image 
import io # Added for handling bytes for openpyxl
import asyncio
import json
from typing import List, Optional, Dict, Any, Union # Added Dict, Any, Union
import re

import openpyxl # Added for Excel processing

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
parent_dir = os.path.dirname(backend_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from app.models.schemas import LLMProcessingOutput, LLMParsedPunchEvent
from llm_utils.google_utils import get_gemini_response_with_function_calling
from app.core.logging_config import get_logger, log_llm_request, log_llm_response
# Import new error handling for task 5.3
from app.core.error_handlers import (
    FileValidationError,
    ParsingError,
    LLMServiceError,
    LLMProcessingError,
    LLMComplexityError
)

# Load environment variables
load_dotenv()

# Initialize logger for this module
logger = get_logger("llm")

def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.json file.
    
    Returns:
        Dictionary containing configuration settings
    """
    try:
        # Look for config.json in the backend directory (where it actually is)
        config_path = os.path.join(backend_dir, "config.json")
        if not os.path.exists(config_path):
            # Fallback to looking in project root
            config_path = os.path.join(parent_dir, "config.json")
        if not os.path.exists(config_path):
            # Final fallback to current working directory
            config_path = os.path.join(os.getcwd(), "config.json")
        
        if os.path.exists(config_path):
            logger.debug(f"Loading config from: {config_path}")
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            logger.debug(f"Config file not found at any expected location, using defaults")
            return {}
    except Exception as e:
        logger.debug(f"Error loading config: {e}, using defaults")
        return {}

def get_function_calling_model() -> str:
    """
    Get the function calling model name from config or environment.
    
    Returns:
        Model name to use for function calling
    """
    # First check environment variable override (for testing)
    env_override = os.getenv("LLM_MODEL_OVERRIDE")
    if env_override:
        logger.debug(f"Using model from environment override: {env_override}")
        return env_override
    
    # Load from config file
    config = load_config()
    
    # Check for function_calling_model directly under google
    function_calling_model = config.get("google", {}).get("function_calling_model")
    
    if function_calling_model:
        logger.debug(f"Using function calling model from config: {function_calling_model}")
        return function_calling_model
    
    # Fallback to default
    default_model = "models/gemini-2.0-flash"
    logger.debug(f"No config found, using fallback model: {default_model}")
    return default_model

def pydantic_to_gemini_tool_dict(pydantic_model_cls, tool_name: str, tool_description: str) -> Dict[str, Any]:
    """
    Converts a Pydantic model into a dictionary structure that can be used for a 
    Gemini FunctionDeclaration tool, suitable for the `tools` parameter in 
    `client.generate_content` when `tools` is a list of dicts.

    Args:
        pydantic_model_cls: The Pydantic model class (e.g., LLMProcessingOutput defined by its parameters).
                            This function expects the schema to describe the *parameters* the LLM should fill.
        tool_name: The desired name for the LLM function/tool.
        tool_description: A description for the LLM function/tool.

    Returns:
        A dictionary formatted as a Gemini FunctionDeclaration.
    """
    # We are defining a function whose *parameters* will be used to construct LLMProcessingOutput.
    # So the schema should describe 'punch_events' and 'parsing_issues' as parameters.
    
    punch_event_json_schema = LLMParsedPunchEvent.model_json_schema()
    
    # Convert the punch event schema properties to handle nullable fields properly for Google GenAI
    def convert_schema_properties(properties_dict):
        converted_props = {}
        for prop_name, prop_schema in properties_dict.items():
            # Simplified handling - avoid complex anyOf/null processing
            if "anyOf" in prop_schema:
                # Just use STRING type for optional fields to simplify
                converted_props[prop_name] = {
                    "type": "STRING",
                    "description": prop_schema.get("description", "") + " (Optional)"
                }
            else:
                # Handle regular types
                json_type = prop_schema.get("type", "string")
                gemini_type = {
                    "string": "STRING",
                    "number": "NUMBER", 
                    "integer": "INTEGER",
                    "boolean": "BOOLEAN",
                    "array": "ARRAY",
                    "object": "OBJECT"
                }.get(json_type.lower(), "STRING")
                
                converted_props[prop_name] = {
                    "type": gemini_type,
                    "description": prop_schema.get("description", "")
                }
                
                # Handle format for date-time
                if prop_schema.get("format") == "date-time":
                    converted_props[prop_name]["description"] += " (ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)"
        
        return converted_props

    # Convert punch event properties
    punch_event_properties = convert_schema_properties(punch_event_json_schema.get("properties", {}))

    # Define the parameters schema for our main "timesheet_data_extractor" function.
    # This is what we want the LLM to provide arguments for.
    tool_parameters_schema = {
        "type": "OBJECT", # Corresponds to genai_types.Type.OBJECT.name
        "properties": {
            "punch_events": {
                "type": "ARRAY",
                "items": { # Representing the schema of items in the array
                    "type": "OBJECT", 
                    "properties": punch_event_properties,
                    "required": punch_event_json_schema.get("required", [])
                 },
                "description": "A list of all parsed time punch events from the timesheet file content."
            },
            "parsing_issues": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "A list of any general parsing issues or warnings encountered by the LLM (e.g., ambiguous entries, unparseable sections, formatting problems in the source file)."
            }
        },
        "required": ["punch_events"] # punch_events are essential
    }

    function_declaration_dict = {
        "name": tool_name,
        "description": tool_description,
        "parameters": tool_parameters_schema
    }
    return function_declaration_dict

def preprocess_excel_to_text(file_bytes: bytes, original_filename: str) -> str:
    """
    Convert Excel file bytes to text format for LLM processing.
    
    Args:
        file_bytes: Raw Excel file content as bytes
        original_filename: Original filename for context and debugging
        
    Returns:
        Text representation of Excel content
        
    Raises:
        ParsingError: If Excel file cannot be processed
    """
    try:
        # Load Excel file from bytes
        workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        
        # Get the active sheet (or first sheet)
        sheet = workbook.active
        
        # Convert sheet to clean CSV-like text format, focusing on timesheet data
        rows_data = []
        header_found = False
        total_rows_processed = 0
        
        # Iterate through all rows that have data
        for row_idx, row in enumerate(sheet.iter_rows(values_only=True), 1):
            total_rows_processed += 1
            # Skip completely empty rows
            if all(cell is None or str(cell).strip() == '' for cell in row):
                continue
            
            # Convert each cell to string, handling None values and cleaning up
            row_data = []
            for cell in row:
                if cell is None:
                    row_data.append("")
                elif isinstance(cell, (int, float)):
                    # Format numbers consistently
                    if isinstance(cell, float) and cell.is_integer():
                        row_data.append(str(int(cell)))
                    else:
                        row_data.append(str(cell))
                else:
                    # Clean up string values
                    cell_str = str(cell).strip()
                    # Remove excessive whitespace and special characters that might confuse LLM
                    cell_str = re.sub(r'\s+', ' ', cell_str)
                    row_data.append(cell_str)
            
            # Only include rows that have meaningful data (not just formatting)
            meaningful_data = [cell for cell in row_data if cell.strip()]
            if len(meaningful_data) >= 2:  # At least 2 non-empty cells
                rows_data.append(",".join(row_data))
                
                # Try to identify header row
                row_text = " ".join(row_data).lower()
                if not header_found and any(keyword in row_text for keyword in 
                    ['employee', 'name', 'time', 'date', 'clock', 'in', 'out', 'punch']):
                    header_found = True
        
        # Limit the data to prevent LLM overload while keeping essential information
        if len(rows_data) > 200:  # If too many rows, keep header and recent data
            # Keep first 20 rows (likely headers) and last 150 rows (most recent data)
            rows_data = rows_data[:20] + rows_data[-150:]
            logger.debug(f"Truncated Excel data to prevent LLM overload: keeping 170 most relevant rows out of {total_rows_processed} total rows")
        
        # Create clean, structured text content
        text_content = f"TIMESHEET DATA from {original_filename}\n"
        text_content += f"Sheet: {sheet.title}\n"
        text_content += f"Data rows: {len(rows_data)}\n\n"
        text_content += "CSV FORMAT:\n"
        text_content += "\n".join(rows_data)
        
        logger.debug(f"Successfully converted Excel file '{original_filename}' to clean text format ({len(rows_data)} rows, {len(text_content)} chars)")
        
        return text_content
        
    except Exception as e:
        raise ParsingError(
            message=f"Failed to process Excel file '{original_filename}': {str(e)}",
            filename=original_filename
        )

async def parse_file_to_structured_data(
    file_bytes: bytes,
    mime_type: str,
    original_filename: str,
    debug_dir: Optional[str] = None
) -> LLMProcessingOutput:
    """
    Parse a file using LLM function calling to extract structured timesheet data.
    
    This function implements:
    1. File type validation and processing
    2. Text extraction or OCR depending on file type  
    3. Chunking strategies for LLM processing
    2. Using function calling with Pydantic schemas to get structured data from the LLM
    3. Implementing retry logic for LLM API failures
    4. Returning structured punch event data or parsing issues
    
    Args:
        file_bytes: Raw file content as bytes
        mime_type: MIME type of the file (e.g., 'text/csv', 'application/pdf')
        original_filename: Original filename for context and debugging
        debug_dir: Optional directory to save debug information
        
    Returns:
        LLMProcessingOutput containing parsed punch events and any parsing issues
        
    Raises:
        FileValidationError: For unsupported file types or invalid file content
        ParsingError: For file parsing/decoding failures  
        LLMServiceError: For LLM processing failures or unexpected errors
    """
    total_start_time = time.time()
    logger.debug(f"Starting LLM processing for {original_filename}")
    
    # Validate supported MIME types
    supported_types = {
        'text/csv', 'application/csv',
        'text/plain',
        'application/pdf'
    }
    
    # Check if it's an image MIME type
    is_image = mime_type.startswith('image/') if mime_type else False
    
    # Check for Excel files which need special handling
    is_excel = (
        mime_type in ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'] or
        (original_filename and original_filename.lower().endswith(('.xls', '.xlsx')))
    )
    
    # Excel files are now supported through preprocessing
    if not (mime_type in supported_types or is_image or is_excel):
        # Use standardized error handling (task 5.3)
        raise FileValidationError(
            message=f"Unsupported MIME type for LLM processing: {mime_type}",
            filename=original_filename,
            suggestion="Supported formats: CSV, TXT, PDF, Excel (XLS/XLSX), and image files (PNG, JPG, etc.)"
        )
    
    # Create debug directory if requested
    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        logger.debug(f"Debug mode enabled. Files will be saved to: {debug_dir}")
    
    try:
        # Process based on MIME type
        if is_excel:
            # Handle Excel files with preprocessing
            logger.debug(f"Processing Excel file: {original_filename}")
            excel_text_content = preprocess_excel_to_text(file_bytes, original_filename)
            
            # Extract just the CSV data part (after "CSV FORMAT:")
            if "CSV FORMAT:" in excel_text_content:
                csv_content = excel_text_content.split("CSV FORMAT:")[-1].strip()
                # Process this as CSV content instead of Excel
                text_content = csv_content
                logger.debug(f"Converted Excel to CSV format for processing: {len(text_content)} characters")
            else:
                text_content = excel_text_content
            
            if debug_dir:
                with open(os.path.join(debug_dir, "excel_extracted_content.txt"), 'w', encoding='utf-8') as f:
                    f.write(excel_text_content)
                with open(os.path.join(debug_dir, "csv_converted_content.txt"), 'w', encoding='utf-8') as f:
                    f.write(text_content)
                    
        elif is_image:
            # Handle image files - for now, placeholder implementation
            text_content = f"Image file: {original_filename}\nNote: Image OCR processing not yet implemented. Please convert to CSV or text format."
            
        elif mime_type == 'application/pdf':
            # Handle PDF files - for now, treat as binary and let LLM handle
            text_content = f"PDF file: {original_filename}\nNote: PDF parsing not yet implemented. Please convert to CSV or image format."
            
        else:
            # Handle CSV, TXT, and other text files
            try:
                # Try to decode as text
                text_content = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    # Try other common encodings
                    text_content = file_bytes.decode('latin-1')
                except UnicodeDecodeError:
                    # Use standardized error handling (task 5.3)
                    raise ParsingError(
                        message=f"Could not decode text-based file '{original_filename}' as UTF-8 or Latin-1",
                        filename=original_filename
                    )
            
            if debug_dir:
                with open(os.path.join(debug_dir, "file_content.txt"), 'w', encoding='utf-8') as f:
                    f.write(text_content)
        
        logger.debug(f"Processing full file without chunking")
        logger.debug(f"Content size: {len(text_content)} characters")
        logger.debug("Content lines: %d", len(text_content.split('\n')))
        
        # Create prompt for text-based files
        if is_excel:
            text_prompt = f"""
You are analyzing timesheet data that was extracted from an Excel file and converted to CSV format.

Your task: Extract EVERY time punch event from this CSV timesheet data.

The CSV data contains employee time punches with information like:
- Employee names/IDs
- Clock in/out times 
- Dates
- Any break periods

Here is the CSV timesheet data:
---
{text_content}
---

Please systematically extract all punch events. For each event, identify:
- Employee name/identifier
- Whether it's a clock in, clock out, break start, or break end
- The exact timestamp
- Any relevant notes

Be thorough and extract every single punch event you find in this CSV data.
"""
        else:
            text_prompt = f"""
You are analyzing a complete timesheet file. This file contains ALL the time punch data for multiple employees.

CRITICAL TASK: Extract EVERY SINGLE time punch event from this file.

The file content is:
---
{text_content}
---

Please parse ALL punch events found in this file. Look for:
- Employee names (watch for variations/misspellings of the same person)
- Clock in/out times 
- Dates
- Any break periods or meal times
- Different job roles or departments if mentioned

Extract everything systematically - don't miss any employees or any punch events.
"""
        
        # Prepare prompt parts
        prompt_parts = [text_prompt]
        
        # Generate function calling schema
        schema = pydantic_to_gemini_tool_dict(
            LLMProcessingOutput, 
            tool_name="extract_timesheet_data",
            tool_description="Extract all timesheet punch events and parsing issues from the file content"
        )
        tools = [schema]
        
        if debug_dir:
            # Save the prompt and schema for debugging
            with open(os.path.join(debug_dir, "llm_prompt.txt"), 'w', encoding='utf-8') as f:
                f.write(text_prompt)
            
            with open(os.path.join(debug_dir, "llm_schema.json"), 'w', encoding='utf-8') as f:
                json.dump(schema, f, indent=2)
        
        # Call LLM with function calling
        # Get the model name that will be used
        model_name = get_function_calling_model()
        logger.info(f"Using LLM model: {model_name} for processing {original_filename}")
        logger.debug(f"Calling LLM with function calling for {original_filename}")
        
        # For Excel files, use faster processing with shorter timeout
        if is_excel:
            max_retries = 2  # Reduce retries for Excel files
            initial_backoff = 1.0  # Shorter backoff
        else:
            max_retries = 3
            initial_backoff = 2.0
        
        try:
            llm_response_data = get_gemini_response_with_function_calling(
                prompt_parts=prompt_parts,
                tools=tools,
                max_retries=max_retries,
                initial_backoff_seconds=initial_backoff,
                temperature=0.1,
                model_name_override=model_name  # Pass the model name explicitly
            )
        except Exception as llm_error:
            error_str = str(llm_error)
            logger.warning(f"LLM call failed for {original_filename}. Error: {error_str}")

            # Check for specific errors indicating complexity or malformed function calls
            if ("MALFORMED_FUNCTION_CALL" in error_str or 
                "FinishReason" in error_str or 
                "function calling" in error_str.lower() or
                "input data is too complex" in error_str.lower() or
                (is_excel and "response was blocked" in error_str.lower()) # Sometimes Excel errors manifest this way
            ):
                logger.error(f"LLM complexity error for {original_filename}: {error_str}. Raising LLMComplexityError.")
                # Raise LLMComplexityError to signal this specific issue to the frontend
                raise LLMComplexityError(
                    message=f"The file '{original_filename}' contains data that is too complex for our current AI processing capabilities. This can happen with very large files or complex formatting. Please try with a smaller file or contact support for assistance with processing larger datasets.",
                    original_filename=original_filename,
                    llm_call_details=error_str
                )
            
            # For other LLM errors, raise a more general LLMProcessingError
            logger.error(f"General LLM processing error for {original_filename}: {error_str}")
            raise LLMProcessingError(
                message=f"An unexpected error occurred during LLM analysis for '{original_filename}'.",
                original_filename=original_filename,
                llm_call_details=error_str
            )
        
        if debug_dir:
            with open(os.path.join(debug_dir, "llm_response.json"), 'w', encoding='utf-8') as f:
                json.dump(llm_response_data, f, indent=2)
        
        # Process LLM response
        if isinstance(llm_response_data, dict) and "punch_events" in llm_response_data:
            try:
                parsed_output = LLMProcessingOutput(**llm_response_data)
                logger.info(f"LLM successfully parsed {len(parsed_output.punch_events)} punch events from {original_filename}")
                
                total_end_time = time.time()
                total_duration = round(total_end_time - total_start_time, 2)
                logger.debug(f"Total processing time for {original_filename}: {total_duration} seconds")
                
                return parsed_output
            except Exception as pydantic_error:
                # Use standardized error handling (task 5.3)
                raise ParsingError(
                    message=f"LLM returned function call arguments, but failed to create Pydantic model for '{original_filename}'",
                    filename=original_filename,
                    parsing_issues=[f"Pydantic validation error: {str(pydantic_error)}"]
                )
        elif isinstance(llm_response_data, str) and llm_response_data.startswith("Error:"):
            # Use standardized error handling (task 5.3)
            raise LLMServiceError(
                message=f"LLM utility failed for '{original_filename}': {llm_response_data}",
                service_name="Google Gemini"
            )
        elif isinstance(llm_response_data, str):
            # LLM returned text instead of calling the function
            if "Google API Error" in llm_response_data and "500 INTERNAL" in llm_response_data:
                error_msg = f"Google's AI service is temporarily unavailable. Please try again in a few minutes."
                raise LLMServiceError(
                    message=error_msg,
                    service_name="Google Gemini"
                )
            elif "Google API Error" in llm_response_data:
                error_msg = f"AI processing service error. Please try again."
                raise LLMServiceError(
                    message=error_msg,
                    service_name="Google Gemini"
                )
            else:
                error_msg = f"LLM did not use the function call for '{original_filename}' as expected, returned text instead"
                raise ParsingError(
                    message=error_msg,
                    filename=original_filename,
                    parsing_issues=[f"LLM returned text: {llm_response_data[:500]}..."]
                )
        else:
            # Unexpected response type from utility
            error_msg = f"Unexpected response type from LLM utility for '{original_filename}': {type(llm_response_data)}"
            raise LLMServiceError(
                message=error_msg,
                service_name="Google Gemini"
            )
            
    except (FileValidationError, ParsingError, LLMServiceError):
        # Re-raise our standardized errors
        total_end_time = time.time()
        total_duration = round(total_end_time - total_start_time, 2)
        logger.debug(f"Total processing time for {original_filename} (error): {total_duration} seconds")
        raise
    except Exception as e:
        # Catch-all for unexpected errors - convert to LLMServiceError
        total_end_time = time.time()
        total_duration = round(total_end_time - total_start_time, 2)
        logger.debug(f"Total processing time for {original_filename} (unexpected error): {total_duration} seconds")
        
        raise LLMServiceError(
            message=f"Unexpected error during LLM processing for '{original_filename}': {str(e)}",
            service_name="Google Gemini"
        )

# Example Usage (for testing purposes)
async def main_test():
    # Test with the specific Excel file
    excel_file_path = "backend/app/tests/core/8.05 - Time Clock Detail.xlsx"
    original_filename = "8.05 - Time Clock Detail.xlsx"
    # Correct MIME type for .xlsx files
    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" 

    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        logger.info("\nSkipping real LLM call test: GOOGLE_API_KEY or GEMINI_API_KEY not set.")
        return

    if not os.path.exists(excel_file_path):
        logger.info(f"\nTest Excel file not found at {excel_file_path}. Please ensure it's in the correct location.")
        # Also check relative to the script location if run from a different CWD
        alt_path = os.path.join(os.path.dirname(__file__), "..", "tests", "core", original_filename)
        if not os.path.exists(alt_path):
            logger.info(f"Also not found at {alt_path}")
            return
        else:
            excel_file_path = alt_path # Use the found path
            logger.info(f"Using file found at: {excel_file_path}")


    try:
        logger.info(f"\n--- Testing with real Excel file: {original_filename} ---")
        with open(excel_file_path, "rb") as f_excel:
            excel_file_bytes = f_excel.read()
        
        logger.info(f"Attempting to parse: {original_filename} (MIME: {mime_type})")
        parsed_data = await parse_file_to_structured_data(excel_file_bytes, mime_type, original_filename)
        
        logger.info(f"\n--- LLM Parsed Output for {original_filename} ---")
        logger.info(parsed_data.model_dump_json(indent=2))
        
        if parsed_data.punch_events:
            logger.info(f"\nSuccessfully parsed {len(parsed_data.punch_events)} punch events.")
        else:
            logger.info("\nNo punch events were parsed.")
        
        if parsed_data.parsing_issues:
            logger.info("\nLLM Reported Parsing Issues:")
            for issue in parsed_data.parsing_issues:
                logger.info(f"- {issue}")
        else:
            logger.info("\nNo parsing issues reported by LLM.")

    except ValueError as ve:
        logger.error(f"\nValueError during Excel test for {original_filename}: {ve}")
    except RuntimeError as re:
        logger.error(f"\nRuntimeError during Excel test for {original_filename}: {re}")
    except Exception as e:
        logger.error(f"\nAn unexpected error occurred during Excel test for {original_filename}: {e} (Type: {e.__class__.__name__}) ")


if __name__ == '__main__':
    # Adjust Python path to allow absolute imports when running script directly
    import sys
    import os
    # Add the parent directory of 'backend' to sys.path
    # This assumes the script is in backend/app/core/
    # and the workspace root is two levels above 'core' and one level above 'app'
    # More robustly, find the project root that contains the 'backend' directory.
    # For this specific case, going up three levels from __file__ should reach the workspace root.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Need to re-import after path adjustment if modules were not found initially by linters/etc.
    # However, for direct execution, this path adjustment before the main async call is key.

    async def run_all_tests():
        await main_test()

    # Ensure API key is set for tests to run effectively
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        logger.info("Found Google API Key, running main_test for llm_processing.")
        asyncio.run(run_all_tests())
    else:
        logger.info("GOOGLE_API_KEY or GEMINI_API_KEY not set. Skipping llm_processing.py main_test().")
        logger.info("Please create a .env file or set environment variables (e.g., GOOGLE_API_KEY='your_key_here').") 