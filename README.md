# Sleep Analysis Service

A microservice for analyzing and recognizing sleep patterns from sensor data, built with FastAPI.

## Overview

This service provides APIs for analyzing sleep data to recognize various sleep stages and patterns. It's designed to be part of Areum's larger ecosystem of health and wellness monitoring services.

## Features

- Sleep stage detection (Awake, Light, Deep, REM)
- Sleep pattern recognition
- Sleep quality assessment
- Health recommendations based on sleep patterns
- RESTful API endpoints
- Health monitoring
- CORS support
- API documentation (Swagger UI)

## Tech Stack

- FastAPI - Modern web framework for building APIs
- Pydantic - Data validation using Python type annotations
- NumPy & Pandas - Data manipulation and analysis
- Scikit-learn - Machine learning capabilities
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

## Running the Service

### Local Development

```bash
uvicorn app.main:app --reload
```

The service will be available at `http://localhost:8000`

### Docker

Build and run using Docker:

```bash
docker build -t sleep-analysis-service .
docker run -p 8000:8000 sleep-analysis-service
```

## API Documentation

Once the service is running, you can access:
- Swagger UI documentation: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`

## API Endpoints

- `POST /api/analyze` - Analyze sleep data to detect stages, patterns, and metrics
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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.