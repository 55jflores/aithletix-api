from pydantic import BaseModel, Field, field_validator
from typing import Optional, Annotated, Literal
from enum import Enum


class Lift(str, Enum):
    squat = "Squat"
    deadlift = "Deadlift"
    bench = "Bench Press"


_REQUIRED_PAYLOAD_SECTIONS = [
    "=== AthleteIQ Physics Context ===",
    "--- Session ---",
    "--- Joint Angles ---",
    "--- Torque Analysis ---",
    "--- Stability ---",
]


def _validate_payload(v: str) -> str:
    for section in _REQUIRED_PAYLOAD_SECTIONS:
        if section not in v:
            raise ValueError(f"Payload missing required section: {section}")
    return v


class RealtimeCoachingRequest(BaseModel):
    payload: str = Field(max_length=2500)
    selected_lift: Lift
    athlete_weight_kg: float

    @field_validator("payload")
    @classmethod
    def validate_payload_structure(cls, v):
        return _validate_payload(v)


class PostSetRequest(BaseModel):
    payload_history: list[Annotated[str, Field(max_length=2500)]] = Field(max_length=30)
    selected_lift: Lift
    rep_count: int
    athlete_weight_kg: float

    @field_validator("payload_history")
    @classmethod
    def validate_snapshot_structures(cls, v):
        for snapshot in v:
            _validate_payload(snapshot)
        return v


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(max_length=1000)
    conversation_history: list[Message] = Field(max_length=50)
    current_payload: Optional[str] = Field(default=None, max_length=2500)
    athlete_weight_kg: float

    @field_validator("current_payload")
    @classmethod
    def validate_current_payload_structure(cls, v):
        if v is not None:
            _validate_payload(v)
        return v
