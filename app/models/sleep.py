from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SleepStageType(str, Enum):
    AWAKE = "awake"
    LIGHT = "light"
    DEEP = "deep"
    REM = "rem"
    UNKNOWN = "unknown"


class SleepQualityLevel(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    VERY_POOR = "very_poor"
    UNKNOWN = "unknown"


class SensorType(str, Enum):
    ACCELEROMETER = "accelerometer"
    GYROSCOPE = "gyroscope"
    HEART_RATE = "heart_rate"
    RESPIRATION = "respiration"
    TEMPERATURE = "temperature"
    NOISE = "noise"
    LIGHT = "light"
    COMBINED = "combined"


class SleepSample(BaseModel):
    """Model for a single sleep data sample."""

    timestamp: datetime
    sensor_type: SensorType
    values: Dict[str, float]


class SleepData(BaseModel):
    """Model for a collection of sleep data samples."""

    data_type: str
    device_info: Dict[str, Any]
    sampling_rate_hz: int
    start_time: datetime
    end_time: Optional[datetime] = None
    samples: List[SleepSample]
    metadata: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class SleepMetrics(BaseModel):
    """Model for metrics calculated from sleep data."""

    total_duration_minutes: float
    sleep_efficiency: float  # Percentage of time actually sleeping
    time_to_fall_asleep_minutes: float  # Sleep latency
    awakenings_count: int
    awake_time_minutes: float
    light_sleep_minutes: float
    deep_sleep_minutes: float
    rem_sleep_minutes: float
    movement_index: float  # Overall movement during sleep (0-1)
    hr_average: Optional[float] = None  # Average heart rate during sleep
    hr_lowest: Optional[float] = None  # Lowest heart rate during sleep
    hr_variability: Optional[float] = None  # Heart rate variability
    respiration_rate: Optional[float] = None  # Average breaths per minute
    sleep_quality: SleepQualityLevel = SleepQualityLevel.UNKNOWN


class SleepStage(BaseModel):
    """Model for a detected sleep stage segment."""

    start_time: datetime
    end_time: datetime
    stage_type: SleepStageType
    confidence: float
    metrics: Optional[Dict[str, Any]] = None


class SleepPattern(BaseModel):
    """Model for sleep patterns detected across multiple stages."""

    pattern_type: str  # e.g., "normal", "fragmented", "delayed", "advanced"
    description: str
    total_duration_minutes: float
    stages: List[SleepStage]
    quality_factors: Optional[Dict[str, Any]] = None


class SleepAnalysisRequest(BaseModel):
    """Model for a request to analyze sleep data."""

    sleep_data: SleepData
    include_metrics: bool = True
    include_patterns: bool = True
    include_stages: bool = True
    user_id: str
    session_id: Optional[str] = None
    user_feedback: Optional[Dict[str, Any]] = None


class SleepAnalysisResponse(BaseModel):
    """Model for a response containing sleep analysis results."""

    status: str
    message: Optional[str] = None
    sleep_stages: List[SleepStage] = []
    sleep_patterns: List[SleepPattern] = []
    dominant_stage: SleepStageType = SleepStageType.UNKNOWN
    overall_metrics: Optional[SleepMetrics] = None
    recommendations: Optional[List[str]] = None
