import os
import anthropic
from fastapi import APIRouter, Depends, Request, HTTPException
from models.requests import PRInsightRequest
from middleware.auth import verify_token
from middleware.rate_limit import limiter
router = APIRouter()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
PR_INSIGHT_SYSTEM_PROMPT = """You are a strength coach reviewing one lift's personal-record history for an athlete. The athlete reads your response directly inside their training app.
Write 2-3 short paragraphs of grounded observations:
- Lead with the progression trend — how the estimated 1RM has moved over time.
- Surface anything genuinely interesting in THEIR numbers: rep-strength versus top-end singles, RPE patterns, plateaus or stalls, and the activity conditions in the 24h before their strongest lifts.
- Frame everything as observations, never predictions or promises. Write "your recent rate suggests" rather than "you will hit X".
- When the data is thin — few entries, or few with health context — say so plainly. Never present a trend from two or three points as established.
- Never give medical, injury, or rehab advice.
- No generic filler ("keep up the great work", "stay consistent"). Every sentence must reference the athlete's actual numbers.
- Plain prose. No markdown headers, no bullet points, no emoji.
Notes on the data:
- "est. 1RM" is an Epley estimate the app already computed; a higher-rep set can out-score a heavier single.
- "24h before" activity (steps, active calories, floors) is the lead-up to that lift. Active calories prefixed with ~ are estimates, not measured.
- Some entries have no 24h context — they were logged before that tracking existed. Do not treat missing context as zero activity.
"""
@router.post("/pr-insight")
@limiter.limit("30/day")
async def pr_insight(
    request: Request,
    body: PRInsightRequest,
    user=Depends(verify_token),
):
    # Format the structured PR history into a readable block for the model.
    lines = []
    for e in body.entries:
        if e.is_bodyweight:
            head = f"{e.date}: bodyweight x {e.reps} reps"
        else:
            head = f"{e.date}: {e.weight_lbs:g} {body.unit} x {e.reps}"
        if e.rpe is not None:
            head += f", RPE {e.rpe}"
        if not e.is_bodyweight:
            head += f"  (est. 1RM {e.estimated_1rm:g} {body.unit})"
        if e.snapshot is not None:
            s = e.snapshot
            ctx = []
            if s.steps is not None:
                ctx.append(f"{s.steps} steps")
            if s.active_cal is not None:
                ctx.append(f"~{round(s.active_cal)} active cal")
            if s.flights is not None:
                ctx.append(f"{s.flights} floors")
            if s.bodyweight is not None:
                ctx.append(f"{s.bodyweight:g} lb bodyweight")
            if ctx:
                head += "\n    24h before: " + ", ".join(ctx)
        lines.append(head)
    history_block = "\n".join(lines)
    user_content = (
        f'<pr_history lift="{body.lift}" entries="{len(body.entries)}">\n'
        f"{history_block}\n"
        f"</pr_history>\n\n"
        f"Give the athlete your read on their {body.lift} history."
    )
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=450,
            system=PR_INSIGHT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        text = "".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()
        if not text:
            raise HTTPException(status_code=502, detail="Empty insight returned.")
        return {"insight": text}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Insight generation failed. Please try again.",
        )


