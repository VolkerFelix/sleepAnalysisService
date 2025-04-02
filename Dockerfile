# Use CUDA-enabled base image for GPU support
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 AS cuda-base

# Install Python and required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.9 \
    python3-pip \
    python3-dev \
    python3-setuptools \
    gcc \
    g++ \
    build-essential \
    libgomp1 \
    git \
    wget \
    ninja-build \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set Python aliases for convenience
RUN ln -sf /usr/bin/python3.9 /usr/bin/python && \
    ln -sf /usr/bin/python3.9 /usr/bin/python3

# Create a non-root user to run the app
RUN useradd -m -u 1000 app
WORKDIR /app
RUN chown app:app /app

# Apple Silicon variant
FROM --platform=linux/arm64 python:3.9-slim AS arm-base

# Install system dependencies for Apple Silicon
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    libgomp1 \
    git \
    wget \
    ninja-build \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user to run the app
RUN useradd -m -u 1000 app
WORKDIR /app
RUN chown app:app /app

# Detect architecture and choose appropriate base
FROM cuda-base AS amd64-build
FROM arm-base AS arm64-build
FROM ${TARGETARCH}-build AS final

# Set up environment variables for better performance
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 \
    CUDA_VISIBLE_DEVICES=0 \
    HF_HUB_CACHE=/app/.cache/huggingface \
    HF_DATASETS_CACHE=/app/.cache/huggingface/datasets \
    TRANSFORMERS_CACHE=/app/.cache/huggingface/transformers

# Create directory for model cache
RUN mkdir -p /app/.cache/huggingface && \
    chown -R app:app /app/.cache

# Copy requirements first for better caching
COPY --chown=app:app requirements.txt .

# Switch to non-root user
USER app

# Install Python dependencies with optimizations for different architectures
RUN if [ "$(uname -m)" = "aarch64" ]; then \
        # For Apple Silicon/ARM
        pip install --no-cache-dir --upgrade pip && \
        pip install --no-cache-dir -r requirements.txt && \
        # Reinstall PyTorch with MPS support
        pip install --no-cache-dir --force-reinstall torch torchvision torchaudio; \
    else \
        # For CUDA (x86_64)
        pip install --no-cache-dir --upgrade pip && \
        pip install --no-cache-dir -r requirements.txt && \
        # Reinstall PyTorch with CUDA support
        pip install --no-cache-dir --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118; \
    fi

# Install additional dependencies for better performance
RUN pip install --no-cache-dir \
    bitsandbytes \
    accelerate

# Try to install flash-attn but continue if it fails
RUN pip install --no-cache-dir flash-attn || echo "flash-attn installation failed, continuing without it"

# Copy the application code
COPY --chown=app:app . .

# Expose port
EXPOSE 8000

# Run the application with optimized settings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
