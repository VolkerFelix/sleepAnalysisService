import json
import math
import random
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.models.sleep import SensorType, SleepData, SleepSample

client = TestClient(app)


def create_valid_sleep_data():
    """Create valid sleep data sample for testing."""
    samples = []
    now = datetime.utcnow()
    start_time = now - timedelta(hours=8)  # 8 hours of sleep

    # Create samples at 1-minute intervals
    for i in range(480):  # 480 minutes = 8 hours
        timestamp = start_time + timedelta(minutes=i)

        # Add accelerometer data
        x = 0.1 * math.sin(i / 20) + 0.05 * (random.random() - 0.5)
        y = 0.1 * math.cos(i / 25) + 0.05 * (random.random() - 0.5)
        z = 0.95 + 0.05 * math.sin(i / 30) + 0.05 * (random.random() - 0.5)

        acc_sample = SleepSample(
            timestamp=timestamp,
            sensor_type=SensorType.ACCELEROMETER,
            values={"x": x, "y": y, "z": z},
        )
        samples.append(acc_sample)

        # Add heart rate data
        if i % 5 == 0:  # Every 5 minutes
            hr = 60 + 10 * math.sin(i / 90) + 5 * random.random()
            hr_sample = SleepSample(
                timestamp=timestamp,
                sensor_type=SensorType.HEART_RATE,
                values={"bpm": hr},
            )
            samples.append(hr_sample)

    return SleepData(
        data_type="sleep_monitoring",
        device_info={"device_type": "test", "model": "test-device"},
        sampling_rate_hz=1 / 60,  # 1 sample per minute
        start_time=start_time,
        end_time=now,
        samples=samples,
        id=f"test-valid-{uuid.uuid4()}",
    )


def create_invalid_sleep_data(issue="short_duration"):
    """Create invalid sleep data with specific issues."""
    samples = []
    now = datetime.utcnow()

    if issue == "short_duration":
        start_time = now - timedelta(minutes=15)  # Only 15 minutes
        duration_minutes = 15
    elif issue == "sparse_data":
        start_time = now - timedelta(hours=8)
        duration_minutes = 480
    elif issue == "missing_sensors":
        start_time = now - timedelta(hours=8)
        duration_minutes = 480
    else:
        start_time = now - timedelta(hours=1)  # Default 1 hour
        duration_minutes = 60

    # Create samples based on the issue
    for i in range(duration_minutes):
        timestamp = start_time + timedelta(minutes=i)

        # For sparse data, only add samples occasionally
        if issue == "sparse_data" and i % 30 != 0:
            continue

        # For missing sensors, don't add accelerometer data
        if issue != "missing_sensors":
            x = 0.1 * math.sin(i / 20) + 0.05 * (random.random() - 0.5)
            y = 0.1 * math.cos(i / 25) + 0.05 * (random.random() - 0.5)
            z = 0.95 + 0.05 * math.sin(i / 30) + 0.05 * (random.random() - 0.5)

            acc_sample = SleepSample(
                timestamp=timestamp,
                sensor_type=SensorType.ACCELEROMETER,
                values={"x": x, "y": y, "z": z},
            )
            samples.append(acc_sample)

        # Add heart rate occasionally
        if i % 10 == 0:
            hr = 60 + 10 * math.sin(i / 90) + 5 * random.random()
            hr_sample = SleepSample(
                timestamp=timestamp,
                sensor_type=SensorType.HEART_RATE,
                values={"bpm": hr},
            )
            samples.append(hr_sample)

    return SleepData(
        data_type="sleep_monitoring",
        device_info={"device_type": "test", "model": "test-device"},
        sampling_rate_hz=1 / 60,  # 1 sample per minute
        start_time=start_time,
        end_time=now,
        samples=samples,
        id=f"test-invalid-{issue}-{uuid.uuid4()}",
    )


def test_valid_data():
    """Test that valid sleep data passes validation."""
    data = create_valid_sleep_data()

    # Convert to dict for JSON serialization
    data_dict = json.loads(data.json())

    # Call the validation endpoint
    response = client.post("/api/validate", json=data_dict)

    # Check response
    assert response.status_code == 200
    result = response.json()

    assert result["valid"] is True, "Valid data should pass validation"


def test_short_duration_data():
    """Test validation of sleep data with too short duration."""
    data = create_invalid_sleep_data(issue="short_duration")

    # Convert to dict for JSON serialization
    data_dict = json.loads(data.json())

    # Call the validation endpoint
    response = client.post("/api/validate", json=data_dict)

    # Check response
    assert response.status_code == 200
    result = response.json()

    assert result["valid"] is False, "Short duration data should fail validation"
    assert "short" in result["reason"].lower(), "Reason should mention short duration"


def test_sparse_data():
    """Test validation of sleep data with insufficient sample density."""
    data = create_invalid_sleep_data(issue="sparse_data")

    # Convert to dict for JSON serialization
    data_dict = json.loads(data.json())

    # Call the validation endpoint
    response = client.post("/api/validate", json=data_dict)

    # Check response
    assert response.status_code == 200
    result = response.json()

    assert result["valid"] is False, "Sparse data should fail validation"
    assert (
        "coverage" in result["reason"].lower()
        or "insufficient" in result["reason"].lower()
    ), "Reason should mention coverage"


def test_missing_sensor_data():
    """Test validation of sleep data with missing sensor types."""
    data = create_invalid_sleep_data(issue="missing_sensors")

    # Convert to dict for JSON serialization
    data_dict = json.loads(data.json())

    # Call the validation endpoint
    response = client.post("/api/validate", json=data_dict)

    # Check response
    assert response.status_code == 200
    result = response.json()

    # Either it's invalid due to missing accelerometer, or we have other issues
    if result["valid"] is False:
        assert "sensor" in result["reason"].lower(), "Reason should mention sensor data"
    else:
        # If it passes despite missing accelerometer, verify with analysis endpoint
        # that results are still reasonable
        request = {
            "sleep_data": data_dict,
            "include_metrics": True,
            "include_patterns": True,
            "include_stages": True,
            "user_id": "test-user",
        }

        analysis_response = client.post("/api/analyze", json=request)
        assert analysis_response.status_code == 200
        analysis = analysis_response.json()

        # Even with missing sensors, we should get some sort of analysis
        assert "overall_metrics" in analysis
        assert analysis["overall_metrics"] is not None
