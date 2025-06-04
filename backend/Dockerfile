# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed by some Python packages
# (e.g., for psycopg2 if not using -binary, or other C extensions)
# For now, keeping it minimal. Add more if build errors occur for specific packages.
# RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment
# RUN python -m venv /opt/venv
# ENV PATH="/opt/venv/bin:$PATH"

# Copy the requirements files into the container at /app
COPY requirements.txt requirements-dev.txt ./

# Install any needed packages specified in requirements.txt and requirements-dev.txt
# Using --no-cache-dir can reduce image size slightly
# RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend application code into the container at /app
COPY ./app ./app

# Copy the llm_utils directory (LLM processing utilities)
COPY ./llm_utils ./llm_utils

# Copy the config.json file
COPY ./config.json ./config.json

# Make port 80 available to the world outside this container
# (FastAPI/Uvicorn will run on this port by default, or we can specify)
EXPOSE 8000

# Define environment variable for the port (optional, Uvicorn defaults to 8000)
ENV PORT 8000

# Run app.main:app when the container launches
# Use 0.0.0.0 to bind to all network interfaces
# Use --reload for development only, remove for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 