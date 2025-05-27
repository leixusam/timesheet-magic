# Google GenAI Utilities using the google.genai SDK

import os
from google import genai
from google.genai import errors as genai_errors # Use this for all SDK errors
import json

# Load model configuration
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
MODEL_CONFIG = {"google": {"default_model": "gemini-1.5-flash-latest", "vision_model": "gemini-pro-vision"}} # Default fallback
try:
    with open(CONFIG_PATH, 'r') as f:
        MODEL_CONFIG = json.load(f)
except FileNotFoundError:
    print(f"Warning: {CONFIG_PATH} not found. Using default Google model names.")
except json.JSONDecodeError:
    print(f"Warning: Error decoding {CONFIG_PATH}. Using default Google model names.")

GOOGLE_DEFAULT_MODEL = MODEL_CONFIG.get("google", {}).get("default_model", "gemini-1.5-flash-latest")
GOOGLE_VISION_MODEL = MODEL_CONFIG.get("google", {}).get("vision_model", "gemini-pro-vision")

def get_google_gemini_response(prompt: str, file_content: bytes = None, filename: str = None, mime_type: str = None):
    """
    Gets a response from Google Gemini API using the google.genai SDK.
    Handles text prompts and optional file uploads (images for gemini-pro-vision, text for gemini-1.5-flash-latest).
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Error: GOOGLE_API_KEY not found in environment variables. Please set it in your .env file or system environment."

    # Create the client - this is the correct pattern for google-genai SDK
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return f"Error creating Google GenAI client: {e}. Check if the API key is valid and the library is installed correctly."

    model_name = GOOGLE_DEFAULT_MODEL
    contents = [prompt]

    if file_content and filename and mime_type:
        if 'image' in mime_type.lower():
            model_name = GOOGLE_VISION_MODEL
            # For vision models, we need to structure the content differently
            # The SDK expects parts for multimodal content
            from google.genai import types
            image_part = types.Part.from_bytes(data=file_content, mime_type=mime_type)
            text_part = types.Part.from_text(text=prompt)
            contents = [text_part, image_part]
        else:
            try:
                file_text_content = file_content[:50000].decode(errors='ignore') 
                # For non-image files, append text content to the prompt
                enhanced_prompt = f"{prompt}\n\n--- User Uploaded File: {filename} (MIME type: {mime_type}) ---\n{file_text_content}\n--- End of File Content ---"
                contents = [enhanced_prompt]
            except Exception as e:
                return f"Error decoding or appending non-image file content: {e}"
    elif file_content:
        try:
            file_text_content = file_content[:50000].decode(errors='ignore')
            enhanced_prompt = f"{prompt}\n\n--- User Uploaded File (name/type unknown) ---\n{file_text_content}\n--- End of File Content ---"
            contents = [enhanced_prompt]
        except Exception as e:
            return f"Error decoding or appending file content (unknown type): {e}"

    try:
        # Use the client-based API pattern as shown in the documentation
        response = client.models.generate_content(
            model=model_name,
            contents=contents
        )

        # Check for blocked content due to safety or other reasons
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason:
            return (f"Error: Google API blocked the prompt. Reason: {response.prompt_feedback.block_reason.name}. "
                    f"Safety ratings: {response.prompt_feedback.safety_ratings if hasattr(response.prompt_feedback, 'safety_ratings') else 'N/A'}")
        
        # Check if we have a valid response
        if not hasattr(response, 'text') or not response.text:
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback and hasattr(response.prompt_feedback, 'safety_ratings'):
                for rating in response.prompt_feedback.safety_ratings:
                    if hasattr(rating, 'blocked') and rating.blocked:
                        return (f"Error: Google API blocked the prompt due to safety concerns. "
                                f"Category: {rating.category}, Probability: {rating.probability.name if hasattr(rating, 'probability') else 'N/A'}")
            return "Error: Received an empty response from Google Gemini. The prompt might have been blocked or resulted in no content."

        return response.text

    except genai_errors.APIError as e: # Catch-all for API errors from the google.genai SDK
        error_message = f"Google API Error: {str(e)}."
        # Try to infer more details from the error message
        if "API_KEY_INVALID" in str(e) or "API key not valid" in str(e) or "permission_denied" in str(e).lower() or "unauthorized" in str(e).lower():
            error_message += " This may indicate an issue with your GOOGLE_API_KEY (invalid, disabled, or missing permissions). Please verify your API key and project setup."
        elif "not found" in str(e).lower() or "could not find" in str(e).lower():
            error_message += f" The requested resource (e.g., model '{model_name}') might not be found or available."
        elif "quota" in str(e).lower() or "resource_exhausted" in str(e).lower():
             error_message += " You may have exceeded your API quota (Rate Limit). Please check your usage and limits."
        return error_message
    except Exception as e:
        return f"An unexpected error occurred while interacting with Google Generative AI: {str(e)} (Type: {e.__class__.__name__})" 