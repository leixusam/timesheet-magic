from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel # For potential request body validation, though Form is used here
import os
import sys
from typing import Optional # For UploadFile

# Add project root to sys.path to allow importing llm_utils
# This assumes backend/main.py is one level deep from the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from llm_utils import get_openai_chat_response, get_google_gemini_response
from dotenv import load_dotenv

# Load .env file from the project root
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(DOTENV_PATH)

app = FastAPI()

# CORS middleware to allow frontend requests (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "null"], # "null" for local file:// origin
    allow_credentials=True,
    allow_methods=["POST"], # Only allow POST for this endpoint
    allow_headers=["*"] # Or specify necessary headers
)

# Model for the form data is not strictly necessary when using Form directly,
# but can be good for documentation or if you switch to JSON body.
# class AIQuery(BaseModel):
# text: str
# provider: str

@app.post("/api/generate")
async def generate_text(
    provider: str = Form(...),
    text: str = Form(...),
    file: Optional[UploadFile] = File(None) # Optional file upload
):
    print(f"Backend received: Provider='{provider}', Text='{text[:50]}...', File='{file.filename if file else None}'")

    file_content: Optional[bytes] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None

    if file:
        file_content = await file.read()
        filename = file.filename
        mime_type = file.content_type
        print(f"File details: Name='{filename}', Type='{mime_type}', Size='{len(file_content)} bytes'")

    # API key checks (redundant if utils handle it, but good for early exit)
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not configured in backend.")
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set. Please configure it in the .env file.")
    if provider == "google" and not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY not configured in backend.")
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not set. Please configure it in the .env file.")

    response_text = ""
    try:
        if provider == "openai":
            response_text = get_openai_chat_response(prompt=text, file_content=file_content, filename=filename)
        elif provider == "google":
            response_text = get_google_gemini_response(prompt=text, file_content=file_content, filename=filename, mime_type=mime_type)
        else:
            raise HTTPException(status_code=400, detail="Invalid AI provider specified. Choose 'openai' or 'google'.")
        
        # The utility functions now return error strings prefixed with "Error:"
        if isinstance(response_text, str) and response_text.startswith("Error:"):
            print(f"LLM Util Error: {response_text}")
            # Pass the detailed error from the util to the client
            raise HTTPException(status_code=500, detail=response_text)
            
        return {"response": response_text}
    except HTTPException as e:
        # Re-raise HTTPExceptions directly (e.g., from provider check or invalid provider)
        raise e 
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(f"Unexpected backend error: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred on the server: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print(f"Starting Uvicorn server for backend.main:app...")
    print(f"Project root (for .env): {PROJECT_ROOT}")
    print(f"Attempting to load .env from: {DOTENV_PATH}")
    # For debugging, check if keys are loaded (don't print keys themselves)
    print(f"OpenAI Key Loaded: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
    print(f"Google Key Loaded: {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 