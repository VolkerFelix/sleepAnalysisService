from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

from app.core.config import settings
from app.models.sleep import (
    SleepData,
    SleepMetrics,
    SleepQualityLevel,
    SleepSample,
    SleepStage,
    SleepStageType,
)


def calculate_sleep_metrics(
    data: SleepData, stages: Optional[List[SleepStage]] = None
) -> SleepMetrics:
    """Calculate sleep metrics from sleep data and optionally pre-detected stages."""
    # Handle empty data case
    if not data.samples:
        return SleepMetrics(
            total_duration_minutes=0.0,
            sleep_efficiency=0.0,
            time_to_fall_asleep_minutes=0.0,
            awakenings_count=0,
            awake_time_minutes=0.0,
            light_sleep_minutes=0.0,
            deep_sleep_minutes=0.0,
            rem_sleep_minutes=0.0,
            movement_index=0.0,
            sleep_quality=SleepQualityLevel.VERY_POOR,
        )

    # Calculate total duration
    start_time = data.start_time
    end_time = data.end_time if data.end_time else data.samples[-1].timestamp
    total_duration_minutes = (end_time - start_time).total_seconds() / 60.0

    # If stages are provided, use them for detailed metrics
    if stages:
        # Calculate time in each sleep stage
        stage_durations = _calculate_stage_durations(stages)

        # Sleep efficiency is the percentage of time spent sleeping
        total_sleep_minutes = (
            stage_durations.get(SleepStageType.LIGHT, 0.0)
            + stage_durations.get(SleepStageType.DEEP, 0.0)
            + stage_durations.get(SleepStageType.REM, 0.0)
        )
        sleep_efficiency = (
            (total_sleep_minutes / total_duration_minutes) * 100
            if total_duration_minutes > 0
            else 0.0
        )

        # Calculate sleep latency (time to fall asleep)
        time_to_fall_asleep_minutes = _calculate_sleep_latency(stages, start_time)

        # Count awakenings
        awakenings_count, awake_time_minutes = _count_awakenings(stages)

        # Extract individual stage durations
        light_sleep_minutes = stage_durations.get(SleepStageType.LIGHT, 0.0)
        deep_sleep_minutes = stage_durations.get(SleepStageType.DEEP, 0.0)
        rem_sleep_minutes = stage_durations.get(SleepStageType.REM, 0.0)
    else:
        # Without stages, estimate metrics from the raw data
        sleep_efficiency = _estimate_sleep_efficiency(data)
        time_to_fall_asleep_minutes = _estimate_sleep_latency(
            data.start_time, data.samples
        )
        movement_data = _extract_movement_data(data)
        awakenings_count = _estimate_awakenings(movement_data)
        awake_time_minutes = total_duration_minutes * (1 - sleep_efficiency / 100)

        # Estimate sleep stage durations based on typical distributions
        # Rough estimates: 50-60% light, 10-25% deep, 20-25% REM
        light_sleep_minutes = total_duration_minutes * sleep_efficiency / 100 * 0.55
        deep_sleep_minutes = total_duration_minutes * sleep_efficiency / 100 * 0.20
        rem_sleep_minutes = total_duration_minutes * sleep_efficiency / 100 * 0.25

    # Calculate movement index
    movement_index = _calculate_movement_index(data)

    # Calculate heart rate metrics if available
    hr_metrics = _calculate_heart_rate_metrics(data)

    # Calculate respiration rate if available
    respiration_rate = _calculate_respiration_rate(data)

    # Determine sleep quality
    sleep_quality = _determine_sleep_quality(
        total_duration_minutes=total_duration_minutes,
        sleep_efficiency=sleep_efficiency,
        deep_sleep_percentage=(deep_sleep_minutes / total_duration_minutes) * 100
        if total_duration_minutes > 0
        else 0,
        rem_sleep_percentage=(rem_sleep_minutes / total_duration_minutes) * 100
        if total_duration_minutes > 0
        else 0,
        awakenings_count=awakenings_count,
        time_to_fall_asleep_minutes=time_to_fall_asleep_minutes,
    )

    return SleepMetrics(
        total_duration_minutes=float(total_duration_minutes),
        sleep_efficiency=float(sleep_efficiency),
        time_to_fall_asleep_minutes=float(time_to_fall_asleep_minutes),
        awakenings_count=int(awakenings_count),
        awake_time_minutes=float(awake_time_minutes),
        light_sleep_minutes=float(light_sleep_minutes),
        deep_sleep_minutes=float(deep_sleep_minutes),
        rem_sleep_minutes=float(rem_sleep_minutes),
        movement_index=float(movement_index),
        hr_average=hr_metrics.get("average"),
        hr_lowest=hr_metrics.get("lowest"),
        hr_variability=hr_metrics.get("variability"),
        respiration_rate=respiration_rate,
        sleep_quality=sleep_quality,
    )


def _calculate_stage_durations(stages: List[SleepStage]) -> Dict[SleepStageType, float]:
    """Calculate the duration in minutes for each sleep stage."""
    durations = {}
    for stage in stages:
        duration_minutes = (stage.end_time - stage.start_time).total_seconds() / 60.0
        if stage.stage_type not in durations:
            durations[stage.stage_type] = 0.0
        durations[stage.stage_type] += duration_minutes

    return durations


def _calculate_sleep_latency(stages: List[SleepStage], start_time: datetime) -> float:
    """Calculate sleep latency (time to fall asleep) from sleep stages."""
    # Find the first non-awake stage
    for stage in sorted(stages, key=lambda s: s.start_time):
        if stage.stage_type != SleepStageType.AWAKE:
            return (stage.start_time - start_time).total_seconds() / 60.0

    # If no sleep stages found, return full duration (user probably didn't sleep)
    return 0.0


def _count_awakenings(stages: List[SleepStage]) -> tuple:
    """Count the number of awakenings after initial sleep onset."""
    if not stages:
        return 0, 0.0

    # Sort stages by start time
    sorted_stages = sorted(stages, key=lambda s: s.start_time)

    # Find first non-awake stage (sleep onset)
    sleep_started = False
    awakenings = 0
    awake_time_minutes = 0.0

    for stage in sorted_stages:
        if not sleep_started:
            if stage.stage_type != SleepStageType.AWAKE:
                sleep_started = True
        else:
            if stage.stage_type == SleepStageType.AWAKE:
                awakenings += 1
                awake_time_minutes += (
                    stage.end_time - stage.start_time
                ).total_seconds() / 60.0

    return awakenings, awake_time_minutes


def _extract_movement_data(data: SleepData) -> pd.DataFrame:
    """Extract movement-related data from sleep data samples."""
    movement_data = []

    for sample in data.samples:
        if sample.sensor_type in ["accelerometer", "gyroscope"]:
            # Extract time and movement values
            sample_dict: Dict[str, Union[datetime, float]] = {
                "timestamp": sample.timestamp,
            }

            # Add all values from the sample
            for key, value in sample.values.items():
                sample_dict[key] = value

            movement_data.append(sample_dict)

    return pd.DataFrame(movement_data) if movement_data else pd.DataFrame()


def _estimate_sleep_efficiency(data: SleepData) -> float:
    """Estimate sleep efficiency from raw data when sleep stages are not available."""
    # Extract movement data
    movement_df = _extract_movement_data(data)

    if movement_df.empty:
        return 80.0  # Default estimate if no movement data

    # Calculate magnitude of movement (if accelerometer data is available)
    if all(col in movement_df.columns for col in ["x", "y", "z"]):
        movement_df["magnitude"] = np.sqrt(
            movement_df["x"] ** 2 + movement_df["y"] ** 2 + movement_df["z"] ** 2
        )

        # Calculate proportion of time with low movement (likely sleep)
        low_movement_threshold = settings.SLEEP_DETECTION_THRESHOLD
        low_movement_samples = (movement_df["magnitude"] < low_movement_threshold).sum()

        sleep_efficiency = (low_movement_samples / len(movement_df)) * 100
        return min(98.0, max(50.0, sleep_efficiency))  # Keep within reasonable bounds

    return 80.0  # Default estimate


def _estimate_sleep_latency(
    start_time: datetime,
    movement_data: List[SleepSample],
    threshold: float = 0.5,
    default_estimate: float = 15.0,
) -> float:
    """Estimate sleep latency (time to fall asleep) based on movement data."""
    if not movement_data:
        return default_estimate

    # Sort movement data by timestamp
    sorted_data = sorted(movement_data, key=lambda x: x.timestamp)

    # Filter data to only include samples after start_time
    relevant_data = [sample for sample in sorted_data if sample.timestamp >= start_time]

    if not relevant_data:
        return default_estimate

    # Look for a period of low movement that indicates sleep onset
    window_size = timedelta(minutes=5)
    current_time = start_time

    while current_time < relevant_data[-1].timestamp:
        window_end = current_time + window_size
        window_samples = [
            sample
            for sample in relevant_data
            if current_time <= sample.timestamp < window_end
        ]

        if window_samples:
            # Calculate average movement intensity in window
            movement_intensities = [
                float(sample.values.get("movement_intensity", 0.0))
                for sample in window_samples
                if "movement_intensity" in sample.values
            ]

            if movement_intensities:
                avg_movement = sum(movement_intensities) / len(movement_intensities)
                if avg_movement < threshold:
                    # Found sleep onset - calculate minutes from start
                    return float((current_time - start_time).total_seconds() / 60.0)

        current_time = window_end

    # If no clear sleep onset found, return default estimate
    return default_estimate


def _estimate_awakenings(movement_df: pd.DataFrame) -> int:
    """Estimate number of awakenings from movement data."""
    if movement_df.empty or "magnitude" not in movement_df.columns:
        return 2  # Default estimate

    # Use a rolling window to smooth the movement data
    window_size = min(100, len(movement_df) // 10)  # Reasonable window size
    if window_size > 0:
        movement_df["rolling_mean"] = (
            movement_df["magnitude"].rolling(window=window_size, min_periods=1).mean()
        )

        # Define awake threshold as significant movement
        awake_threshold = settings.MOVEMENT_THRESHOLD

        # Identify periods of being awake (high movement)
        movement_df["awake"] = movement_df["rolling_mean"] > awake_threshold

        # Count transitions from sleep to awake
        awakenings = 0
        prev_state = True  # Start as awake

        for state in movement_df["awake"]:
            if not prev_state and state:  # Transition from sleep to awake
                awakenings += 1
            prev_state = state

        return min(10, max(0, awakenings))  # Keep within reasonable bounds

    return 2  # Default estimate


def _calculate_movement_index(data: SleepData) -> float:
    """Calculate movement index from sleep data."""
    movement_df = _extract_movement_data(data)

    if movement_df.empty:
        return 0.5  # Default value

    # Calculate movement index based on variation in acceleration if available
    if all(col in movement_df.columns for col in ["x", "y", "z"]):
        # Calculate magnitude
        movement_df["magnitude"] = np.sqrt(
            movement_df["x"] ** 2 + movement_df["y"] ** 2 + movement_df["z"] ** 2
        )

        # Remove gravity component (approximately 1.0)
        movement_df["adjusted_magnitude"] = np.abs(movement_df["magnitude"] - 1.0)

        # Calculate movement index as normalized average movement
        avg_movement = movement_df["adjusted_magnitude"].mean()
        return min(1.0, max(0.0, avg_movement / 0.5))  # Normalize to 0-1 range

    return 0.5  # Default value


def _calculate_heart_rate_metrics(data: SleepData) -> Dict[str, Optional[float]]:
    """Calculate heart rate metrics if heart rate data is available."""
    hr_metrics: Dict[str, Optional[float]] = {
        "average": None,
        "lowest": None,
        "variability": None,
    }

    # Extract heart rate samples
    hr_samples = [
        sample
        for sample in data.samples
        if sample.sensor_type == "heart_rate" and "bpm" in sample.values
    ]

    if not hr_samples:
        return hr_metrics

    # Extract BPM values
    hr_values = [sample.values["bpm"] for sample in hr_samples]

    # Calculate metrics
    hr_metrics["average"] = float(np.mean(hr_values))
    hr_metrics["lowest"] = float(np.min(hr_values))

    # Calculate heart rate variability (simplified)
    if len(hr_values) > 1:
        # Convert to numpy array for calculations
        hr_array = np.array(hr_values)

        # Calculate successive differences
        rr_diffs = np.abs(np.diff(hr_array))

        # RMSSD (Root Mean Square of Successive Differences)
        if len(rr_diffs) > 0:
            rmssd = np.sqrt(np.mean(rr_diffs**2))
            hr_metrics["variability"] = float(rmssd)

    return hr_metrics


def _calculate_respiration_rate(data: SleepData) -> Optional[float]:
    """Calculate average respiration rate if respiration data is available."""
    # Extract respiration samples
    resp_samples = [
        sample
        for sample in data.samples
        if sample.sensor_type == "respiration" and "rate" in sample.values
    ]

    if not resp_samples:
        return None

    # Extract rate values
    resp_values = [sample.values["rate"] for sample in resp_samples]

    # Calculate average
    return float(np.mean(resp_values))


def _determine_sleep_quality(
    total_duration_minutes: float,
    sleep_efficiency: float,
    deep_sleep_percentage: float,
    rem_sleep_percentage: float,
    awakenings_count: int,
    time_to_fall_asleep_minutes: float,
) -> SleepQualityLevel:
    """Determine overall sleep quality based on various metrics."""
    # Create a scoring system (0-100)
    score = 0

    # Duration score (optimal: 7-9 hours)
    if 420 <= total_duration_minutes <= 540:
        score += 25  # Full points for optimal duration
    elif 360 <= total_duration_minutes < 420 or 540 < total_duration_minutes <= 600:
        score += 20  # Good but not optimal
    elif 300 <= total_duration_minutes < 360 or 600 < total_duration_minutes <= 660:
        score += 15  # Acceptable
    else:
        score += 5  # Poor duration

    # Sleep efficiency score (optimal: >85%)
    if sleep_efficiency >= 90:
        score += 25
    elif 85 <= sleep_efficiency < 90:
        score += 20
    elif 75 <= sleep_efficiency < 85:
        score += 15
    elif 65 <= sleep_efficiency < 75:
        score += 10
    else:
        score += 5

    # Deep sleep score (optimal: 15-25% of total sleep)
    if 15 <= deep_sleep_percentage <= 25:
        score += 15
    elif 10 <= deep_sleep_percentage < 15 or 25 < deep_sleep_percentage <= 30:
        score += 10
    else:
        score += 5

    # REM sleep score (optimal: 20-25% of total sleep)
    if 20 <= rem_sleep_percentage <= 25:
        score += 15
    elif 15 <= rem_sleep_percentage < 20 or 25 < rem_sleep_percentage <= 30:
        score += 10
    else:
        score += 5

    # Awakenings score (optimal: <2)
    if awakenings_count < 2:
        score += 10
    elif 2 <= awakenings_count <= 4:
        score += 7
    elif 5 <= awakenings_count <= 7:
        score += 4
    else:
        score += 1

    # Sleep latency score (optimal: <15 minutes)
    if time_to_fall_asleep_minutes < 15:
        score += 10
    elif 15 <= time_to_fall_asleep_minutes <= 30:
        score += 7
    elif 30 < time_to_fall_asleep_minutes <= 60:
        score += 4
    else:
        score += 1

    # Convert score to quality level
    if score >= 85:
        return SleepQualityLevel.EXCELLENT
    elif 70 <= score < 85:
        return SleepQualityLevel.GOOD
    elif 55 <= score < 70:
        return SleepQualityLevel.FAIR
    elif 40 <= score < 55:
        return SleepQualityLevel.POOR
    else:
        return SleepQualityLevel.VERY_POOR
