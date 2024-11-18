# Stage 1: Builder
FROM python:3.11-slim AS builder

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONWARNINGS="ignore" \
    TF_ENABLE_ONEDNN_OPTS=0 \
    TF_CPP_MIN_LOG_LEVEL=3

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    ca-certificates \
    libjpeg-dev \
    zlib1g-dev \
    ffmpeg

# Set working directory for the build stage
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Upgrade pip and install Python dependencies into a virtual environment
RUN pip install --upgrade pip \
    && pip install --no-cache-dir virtualenv \
    && virtualenv venv \
    && ./venv/bin/pip install --no-cache-dir -r requirements.txt

# Remove unneeded packages and clear apt cache to reduce image size
RUN apt-get remove -y build-essential git \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Final Image
FROM python:3.11-slim AS final

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONWARNINGS="ignore" \
    TF_ENABLE_ONEDNN_OPTS=0 \
    TF_CPP_MIN_LOG_LEVEL=3

# Install only the runtime dependencies required by your application
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the final image
WORKDIR /app

# Copy only the virtual environment with installed packages from builder stage
COPY --from=builder /app/venv /app/venv

# Copy the application code into the container
COPY . .

# Expose the port Uvicorn will run on
EXPOSE 8000

# Activate virtual environment and run the FastAPI application using Uvicorn
CMD ["/app/venv/bin/uvicorn", "moseca.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
