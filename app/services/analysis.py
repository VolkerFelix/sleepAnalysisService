from typing import Dict, List, Optional, Tuple

from app.models.sleep import (
    SleepAnalysisRequest,
    SleepAnalysisResponse,
    SleepData,
    SleepMetrics,
    SleepPattern,
    SleepQualityLevel,
    SleepStage,
    SleepStageType,
)
from app.utils.metrics import calculate_sleep_metrics
from app.utils.patterns import detect_sleep_patterns, detect_sleep_stages


class SleepAnalysisService:
    """Service for analyzing sleep data and detecting sleep stages and patterns."""

    def __init__(self):
        # Could initialize ML models or other resources here
        pass

    def analyze_sleep(self, request: SleepAnalysisRequest) -> SleepAnalysisResponse:
        """Analyze sleep data and detect sleep stages, patterns, and metrics."""
        # Detect sleep stages
        sleep_stages = []
        if request.include_stages:
            sleep_stages = detect_sleep_stages(request.sleep_data)

        # Calculate overall metrics
        overall_metrics = None
        if request.include_metrics:
            overall_metrics = calculate_sleep_metrics(request.sleep_data, sleep_stages)

        # Determine dominant sleep stage
        dominant_stage = self._determine_dominant_stage(sleep_stages)

        # Generate sleep patterns if requested
        sleep_patterns = []
        if request.include_patterns and sleep_stages:
            sleep_patterns = detect_sleep_patterns(request.sleep_data, sleep_stages)

        # Generate recommendations based on analysis
        recommendations = self._generate_recommendations(overall_metrics, sleep_patterns) if overall_metrics else None

        # Initialize response
        response = SleepAnalysisResponse(
            status="success",
            sleep_stages=sleep_stages,
            sleep_patterns=sleep_patterns,
            dominant_stage=dominant_stage,
            overall_metrics=overall_metrics,
            recommendations=recommendations,
        )

        return response

    def _determine_dominant_stage(
        self, stages: List[SleepStage]
    ) -> SleepStageType:
        """Determine the dominant sleep stage from a list of stages."""
        if not stages:
            return SleepStageType.UNKNOWN

        # Count duration for each stage type
        duration_by_type = {}
        for stage in stages:
            stage_type = stage.stage_type
            duration = (stage.end_time - stage.start_time).total_seconds() / 60.0  # Convert to minutes

            if stage_type not in duration_by_type:
                duration_by_type[stage_type] = 0

            duration_by_type[stage_type] += duration

        # If no durations were added (which shouldn't happen but just in case)
        if not duration_by_type:
            return SleepStageType.UNKNOWN

        # Find the stage type with the longest duration
        try:
            dominant_type = max(duration_by_type.items(), key=lambda x: x[1])[0]
            return dominant_type
        except Exception as e:
            print(f"Error determining dominant sleep stage: {e}")
            return SleepStageType.UNKNOWN

    def _generate_recommendations(
        self, metrics: SleepMetrics, patterns: List[SleepPattern]
    ) -> List[str]:
        """Generate sleep quality recommendations based on analysis."""
        recommendations = []

        if not metrics:
            return recommendations

        # Check sleep duration
        if metrics.total_duration_minutes < 420:  # Less than 7 hours
            recommendations.append(
                "Consider increasing your sleep duration to at least 7-8 hours for optimal health."
            )
        elif metrics.total_duration_minutes > 600:  # More than 10 hours
            recommendations.append(
                "You're sleeping longer than average. While this might be necessary for recovery, consistently sleeping more than 9 hours might indicate other health issues."
            )

        # Check sleep efficiency
        if metrics.sleep_efficiency < 85:
            recommendations.append(
                "Your sleep efficiency is lower than optimal. Consider limiting time in bed when not sleeping and establishing a consistent sleep schedule."
            )

        # Check time to fall asleep
        if metrics.time_to_fall_asleep_minutes > 30:
            recommendations.append(
                "It's taking you longer than ideal to fall asleep. Consider establishing a relaxing pre-sleep routine and avoiding screens before bedtime."
            )

        # Check awakenings
        if metrics.awakenings_count > 3:
            recommendations.append(
                "You experienced multiple awakenings. This could be affecting your sleep quality. Consider limiting fluid intake before bed and ensuring your sleep environment is quiet and comfortable."
            )

        # Check deep sleep
        ideal_deep_sleep_percentage = 20  # Approximately 20% of total sleep should be deep sleep
        deep_sleep_percentage = (metrics.deep_sleep_minutes / metrics.total_duration_minutes) * 100
        
        if deep_sleep_percentage < 15:
            recommendations.append(
                "Your deep sleep percentage is lower than optimal. Consider regular exercise (but not too close to bedtime) and maintaining a consistent sleep schedule to improve deep sleep."
            )

        # Check REM sleep
        ideal_rem_sleep_percentage = 25  # Approximately 25% of total sleep should be REM sleep
        rem_sleep_percentage = (metrics.rem_sleep_minutes / metrics.total_duration_minutes) * 100
        
        if rem_sleep_percentage < 20:
            recommendations.append(
                "Your REM sleep percentage is lower than optimal. REM sleep is important for cognitive function and emotional processing. Avoiding alcohol and certain medications before bed can improve REM sleep."
            )

        # Provide general recommendation if quality is poor
        if metrics.sleep_quality in [SleepQualityLevel.POOR, SleepQualityLevel.VERY_POOR]:
            recommendations.append(
                "Your overall sleep quality could be improved. Consider factors such as room temperature (60-67°F/15-20°C is ideal), minimizing noise and light, and establishing a consistent sleep schedule."
            )

        # If no specific recommendations were generated but sleep quality isn't excellent
        if not recommendations and metrics.sleep_quality != SleepQualityLevel.EXCELLENT:
            recommendations.append(
                "While no specific issues were identified, continuing to maintain good sleep hygiene practices will help ensure quality rest."
            )

        return recommendations

    def calculate_sleep_metrics(self, data: SleepData, stages: Optional[List[SleepStage]] = None) -> SleepMetrics:
        """Calculate sleep metrics from sleep data and optionally pre-detected stages."""
        return calculate_sleep_metrics(data, stages)

    def get_supported_stage_types(self) -> List[SleepStageType]:
        """Get a list of all supported sleep stage types."""
        return list(SleepStageType)