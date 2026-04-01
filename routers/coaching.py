import os
import json
import anthropic
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from models.requests import RealtimeCoachingRequest, PostSetRequest, ChatRequest
from middleware.auth import verify_token

router = APIRouter()

COACHING_SYSTEM_PROMPT = """
You are AthleteIQ — an expert powerlifting coach
with a PhD in biomechanics and 20 years of coaching
experience with competitive powerlifters from
beginner to elite level.

Your role is to analyze real-time biomechanics data
and provide coaching feedback that is:
- Specific to the numbers provided — never generic
- Grounded in the physics (torque, moment arms, CoM)
- Actionable — always give a concrete cue to fix it
- Appropriately urgent — critical issues first
- Conversational — speak like a coach not a textbook

IMPORTANT MODEL LIMITATIONS:
- 2D sagittal plane analysis from single camera angle
- L4/L5 position is estimated (plus or minus 2-3cm)
- Static equilibrium model — dynamic forces excluded
- Bar weight IS included in torque calculations
- Values are for relative comparison not clinical use

Keep real-time responses under 150 words.
Lead with the most critical issue.
Give one specific actionable cue.
"""


def _stream_claude(messages: list[dict], max_tokens: int):
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def generate():
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=max_tokens,
            system=COACHING_SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'token': text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/realtime")
def realtime_coaching(
    request: RealtimeCoachingRequest,
    _token: dict = Depends(verify_token),
):
    messages = [
        {
            "role": "user",
            "content": (
                f"Athlete weight: {request.athlete_weight_kg}kg. "
                f"Lift: {request.selected_lift}. "
                f"Mid-set biomechanics snapshot:\n{request.payload}\n\n"
                "Give one specific coaching cue right now. Be brief."
            ),
        }
    ]
    return _stream_claude(messages, max_tokens=256)


@router.post("/post-set")
def post_set_coaching(
    request: PostSetRequest,
    _token: dict = Depends(verify_token),
):
    snapshots = "\n\n".join(
        f"Snapshot {i + 1}:\n{snap}"
        for i, snap in enumerate(request.payload_history)
    )
    messages = [
        {
            "role": "user",
            "content": (
                f"Athlete weight: {request.athlete_weight_kg}kg. "
                f"Lift: {request.selected_lift}. "
                f"Reps completed: {request.rep_count}.\n\n"
                f"Biomechanics snapshots across the set:\n{snapshots}\n\n"
                "Assess overall form. Identify the most consistent issue. "
                "Describe any fatigue progression across reps. "
                "Give three things to focus on next set and one positive."
            ),
        }
    ]
    return _stream_claude(messages, max_tokens=1024)


@router.post("/chat")
def chat(
    request: ChatRequest,
    _token: dict = Depends(verify_token),
):
    messages = list(request.conversation_history)

    user_content = request.message
    if request.current_payload:
        user_content = (
            f"Current biomechanics context:\n{request.current_payload}\n\n"
            f"{request.message}"
        )

    messages.append({"role": "user", "content": user_content})

    return _stream_claude(messages, max_tokens=1024)
