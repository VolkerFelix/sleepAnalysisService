import logging
import os
import platform
from datetime import datetime
from typing import Dict

import torch
from huggingface_hub import login
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.core.config import settings
from app.models.nlg import SleepNLGResponse, UserSleepContext
from app.models.sleep import SleepAnalysisResponse, SleepQualityLevel

logger = logging.getLogger(__name__)


class SleepNLGService:
    """Service for generating natural language responses from sleep analysis data."""

    def __init__(self):
        # Detect Apple Silicon
        self.is_apple_silicon = (
            platform.system() == "Darwin" and platform.machine() == "arm64"
        )

        # Set appropriate device
        if torch.backends.mps.is_available() and self.is_apple_silicon:
            self.device = "mps"  # Metal Performance Shaders for Apple Silicon
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

        logger.info(f"Using device: {self.device}")

        # Check available memory and recommend lightweight mode if needed
        self._check_system_resources()

        self.model_name = settings.NLG_MODEL_PATH
        self.tokenizer = None
        self.model = None
        self.user_contexts: Dict[str, UserSleepContext] = {}  # In-memory store for demo
        self._load_model()

    def _check_system_resources(self):
        """Check if the system has enough resources for the full model."""
        try:
            import psutil

            # Get available system memory in GB
            available_memory_gb = psutil.virtual_memory().available / (1024**3)
            logger.info(f"Available system memory: {available_memory_gb:.2f} GB")

            # For Mistral 7B, recommend at least 16GB of available memory
            if available_memory_gb < 16:
                logger.warning(
                    f"Limited memory available ({available_memory_gb:.2f} GB). "
                    "Consider setting NLG_USE_SMALL_MODEL=True in settings."
                )

                # If very limited memory, auto-switch to small model mode
                if available_memory_gb < 8 and not settings.NLG_USE_SMALL_MODEL:
                    logger.warning(
                        """Very limited memory detected.
                        Automatically switching to small model."""
                    )
                    # Dynamically update settings
                    settings.NLG_USE_SMALL_MODEL = True

        except ImportError:
            logger.warning("psutil not installed. Cannot check system resources.")
        except Exception as e:
            logger.warning(f"Error checking system resources: {str(e)}")

    def _load_model(self):
        """Load the NLG model for inference."""
        try:
            try:
                # First check if token is in environment variable
                hf_token = os.environ.get("HUGGING_FACE_HUB_TOKEN")

                # If not in environment, check if it's in settings (from .env file)
                if not hf_token and settings.HUGGING_FACE_HUB_TOKEN:
                    hf_token = settings.HUGGING_FACE_HUB_TOKEN

                if hf_token:
                    logger.info("Logging in to Hugging Face using token")
                    login(token=hf_token)
                else:
                    logger.info(
                        "No Hugging Face token found in environment or .env file"
                    )
            except Exception as auth_error:
                logger.warning(f"Hugging Face authentication error: {str(auth_error)}")
                logger.warning(
                    "Will try to load different model without authentication"
                )
            # Determine which model to use
            if settings.NLG_USE_SMALL_MODEL:
                model_path = settings.NLG_FALLBACK_MODEL_PATH
                logger.info(f"Loading small NLG model: {model_path}")
            else:
                model_path = self.model_name
                logger.info(f"Loading NLG model: {model_path}")

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)

            # Set appropriate loading parameters based on platform and model size
            if settings.NLG_USE_SMALL_MODEL:
                # Smaller model uses less memory
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    torch_dtype=torch.float16
                    if self.device != "cpu"
                    else torch.float32,
                    device_map="auto",
                )
            elif self.is_apple_silicon:
                # Attempt with reduced precision for Apple Silicon
                try:
                    # Try loading with device_map="auto" first
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_path, torch_dtype=torch.float16, device_map="auto"
                    )
                except (RuntimeError, ValueError, MemoryError) as e:
                    logger.warning(
                        f"Error loading full model: {str(e)}. Trying smaller model..."
                    )
                    # Fall back to the smaller model
                    model_path = settings.NLG_FALLBACK_MODEL_PATH
                    self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_path, torch_dtype=torch.float16, device_map="auto"
                    )
            else:
                # For other platforms
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_path, torch_dtype=torch.float16, device_map="auto"
                )

            # Record which model was actually loaded
            self.loaded_model_path = model_path
            logger.info(f"NLG model loaded successfully: {model_path}")
        except Exception as e:
            logger.error(f"Error loading NLG model: {str(e)}")
            # Fallback to simpler text generation if model loading fails
            self.model = None
            self.tokenizer = None

    def generate_response(
        self, analysis_result: SleepAnalysisResponse, user_id: str
    ) -> SleepNLGResponse:
        """
        Generate a natural language response based on sleep analysis results.

        Args:
            analysis_result: The analytical results from sleep analysis
            user_id: The user's ID for context retrieval

        Returns:
            A conversational response about the user's sleep
        """
        # Get or create user context
        user_context = self._get_user_context(user_id)

        # Create prompt for the model
        prompt = self._create_prompt(analysis_result, user_context)

        # Generate text using the model or fallback to template-based generation
        if self.model and self.tokenizer:
            generated_text = self._generate_from_model(prompt)
        else:
            generated_text = self._generate_from_templates(
                analysis_result, user_context
            )

        # Update user context with new analysis
        self._update_user_context(user_id, analysis_result)

        # Parse generated text into structured response
        return self._parse_generated_text(generated_text, analysis_result)

    def _get_user_context(self, user_id: str) -> UserSleepContext:
        """Retrieve or create user context."""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = UserSleepContext(user_id=user_id)
        return self.user_contexts[user_id]

    def _update_user_context(self, user_id: str, analysis: SleepAnalysisResponse):
        """Update user context with new sleep analysis data."""
        context = self._get_user_context(user_id)

        # Add new sleep metrics to history
        if analysis.overall_metrics:
            context.sleep_history.append(
                {
                    "date": datetime.now().isoformat(),
                    "quality": analysis.overall_metrics.sleep_quality,
                    "duration": analysis.overall_metrics.total_duration_minutes,
                    "efficiency": analysis.overall_metrics.sleep_efficiency,
                }
            )

            # Keep only the last 30 entries
            if len(context.sleep_history) > 30:
                context.sleep_history = context.sleep_history[-30:]

        # Update last recommendations
        if analysis.recommendations:
            context.last_recommendations = analysis.recommendations

        # Save back to the store
        self.user_contexts[user_id] = context

    def _create_prompt(
        self, analysis: SleepAnalysisResponse, context: UserSleepContext
    ) -> str:
        """Create a comprehensive prompt for the NLG model."""
        metrics = analysis.overall_metrics

        # Calculate trend information if history exists
        trend_info = self._calculate_sleep_trends(context)

        # Format the metrics section
        metrics_text = ""
        if metrics:
            metrics_text = f"""
                Sleep Quality: {metrics.sleep_quality}
                Total Sleep Duration: {metrics.total_duration_minutes:.1f} minutes
                Sleep Efficiency: {metrics.sleep_efficiency:.1f}%
                Time to Fall Asleep: {metrics.time_to_fall_asleep_minutes:.1f} minutes
                Deep Sleep: {metrics.deep_sleep_minutes:.1f} minutes
                ({(metrics.deep_sleep_minutes/metrics.total_duration_minutes*100):.1f}%)
                REM Sleep: {metrics.rem_sleep_minutes:.1f} minutes
                ({(metrics.rem_sleep_minutes/metrics.total_duration_minutes*100):.1f}%)
                Light Sleep: {metrics.light_sleep_minutes:.1f} minutes
                ({(metrics.light_sleep_minutes/metrics.total_duration_minutes*100):.1f}%)
                Awakenings: {metrics.awakenings_count}
                """

        # Format the patterns section
        patterns_text = ""
        if analysis.sleep_patterns:
            patterns_text = "Sleep Patterns Detected:\n"
            for pattern in analysis.sleep_patterns:
                patterns_text += f"- {pattern.pattern_type}: {pattern.description}\n"

        # Format recommendations
        recommendations_text = ""
        if analysis.recommendations:
            recommendations_text = "Recommendations:\n"
            for i, rec in enumerate(analysis.recommendations, 1):
                # Clean up recommendations (remove extra whitespace)
                clean_rec = " ".join(rec.split())
                recommendations_text += f"{i}. {clean_rec}\n"

        # Format trend information
        trend_text = ""
        if trend_info:
            trend_text = f"""
                Sleep Trends:
                - Duration Trend: {trend_info.get('duration_trend', 'No trend data')}
                - Quality Trend: {trend_info.get('quality_trend', 'No trend data')}
                - Compared to Average: {trend_info.get('compared_to_average',
                    'No comparison data')}
                """

        # Previous interactions context
        previous_context = ""
        if context.last_recommendations:
            previous_context = "Previous Recommendations:\n"
            for i, rec in enumerate(context.last_recommendations, 1):
                clean_rec = " ".join(rec.split())
                previous_context += f"{i}. {clean_rec}\n"

        # Build the complete prompt
        prompt = f"""<s>[INST] You are a helpful, empathetic sleep coach assistant.
            Generate a personalized, conversational sleep analysis response
            based on the following data.
            Make the response sound natural and human-like, not clinical or robotic.
            Be empathetic and encouraging.
            Organize your response with:
            1. A personalized greeting
            2. A conversational summary of their sleep
            3. Key insights about their sleep patterns (2-3 insights)
            4. Personalized recommendations (2-3)
            5. A supportive conclusion

            DATA:
            {metrics_text}
            {patterns_text}
            {trend_text}
            {previous_context}

            Now generate a conversational sleep analysis that sounds like
            it's from a knowledgeable sleep coach: [/INST]</s>
            """
        return prompt

    def _generate_from_model(self, prompt: str) -> str:
        """Generate text using the loaded model."""
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

            # Generate with appropriate parameters
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs.input_ids,
                    max_new_tokens=1024,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                )

            # Decode the generated text
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract just the assistant's response (remove the prompt)
            response_text = generated_text.split("[/INST]</s>")[-1].strip()

            return response_text
        except Exception as e:
            logger.error(f"Error generating text from model: {str(e)}")
            # Fallback to template-based generation
            return self._generate_fallback_response()

    def _generate_from_templates(
        self, analysis: SleepAnalysisResponse, context: UserSleepContext
    ) -> str:
        """Fallback template-based generation when model is unavailable."""
        metrics = analysis.overall_metrics

        # Simple template-based response
        if not metrics:
            return """I couldn't analyze your sleep data properly.
                Please try again or contact support."""

        quality_text = {
            SleepQualityLevel.EXCELLENT: "excellent",
            SleepQualityLevel.GOOD: "good",
            SleepQualityLevel.FAIR: "fair",
            SleepQualityLevel.POOR: "poor",
            SleepQualityLevel.VERY_POOR: "very poor",
            SleepQualityLevel.UNKNOWN: "unclear",
        }.get(metrics.sleep_quality, "unclear")

        hours = metrics.total_duration_minutes / 60.0

        response = f"""Hi there!

            Based on your sleep data, it looks like you had {quality_text}
            sleep last night, sleeping for about {hours:.1f} hours
            with a sleep efficiency of {metrics.sleep_efficiency:.1f}%.

            You spent {metrics.deep_sleep_minutes:.1f} minutes in deep sleep
            and {metrics.rem_sleep_minutes:.1f} minutes in REM sleep,
            which are both important for physical and mental recovery.
            """

        if metrics.awakenings_count > 3:
            response += f"""\nI noticed you woke up {metrics.awakenings_count}
                times during the night, which might be affecting your overall
                sleep quality."""

        if analysis.recommendations:
            response += "\n\nHere are some personalized recommendations:\n"
            for i, rec in enumerate(analysis.recommendations[:3], 1):
                clean_rec = " ".join(rec.split())
                response += f"{i}. {clean_rec}\n"

        response += """\nKeep tracking your sleep, and we'll work together
            to improve your rest and recovery!"""

        return response

    def _generate_fallback_response(self) -> str:
        """Generate a generic response when everything else fails."""
        return """Hi there!

            I've looked at your sleep data, but I'm having trouble
            generating a detailed analysis right now.

            Your sleep patterns are being tracked, and the data
            is being recorded successfully. To get more insights,
            please continue tracking your sleep, and we'll provide more detailed
            analysis as we collect more data.

            In the meantime, remember that consistent sleep schedules
            and creating a relaxing bedtime routine can help improve your sleep quality.

            Keep up the good work with tracking your sleep!
            """

    def _parse_generated_text(
        self, text: str, analysis: SleepAnalysisResponse
    ) -> SleepNLGResponse:
        """Parse generated text into structured NLG response components."""
        # Simple parsing - in a real implementation, this would be more sophisticated
        paragraphs = [p for p in text.split("\n\n") if p.strip()]

        summary = paragraphs[0] if paragraphs else "Sleep analysis completed."

        # Extract what seem to be insights (middle paragraphs)
        insights = []
        if len(paragraphs) > 2:
            for p in paragraphs[1:-1]:
                if not p.startswith("Here are") and not p.lower().startswith(
                    "recommendation"
                ):
                    insights.append(p)

        # Use original recommendations if available, otherwise try to extract from text
        if analysis.recommendations:
            recommendations = analysis.recommendations
        else:
            recommendations = []
            for p in paragraphs:
                if (
                    "recommend" in p.lower()
                    or p.lower().startswith("try ")
                    or p.lower().startswith("consider ")
                ):
                    recommendations.append(p)

        # Use the last paragraph as a conclusion if available
        conclusion = paragraphs[-1] if paragraphs else ""

        return SleepNLGResponse(
            conversational_response=text,
            summary=summary,
            insights=insights,
            recommendations=recommendations,
            conclusion=conclusion,
        )

    def _calculate_sleep_trends(self, context: UserSleepContext) -> Dict[str, str]:
        """Calculate sleep trends from historical data."""
        if not context.sleep_history or len(context.sleep_history) < 3:
            return {}

        # Get recent history (up to last 7 entries)
        recent = context.sleep_history[-7:]

        # Calculate averages
        avg_duration = sum(entry.get("duration", 0) for entry in recent) / len(recent)

        # Get latest metrics
        latest = recent[-1]
        latest_duration = latest.get("duration", 0)

        # Determine duration trend
        duration_diff = latest_duration - avg_duration
        if abs(duration_diff) < 15:  # Less than 15 minutes difference
            duration_trend = (
                "Your sleep duration is consistent with your recent average"
            )
        elif duration_diff > 0:
            duration_trend = f"""You slept {int(duration_diff/60*10)/10:.1f}
                hours longer than your recent average"""
        else:
            duration_trend = f"""You slept {int(abs(duration_diff)/60*10)/10:.1f}
                hours less than your recent average"""

        # Simple quality trend based on recent entries
        quality_counts: Dict = {}
        for entry in recent:
            quality = entry.get("quality", "unknown")
            quality_counts[quality] = quality_counts.get(quality, 0) + 1

        most_common_quality = max(quality_counts.items(), key=lambda x: x[1])[0]
        latest_quality = latest.get("quality", "unknown")

        if latest_quality == most_common_quality:
            quality_trend = f"""Your sleep quality remains {latest_quality},
                which is consistent with your recent pattern"""
        else:
            quality_trend = f"""Your sleep quality was {latest_quality},
                which differs from your usual {most_common_quality} sleep"""

        return {
            "duration_trend": duration_trend,
            "quality_trend": quality_trend,
            "compared_to_average": f"""You had
                {int(abs(duration_diff)/60*10)/10:.1f} hours
                {'more' if duration_diff > 0 else 'less'} sleep
                than your average""",
        }
