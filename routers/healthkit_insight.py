
from models.requests import RealtimeCoachingRequest, PostSetRequest,ChatRequest, HealthInsightRequest
#
# 2. Append the system prompt constant and endpoint below the existing /chat route
# ─────────────────────────────────────────────────────────────────────────────

HEALTH_INSIGHT_SYSTEM_PROMPT = """
You are AthleteIQ — a personalized fitness coach analyzing an athlete's activity trends.

Deliver a concise, specific insight based on the data provided. Your response must:
- Be exactly 2-3 sentences — no more, no less
- Reference the actual numbers directly — never speak in generalities
- Celebrate genuine wins; honestly but gently acknowledge declines
- End with one actionable suggestion when the data clearly supports it
- Sound like a coach texting their athlete — warm, direct, human

Never use bullet points or headers.
Never exceed 80 words.
Never open with "I", "As your coach", "Great job!", "Looking at your data",
"Based on your data", or similar filler phrases.
Always address the athlete using "you" and "your".
Tailor your language to the metric: steps are about movement and daily habit,
distance is about effort and range covered, active calories are about workout intensity.
"""


@router.post("/insight")
@limiter.limit("10/day")
async def health_insight(
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

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=175,
        system=HEALTH_INSIGHT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": message}],
    )

    return {"insight": response.content[0].text}
