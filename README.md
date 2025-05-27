# AI Multi-Tool Template

This project is a basic template for AI applications, providing a scaffold with a frontend, backend, and LLM utilities for OpenAI and Google Generative AI. It features a simple web interface to send prompts and (optionally) files to either AI provider and view the response.

## Project Structure

```
.
├── backend/
│   └── main.py         # FastAPI backend (Python)
├── frontend/
│   └── index.html      # HTML frontend with Tailwind CSS and JavaScript
├── llm_utils/
│   ├── __init__.py
│   ├── openai_utils.py # Utilities for OpenAI API
│   └── google_utils.py # Utilities for Google Generative AI API
├── .gitignore
├── config.json         # Configuration for model names
├── README.md
├── requirements.txt    # Python dependencies
└── .env                # For API keys (you need to create this based on .env.example if provided, or manually)
```

## Features

-   **Dual AI Provider Support:** Easily switch between OpenAI (GPT models) and Google (Gemini models).
-   **File Uploads:** Basic support for including file content with your prompts.
    -   OpenAI: File content (text snippet) is added to the system message.
    -   Google: Uses `gemini-pro-vision` for images and prepends text content for other file types with `gemini-pro`.
-   **Simple Web Interface:** Built with HTML, Tailwind CSS, and vanilla JavaScript.
-   **FastAPI Backend:** Robust and easy-to-develop Python backend.
-   **Reusable LLM Utilities:** Modular code for AI interactions.
-   **Environment-based API Key Management:** Uses a `.env` file for secure API key storage.

## Setup

1.  **Clone/Copy Project:**
    If this were a git repository, you would clone it. For now, ensure you have all the files in a project directory.

2.  **Create Python Virtual Environment:**
    It's highly recommended to use a virtual environment.
    ```bash
    python3 -m venv venv
    # On macOS/Linux
    source venv/bin/activate
    # On Windows
    # venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up API Keys:**
    Create a file named `.env` in the **root** of the project directory (alongside `requirements.txt` and the `backend` folder).
    Add your API keys to this file:
    ```env
    OPENAI_API_KEY="your_openai_api_key_here"
    GOOGLE_API_KEY="your_google_api_key_here"
    ```
    -   Replace `your_openai_api_key_here` with your key from [OpenAI Platform](https://platform.openai.com/account/api-keys).
    -   Replace `your_google_api_key_here` with your key from [Google AI Studio (formerly MakerSuite)](https://aistudio.google.com/app/apikey).

## Running the Application

1.  **Start the Backend Server:**
    Open a terminal, ensure your virtual environment is activated, navigate to the project root, and run:
    ```bash
    python backend/main.py
    ```
    The backend will start, typically at `http://127.0.0.1:8000`. Check the terminal output for the exact address.
    The `main.py` script uses `uvicorn.run("main:app", ..., reload=True)`, so changes to `backend/main.py` should auto-reload the server.

2.  **Open the Frontend:**
    Open the `frontend/index.html` file directly in your web browser (e.g., by double-clicking it or using "File > Open" in your browser).

3.  **Interact with the AI:**
    -   The page will load; you can choose an AI provider.
    -   Type your query in the prompt input box.
    -   Optionally, select a file to upload.
    -   Click "Send Prompt". The response from the AI will appear below the form.

## LLM Utilities (`llm_utils`)

Model names for both OpenAI and Google are now configurable via the `config.json` file in the project root. The utilities will fall back to default model names if this file is missing or improperly formatted.

-   `openai_utils.py`:
    -   `get_openai_chat_response()`: Interacts with OpenAI chat models (e.g., `gpt-3.5-turbo`).
    -   Handles API key loading from environment variables.
    -   Basic file handling: prepends file name and a snippet of its content to the system message.
    -   Includes error handling for common API issues.

-   `google_utils.py`:
    -   `get_google_gemini_response()`: Interacts with Google Gemini models.
    -   Handles API key loading and configuration.
    -   File handling: 
        -   Uses `gemini-pro-vision` if an image MIME type is detected.
        -   For other file types, it prepends the file name and a snippet of its content to the prompt for `gemini-pro`.
    -   Includes error handling for common API issues and prompt feedback (e.g., safety blocks).

This template provides a solid foundation. You can expand upon it by adding more sophisticated file handling, specific model configurations, database integration, user authentication, and more complex frontend features. 