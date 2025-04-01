import json

from fastapi.testclient import TestClient

from app.main import app
from app.models.sleep import SleepAnalysisRequest
from tests.integration.common import create_test_sleep_data

client = TestClient(app)


def test_conversational_analysis():
    """Test the conversational sleep analysis endpoint."""
    # Create test data for good quality sleep
    sleep_data = create_test_sleep_data(duration_hours=8, quality="good")

    # Create request
    request = SleepAnalysisRequest(
        sleep_data=sleep_data,
        include_metrics=True,
        include_patterns=True,
        include_stages=True,
        user_id="test-user-nlg-1",
    )

    # Convert to dict for JSON serialization
    request_dict = json.loads(request.json())

    # Call the endpoint
    response = client.post("/api/analyze/conversational", json=request_dict)

    # Verify response
    assert response.status_code == 200
    data = response.json()

    # Check conversational response structure
    assert "conversational_response" in data
    assert len(data["conversational_response"]) > 50

    # Check that the response contains key components
    assert "summary" in data
    assert "insights" in data
    assert "recommendations" in data

    # Validate that the conversational response doesn't sound too robotic
    conversational_text = data["conversational_response"]

    # It should not contain statistical markers from the raw data
    assert "SleepQualityLevel" not in conversational_text
    assert "sleep_efficiency: " not in conversational_text

    # Should contain natural language about sleep
    assert any(
        term in conversational_text.lower()
        for term in ["sleep", "rest", "night", "bed", "tired", "energy"]
    )

    print("Conversational Response:", conversational_text)


def test_conversational_analysis_poor_sleep():
    """Test conversational analysis with poor quality sleep data."""
    # Create test data for poor quality sleep
    sleep_data = create_test_sleep_data(duration_hours=5, quality="poor")

    # Create request
    request = SleepAnalysisRequest(
        sleep_data=sleep_data,
        include_metrics=True,
        include_patterns=True,
        include_stages=True,
        user_id="test-user-nlg-2",
    )

    # Convert to dict for JSON serialization
    request_dict = json.loads(request.json())

    # Call the endpoint
    response = client.post("/api/analyze/conversational", json=request_dict)

    # Verify response
    assert response.status_code == 200
    data = response.json()

    # The response for poor sleep should contain supportive language
    conversational_text = data["conversational_response"].lower()

    # Should have some supportive or improvement-oriented content
    assert any(
        term in conversational_text
        for term in ["improve", "better", "help", "suggest", "recommend", "try"]
    )

    print("Poor Sleep Response:", data["conversational_response"])
