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

    # FIXED: Set a proper sampling rate that matches our actual sample generation
    # We're generating samples every 5 minutes, so our rate is 1/300 Hz
    sampling_rate_hz = 1 / 300  # 1 sample per 5 minutes

    # Generate samples for full 8-hour duration (96 five-minute intervals)
    for i in range(96):  # 96 five-minute intervals in 8 hours
        timestamp = start_time + timedelta(minutes=i * 5)

        # Add accelerometer data
        x = 0.1 * math.sin(i / 4) + 0.05 * (random.random() - 0.5)
        y = 0.1 * math.cos(i / 5) + 0.05 * (random.random() - 0.5)
        z = 0.95 + 0.05 * math.sin(i / 6) + 0.05 * (random.random() - 0.5)

        acc_sample = SleepSample(
            timestamp=timestamp,
            sensor_type=SensorType.ACCELEROMETER,
            values={
                "x": x,
                "y": y,
                "z": z,
                "movement_intensity": 0.1 + 0.05 * random.random(),
            },
        )
        samples.append(acc_sample)

        # Add heart rate data every 15 minutes (every 3rd iteration)
        if i % 3 == 0:
            hr = 60 + 10 * math.sin(i / 18) + 5 * random.random()
            hr_sample = SleepSample(
                timestamp=timestamp,
                sensor_type=SensorType.HEART_RATE,
                values={"bpm": hr},
            )
            samples.append(hr_sample)

            # Also add respiration data
            resp_rate = 12 + 4 * random.random()
            resp_sample = SleepSample(
                timestamp=timestamp,
                sensor_type=SensorType.RESPIRATION,
                values={"rate": resp_rate},
            )
            samples.append(resp_sample)

    return SleepData(
        data_type="sleep_monitoring",
        device_info={"device_type": "test", "model": "test-device"},
        sampling_rate_hz=sampling_rate_hz,  # Consistent with our actual sampling
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
        sampling_rate_hz = 1 / 60  # 1 sample per minute
    elif issue == "sparse_data":
        start_time = now - timedelta(hours=8)
        duration_minutes = 480
        sampling_rate_hz = 1 / 60  # 1 sample per minute, but we'll generate far fewer
    elif issue == "missing_sensors":
        start_time = now - timedelta(hours=8)
        duration_minutes = 480
        sampling_rate_hz = 1 / 300  # 1 sample per 5 minutes
    else:
        start_time = now - timedelta(hours=1)  # Default 1 hour
        duration_minutes = 60
        sampling_rate_hz = 1 / 60

    # Create samples based on the issue
    if issue == "short_duration":
        # Create sufficient samples for the short duration
        for i in range(duration_minutes):
            timestamp = start_time + timedelta(minutes=i)

            # Add accelerometer data
            acc_sample = SleepSample(
                timestamp=timestamp,
                sensor_type=SensorType.ACCELEROMETER,
                values={
                    "x": 0.1 * math.sin(i / 4) + 0.05 * (random.random() - 0.5),
                    "y": 0.1 * math.cos(i / 5) + 0.05 * (random.random() - 0.5),
                    "z": 0.95 + 0.05 * math.sin(i / 6) + 0.05 * (random.random() - 0.5),
                    "movement_intensity": 0.1 + 0.05 * random.random(),
                },
            )
            samples.append(acc_sample)

            # Add heart rate occasionally
            if i % 5 == 0:
                hr = 60 + 10 * math.sin(i / 10) + 5 * random.random()
                hr_sample = SleepSample(
                    timestamp=timestamp,
                    sensor_type=SensorType.HEART_RATE,
                    values={"bpm": hr},
                )
                samples.append(hr_sample)

    elif issue == "sparse_data":
        # Create very few samples over the full duration
        for i in range(0, duration_minutes, 60):  # Only 1 sample per hour
            timestamp = start_time + timedelta(minutes=i)

            acc_sample = SleepSample(
                timestamp=timestamp,
                sensor_type=SensorType.ACCELEROMETER,
                values={
                    "x": 0.1 * math.sin(i / 60) + 0.05 * (random.random() - 0.5),
                    "y": 0.1 * math.cos(i / 60) + 0.05 * (random.random() - 0.5),
                    "z": 0.95
                    + 0.05 * math.sin(i / 60)
                    + 0.05 * (random.random() - 0.5),
                    "movement_intensity": 0.1 + 0.05 * random.random(),
                },
            )
            samples.append(acc_sample)

    elif issue == "missing_sensors":
        # Create data with only heart rate, no accelerometer
        for i in range(0, duration_minutes, 5):  # Every 5 minutes
            timestamp = start_time + timedelta(minutes=i)

            hr = 60 + 10 * math.sin(i / 30) + 5 * random.random()
            hr_sample = SleepSample(
                timestamp=timestamp,
                sensor_type=SensorType.HEART_RATE,
                values={"bpm": hr},
            )
            samples.append(hr_sample)

    else:
        # Default invalid data
        for i in range(0, duration_minutes, 10):  # Every 10 minutes
            timestamp = start_time + timedelta(minutes=i)

            acc_sample = SleepSample(
                timestamp=timestamp,
                sensor_type=SensorType.ACCELEROMETER,
                values={
                    "x": 0.1 * (random.random() - 0.5),
                    "y": 0.1 * (random.random() - 0.5),
                    "z": 1.0 + 0.1 * (random.random() - 0.5),
                    "movement_intensity": 0.2 + 0.1 * random.random(),
                },
            )
            samples.append(acc_sample)

    return SleepData(
        data_type="sleep_monitoring",
        device_info={"device_type": "test", "model": "test-device"},
        sampling_rate_hz=sampling_rate_hz,
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

    # Print response for debugging
    print(f"Validation response: {response.json()}")

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

    assert result["valid"] is False, "Missing sensor data should fail validation"
    assert (
        "accelerometer" in result["reason"].lower()
    ), "Reason should mention missing accelerometer data"
