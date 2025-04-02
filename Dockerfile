# Base image for both architectures
FROM python:3.9-slim AS base

# Common system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    libgomp1 \
    git \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up environment variables for better performance
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_CACHE=/app/.cache/huggingface \
    HF_DATASETS_CACHE=/app/.cache/huggingface/datasets \
    TRANSFORMERS_CACHE=/app/.cache/huggingface/transformers \
    PATH="/home/app/.local/bin:${PATH}"

# Create a non-root user to run the app
RUN useradd -m -u 1000 app
WORKDIR /app
RUN mkdir -p /app/.cache/huggingface && \
    chown -R app:app /app

# Copy requirements file
COPY --chown=app:app requirements.txt .

# Switch to non-root user
USER app

# Install common dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install additional ML dependencies that don't require CUDA compilation
RUN pip install --no-cache-dir accelerate

# Copy the application code
COPY --chown=app:app . .

# For local development on CUDA-capable machines, build with:
# docker build --target cuda -t sleep-analysis-service:cuda .
FROM base AS cuda

# Install CUDA-specific PyTorch
USER app
RUN pip install --no-cache-dir --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For Apple Silicon, build with:
# docker build --target apple-silicon --platform=linux/arm64 -t sleep-analysis-service:apple .
FROM base AS apple-silicon

# Install PyTorch for Apple Silicon
USER app
RUN pip install --user --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.6.0

# Expose port
EXPOSE 8000

# Run the application with optimized settings
ENTRYPOINT ["/home/app/.local/bin/uvicorn"]
CMD ["app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
