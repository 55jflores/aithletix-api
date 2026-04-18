
import os
import json
import anthropic
from models.requests import RealtimeCoachingRequest, PostSetRequest,ChatRequest, HealthInsightRequest,WeeklyDigestRequest
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from middleware.auth import verify_token
from middleware.rate_limit import limiter

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

HEALTH_INSIGHT_SYSTEM_PROMPT = """
You are AthleteIQ — a personalized fitness coach analyzing an athlete's activity trends.

Deliver a concise, specific insight based on the data provided. Your response must:
- Be exactly 2-3 sentences — no more, no less
- Reference the actual numbers directly — never speak in generalities
- Celebrate genuine wins; honestly but gently acknowledge declines
- Sound like a coach texting their athlete — warm, direct, human

After your insight, append exactly ||ACTION|| followed by one specific, actionable
suggestion tied directly to the data. The action must be one sentence, under 20 words,
and immediately actionable.

Never use bullet points or headers.
Never exceed 80 words before the ||ACTION|| delimiter.
Never open with "I", "As your coach", "Great job!", "Looking at your data",
"Based on your data", or similar filler phrases.
Always address the athlete using "you" and "your".
Tailor your language to the metric: steps are about movement and daily habit,
distance is about effort and range covered, active calories are about workout intensity.
"""

router = APIRouter()

@router.post("/insight")
@limiter.limit("10/day")
async def healthkit_insight(
    request: Request,
    body: HealthInsightRequest,
    user=Depends(verify_token),
):
    from datetime import date as date_type

    # Integer formatting for steps/calories; one decimal for distance
    def fmt(value: float) -> str:
        return f"{value:.0f}" if body.metric in ("steps", "calories") else f"{value:.1f}"

    # Trend as a signed percentage so Claude can reference the magnitude
    long_term = max(body.long_term_avg, 1)
    trend_pct  = round(abs(body.recent_avg - body.long_term_avg) / long_term * 100)
    trend_desc = (
        f"up {trend_pct}% vs 12-month average"
        if body.recent_avg >= body.long_term_avg
        else f"down {trend_pct}% vs 12-month average"
    )

    # Goal progress line — steps only
    goal_line = ""
    if body.metric == "steps" and body.goal > 0:
        progress_pct = round(body.today_value / body.goal * 100)
        goal_line = (
            f"Goal progress today: {fmt(body.today_value)} / {fmt(body.goal)} steps "
            f"({progress_pct}%)\n"
        )

    message = (
        f"Day: {date_type.today().strftime('%A')}\n"
        f"Metric: {body.metric.capitalize()} ({body.unit_label})\n"
        f"Today so far: {fmt(body.today_value)} {body.unit_label}\n"
        f"{goal_line}"
        f"Recent average: {fmt(body.recent_avg)} {body.unit_label}/day\n"
        f"12-month average: {fmt(body.long_term_avg)} {body.unit_label}/day\n"
        f"Trend: {trend_desc}\n"
        f"Personal best day: {fmt(body.best_day)} {body.unit_label}\n"
    )

    def generate():
        try:
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=175,
                system=HEALTH_INSIGHT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": message}],
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'token': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:
            yield f"data: {json.dumps({'error': 'Streaming failed. Please try again.'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

WEEKLY_DIGEST_SYSTEM_PROMPT = """
You are AthleteIQ — a personalized fitness coach delivering a weekly performance recap.

You will receive one week of activity data across three metrics: steps, distance, and active calories.
Each metric includes this week's average, last week's average, and a percentage change.

Your response must:
- Be exactly 4-5 sentences — no more, no less
- Open by naming the metric that changed most significantly (positively or negatively)
- Reference specific numbers for at least two of the three metrics
- Identify one clear pattern or insight that spans multiple metrics when possible
- Close with one concrete, specific focus for the coming week tied to the data
- Sound like a coach writing a short weekly debrief — honest, encouraging, direct

Never use bullet points, headers, or numbered lists.
Never exceed 150 words.
Never open with "I", "As your coach", "Great week!", "Looking at your data",
"Based on your data", "This week", or similar filler openers.
Always address the athlete using "you" and "your".
"""


def _pct_change(this_week: float, last_week: float) -> str:
    """Return a signed percentage change string, e.g. '+12%' or '-5%'."""
    if last_week <= 0:
        return "no prior data"
    pct = round((this_week - last_week) / last_week * 100)
    return f"+{pct}%" if pct >= 0 else f"{pct}%"


@router.post("/weekly-digest")
@limiter.limit("7/day")
async def weekly_digest(
    request: Request,
    body: WeeklyDigestRequest,
    user=Depends(verify_token),
):
    steps_change    = _pct_change(body.steps_this_week,    body.steps_last_week)
    distance_change = _pct_change(body.distance_this_week, body.distance_last_week)
    calories_change = _pct_change(body.calories_this_week, body.calories_last_week)

    message = (
        f"Weekly activity summary:\n\n"
        f"Steps\n"
        f"  This week avg:  {body.steps_this_week:.0f} steps/day\n"
        f"  Last week avg:  {body.steps_last_week:.0f} steps/day\n"
        f"  Change:         {steps_change}\n"
        f"  Best day:       {body.steps_best_day:.0f} steps\n"
        f"  Goal ({body.steps_goal:.0f}/day) hit: {body.steps_goal_days} / 7 days\n\n"
        f"Distance\n"
        f"  This week avg:  {body.distance_this_week:.2f} {body.distance_unit}/day\n"
        f"  Last week avg:  {body.distance_last_week:.2f} {body.distance_unit}/day\n"
        f"  Change:         {distance_change}\n\n"
        f"Active Calories\n"
        f"  This week avg:  {body.calories_this_week:.0f} kcal/day\n"
        f"  Last week avg:  {body.calories_last_week:.0f} kcal/day\n"
        f"  Change:         {calories_change}\n"
    )

    async def _stream():
        try:
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=250,
                system=WEEKLY_DIGEST_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": message}],
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'token': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")
