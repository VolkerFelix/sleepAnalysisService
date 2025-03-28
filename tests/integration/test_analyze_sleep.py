import json

from fastapi.testclient import TestClient

from app.main import app
from app.models.sleep import SleepAnalysisRequest, SleepStageType
from tests.integration.common import create_test_sleep_data

client = TestClient(app)


def test_analyze_sleep_good_quality():
    """Test sleep analysis with good quality sleep data."""
    # Create test data for good quality sleep
    sleep_data = create_test_sleep_data(duration_hours=8, quality="good")

    # Create request
    request = SleepAnalysisRequest(
        sleep_data=sleep_data,
        include_metrics=True,
        include_patterns=True,
        include_stages=True,
        user_id="test-user-1",
    )

    # Convert to dict for JSON serialization
    request_dict = json.loads(request.json())

    # Call the endpoint
    response = client.post("/api/analyze", json=request_dict)

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Check sleep stages
    assert len(data["sleep_stages"]) > 0

    # Check if deep sleep was detected
    found_deep = False
    for stage in data["sleep_stages"]:
        if stage["stage_type"] == SleepStageType.DEEP:
            found_deep = True
            break

    assert found_deep, "Deep sleep should be detected in good quality sleep"

    # Check metrics
    assert data["overall_metrics"] is not None
    assert (
        data["overall_metrics"]["sleep_efficiency"] > 80.0
    ), "Good sleep should have high sleep efficiency"

    # Check sleep quality
    assert data["overall_metrics"]["sleep_quality"] in [
        "good",
        "excellent",
    ], "Good sleep should have good or excellent quality"


def test_analyze_sleep_poor_quality():
    """Test sleep analysis with poor quality sleep data."""
    # Create test data for poor quality sleep
    sleep_data = create_test_sleep_data(duration_hours=6, quality="poor")

    # Create request
    request = SleepAnalysisRequest(
        sleep_data=sleep_data,
        include_metrics=True,
        include_patterns=True,
        include_stages=True,
        user_id="test-user-2",
    )

    # Convert to dict for JSON serialization
    request_dict = json.loads(request.json())

    # Call the endpoint
    response = client.post("/api/analyze", json=request_dict)

    # Verify response
    assert response.status_code == 200
    data = response.json()

    # Check sleep stages
    assert len(data["sleep_stages"]) > 0

    # Poor sleep should have more awakenings and less deep sleep
    awake_stages = [
        s for s in data["sleep_stages"] if s["stage_type"] == SleepStageType.AWAKE
    ]
    assert len(awake_stages) > 0, "Poor sleep should have awake stages"

    # Check metrics
    assert data["overall_metrics"] is not None

    # Check for awakenings - poor sleep should have some
    assert (
        data["overall_metrics"]["awakenings_count"] > 0
    ), "Poor sleep should have awakenings"

    # Check sleep quality
    assert data["overall_metrics"]["sleep_quality"] in [
        "fair",
        "poor",
        "very_poor",
    ], "Poor sleep should have lower quality rating"

    # Check recommendations
    assert data["recommendations"] is not None
    assert (
        len(data["recommendations"]) > 0
    ), "Poor sleep should generate recommendations"


def test_calculate_sleep_metrics():
    """Test the sleep metrics calculation endpoint."""
    # Create test data
    sleep_data = create_test_sleep_data(duration_hours=7, quality="good")

    # Convert to dict for JSON serialization
    data_dict = json.loads(sleep_data.json())

    # Call the endpoint
    response = client.post("/api/metrics", json=data_dict)

    # Verify response
    assert response.status_code == 200
    metrics = response.json()

    # Check metrics structure
    assert "total_duration_minutes" in metrics
    assert "sleep_efficiency" in metrics
    assert "time_to_fall_asleep_minutes" in metrics
    assert "awakenings_count" in metrics
    assert "light_sleep_minutes" in metrics
    assert "deep_sleep_minutes" in metrics
    assert "rem_sleep_minutes" in metrics
    assert "sleep_quality" in metrics

    # Check valid ranges
    assert metrics["total_duration_minutes"] > 0
    assert 0 <= metrics["sleep_efficiency"] <= 100
    assert metrics["time_to_fall_asleep_minutes"] >= 0
    assert metrics["awakenings_count"] >= 0
    assert metrics["deep_sleep_minutes"] >= 0


def test_get_sleep_stage_types():
    """Test retrieving the list of supported sleep stage types."""
    response = client.get("/api/stage_types")

    assert response.status_code == 200
    types = response.json()

    # Verify all expected stage types are present
    expected_types = [
        "awake",
        "light",
        "deep",
        "rem",
        "unknown",
    ]
    for stage_type in expected_types:
        assert (
            stage_type in types
        ), f"Sleep stage type '{stage_type}' should be in the list"
