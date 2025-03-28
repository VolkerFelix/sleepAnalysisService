from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.models.sleep import (
    SleepAnalysisRequest,
    SleepAnalysisResponse,
    SleepData,
    SleepMetrics,
    SleepStageType,
)
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


@router.post("/validate", response_model=Dict[str, bool])
async def validate_sleep_data(data: SleepData):
    """Validate sleep data for quality and completeness."""
    try:
        # Check if data has minimum duration
        if not data.samples:
            return {"valid": False, "reason": "No sleep data samples provided"}
        
        # Check if sufficient duration (at least 30 minutes)
        start_time = data.start_time
        if data.end_time:
            end_time = data.end_time
        else:
            # Use the last sample timestamp as end time
            end_time = data.samples[-1].timestamp
            
        duration_minutes = (end_time - start_time).total_seconds() / 60
        
        if duration_minutes < 30:
            return {
                "valid": False,
                "reason": f"Sleep duration too short: {duration_minutes:.1f} minutes (minimum 30 minutes required)",
            }
            
        # Check sampling rate is sufficient
        expected_samples = int((end_time - start_time).total_seconds() * data.sampling_rate_hz)
        actual_samples = len(data.samples)
        completeness = (actual_samples / expected_samples) * 100 if expected_samples > 0 else 0
        
        if completeness < 70:  # Less than 70% of expected samples
            return {
                "valid": False,
                "reason": f"Insufficient data coverage: {completeness:.1f}% of expected samples",
            }
            
        # Validate sensor types
        sensor_types = set(sample.sensor_type for sample in data.samples)
        if len(sensor_types) == 0:
            return {"valid": False, "reason": "No sensor data available"}
            
        return {"valid": True}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error validating sleep data: {str(e)}"
        )