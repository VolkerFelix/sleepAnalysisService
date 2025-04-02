# Sleep Analysis Service

A microservice for analyzing and recognizing sleep patterns from sensor data, built with FastAPI.

## Overview

This service provides APIs for analyzing sleep data to recognize various sleep stages and patterns. It's designed to be part of Areum's larger ecosystem of health and wellness monitoring services.

## Features

- Sleep stage detection (Awake, Light, Deep, REM)
- Sleep pattern recognition
- Sleep quality assessment
- Health recommendations based on sleep patterns
- Natural language conversational sleep analysis
- Personalized sleep insights
- RESTful API endpoints
- Health monitoring
- CORS support
- API documentation (Swagger UI)

## Tech Stack

- FastAPI - Modern web framework for building APIs
- Pydantic - Data validation using Python type annotations
- NumPy & Pandas - Data manipulation and analysis
- Scikit-learn - Machine learning for sleep stage detection
- PyTorch - Deep learning framework for NLG capabilities
- Hugging Face Transformers - State-of-the-art NLP models
- Mistral & OPT - Language models for natural sleep analysis
- Docker support for containerization

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- Docker (optional, for containerized deployment)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/sleepAnalysisService.git
cd sleepAnalysisService
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Development Setup

1. Install development dependencies:
```bash
pip install -r requirements.txt
```

2. Set up pre-commit hooks:
```bash
pre-commit install
```

3. Configure NLG settings (optional):
Create a `.env` file in the project root:
```
# Hugging Face authentication for accessing gated models
HUGGING_FACE_HUB_TOKEN=your_token_here

# NLG settings
NLG_USE_SMALL_MODEL=False  # Set to True to use smaller model on resource-constrained systems
```

## Running the Service

### Local Development

```bash
uvicorn app.main:app --reload
```

The service will be available at `http://localhost:8000`

### Docker

The service can be deployed using Docker with hardware acceleration support for different platforms.

#### Basic Build (CPU only)

```bash
docker build -t sleep-analysis-service .
docker run -p 8000:8000 sleep-analysis-service
```

#### CUDA-enabled Build (for NVIDIA GPUs)

```bash
docker build --target cuda -t sleep-analysis-service:cuda .
docker run --gpus all -p 8000:8000 sleep-analysis-service:cuda
```

#### Apple Silicon Build (for M1/M2 Macs)

```bash
docker build --target apple-silicon --platform=linux/arm64 -t sleep-analysis-service:apple .
docker run -p 8000:8000 sleep-analysis-service:apple
```

#### Multi-platform Build (CI/CD)

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t sleep-analysis-service:multi .
```

## Hardware Acceleration

The service is optimized to use:
- NVIDIA CUDA for GPU acceleration on compatible hardware
- Apple Metal Performance Shaders (MPS) on Apple Silicon Macs

This significantly improves the performance of ML models, especially for natural language generation using the Mistral 7B model.

## API Documentation

Once the service is running, you can access:
- Swagger UI documentation: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`

## API Endpoints

- `POST /api/analyze` - Analyze sleep data to detect stages, patterns, and metrics
- `POST /api/analyze/conversational` - Get natural language, conversational analysis of sleep data
- `GET /api/stage_types` - Get all supported sleep stage types
- `POST /api/metrics` - Calculate sleep metrics from sleep data
- `POST /api/validate` - Validate sleep data for quality and completeness
- `GET /health` - Service health check

## Testing

Run tests using pytest:

```bash
pytest
```

## Project Structure

```
sleepAnalysisService/
├── app/
│   ├── api/        # API routes and endpoints
│   ├── core/       # Core configuration and settings
│   ├── models/     # Data models and schemas
│   ├── services/   # Business logic and services
│   └── utils/      # Utility functions
├── tests/          # Test files
├── Dockerfile      # Container configuration
├── requirements.txt # Python dependencies
└── pyproject.toml  # Project configuration
```

## Natural Language Sleep Analysis

The service includes a sophisticated natural language generation component that transforms analytical sleep data into human-like, conversational insights. This feature enables:

- Personalized sleep reports in natural language
- Context-aware insights that reference previous sleep patterns
- Empathetic messaging that adapts to sleep quality
- Actionable recommendations presented in a conversational style
- Varied response styles that avoid repetitive phrasing

### Using the Conversational API

To get natural language sleep analysis, use the `/api/analyze/conversational` endpoint with the same request format as the standard analysis endpoint. The response includes:

```json
{
  "conversational_response": "A complete natural language summary of sleep data",
  "summary": "A brief overview of the sleep session",
  "insights": ["Key insight 1", "Key insight 2"],
  "recommendations": ["Recommendation 1", "Recommendation 2"],
  "conclusion": "A supportive closing statement"
}
```

## Sleep Data Format

The service accepts sleep data in the following format:

```json
{
  "data_type": "sleep_monitoring",
  "device_info": {
    "device_type": "smartwatch",
    "model": "health-tracker-2000"
  },
  "sampling_rate_hz": 1,
  "start_time": "2023-04-10T22:00:00Z",
  "end_time": "2023-04-11T06:30:00Z",
  "samples": [
    {
      "timestamp": "2023-04-10T22:00:00Z",
      "sensor_type": "accelerometer",
      "values": {"x": 0.1, "y": -0.02, "z": 0.98}
    },
    {
      "timestamp": "2023-04-10T22:00:01Z",
      "sensor_type": "heart_rate",
      "values": {"bpm": 72}
    }
  ]
}
```

## Performance Considerations

The natural language generation component uses the Mistral 7B model, which requires significant computational resources:

- At least 16GB of RAM for optimal performance
- GPU acceleration highly recommended for production use
- Apple Silicon Macs benefit from MPS acceleration
- The service automatically falls back to a smaller model on resource-constrained systems

You can configure `NLG_USE_SMALL_MODEL=True` in your `.env` file to always use the smaller model.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.
