from pydantic import BaseModel
from typing import Optional


class RealtimeCoachingRequest(BaseModel):
    payload: str
    selected_lift: str
    athlete_weight_kg: float


class PostSetRequest(BaseModel):
    payload_history: list[str]
    selected_lift: str
    rep_count: int
    athlete_weight_kg: float


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict]
    current_payload: Optional[str] = None
    athlete_weight_kg: float
