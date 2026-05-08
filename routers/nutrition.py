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

    lines = [
        f"Today's workout: {body.workout_type}",
        f"Calorie target: {body.daily_target} kcal ({body.goal_label})",
        f"Active calorie burn: {body.active_burn} kcal",
        f"Protein target: {body.protein_target}g{protein_note}",
    ]

    has_logged_data = body.calories_eaten is not None or body.protein_grams is not None

    if body.calories_eaten is not None:
        remaining_cal = body.daily_target - body.calories_eaten
        pct = round(body.calories_eaten / body.daily_target * 100) if body.daily_target > 0 else 0
        if remaining_cal > 0:
            lines.append(
                f"Calories logged so far: {body.calories_eaten} kcal "
                f"({pct}% of target, {remaining_cal} kcal remaining)"
            )
        else:
            lines.append(
                f"Calories logged: {body.calories_eaten} kcal "
                f"(target met, {abs(remaining_cal)} kcal over)"
            )

    if body.protein_grams is not None:
        remaining_pro = body.protein_target - body.protein_grams
        if remaining_pro > 0:
            lines.append(
                f"Protein logged so far: {body.protein_grams}g ({remaining_pro}g remaining)"
            )
        else:
            lines.append(
                f"Protein logged: {body.protein_grams}g "
                f"(goal met, {abs(remaining_pro)}g over)"
            )

    task = "Write 2 sentences of specific nutrition guidance for today based on these exact numbers."
    if has_logged_data:
        task += " Reference what has been logged and what still needs to be hit."

    lines += ["", task, "Then on a new line write: TIP: [one concise tip, 7 words or fewer]"]

    messages = [{"role": "user", "content": "\n".join(lines)}]
    return _stream_claude(messages, max_tokens=200)
