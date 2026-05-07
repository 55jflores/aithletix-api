import os
import json
import anthropic
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from models.requests import NutritionInsightRequest
from middleware.auth import verify_token
from middleware.rate_limit import limiter

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

router = APIRouter()

NUTRITION_SYSTEM_PROMPT = """
You are Aithletix – a sports nutrition coach who gives brief, data-driven guidance.
Your role is to help athletes understand how today's nutrition targets relate to their training.

Rules:
- Reference the specific numbers provided (calories, protein, active burn)
- Be direct and practical – like a coach texting their athlete
- No generic advice – every sentence must relate to the data given
- Do not give medical or clinical advice
- Keep total response to exactly 2 sentences of insight, then one short tip
"""


def _stream_claude(messages: list[dict], max_tokens: int):
    def generate():
        try:
            with client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                system=NUTRITION_SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'token': text})}\n\n"
                yield "data: [DONE]\n\n"
        except Exception:
            yield f"data: {json.dumps({'error': 'Streaming failed. Please try again.'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/insight")
@limiter.limit("20/minute")
def nutrition_insight(
    request: Request,
    body: NutritionInsightRequest,
    user=Depends(verify_token),
):
    protein_note = (
        f" (includes +{body.protein_bonus}g strength bonus)" if body.protein_bonus > 0 else ""
    )
    content = (
        f"Today's workout: {body.workout_type}\n"
        f"Calorie target: {body.daily_target} kcal ({body.goal_label})\n"
        f"Active calorie burn: {body.active_burn} kcal\n"
        f"Protein target: {body.protein_target}g{protein_note}\n\n"
        "Write 2 sentences of specific nutrition guidance for today based on these exact numbers.\n"
        "Then on a new line write: TIP: [one concise tip, 7 words or fewer]"
    )
    messages = [{"role": "user", "content": content}]
    return _stream_claude(messages, max_tokens=200)
