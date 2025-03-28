from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from app.core.config import settings
from app.models.sleep import (
    SleepData,
    SleepPattern,
    SleepSample,
    SleepStage,
    SleepStageType,
)


def detect_sleep_stages(data: SleepData) -> List[SleepStage]:
    """Detect sleep stages from sleep data."""
    # Handle empty data case
    if not data.samples:
        return []

    # Extract features from the sleep data
    features = extract_features(data)
    
    if not features:
        return []

    stages = []
    current_stage = None
    segment_start = None

    for feature in features:
        stage_type, confidence = classify_sleep_stage(feature)

        # Start a new segment if stage changes
        if current_stage != stage_type or not current_stage:
            # Save the previous segment if it exists
            if current_stage and segment_start:
                stages.append(
                    SleepStage(
                        start_time=segment_start,
                        end_time=feature["start_time"],
                        stage_type=current_stage,
                        confidence=confidence,
                    )
                )

            # Start a new segment
            current_stage = stage_type
            segment_start = feature["start_time"]
        else:
            # Continue current segment
            pass

    # Add the last segment
    if current_stage and segment_start and features:
        last_time = features[-1]["end_time"]
        stages.append(
            SleepStage(
                start_time=segment_start,
                end_time=last_time,
                stage_type=current_stage,
                confidence=0.7,  # Default confidence for final segment
            )
        )

    # Filter out very short segments (less than MIN_SLEEP_STAGE_DURATION)
    min_duration = timedelta(minutes=settings.MIN_SLEEP_STAGE_DURATION)
    filtered_stages = [
        stage for stage in stages 
        if (stage.end_time - stage.start_time) >= min_duration
    ]

    return filtered_stages


def extract_features(data: SleepData) -> List[Dict]:
    """Extract features from sleep data for stage classification."""
    samples = data.samples

    # Return empty features list if there are no samples
    if not samples:
        return []

    # Group samples by sensor type
    samples_by_type = {}
    for sample in samples:
        if sample.sensor_type not in samples_by_type:
            samples_by_type[sample.sensor_type] = []
        samples_by_type[sample.sensor_type].append(sample)

    # Determine window size based on sampling rate
    # Approximately 5-minute windows
    window_duration = timedelta(minutes=5)
    
    # Get all timestamps sorted
    all_timestamps = sorted([sample.timestamp for sample in samples])
    
    if not all_timestamps:
        return []
    
    start_time = all_timestamps[0]
    end_time = all_timestamps[-1]
    
    # Create windows
    features = []
    current_time = start_time
    
    while current_time < end_time:
        window_end = current_time + window_duration
        
        # Extract samples in this window
        window_samples = {
            sensor_type: [
                s for s in sensor_samples 
                if current_time <= s.timestamp < window_end
            ]
            for sensor_type, sensor_samples in samples_by_type.items()
        }
        
        # Skip if no samples in window
        if not any(window_samples.values()):
            current_time = window_end
            continue
        
        # Extract features for this window
        feature_vector = {
            "start_time": current_time,
            "end_time": window_end,
        }
        
        # Add movement features if accelerometer data is available
        if "accelerometer" in window_samples and window_samples["accelerometer"]:
            acc_samples = window_samples["accelerometer"]
            x_values = [s.values.get("x", 0) for s in acc_samples if "x" in s.values]
            y_values = [s.values.get("y", 0) for s in acc_samples if "y" in s.values]
            z_values = [s.values.get("z", 0) for s in acc_samples if "z" in s.values]
            
            if x_values and y_values and z_values:
                # Calculate movement features
                feature_vector.update({
                    "mean_x": np.mean(x_values),
                    "mean_y": np.mean(y_values),
                    "mean_z": np.mean(z_values),
                    "var_x": np.var(x_values),
                    "var_y": np.var(y_values),
                    "var_z": np.var(z_values),
                    "mean_magnitude": np.mean([np.sqrt(x**2 + y**2 + z**2) for x, y, z in zip(x_values, y_values, z_values)]),
                    "movement_intensity": np.mean([np.abs(np.sqrt(x**2 + y**2 + z**2) - 1.0) for x, y, z in zip(x_values, y_values, z_values)]),
                })
        
        # Add heart rate features if available
        if "heart_rate" in window_samples and window_samples["heart_rate"]:
            hr_samples = window_samples["heart_rate"]
            hr_values = [s.values.get("bpm", 0) for s in hr_samples if "bpm" in s.values]
            
            if hr_values:
                feature_vector.update({
                    "mean_hr": np.mean(hr_values),
                    "min_hr": np.min(hr_values),
                    "max_hr": np.max(hr_values),
                    "var_hr": np.var(hr_values),
                })
        
        # Add respiration features if available
        if "respiration" in window_samples and window_samples["respiration"]:
            resp_samples = window_samples["respiration"]
            resp_values = [s.values.get("rate", 0) for s in resp_samples if "rate" in s.values]
            
            if resp_values:
                feature_vector.update({
                    "mean_resp": np.mean(resp_values),
                    "var_resp": np.var(resp_values),
                })
        
        features.append(feature_vector)
        current_time = window_end
    
    return features


def classify_sleep_stage(features: Dict) -> Tuple[SleepStageType, float]:
    """Classify sleep stage based on extracted features."""
    # In a real implementation, this would use a trained machine learning model
    # Simplified logic for demonstration purposes

    # Default values if required features are missing
    movement_intensity = features.get("movement_intensity", 0.3)
    mean_magnitude = features.get("mean_magnitude", 1.0)
    var_x = features.get("var_x", 0.02)
    var_y = features.get("var_y", 0.02)
    var_z = features.get("var_z", 0.02)
    mean_hr = features.get("mean_hr", 70)
    var_hr = features.get("var_hr", 5)
    
    # Calculate total variance for simplified sleep stage detection
    total_var = var_x + var_y + var_z
    
    # Detect AWAKE stage
    if movement_intensity > settings.MOVEMENT_THRESHOLD or total_var > 0.1:
        return SleepStageType.AWAKE, 0.85
    
    # Detect REM sleep - characterized by increased brain activity but physical paralysis
    # Higher heart rate variability but low physical movement
    if (var_hr > 8 or mean_hr > 65) and movement_intensity < settings.REM_SLEEP_THRESHOLD:
        return SleepStageType.REM, 0.8
    
    # Detect DEEP sleep - characterized by very low movement and steady, slow heart rate
    if movement_intensity < settings.DEEP_SLEEP_THRESHOLD and (mean_hr < 60 or var_hr < 3):
        return SleepStageType.DEEP, 0.85
    
    # Default to LIGHT sleep
    return SleepStageType.LIGHT, 0.75


def detect_sleep_patterns(data: SleepData, stages: List[SleepStage]) -> List[SleepPattern]:
    """Detect sleep patterns from a list of sleep stages."""
    if not stages:
        return []

    patterns = []
    
    # Get total sleep duration
    start_time = min(stage.start_time for stage in stages)
    end_time = max(stage.end_time for stage in stages)
    total_duration_minutes = (end_time - start_time).total_seconds() / 60.0
    
    # Check for normal sleep pattern
    # Normal sleep typically follows: AWAKE → LIGHT → DEEP → LIGHT → REM and repeats
    # with approximately 4-5 sleep cycles
    
    # Count sleep cycles (roughly defined as LIGHT → DEEP → LIGHT → REM)
    cycles = _count_sleep_cycles(stages)
    
    # Calculate stage percentages
    stage_durations = {}
    for stage in stages:
        duration = (stage.end_time - stage.start_time).total_seconds() / 60.0
        if stage.stage_type not in stage_durations:
            stage_durations[stage.stage_type] = 0
        stage_durations[stage.stage_type] += duration
    
    total_sleep_time = sum(duration for stage_type, duration in stage_durations.items() 
                          if stage_type != SleepStageType.AWAKE)
    
    stage_percentages = {
        stage_type: (duration / total_sleep_time * 100 if total_sleep_time > 0 else 0) 
        for stage_type, duration in stage_durations.items()
        if stage_type != SleepStageType.AWAKE
    }
    
    # Check for normal sleep pattern
    if (3 <= cycles <= 5 and 
        stage_percentages.get(SleepStageType.DEEP, 0) >= 15 and 
        stage_percentages.get(SleepStageType.REM, 0) >= 15):
        
        patterns.append(
            SleepPattern(
                pattern_type="normal",
                description="Normal sleep pattern with good distribution of sleep stages",
                total_duration_minutes=total_duration_minutes,
                stages=stages,
                quality_factors={
                    "sleep_cycles": cycles,
                    "stage_percentages": stage_percentages,
                },
            )
        )
    
    # Check for fragmented sleep pattern
    awake_stages = [s for s in stages if s.stage_type == SleepStageType.AWAKE]
    awake_count = len(awake_stages)
    if awake_count > 3 or (awake_count > 0 and stage_durations.get(SleepStageType.AWAKE, 0) > 60):
        patterns.append(
            SleepPattern(
                pattern_type="fragmented",
                description="Fragmented sleep with multiple awakenings",
                total_duration_minutes=total_duration_minutes,
                stages=stages,
                quality_factors={
                    "awakening_count": awake_count,
                    "awake_time_minutes": stage_durations.get(SleepStageType.AWAKE, 0),
                },
            )
        )
    
    # Check for deep sleep deficiency
    if stage_percentages.get(SleepStageType.DEEP, 0) < 10:
        patterns.append(
            SleepPattern(
                pattern_type="deep_sleep_deficiency",
                description="Insufficient deep sleep",
                total_duration_minutes=total_duration_minutes,
                stages=stages,
                quality_factors={
                    "deep_sleep_percentage": stage_percentages.get(SleepStageType.DEEP, 0),
                },
            )
        )
    
    # Check for REM sleep deficiency
    if stage_percentages.get(SleepStageType.REM, 0) < 15:
        patterns.append(
            SleepPattern(
                pattern_type="rem_sleep_deficiency",
                description="Insufficient REM sleep",
                total_duration_minutes=total_duration_minutes,
                stages=stages,
                quality_factors={
                    "rem_sleep_percentage": stage_percentages.get(SleepStageType.REM, 0),
                },
            )
        )
    
    # If no specific patterns were found, create a generic pattern
    if not patterns:
        patterns.append(
            SleepPattern(
                pattern_type="undetermined",
                description="Sleep pattern does not match known patterns",
                total_duration_minutes=total_duration_minutes,
                stages=stages,
                quality_factors={
                    "sleep_cycles": cycles,
                    "stage_percentages": stage_percentages,
                },
            )
        )
    
    return patterns


def _count_sleep_cycles(stages: List[SleepStage]) -> int:
    """Count approximate number of sleep cycles from sleep stages."""
    # Sort stages by start time
    sorted_stages = sorted(stages, key=lambda s: s.start_time)
    
    # Look for transitions from REM to LIGHT/DEEP which typically mark the end of a cycle
    cycles = 0
    in_rem = False
    
    for i in range(len(sorted_stages) - 1):
        current_stage = sorted_stages[i]
        next_stage = sorted_stages[i + 1]
        
        # Mark when we enter REM
        if current_stage.stage_type == SleepStageType.REM:
            in_rem = True
        
        # Count a cycle when transitioning out of REM to LIGHT or DEEP
        if in_rem and current_stage.stage_type == SleepStageType.REM and (
            next_stage.stage_type == SleepStageType.LIGHT or 
            next_stage.stage_type == SleepStageType.DEEP
        ):
            cycles += 1
            in_rem = False
    
    # If there are no clear cycles but we have deep sleep and REM stages,
    # estimate cycles based on total sleep duration
    if cycles == 0:
        deep_stages = [s for s in stages if s.stage_type == SleepStageType.DEEP]
        rem_stages = [s for s in stages if s.stage_type == SleepStageType.REM]
        
        if deep_stages and rem_stages:
            # Calculate total sleep time excluding AWAKE stages
            sleep_time = sum(
                (s.end_time - s.start_time).total_seconds() / 60.0
                for s in stages
                if s.stage_type != SleepStageType.AWAKE
            )
            
            # Approximate cycles based on typical 90-minute cycle duration
            cycles = round(sleep_time / 90)
    
    # Ensure reasonable range
    return min(6, max(1, cycles))