# Aithletix API

FastAPI backend for the Aithletix iOS app. Handles biomechanics coaching (powered by Claude Opus) and HealthKit activity insights (Claude Sonnet/Haiku), streaming responses back to the client via SSE.

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `SUPABASE_JWT_PUBLIC_KEY` | Supabase ES256 public key (JWK JSON or PEM string) used to verify JWT tokens |
| `DEV_TOKEN_SECRET` | Secret for the `/auth/dev-token` endpoint (local dev only) |

## Local Development

1. Clone the repository and navigate to the project folder.

2. Create a `.env` file in the root directory:
   ```
   ANTHROPIC_API_KEY=your-key-here
   SUPABASE_JWT_PUBLIC_KEY=your-public-key-here
   DEV_TOKEN_SECRET=your-dev-secret-here
   ```

3. Install dependencies (Python 3.11, Anaconda recommended):
   ```bash
   pip install -r requirements.txt
   ```

4. Start the development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

5. API is available at `http://localhost:8000`  
   Interactive docs at `http://localhost:8000/docs`

## Authentication

All endpoints except `GET /health` require a `Bearer` JWT token issued by Supabase (ES256).

For local development, generate a short-lived dev token:

```
POST /auth/dev-token
```

Request body:
```json
{ "secret": "<DEV_TOKEN_SECRET>" }
```

Response:
```json
{
  "token": "<jwt>",
  "user_id": "dev-user-001",
  "display_name": "Dev Athlete",
  "email": "dev@aithletix.app"
}
```

---

## Endpoints

### Health Check

**`GET /health`** — no authentication required.

Response:
```json
{ "status": "ok", "app": "Aithletix API v1" }
```

---

### Coaching

All coaching endpoints require authentication. Payloads must contain the sections:
`=== AthleteIQ Physics Context ===`, `--- Session ---`, `--- Joint Angles ---`, `--- Torque Analysis ---`, `--- Stability ---`.

---

**`POST /coaching/realtime`** — rate limit: 30/min

Mid-set coaching cue based on a single biomechanics snapshot.

Request body:
```json
{
  "payload": "<aiContextPayload string from iOS>",
  "selected_lift": "Squat",
  "athlete_weight": 90.0,
  "weight_unit": "kg"
}
```

`selected_lift` must be one of: `"Squat"`, `"Deadlift"`, `"Bench Press"`.  
`weight_unit` must be `"kg"` or `"lbs"`.

Response: SSE stream
```
data: {"token": "Drive"}
data: {"token": " your"}
...
data: [DONE]
```

---

**`POST /coaching/post-set`** — rate limit: 10/min

Full form assessment after a completed set, based on per-rep snapshots.

Request body:
```json
{
  "payload_history": ["<snapshot rep 1>", "<snapshot rep 2>"],
  "selected_lift": "Deadlift",
  "rep_count": 3,
  "athlete_weight": 90.0,
  "weight_unit": "kg"
}
```

Response: SSE stream

---

**`POST /coaching/chat`** — rate limit: 20/min

Multi-turn conversational coaching with optional live biomechanics context.

Request body:
```json
{
  "message": "Why is my lower back rounding?",
  "conversation_history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "current_payload": "<optional live physics context>",
  "athlete_weight": 90.0,
  "weight_unit": "kg"
}
```

Response: SSE stream

---

### HealthKit

---

**`POST /healthkit/snapshot`** — rate limit: 500/day

Generates a full AI health snapshot with five structured sections: `daily_brief`, `step_insight`, `distance_insight`, `calorie_insight`, and `weekly_digest`. Results are cached per user per time-of-day slot for the current day.

Request body:
```json
{
  "steps_today": 7200,
  "steps_goal": 10000,
  "steps_yesterday": 8500,
  "steps_recent_avg": 7800,
  "steps_long_term_avg": 7200,
  "steps_best_day": 15000,
  "step_streak": 4,
  "steps_this_week": 7500,
  "steps_last_week": 6900,
  "steps_goal_days": 3,
  "distance_today": 3.2,
  "distance_unit": "mi",
  "distance_recent_avg": 3.5,
  "distance_long_term_avg": 3.1,
  "distance_best_day": 7.2,
  "distance_streak": 4,
  "distance_this_week": 3.4,
  "distance_last_week": 3.0,
  "calories_today": 420,
  "calories_recent_avg": 450,
  "calories_long_term_avg": 400,
  "calories_best_day": 900,
  "calorie_streak": 4,
  "calories_this_week": 440,
  "calories_last_week": 390,
  "time_of_day": "morning",
  "date": "Monday, May 05, 2025",
  "force_refresh": false
}
```

`time_of_day` must be `"morning"`, `"afternoon"`, or `"evening"`.  
`distance_unit` must be `"mi"` or `"km"`.  
Set `force_refresh: true` to bypass the cache.

Response: SSE stream

---

**`POST /healthkit/chat`** — rate limit: 30/day

Multi-turn chat about daily activity trends (steps, distance, active calories).

Request body:
```json
{
  "message": "How were my steps this week compared to last?",
  "health_context": "<raw health context string>",
  "history": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

Response: SSE stream

---

**`POST /healthkit/share-summary`** — rate limit: 10/day

Generates a single punchy sentence for a shareable activity card.

Request body:
```json
{
  "steps": 10200,
  "step_goal": 10000,
  "distance": 4.5,
  "distance_unit": "mi",
  "calories": 520,
  "step_streak": 5,
  "distance_streak": 3,
  "calorie_streak": 5,
  "goal_hit": true
}
```

Response:
```json
{ "summary": "Five days straight hitting your step goal — keep the streak alive." }
```
