import os
import json
import anthropic
from datetime import date
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from models.requests import NutritionInsightRequest, NutritionChatRequest, NutritionShareCardRequest
from middleware.auth import verify_token
from middleware.rate_limit import limiter

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

router = APIRouter()

today = date.today().strftime("%A, %B %d, %Y")

# ── Insight ───────────────────────────────────────────────────────────────────

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


# ── Chat ──────────────────────────────────────────────────────────────────────

NUTRITION_CHAT_SYSTEM_PROMPT = """
You are Aithletix — a knowledgeable, encouraging nutrition coach
specializing in daily fueling: calorie targets, protein goals, and how nutrition ties to training.

At the start of each conversation you will receive a snapshot of the user's
nutrition data inside <nutrition_context> tags. Treat it as your primary source of
truth. Today's date will be included — use it to correctly interpret relative
terms like "today" or "this week."

Your responses must:
- Be concise — 2-4 sentences. Go longer only when explaining a concept or
interpreting a trend that genuinely requires it.
- Reference the user's actual numbers when they support the answer.
- Be warm and direct — like a coach who knows their athlete well.
- Address the user as "you" — never "the athlete" or in third person.
- Stay focused on nutrition, fueling, recovery, and how food relates to their training.

If a metric was not included in the nutrition context, say so — never invent numbers.
If a question is outside your scope (medical advice, injury diagnosis, etc.),
acknowledge it briefly and redirect to what you can help with.
Never speculate about medical conditions or give medical advice.
Never use bullet points or headers unless the user explicitly asks for a list.
"""


@router.post("/chat")
@limiter.limit("30/day")
async def nutrition_chat(
    request: Request,
    body: NutritionChatRequest,
    user=Depends(verify_token),
):
    messages = [
        {
            "role": "user",
            "content": (
                f"<nutrition_context>\n"
                f"Today: {today}\n\n"
                f"{body.nutrition_context}\n"
                f"</nutrition_context>"
            ),
        },
        {
            "role": "assistant",
            "content": "Got it — I have your nutrition data loaded. What would you like to know?",
        },
    ]

    for turn in body.history:
        role = turn.get("role", "")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({
                "role": role,
                "content": f"<user_message>{content}</user_message>" if role == "user" else content,
            })

    messages.append({
        "role": "user",
        "content": f"<user_message>{body.message}</user_message>",
    })

    async def _stream():
        try:
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=300,
                system=NUTRITION_CHAT_SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'token': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:
            yield f"data: {json.dumps({'error': 'Streaming failed. Please try again.'})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


# ── Share Card ────────────────────────────────────────────────────────────────

@router.post("/share-summary")
@limiter.limit("10/day")
async def nutrition_share_summary(
    request: Request,
    body: NutritionShareCardRequest,
    user=Depends(verify_token),
):
    parts = []

    if body.calories_eaten is not None:
        pct = round(body.calories_eaten / body.daily_target * 100) if body.daily_target > 0 else 0
        parts.append(
            f"Calories: {body.calories_eaten} of {body.daily_target} kcal ({pct}%, {'hit' if body.calories_hit else 'not yet hit'})."
        )
    else:
        parts.append(f"Calorie target: {body.daily_target} kcal (none logged yet).")

    if body.protein_grams is not None:
        parts.append(
            f"Protein: {body.protein_grams}g of {body.protein_target}g ({'hit' if body.protein_hit else 'not yet hit'})."
        )
    else:
        parts.append(f"Protein target: {body.protein_target}g (none logged yet).")

    user_message = " ".join(parts)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=25,
        system=(
            "You are a nutrition coach writing one line for a shareable nutrition card. "
            "Write exactly ONE punchy sentence, 10-15 words. "
            "Priority order: if both calorie and protein goals were hit, celebrate that. "
            "If only one was hit, highlight it. "
            "If neither was hit, motivate without shaming. "
            "Be direct and energizing. No emojis. No quotes. No preamble."
        ),
        messages=[{"role": "user", "content": user_message}],
    )

    return {"summary": message.content[0].text.strip()}
