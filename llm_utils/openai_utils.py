# OpenAI LLM Utilities

import openai
import os
import json

# Load environment variables
# from dotenv import load_dotenv
# load_dotenv() # Consider loading .env file if you choose to use one

# Load model configuration
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
MODEL_CONFIG = {"openai": {"default_model": "gpt-3.5-turbo"}} # Default fallback
try:
    with open(CONFIG_PATH, 'r') as f:
        MODEL_CONFIG = json.load(f)
except FileNotFoundError:
    print(f"Warning: {CONFIG_PATH} not found. Using default OpenAI model name.")
except json.JSONDecodeError:
    print(f"Warning: Error decoding {CONFIG_PATH}. Using default OpenAI model name.")

OPENAI_DEFAULT_MODEL = MODEL_CONFIG.get("openai", {}).get("default_model", "gpt-3.5-turbo")
# OPENAI_VISION_MODEL = MODEL_CONFIG.get("openai", {}).get("vision_model", "gpt-4-vision-preview") # If you implement vision for OpenAI

# openai.api_key = os.getenv("OPENAI_API_KEY") # The SDK does this by default

def get_openai_response(prompt: str, file_content: bytes = None, filename: str = None):
    """Gets a response from OpenAI, potentially with file context."""
    # Placeholder for actual implementation
    if not openai.api_key:
        return "Error: OPENAI_API_KEY not configured."

    if file_content:
        # This is a simplified example. For actual file uploads with OpenAI,
        # you might need to use the Assistants API or other methods depending on your exact needs.
        # For now, we'll just prepend a message about the file to the prompt.
        prompt = f"The user uploaded a file named '{filename}'.\n\nContent (first 1000 chars):\n{file_content[:1000].decode(errors='ignore')}\n\nUser prompt: {prompt}"

    try:
        response = openai.Completion.create(
            engine="text-davinci-003",  # Or another model like gpt-3.5-turbo with ChatCompletion
            prompt=prompt,
            max_tokens=150
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error interacting with OpenAI: {e}"

# Example for ChatCompletion (more common now):
def get_openai_chat_response(prompt: str, file_content: bytes = None, filename: str = None):
    """Gets a chat response from OpenAI (e.g., gpt-3.5-turbo or gpt-4), potentially with file context."""
    # The OpenAI SDK automatically loads the API key from the OPENAI_API_KEY environment variable.
    # If it's not set, the SDK will raise an error.
    # We add a check here for a more user-friendly message if running locally and it's missing.
    if not os.getenv("OPENAI_API_KEY"):
         return "Error: OPENAI_API_KEY not found in environment variables. Please set it in your .env file or system environment."

    messages = []
    if file_content:
        # This is a simplified way to include file context for chat models.
        # For larger files or more complex interactions (e.g. vision capabilities with GPT-4o),
        # you might need to summarize, chunk, or use specific APIs/tools.
        # For simplicity, we'll inform the model about the uploaded file and include a snippet.
        messages.append({
            "role": "system",
            "content": f"The user has uploaded a file named '{filename}'. Its content (first 1000 characters) is: {file_content[:1000].decode(errors='ignore')}"
        })
    
    messages.append({"role": "user", "content": prompt})

    try:
        client = openai.OpenAI() # Initializes with API key from environment
        response = client.chat.completions.create(
            model=OPENAI_DEFAULT_MODEL, # Use model from config
            messages=messages,
            max_tokens=500 # Increased max_tokens for potentially longer responses
        )
        return response.choices[0].message.content.strip()
    except openai.APIConnectionError as e:
        return f"OpenAI API Connection Error: {e}"
    except openai.RateLimitError as e:
        return f"OpenAI API Rate Limit Exceeded: {e}"
    except openai.AuthenticationError as e:
        return f"OpenAI API Authentication Error: {e}. Check your API key."
    except openai.APIError as e:
        return f"OpenAI API Error: {e}"
    except Exception as e:
        return f"An unexpected error occurred with OpenAI: {e}" 