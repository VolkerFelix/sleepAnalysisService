from typing import List

from fastapi import APIRouter, HTTPException

from app.models.sleep import (
    SensorType,
    SleepAnalysisRequest,
    SleepAnalysisResponse,
    SleepData,
    SleepMetrics,
    SleepStageType,
)
from app.models.validation import ValidationResponse
from app.services.analysis import SleepAnalysisService

router = APIRouter()
sleep_service = SleepAnalysisService()


@router.post("/analyze", response_model=SleepAnalysisResponse)
async def analyze_sleep(request: SleepAnalysisRequest):
    """Analyze sleep data and detect sleep stages, patterns, and metrics."""
    try:
        response = sleep_service.analyze_sleep(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error analyzing sleep data: {str(e)}"
        )


@router.get("/stage_types", response_model=List[SleepStageType])
async def get_sleep_stage_types():
    """Get a list of all supported sleep stage types."""
    try:
        return sleep_service.get_supported_stage_types()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving sleep stage types: {str(e)}"
        )


@router.post("/metrics", response_model=SleepMetrics)
async def calculate_sleep_metrics(data: SleepData):
    """Calculate sleep metrics from sleep data."""
    try:
        metrics = sleep_service.calculate_sleep_metrics(data)
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating sleep metrics: {str(e)}"
        )


@router.post("/validate", response_model=ValidationResponse)
async def validate_sleep_data(data: SleepData):
    """Validate sleep data for quality and completeness."""
    try:
        # Debug info
        print(f"Validating sleep data with {len(data.samples)} samples")
        print(f"Start time: {data.start_time}, End time: {data.end_time or 'None'}")
        print(f"Sampling rate: {data.sampling_rate_hz} Hz")

        # Check if data has minimum duration
        if not data.samples:
            return ValidationResponse(
                valid=False, reason="No sleep data samples provided"
            )

        # Check if sufficient duration (at least 30 minutes)
        start_time = data.start_time
        if data.end_time:
            end_time = data.end_time
        else:
            # Use the last sample timestamp as end time
            end_time = data.samples[-1].timestamp

        duration_minutes = (end_time - start_time).total_seconds() / 60
        print(f"Duration: {duration_minutes:.1f} minutes")

        if duration_minutes < 30:
            return ValidationResponse(
                valid=False,
                reason=f"""Sleep duration too short: {duration_minutes:.1f}
                minutes (minimum 30 minutes required""",
            )

        # IMPORTANT: First validate sensor types - check this BEFORE completeness
        sensor_types = set(sample.sensor_type for sample in data.samples)
        print(f"Sensor types: {sensor_types}")

        if len(sensor_types) == 0:
            return ValidationResponse(valid=False, reason="No sensor data available")

        # Check for accelerometer data before evaluating completeness
        has_accelerometer = False
        for sensor_type in sensor_types:
            if sensor_type == SensorType.ACCELEROMETER:
                has_accelerometer = True
                break

        if not has_accelerometer:
            return ValidationResponse(
                valid=False,
                reason="""Missing accelerometer data, which is required
                for sleep analysis""",
            )

        # Now check sampling rate is sufficient for accelerometer data
        accelerometer_samples = [
            sample
            for sample in data.samples
            if sample.sensor_type == SensorType.ACCELEROMETER
        ]

        # Only check completeness for accelerometer data
        expected_acc_samples = int(
            (end_time - start_time).total_seconds() / 300
        )  # 1 per 5 minutes
        actual_acc_samples = len(accelerometer_samples)

        # Calculate completeness percentage
        completeness = (
            (actual_acc_samples / expected_acc_samples * 100)
            if expected_acc_samples > 0
            else 0
        )

        print(
            f"""Expected accelerometer samples: {expected_acc_samples},
            Actual: {actual_acc_samples}"""
        )
        print(f"Completeness: {completeness:.1f}%")

        if completeness < 30:
            return ValidationResponse(
                valid=False,
                reason=f"""Insufficient data coverage: {completeness:.1f}%
                of expected samples (minimum 30% required""",
            )

        return ValidationResponse(valid=True, reason="Data validation passed")
    except Exception as e:
        print(f"Error in validation: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error validating sleep data: {str(e)}"
        )
