# Google GenAI Utilities using the google.genai SDK

import os
import json
import time # For retry logic
from typing import List, Dict, Any, Union, Optional # For type hinting

from google.genai import Client
from google.genai import types as genai_types
from google.genai import errors as genai_errors

print(f"DEBUG: Loaded google.genai Client from: {Client.__module__ if hasattr(Client, '__module__') else 'Not available'}")

# --- API Key Configuration ---
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if API_KEY:
    try:
        # Create client instance with API key
        client = Client(api_key=API_KEY)
        print("Google GenAI SDK client created successfully.")
    except Exception as e:
        print(f"Error creating Google GenAI SDK client: {e}. LLM calls may fail.")
        client = None
else:
    print("Warning (google_utils): GOOGLE_API_KEY or GEMINI_API_KEY not found. LLM calls will fail.")
    client = None

# Load model configuration
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
MODEL_CONFIG = {"google": {"default_model": "gemini-1.5-flash-latest", "vision_model": "gemini-1.5-flash-latest"}}
try:
    with open(CONFIG_PATH, 'r') as f:
        MODEL_CONFIG = json.load(f)
except FileNotFoundError:
    print(f"Warning: {CONFIG_PATH} not found. Using default Google model names.")
except json.JSONDecodeError:
    print(f"Warning: Error decoding {CONFIG_PATH}. Using default Google model names.")

GOOGLE_DEFAULT_MODEL = MODEL_CONFIG.get("google", {}).get("default_model", "gemini-1.5-flash-latest")
# GOOGLE_VISION_MODEL is kept for the existing function, but the new function gives more control
GOOGLE_VISION_MODEL = MODEL_CONFIG.get("google", {}).get("vision_model", "gemini-1.5-flash-latest") 

def get_google_gemini_response(prompt: str, file_content: bytes = None, filename: str = None, mime_type: str = None):
    """
    Gets a response from Google Gemini API using the google.genai SDK.
    Handles text prompts and optional file uploads (images, text).
    This function is kept for simpler, non-function-calling use cases.
    It uses google.genai.Client().
    """
    if not client:
        return "Error: GOOGLE_API_KEY or GEMINI_API_KEY not configured or client not created."

    model_name_to_use = GOOGLE_DEFAULT_MODEL
    contents_for_sdk = []

    # Prepare content based on input
    # This simple version assumes prompt is always text, and file_content might be image or appended text.
    # The new function will handle more complex `prompt_parts`.
    text_part_of_prompt = prompt

    if file_content and mime_type:
        if 'image' in mime_type.lower():
            model_name_to_use = GOOGLE_VISION_MODEL # Ensure this model is appropriate
            # For multi-part prompts (text + image), structure as a list of parts.
            # The google.genai SDK can take dicts for parts.
            image_data_dict = {"mime_type": mime_type, "data": file_content}
            contents_for_sdk = [text_part_of_prompt, image_data_dict]
        else: # Treat as text to append
            try:
                file_text_content = file_content.decode(errors='ignore')
                text_part_of_prompt = f"{prompt}\\n\\n--- User Uploaded File: {filename or 'unknown'} (MIME type: {mime_type}) ---\\n{file_text_content[:50000]}\\n--- End of File Content ---"
                contents_for_sdk = [text_part_of_prompt]
            except Exception as e:
                return f"Error decoding or appending non-image file content: {e}"
    else:
        contents_for_sdk = [text_part_of_prompt]

    try:
        # Use client.models.generate_content instead of genai.GenerativeModel
        model_path = f"models/{model_name_to_use}" if not model_name_to_use.startswith("models/") else model_name_to_use
        response = client.models.generate_content(
            model=model_path,
            contents=contents_for_sdk
        )

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            return (f"Error: Google API blocked the prompt. Reason: {response.prompt_feedback.block_reason.name}. "
                    f"Safety ratings: {response.prompt_feedback.safety_ratings if hasattr(response.prompt_feedback, 'safety_ratings') else 'N/A'}")
        
        # The .text accessor on GenerateContentResponse is the primary way to get simple text.
        if not response.text:
            if response.candidates:
                for candidate in response.candidates:
                    # Check if a candidate was blocked or stopped for unusual reasons
                    if candidate.finish_reason not in [genai_types.Candidate.FinishReason.STOP, genai_types.Candidate.FinishReason.MAX_TOKENS]:
                        if candidate.safety_ratings:
                            for rating in candidate.safety_ratings:
                                # More robust check for harmful content
                                if rating.probability not in [genai_types.HarmProbability.NEGLIGIBLE, genai_types.HarmProbability.LOW]:
                                    return (f"Error: Google API response potentially blocked due to safety. "
                                            f"Category: {rating.category.name}, Probability: {rating.probability.name}")
            return "Error: Received an empty text response from Google Gemini. The prompt might have been blocked or resulted in no usable content."

        return response.text

    except genai_errors.APIError as e: # Base class for most API errors
        error_message_str = str(e).lower()
        error_message = f"Google API Error ({e.__class__.__name__}): {str(e)}."
        if "api key not valid" in error_message_str or "permissiondenied" in e.__class__.__name__.lower():
            error_message += " This may indicate an issue with your GOOGLE_API_KEY (invalid, disabled, or missing permissions)."
        elif "notfound" in e.__class__.__name__.lower():
            error_message += f" The requested resource (e.g., model 'models/{model_name_to_use}') might not be found."
        elif "resourceexhausted" in e.__class__.__name__.lower() or "quota" in error_message_str:
             error_message += " You may have exceeded your API quota (Rate Limit)."
        elif "invalidargument" in e.__class__.__name__.lower(): 
            error_message += f" Invalid argument provided to the API: {e}"
        return error_message
    except Exception as e:
        return f"An unexpected error occurred (google_utils.get_google_gemini_response): {str(e)} (Type: {e.__class__.__name__})"


def get_gemini_response_with_function_calling(
    prompt_parts: List[Union[str, Dict[str, Any]]], # Can take dicts for parts, SDK handles conversion
    tools: Optional[List[Dict[str, Any]]] = None, # Tools as list of dicts, SDK handles conversion
    model_name_override: Optional[str] = None,
    max_retries: int = 3,
    initial_backoff_seconds: float = 1.0,
    temperature: Optional[float] = None
) -> Union[Dict[str, Any], str]:
    """
    Gets a response from Google Gemini API, supporting multi-modal input, function calling, and retries.
    Uses client.models.generate_content for API interaction.

    Args:
        prompt_parts: A list of content parts for the prompt (strings or dicts for file data).
        tools: An optional list of tool definitions (as dictionaries matching SDK structure).
        model_name_override: Optional model name to use (e.g., 'gemini-1.5-pro-latest').
        max_retries: Maximum number of retries for retryable errors.
        initial_backoff_seconds: Initial backoff time for retries.
        temperature: Optional temperature parameter for controlling randomness (0.0 for deterministic).

    Returns:
        A dictionary with function call arguments if a function is called by the LLM.
        A string with the LLM's text response if no function call is made.
        A string prefixed with "Error:" if an unrecoverable error occurs or retries are exhausted.
    """
    if not client:
        return "Error: GOOGLE_API_KEY or GEMINI_API_KEY not configured or client not created."

    model_to_use_str = model_name_override or GOOGLE_DEFAULT_MODEL
    
    # Prepend "models/" if not already present for client.generate_content model path
    if not model_to_use_str.startswith("models/"):
        model_path_for_api = f"models/{model_to_use_str}"
    else:
        model_path_for_api = model_to_use_str

    if "flash" not in model_to_use_str and "pro" not in model_to_use_str and "standard" not in model_to_use_str:
        print(f"Warning (google_utils): Model '{model_to_use_str}' might not fully support advanced function calling or all multimodal features. Consider models like 'gemini-1.5-flash-latest' or 'gemini-1.5-pro-latest'.")

    current_retry = 0
    while current_retry <= max_retries:
        try:
            print(f"[DEBUG] Starting API call attempt {current_retry + 1}/{max_retries + 1}")
            
            # Use client.models.generate_content instead of genai.GenerativeModel
            # Tools need to be passed through config parameter
            config = None
            if tools:
                print(f"[DEBUG] Converting {len(tools)} tool(s) to proper format...")
                # Convert tool dictionaries to proper Tool objects with FunctionDeclaration
                converted_tools = []
                for i, tool_dict in enumerate(tools):
                    print(f"[DEBUG] Converting tool {i + 1}: {tool_dict.get('name', 'unnamed')}")
                    # Create FunctionDeclaration from the dictionary format
                    func_decl = genai_types.FunctionDeclaration(
                        name=tool_dict["name"],
                        description=tool_dict["description"],
                        parameters=tool_dict["parameters"]
                    )
                    # Create Tool with the FunctionDeclaration
                    tool = genai_types.Tool(function_declarations=[func_decl])
                    converted_tools.append(tool)
                    print(f"[DEBUG] Tool {i + 1} converted successfully")
                
                print(f"[DEBUG] Creating GenerateContentConfig with {len(converted_tools)} tools...")
                config_kwargs = {"tools": converted_tools}
                if temperature is not None:
                    config_kwargs["temperature"] = temperature
                    print(f"[DEBUG] Setting temperature to {temperature}")
                config = genai_types.GenerateContentConfig(**config_kwargs)
                print(f"[DEBUG] Config created successfully")
            else:
                print(f"[DEBUG] No tools provided, creating config for temperature if needed")
                if temperature is not None:
                    config = genai_types.GenerateContentConfig(temperature=temperature)
                    print(f"[DEBUG] Created config with temperature {temperature}")
                else:
                    config = None
                    print(f"[DEBUG] Config will be None")
            
            print(f"[DEBUG] About to call client.models.generate_content with model: {model_path_for_api}")
            print(f"[DEBUG] Prompt parts count: {len(prompt_parts)}")
            print(f"[DEBUG] Config: {'Present' if config else 'None'}")
            
            response = client.models.generate_content(
                model=model_path_for_api,
                contents=prompt_parts,
                config=config
            )
            
            print(f"[DEBUG] API call completed successfully")
            print(f"[DEBUG] Response type: {type(response)}")
            print(f"[DEBUG] Has candidates: {bool(response.candidates)}")
            print(f"[DEBUG] Has prompt_feedback: {bool(response.prompt_feedback)}")

            if response.prompt_feedback and response.prompt_feedback.block_reason:
                print(f"[DEBUG] Prompt was blocked: {response.prompt_feedback.block_reason}")
                return (f"Error: Prompt was blocked by Google API. Reason: {response.prompt_feedback.block_reason.name}. "
                        f"Safety ratings: {response.prompt_feedback.safety_ratings if hasattr(response.prompt_feedback, 'safety_ratings') else 'N/A'}")

            print(f"[DEBUG] Checking for function calls in response...")
            # Check for function call in the first valid candidate
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                print(f"[DEBUG] Found {len(response.candidates[0].content.parts)} parts in response")
                for i, part in enumerate(response.candidates[0].content.parts):
                    print(f"[DEBUG] Part {i + 1}: has function_call = {hasattr(part, 'function_call') and part.function_call}")
                    if part.function_call:
                        print(f"[DEBUG] Function call found! Returning arguments...")
                        return dict(part.function_call.args)
            
            print(f"[DEBUG] No function call found, checking for text response...")
            if response.text:
                print(f"[DEBUG] Text response found: {len(response.text)} characters")
                return response.text
            
            print(f"[DEBUG] No text response, checking candidates for errors...")
            # If no text and no function call, inspect candidates further
            if response.candidates:
                candidate = response.candidates[0]
                print(f"[DEBUG] Candidate finish_reason: {candidate.finish_reason}")
                if candidate.finish_reason not in [genai_types.Candidate.FinishReason.STOP, genai_types.Candidate.FinishReason.MAX_TOKENS]:
                    detailed_error_msg = f"Error: LLM response was empty or incomplete. Finish Reason: {candidate.finish_reason.name}."
                    if candidate.safety_ratings:
                         detailed_error_msg += f" Safety Ratings: {[(sr.category.name, sr.probability.name) for sr in candidate.safety_ratings]}."
                    print(f"[DEBUG] Candidate error: {detailed_error_msg}")
                    return detailed_error_msg
                print(f"[DEBUG] Candidate finished normally but with empty response")
                return "" # Valid empty response (e.g. STOP with no text/FC)
            
            print(f"[DEBUG] No candidates found in response")
            return "Error: Received an empty response with no candidates from Google Gemini."

        except genai_errors.APIError as e: # Catch all Google API errors
            error_type = e.__class__.__name__
            error_message_str = str(e).lower()

            # Check for non-retryable conditions first based on message content or specific error types if they were available
            if "prompt was blocked" in error_message_str or "blockedprompt" in error_type.lower():
                # This also handles cases where response.prompt_feedback.block_reason might have been caught as APIError
                return f"Error: Google API blocked the prompt: {e}"
            # Add other specific non-retryable error string checks if needed, e.g., for invalid_argument before general retry.
            if "invalid argument" in error_message_str or "invalidargument" in error_type.lower():
                return f"Google API Error (InvalidArgumentError likely): {str(e)}. Invalid argument provided."
            if "permissiondenied" in error_type.lower() or "api key not valid" in error_message_str:
                 return f"Google API Error (PermissionDeniedError likely): {str(e)}. Check API key permissions or validity."
            if "notfound" in error_type.lower():
                return f"Google API Error (NotFoundError likely): {str(e)}. Model '{model_path_for_api}' or resource not found."

            # Heuristics for retryable conditions based on error message content or error type
            is_retryable_heuristic = (
                "quota" in error_message_str or 
                "resource exhausted" in error_message_str or 
                "rate limit" in error_message_str or 
                "service unavailable" in error_message_str or
                "deadline exceeded" in error_message_str or
                "internal server error" in error_message_str or
                isinstance(e, genai_errors.ServerError) # If ServerError is a known type
            )

            if is_retryable_heuristic and current_retry < max_retries:
                print(f"Retryable API Error ({error_type}) encountered: {e}. Retry {current_retry + 1}/{max_retries}...")
                backoff_time = (initial_backoff_seconds * (2 ** current_retry)) + (os.urandom(1)[0] / 256.0)
                print(f"Waiting {backoff_time:.2f} seconds before retrying.")
                time.sleep(backoff_time)
                current_retry += 1
            else:
                # Non-retryable or retries exhausted for this type of APIError
                full_error_message = f"Google API Error ({error_type}) after {current_retry} retries (or non-retryable): {str(e)}."
                return full_error_message
        
        except Exception as e: # Catch any other unexpected non-API errors
            print(f"Unexpected non-API error in get_gemini_response_with_function_calling: {e} (Type: {e.__class__.__name__}). Retry {current_retry + 1}/{max_retries}...")
            if current_retry == max_retries:
                return f"Error: An unexpected non-API error occurred after {max_retries} retries: {e}"
            backoff_time = (initial_backoff_seconds * (2 ** current_retry)) + (os.urandom(1)[0] / 256.0)
            time.sleep(backoff_time)
            current_retry += 1
            
    return f"Error: All {max_retries} retries failed for get_gemini_response_with_function_calling."

# Example of how Pydantic schemas can be converted to Gemini Tool dictionary structure:
# This helper would typically live in llm_processing.py or a shared schema utilities module.
#
# from pydantic import BaseModel
# from google.genai import types as genai_types # If constructing genai_types.Tool directly
#
# def pydantic_to_gemini_tool_dict(pydantic_model_cls, tool_name: str, tool_description: str) -> Dict[str, Any]:
#     # Pydantic's .model_json_schema() generates a JSON schema
#     # We need to adapt this to Gemini's FunctionDeclaration parameters schema format
#     # Gemini's `tools` parameter can accept dicts structured like FunctionDeclarations
#     
#     model_schema = pydantic_model_cls.model_json_schema()
#     
#     # Basic mapping from JSON Schema types to Gemini's Schema types (approximated)
#     # Gemini's Type enum: STRING, NUMBER, INTEGER, BOOLEAN, ARRAY, OBJECT
#     type_mapping = {
#         "string": "STRING",
#         "number": "NUMBER",
#         "integer": "INTEGER",
#         "boolean": "BOOLEAN",
#         "array": "ARRAY",
#         "object": "OBJECT",
#     }
# 
#     properties = {}
#     if "properties" in model_schema:
#         for name, prop_schema in model_schema["properties"].items():
#             # Determine Gemini type (this is a simplified mapping)
#             json_type = prop_schema.get("type", "string") # Default to string if type not specified
#             gemini_type = type_mapping.get(json_type.lower(), "STRING")
#             
#             # Handle enums (if present in Pydantic schema, map to string with enum values in description)
#             enum_values = prop_schema.get("enum")
#             description = prop_schema.get("description", "")
#             if enum_values:
#                 description += f" (Enum: {", ".join(map(str, enum_values))})"

#             parameter_prop = {
#                 "type": gemini_type,
#                 "description": description
#             }
#             # For arrays, specify items schema if possible (simplified here)
#             if gemini_type == "ARRAY" and "items" in prop_schema and "type" in prop_schema["items"]:
#                 parameter_prop["items"] = {"type": type_mapping.get(prop_schema["items"]["type"].lower(), "STRING")}
#             
#             properties[name] = parameter_prop
# 
#     function_declaration_dict = {
#         "name": tool_name,
#         "description": tool_description,
#         "parameters": {
#             "type": "OBJECT", # The 'parameters' field itself is an object schema
#             "properties": properties,
#             "required": model_schema.get("required", [])
#         }
#     }
#     # The `tools` argument to `client.generate_content` takes an Iterable of Tool or dict.
#     # A dict structured like a FunctionDeclaration is accepted.
#     return function_declaration_dict 
#
# Example Usage (conceptual, in llm_processing.py):
# from backend.app.models.schemas import LLMProcessingOutput # Your Pydantic model
# tool_dict = pydantic_to_gemini_tool_dict(LLMProcessingOutput, "timesheet_parser", "Parses timesheet data.")
# result = get_gemini_response_with_function_calling(prompt_parts, tools=[tool_dict]) 