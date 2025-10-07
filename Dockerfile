
# Use an official Python runtime as a parent image
FROM python:3.10-slim

# --- 1. SYSTEM DEPENDENCY FIX ---
# Install system-level dependencies required for compilation (FAISS, Sentence-Transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*
# --- END: SYSTEM DEPENDENCY FIX ---

# Set the working directory in the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .

# Install necessary Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- 2. CRITICAL COPY FIX: Copy source modules and frontend ---

# Copy the core Python module (where app.main:app lives).
# This automatically copies the 'app/logs' folder where PDFs are stored.
COPY ./app /app/app

# Copy the frontend files
COPY ./frontend /app/frontend

# NOTE: The root-level COPY ./logs is REMOVED to solve the file-not-found conflict.
# The necessary logs folder structure (app/logs) is already copied above.

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define the command to run your app using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Use an official Python runtime as a parent image
FROM python:3.10-slim

# --- 1. SYSTEM DEPENDENCY FIX ---
# Install system-level dependencies required for compilation (FAISS, Sentence-Transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*
# --- END: SYSTEM DEPENDENCY FIX ---

# Set the working directory in the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .

# Install necessary Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- 2. CRITICAL COPY FIX: Copy source modules and frontend ---

# Copy the core Python module (where app.main:app lives). 
# This automatically copies the 'app/logs' folder where PDFs are stored.
COPY ./app /app/app

# Copy the frontend files 
COPY ./frontend /app/frontend 

# NOTE: The root-level COPY ./logs is REMOVED to solve the file-not-found conflict.
# The necessary logs folder structure (app/logs) is already copied above.

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define the command to run your app using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

