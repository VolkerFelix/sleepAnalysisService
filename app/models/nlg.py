from typing import Dict, List, Optional

from pydantic import BaseModel


class SleepNLGResponse(BaseModel):
    """Model for NLG-generated sleep analysis responses."""

    conversational_response: str
    summary: str
    insights: List[str] = []
    recommendations: List[str] = []
    conclusion: Optional[str] = None
    follow_up_questions: List[str] = []


class UserSleepContext(BaseModel):
    """Model for storing user sleep context and history."""

    user_id: str
    sleep_history: List[Dict] = []
    preferred_tone: Optional[str] = None
    response_detail_level: str = "standard"  # "brief", "standard", "detailed"
    last_recommendations: Optional[List[str]] = None
    improvement_goals: Optional[List[str]] = None
