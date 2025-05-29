import os
from dotenv import load_dotenv
# Pillow is not strictly needed here anymore if MIME type is passed in and validated upstream
# import Image 
import io # Added for handling bytes for openpyxl
import asyncio
import json
from typing import List, Optional, Dict, Any, Union # Added Dict, Any, Union

import openpyxl # Added for Excel processing

from backend.app.models.schemas import LLMProcessingOutput, LLMParsedPunchEvent
from llm_utils.google_utils import get_gemini_response_with_function_calling

# Load environment variables
load_dotenv()

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
    Sends raw file content (image, PDF, text, or pre-processed Excel) to a multi-modal LLM 
    for direct parsing into a structured Pydantic schema using function calling,
    leveraging the enhanced utility in llm_utils.google_utils.

    Args:
        file_bytes: The raw bytes of the file.
        mime_type: The MIME type of the file (e.g., 'image/png', 'application/pdf', 'text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet').
        original_filename: The name of the original file, for context.
        debug_dir: The directory to save debug files (optional).

    Returns:
        An LLMProcessingOutput object with the parsed data.

    Raises:
        ValueError: If the MIME type is unsupported or if text/Excel content cannot be decoded/parsed.
        RuntimeError: If LLM interaction fails or data cannot be normalized.
    """
    
    tool_name = "timesheet_data_extractor"
    tool_description = f"Extracts structured timesheet data (employee punch events and parsing issues) directly from the content of the provided file named '{original_filename}' (MIME type: {mime_type})."
    
    timesheet_tool_dict = pydantic_to_gemini_tool_dict(LLMProcessingOutput, tool_name, tool_description)

    # Save debug information if debug_dir is provided
    if debug_dir:
        import json
        os.makedirs(debug_dir, exist_ok=True)
        
        # Save function declaration
        with open(os.path.join(debug_dir, "function_declaration.json"), 'w') as f:
            json.dump(timesheet_tool_dict, f, indent=2)
        
        # Save schema information
        schema_info = {
            "tool_name": tool_name,
            "tool_description": tool_description,
            "pydantic_schema": LLMProcessingOutput.model_json_schema(),
            "punch_event_schema": LLMParsedPunchEvent.model_json_schema()
        }
        with open(os.path.join(debug_dir, "schema_info.json"), 'w') as f:
            json.dump(schema_info, f, indent=2)
        
        print(f"[DEBUG] Function declaration saved to {debug_dir}/function_declaration.json")

    prompt_intro = f"""You are a timesheet data extraction specialist. Your task is to analyze the provided timesheet file and extract ALL individual employee punch events.

IMPORTANT: You MUST use the '{tool_name}' function to return your findings. Do not provide a text response.

CRITICAL: Extract ALL punch events from the entire timesheet. Look for every single clock in, clock out, break start, break end entry for every employee. The timesheet may contain hundreds of entries - extract them all.

File to analyze: '{original_filename}' (MIME type: {mime_type})

For each punch event, extract:
- Employee name/identifier as it appears in the file
- Exact timestamp of each punch (clock in, clock out, break start, break end, etc.)
- Type of punch (Clock In, Clock Out, Break Start, Break End, Lunch Start, Lunch End, etc.)
- Any additional details like role, department, or notes if present

Return ALL punch events in the punch_events array. Do not stop at the first few - process the entire timesheet data.

Also note any parsing issues you encounter (unclear data, missing information, formatting problems).

Use the '{tool_name}' function with your extracted data now:"""
    
    prepared_prompt_parts: List[Union[str, Dict[str, Any]]] = [prompt_intro]

    if mime_type.startswith("image/") or mime_type == "application/pdf":
        prepared_prompt_parts.append({"mime_type": mime_type, "data": file_bytes})
    elif mime_type.startswith("text/") or mime_type == "text/csv" or mime_type == "application/csv":
        try:
            text_content = file_bytes.decode('utf-8')
            prepared_prompt_parts.append("\n\n--- Timesheet Text Content ---\n" + text_content + "\n--- End of Text Content ---")
        except UnicodeDecodeError as e:
            raise ValueError(f"Could not decode text-based file '{original_filename}' as UTF-8: {e}")
    elif mime_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
        try:
            workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True) # data_only=True to get values not formulas
            sheet = workbook.active # Or iterate through workbook.sheetnames and workbook[sheet_name]
            
            extracted_text_lines = []
            data_row_count = 0
            header_found = False
            
            for row_idx, row in enumerate(sheet.iter_rows()):
                row_values = []
                for cell in row:
                    cell_value = cell.value
                    if cell_value is None:
                        row_values.append("") # Represent empty cells as empty strings
                    else:
                        row_values.append(str(cell_value).strip()) # Convert to string and strip whitespace
                
                row_text = ",".join(row_values)
                
                # Skip completely empty rows
                if not row_text.strip() or row_text.replace(",", "").strip() == "":
                    continue
                
                # Look for header-like content or employee data
                row_lower = row_text.lower()
                if any(keyword in row_lower for keyword in ["employee", "name", "clock", "time", "punch", "in", "out", "date", "shift"]):
                    header_found = True
                
                # If we found header-like content, start including subsequent rows
                if header_found:
                    extracted_text_lines.append(row_text)
                    if any(char.isdigit() for char in row_text) and ("am" in row_lower or "pm" in row_lower or ":" in row_text):
                        data_row_count += 1
                
                # Continue processing all rows (removed the 50-row limit for complete processing)
                # if data_row_count >= 50:  # Removed this limit
                #     extracted_text_lines.append("... [Additional timesheet data truncated for processing]")
                #     break
            
            excel_text_content = "\n".join(extracted_text_lines)
            
            if not excel_text_content.strip():
                print(f"Warning: Excel file '{original_filename}' ({mime_type}) was parsed but yielded no text content.")
                return LLMProcessingOutput(punch_events=[], parsing_issues=[f"Excel file '{original_filename}' parsed to empty text content."])

            # Check if content is too large for single processing
            MAX_CHARS = 50000  # Increased limit for complete processing
            if len(excel_text_content) > MAX_CHARS:
                print(f"Warning: Excel content is large ({len(excel_text_content)} chars), will process in chunks")
                
                # Split into chunks by lines to maintain data integrity
                lines = extracted_text_lines
                chunk_size = min(100, len(lines) // 3)  # Process in chunks of ~100 lines or 1/3 of total
                chunks = [lines[i:i + chunk_size] for i in range(0, len(lines), chunk_size)]
                
                print(f"Processing {len(chunks)} chunks of approximately {chunk_size} lines each")
                
                all_punch_events = []
                all_parsing_issues = []
                
                for chunk_idx, chunk_lines in enumerate(chunks):
                    chunk_content = "\n".join(chunk_lines)
                    chunk_prompt = prompt_intro.replace(
                        "extract ALL individual employee punch events",
                        f"extract all punch events from this chunk ({chunk_idx + 1}/{len(chunks)})"
                    )
                    
                    print(f"Processing chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk_content)} chars)")
                    
                    chunk_prompt_parts = [
                        chunk_prompt,
                        f"\n\n--- Excel Chunk {chunk_idx + 1}/{len(chunks)} ---\n" + chunk_content + "\n--- End of Chunk ---"
                    ]
                    
                    try:
                        chunk_response = get_gemini_response_with_function_calling(
                            prompt_parts=chunk_prompt_parts,
                            tools=[timesheet_tool_dict],
                            model_name_override=model_override,
                            max_retries=2
                        )
                        
                        if isinstance(chunk_response, dict):
                            # Process chunk response same as main response
                            if "punch_events" in chunk_response:
                                all_punch_events.extend(chunk_response.get("punch_events", []))
                                all_parsing_issues.extend(chunk_response.get("parsing_issues", []))
                            elif "employee_identifier_in_file" in chunk_response:
                                all_punch_events.append(chunk_response)
                    
                    except Exception as chunk_error:
                        print(f"Error processing chunk {chunk_idx + 1}: {chunk_error}")
                        all_parsing_issues.append(f"Error processing chunk {chunk_idx + 1}: {str(chunk_error)}")
                
                print(f"Chunk processing complete. Total events: {len(all_punch_events)}")
                return LLMProcessingOutput(
                    punch_events=all_punch_events,
                    parsing_issues=all_parsing_issues
                )
            else:
                # Process normally if content is small enough
                excel_text_content = excel_text_content[:MAX_CHARS] + ("\n... [TRUNCATED]" if len(excel_text_content) > MAX_CHARS else "")

            prepared_prompt_parts.append("\n\n--- Extracted Excel Content (CSV-like format) ---\n" + excel_text_content + "\n--- End of Excel Content ---")
            print(f"Successfully pre-processed Excel file '{original_filename}' ({mime_type}) to text for LLM. Data rows found: {data_row_count}")
        except Exception as e:
            # Catching general exceptions from openpyxl loading/parsing
            raise ValueError(f"Failed to parse Excel file '{original_filename}' ({mime_type}). Error: {e}")
    else:
        raise ValueError(f"Unsupported MIME type for LLM processing: {mime_type}. Supported: image/*, application/pdf, text/*, text/csv, Excel.")

    try:
        print(f"Calling LLM utility for file: {original_filename} (MIME: {mime_type})")
        print(f"[DEBUG] Prepared prompt parts: {len(prepared_prompt_parts)} parts")
        for i, part in enumerate(prepared_prompt_parts):
            if isinstance(part, str):
                print(f"[DEBUG] Part {i + 1}: String with {len(part)} characters")
            else:
                print(f"[DEBUG] Part {i + 1}: Dict with keys: {list(part.keys())}")
        
        # Use the default model from config for most files, can be overridden if needed
        model_override = None
        # For larger files or when the default model fails, try the high-power model
        if len(str(prepared_prompt_parts)) > 10000:  # Use Pro model for larger content
            try:
                import json
                config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config.json')
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    model_override = config.get("google", {}).get("high_model")
                    print(f"[DEBUG] Using high-power model for large content: {model_override}")
            except Exception:
                pass  # Fall back to default model if config loading fails
        
        print(f"[DEBUG] Creating tool dictionary...")
        print(f"[DEBUG] Tool name: {timesheet_tool_dict.get('name')}")
        print(f"[DEBUG] Tool description length: {len(timesheet_tool_dict.get('description', ''))}")
        print(f"[DEBUG] Tool parameters keys: {list(timesheet_tool_dict.get('parameters', {}).keys())}")
        
        print(f"[DEBUG] About to call get_gemini_response_with_function_calling...")
        # Call the enhanced utility from llm_utils
        
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
        
        llm_response_data = get_gemini_response_with_function_calling(
            prompt_parts=prepared_prompt_parts,
            tools=[timesheet_tool_dict],
            model_name_override=model_override,
            max_retries=2
        )
        
        print(f"[DEBUG] LLM call completed, response type: {type(llm_response_data)}")
        if isinstance(llm_response_data, str):
            print(f"[DEBUG] String response length: {len(llm_response_data)}")
        elif isinstance(llm_response_data, dict):
            print(f"[DEBUG] Dict response keys: {list(llm_response_data.keys())}")

        if isinstance(llm_response_data, dict):
            # Function call was successful, response_data contains the arguments
            # Construct the Pydantic object from the LLM's arguments
            try:
                print(f"[DEBUG] LLM response keys: {list(llm_response_data.keys())}")
                print(f"[DEBUG] LLM response data: {llm_response_data}")
                
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
            error_msg = f"LLM did not use the function call for '{original_filename}' as expected, returned text instead: '{llm_response_data[:500]}...'"
            print(error_msg)
            # Consider if this text might contain parsing_issues from the LLM.
            # For now, treating as a failure to adhere to function call instruction.
            # You could potentially try to parse this text for fallback `parsing_issues`.
            return LLMProcessingOutput(punch_events=[], parsing_issues=[error_msg]) # Or raise RuntimeError
        else:
            # Unexpected response type from utility
            error_msg = f"Unexpected response type from LLM utility for '{original_filename}': {type(llm_response_data)}"
            print(error_msg)
            raise RuntimeError(error_msg)

    except ValueError as ve: # Re-raise ValueErrors from MIME type handling or decoding
        raise ve 
    except RuntimeError as re: # Re-raise RuntimeErrors from LLM utility or Pydantic parsing
        raise re
    except Exception as e:
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