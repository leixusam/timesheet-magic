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

# Load environment variables
load_dotenv()

def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.json file.
    
    Returns:
        Dictionary containing configuration settings
    """
    try:
        # Look for config.json in the project root (parent of backend)
        config_path = os.path.join(parent_dir, "config.json")
        if not os.path.exists(config_path):
            # Fallback to looking in current directory
            config_path = os.path.join(os.getcwd(), "config.json")
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            print(f"[DEBUG] Config file not found at {config_path}, using defaults")
            return {}
    except Exception as e:
        print(f"[DEBUG] Error loading config: {e}, using defaults")
        return {}

def get_function_calling_model() -> str:
    """
    Get the function calling model from config, with fallbacks.
    
    Returns:
        Model name to use for function calling
    """
    # First check environment variable override (for testing)
    env_override = os.getenv("LLM_MODEL_OVERRIDE")
    if env_override:
        print(f"[DEBUG] Using model from environment override: {env_override}")
        return env_override
    
    # Load from config file
    config = load_config()
    function_calling_model = config.get("google", {}).get("function_calling_model")
    
    if function_calling_model:
        print(f"[DEBUG] Using function calling model from config: {function_calling_model}")
        return function_calling_model
    
    # Final fallback
    fallback_model = "gemini-2.0-flash-exp"
    print(f"[DEBUG] No config found, using fallback model: {fallback_model}")
    return fallback_model

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

async def parse_file_to_structured_data(file_bytes: bytes, mime_type: str, original_filename: str, debug_dir: str = None) -> LLMProcessingOutput:
    """
    Parse a file (CSV, XLSX, PDF, image, or text) to structured timesheet data using LLM.
    
    This function implements task 3.3.2 by:
    1. Handling various file types and converting them to appropriate formats for LLM processing
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
        ValueError: For unsupported file types or invalid file content
        RuntimeError: For LLM processing failures or unexpected errors
    """
    
    total_start_time = time.time()
    print(f"[DEBUG] Starting parse_file_to_structured_data for {original_filename}")
    
    # Validate MIME type and file extension
    supported_mime_types = {
        'text/csv', 'text/plain', 'application/csv', 'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/pdf', 'application/octet-stream'
    }
    
    supported_image_types = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/tiff', 'image/bmp', 'image/gif'
    }
    
    # Check if it's a supported type
    is_supported = (
        mime_type in supported_mime_types or 
        mime_type in supported_image_types or
        (mime_type and mime_type.startswith('image/'))
    )
    
    if not is_supported:
        raise ValueError(f"Unsupported MIME type: {mime_type}. Supported types: CSV, XLSX, PDF, images, and text files.")
    
    # Determine if we need to handle this as an image or text-based file
    is_image = mime_type in supported_image_types or (mime_type and mime_type.startswith('image/'))
    
    try:
        # Create debug directory if specified
        if debug_dir:
            os.makedirs(debug_dir, exist_ok=True)
            print(f"[DEBUG] Created debug directory: {debug_dir}")
        
        # Prepare prompt parts for LLM
        prepared_prompt_parts = []
        
        if is_image:
            # Handle image files (OCR + parsing)
            print(f"Processing image file: {original_filename} (MIME: {mime_type})")
            
            # Add text instruction
            image_prompt = f"""
Please analyze this timesheet image and extract all employee time punch data. The image shows a timesheet for: {original_filename}

Extract the following information for each time punch:
- Employee name/identifier
- Date of the punch
- Time of the punch (clock in/out)
- Role/department if visible
- Any break information if available

Please be thorough and extract all visible time entries. If any data is unclear or ambiguous, note it in the parsing issues.
"""
            prepared_prompt_parts.append(image_prompt)
            
            # Add image data
            prepared_prompt_parts.append({
                "mime_type": mime_type,
                "data": file_bytes
            })
            
        else:
            # Handle text-based files (CSV, XLSX, PDF, TXT)
            print(f"Processing text-based file: {original_filename} (MIME: {mime_type})")
            
            if mime_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                # Handle XLSX files
                try:
                    import pandas as pd
                    import io
                    
                    # Read XLSX file
                    excel_data = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)  # Read all sheets
                    
                    # Convert to text representation
                    text_content = f"Excel file: {original_filename}\n\n"
                    for sheet_name, df in excel_data.items():
                        text_content += f"Sheet: {sheet_name}\n"
                        text_content += df.to_string(index=False, na_rep='')
                        text_content += "\n\n"
                    
                    if debug_dir:
                        with open(os.path.join(debug_dir, "excel_content.txt"), 'w', encoding='utf-8') as f:
                            f.write(text_content)
                    
                except Exception as e:
                    print(f"Error reading XLSX file: {e}")
                    # Fallback to treating as binary data for LLM
                    text_content = f"XLSX file content (binary): {original_filename}\nNote: Could not parse as Excel file due to: {e}"
                    
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
                        text_content = file_bytes.decode('utf-8', errors='replace')
                
                if debug_dir:
                    with open(os.path.join(debug_dir, "file_content.txt"), 'w', encoding='utf-8') as f:
                        f.write(text_content)
            
            print(f"[DEBUG] Processing full file without chunking")
            print(f"[DEBUG] Content size: {len(text_content)} characters")
            print(f"[DEBUG] Content lines: {len(text_content.split('\n'))}")
            
            # Create prompt for text-based files
            text_prompt = f"""
You are analyzing a complete timesheet file. This file contains ALL the time punch data for multiple employees.

CRITICAL TASK: Extract EVERY SINGLE time punch event from this file.

File: {original_filename}

INSTRUCTIONS:
1. Read through the ENTIRE file content carefully
2. Find ALL time punch events (clock in, clock out, breaks)
3. Each time entry = one event (even if multiple times appear on same line)
4. Do NOT skip any employees or time entries
5. Extract ALL events - missing events causes data loss

File content:
{text_content}

For each time punch event, extract:
- Employee name/identifier exactly as it appears
- Date (convert to YYYY-MM-DD format)
- Time with timezone (convert to YYYY-MM-DDTHH:MM:SSZ)  
- Punch type: "clock_in", "clock_out", "break_start", "break_end", or "unknown"
- Role/department if available
- Any notes

Be exhaustive - extract every single time punch event from this file.
"""
            prepared_prompt_parts.append(text_prompt)
        
        # Create the tool definition for structured output
        timesheet_tool_dict = pydantic_to_gemini_tool_dict(
            LLMProcessingOutput,
            "timesheet_data_extractor", 
            "Extract ALL time punch events from complete timesheet file. Must find every single event to avoid data loss."
        )
        
        # Optional model override for testing - defaults to Gemini 2.0 Flash
        model_override = get_function_calling_model()
        
        print(f"[DEBUG] Tool definition created:")
        print(f"[DEBUG] Tool name: {timesheet_tool_dict.get('name')}")
        print(f"[DEBUG] Using model: {model_override}")
        
        print(f"[DEBUG] About to call get_gemini_response_with_function_calling...")
        
        # Save debug prompt if debug_dir is provided
        if debug_dir:
            prompt_debug = {
                "prompt_parts_count": len(prepared_prompt_parts),
                "prompt_parts": []
            }
            for i, part in enumerate(prepared_prompt_parts):
                if isinstance(part, str):
                    prompt_debug["prompt_parts"].append({
                        "type": "text",
                        "length": len(part),
                        "content": part[:1000] + ("..." if len(part) > 1000 else "")  # First 1000 chars
                    })
                else:
                    prompt_debug["prompt_parts"].append({
                        "type": "binary_data",
                        "mime_type": part.get("mime_type"),
                        "data_size": len(part.get("data", []))
                    })
            
            with open(os.path.join(debug_dir, "prompt_debug.json"), 'w') as f:
                json.dump(prompt_debug, f, indent=2)
            print(f"[DEBUG] Prompt debug info saved to {debug_dir}/prompt_debug.json")
        
        start_time = time.time()
        llm_response_data = get_gemini_response_with_function_calling(
            prompt_parts=prepared_prompt_parts,
            tools=[timesheet_tool_dict],
            model_name_override=model_override,
            max_retries=3,
            temperature=0.0  # Deterministic for consistent results
        )
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        print(f"[DEBUG] LLM call completed, response type: {type(llm_response_data)}")
        print(f"[DEBUG] LLM processing took {duration} seconds")
        if isinstance(llm_response_data, str):
            print(f"[DEBUG] String response length: {len(llm_response_data)}")
        elif isinstance(llm_response_data, dict):
            print(f"[DEBUG] Dict response keys: {list(llm_response_data.keys())}")

        if isinstance(llm_response_data, dict):
            # Function call was successful, response_data contains the arguments
            # Construct the Pydantic object from the LLM's arguments
            try:
                print(f"[DEBUG] LLM response keys: {list(llm_response_data.keys())}")
                print(f"[DEBUG] Processing {len(llm_response_data.get('punch_events', []))} events")
                
                # Check if the response is a single punch event or the expected array format
                if "punch_events" in llm_response_data:
                    # Expected format with punch_events array
                    parsed_output = LLMProcessingOutput(
                        punch_events=llm_response_data.get("punch_events", []),
                        parsing_issues=llm_response_data.get("parsing_issues", []) or []  # Handle None case
                    )
                elif "employee_identifier_in_file" in llm_response_data and "timestamp" in llm_response_data:
                    # LLM returned a single punch event - wrap it in an array
                    print(f"[DEBUG] LLM returned single punch event, wrapping in array")
                    parsed_output = LLMProcessingOutput(
                        punch_events=[llm_response_data],
                        parsing_issues=[]
                    )
                else:
                    # Try to extract from any key that looks like it contains punch data
                    punch_events = []
                    for key, value in llm_response_data.items():
                        if isinstance(value, list) and value and isinstance(value[0], dict):
                            if "employee_identifier_in_file" in value[0]:
                                punch_events = value
                                break
                    
                    parsed_output = LLMProcessingOutput(
                        punch_events=punch_events,
                        parsing_issues=[]
                    )
                
                print(f"Successfully parsed data for {original_filename} via LLM utility function call.")
                print(f"[DEBUG] Final result: {len(parsed_output.punch_events)} events, {len(parsed_output.parsing_issues)} issues")
                
                total_end_time = time.time()
                total_duration = round(total_end_time - total_start_time, 2)
                print(f"[DEBUG] Total processing time for {original_filename}: {total_duration} seconds")
                
                return parsed_output
            except Exception as pydantic_error: # Catch errors during Pydantic model instantiation
                error_msg = f"LLM returned function call arguments, but failed to create Pydantic model for '{original_filename}'. Error: {pydantic_error}. LLM Args: {llm_response_data}"
                print(error_msg)
                raise RuntimeError(error_msg)
        elif isinstance(llm_response_data, str) and llm_response_data.startswith("Error:"):
            # An error string was returned from the utility
            error_msg = f"LLM utility failed for '{original_filename}': {llm_response_data}"
            print(error_msg)
            raise RuntimeError(error_msg)
        elif isinstance(llm_response_data, str):
            # LLM returned text instead of calling the function.
            # This is unexpected if a tool was provided and the prompt was clear.
            # Check if it's a Google API error specifically
            if "Google API Error" in llm_response_data and "500 INTERNAL" in llm_response_data:
                error_msg = f"Google's AI service is temporarily unavailable. Please try again in a few minutes. (Technical details: {llm_response_data[:200]}...)"
            elif "Google API Error" in llm_response_data:
                error_msg = f"AI processing service error. Please try again. (Technical details: {llm_response_data[:200]}...)"
            else:
                error_msg = f"LLM did not use the function call for '{original_filename}' as expected, returned text instead: '{llm_response_data[:500]}...'"
            print(error_msg)
            
            total_end_time = time.time()
            total_duration = round(total_end_time - total_start_time, 2)
            print(f"[DEBUG] Total processing time for {original_filename} (LLM text response): {total_duration} seconds")
            
            return LLMProcessingOutput(
                punch_events=[],
                parsing_issues=[error_msg]
            )
        else:
            # Unexpected response type from utility
            error_msg = f"Unexpected response type from LLM utility for '{original_filename}': {type(llm_response_data)}"
            print(error_msg)
            raise RuntimeError(error_msg)

    except ValueError as ve: # Re-raise ValueErrors from MIME type handling or decoding
        total_end_time = time.time()
        total_duration = round(total_end_time - total_start_time, 2)
        print(f"[DEBUG] Total processing time for {original_filename} (ValueError): {total_duration} seconds")
        raise ve 
    except RuntimeError as re: # Re-raise RuntimeErrors from LLM utility or Pydantic parsing
        total_end_time = time.time()
        total_duration = round(total_end_time - total_start_time, 2)
        print(f"[DEBUG] Total processing time for {original_filename} (RuntimeError): {total_duration} seconds")
        raise re
    except Exception as e:
        total_end_time = time.time()
        total_duration = round(total_end_time - total_start_time, 2)
        print(f"[DEBUG] Total processing time for {original_filename} (Exception): {total_duration} seconds")
        error_msg = f"Error during LLM processing for {original_filename} in parse_file_to_structured_data: {e} (Type: {e.__class__.__name__})"
        print(error_msg)
        raise RuntimeError(error_msg)

# Example Usage (for testing purposes)
async def main_test():
    # Test with the specific Excel file
    excel_file_path = "backend/app/tests/core/8.05 - Time Clock Detail.xlsx"
    original_filename = "8.05 - Time Clock Detail.xlsx"
    # Correct MIME type for .xlsx files
    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" 

    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        print("\nSkipping real LLM call test: GOOGLE_API_KEY or GEMINI_API_KEY not set.")
        return

    if not os.path.exists(excel_file_path):
        print(f"\nTest Excel file not found at {excel_file_path}. Please ensure it's in the correct location.")
        # Also check relative to the script location if run from a different CWD
        alt_path = os.path.join(os.path.dirname(__file__), "..", "tests", "core", original_filename)
        if not os.path.exists(alt_path):
            print(f"Also not found at {alt_path}")
            return
        else:
            excel_file_path = alt_path # Use the found path
            print(f"Using file found at: {excel_file_path}")


    try:
        print(f"\n--- Testing with real Excel file: {original_filename} ---")
        with open(excel_file_path, "rb") as f_excel:
            excel_file_bytes = f_excel.read()
        
        print(f"Attempting to parse: {original_filename} (MIME: {mime_type})")
        parsed_data = await parse_file_to_structured_data(excel_file_bytes, mime_type, original_filename)
        
        print(f"\n--- LLM Parsed Output for {original_filename} ---")
        print(parsed_data.model_dump_json(indent=2))
        
        if parsed_data.punch_events:
            print(f"\nSuccessfully parsed {len(parsed_data.punch_events)} punch events.")
        else:
            print("\nNo punch events were parsed.")
        
        if parsed_data.parsing_issues:
            print("\nLLM Reported Parsing Issues:")
            for issue in parsed_data.parsing_issues:
                print(f"- {issue}")
        else:
            print("\nNo parsing issues reported by LLM.")

    except ValueError as ve:
        print(f"\nValueError during Excel test for {original_filename}: {ve}")
    except RuntimeError as re:
        print(f"\nRuntimeError during Excel test for {original_filename}: {re}")
    except Exception as e:
        print(f"\nAn unexpected error occurred during Excel test for {original_filename}: {e} (Type: {e.__class__.__name__}) ")


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
        print("Found Google API Key, running main_test for llm_processing.")
        asyncio.run(run_all_tests())
    else:
        print("GOOGLE_API_KEY or GEMINI_API_KEY not set. Skipping llm_processing.py main_test().")
        print("Please create a .env file or set environment variables (e.g., GOOGLE_API_KEY='your_key_here').") 