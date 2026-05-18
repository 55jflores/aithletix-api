import os

import anthropic
from fastapi import APIRouter, Depends, Request, HTTPException

from models.requests import PRInsightRequest
from middleware.auth import verify_token
from middleware.rate_limit import limiter

router = APIRouter()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# Readable phrasing for the self-reported "last trained" buckets, relative to
# the logged lift's own date.
LAST_TRAINED_LABELS = {
    "today": "same day",
    "yesterday": "1 day before",
    "2_days": "2 days before",
    "3plus_days": "3+ days before",
}
PR_INSIGHT_SYSTEM_PROMPT = """You are a strength coach reviewing one lift's personal-record history for an athlete. The athlete reads your response directly inside their training app.
Write 2-3 short paragraphs of grounded observations:
- Lead with the progression trend — how the estimated 1RM has moved over time.
- Surface anything genuinely interesting in THEIR numbers: rep-strength versus top-end singles, RPE patterns, plateaus or stalls.
- Connect performance to context where the data supports it: did their strongest lifts land on high-recovery days or low ones? Note recovery, recent-training load, and self-reported muscle readiness around standout lifts.
- Frame everything as observations, never predictions or promises. Write "your recent rate suggests" rather than "you will hit X".
- When the data is thin — few entries, or few with context — say so plainly. Never present a trend from two or three points as established.
- Never give medical, injury, or rehab advice.
- No generic filler ("keep up the great work", "stay consistent"). Every sentence must reference the athlete's actual numbers.
- Plain prose. No markdown headers, no bullet points, no emoji.
Notes on the data:
- "est. 1RM" is an Epley estimate the app already computed; a higher-rep set can out-score a heavier single.
- "recovery" is a 0–100 score of how recovered the athlete was that day — a blend of overnight HRV, resting heart rate, and sleep, each compared against the athlete's own baseline. Higher is better; roughly, under 34 is poor, 34–66 moderate, 67+ good. "partial" means fewer than three of those signals had data, so treat it as less certain.
- "recent training" is the athlete's own self-report at log time: how many workouts in the prior 48h, when they last trained relative to the lift, and how their main muscles felt coming in. Treat it as subjective context, not measurement.
- Context is optional and uneven — many entries have none, or only some fields. Do not treat a missing recovery score as a rest day or as full recovery; simply don't comment on what isn't there.
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
            if s.recovery_score is not None:
                score = f"recovery {round(s.recovery_score)}/100"
                if s.recovery_components is not None and s.recovery_components < 3:
                    score += f" (partial — {s.recovery_components} of 3 signals)"
                ctx.append(score)
            if s.bodyweight is not None:
                ctx.append(f"{s.bodyweight:g} lb bodyweight")
            if ctx:
                head += "\n    that day: " + ", ".join(ctx)
            training = []
            if s.workouts_past_2d is not None:
                count = s.workouts_past_2d
                training.append(
                    f"{count} workout{'' if count == 1 else 's'} in prior 48h"
                )
            if s.last_trained is not None:
                label = LAST_TRAINED_LABELS.get(s.last_trained, s.last_trained)
                training.append(f"last trained {label}")
            if s.muscle_feel is not None:
                training.append(f"main muscles felt {s.muscle_feel}")
            if training:
                head += "\n    recent training: " + ", ".join(training)
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

