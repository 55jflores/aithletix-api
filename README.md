# Aithletix API

FastAPI middleware for the Aithletix iOS app. Receives requests from the app, forwards them to the Anthropic Claude API, and streams biomechanics coaching responses back to the client.

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `JWT_SECRET` | Secret used to sign and verify JWT tokens |

## Local Development

1. Clone the repository and navigate to the project folder.

2. Create a `.env` file in the root directory:
   ```
   ANTHROPIC_API_KEY=your-key-here
   JWT_SECRET=your-secret-here
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

## Endpoints

### Health Check

**`GET /health`**
No authentication required.

Response:
```json
{"status": "ok", "app": "Aithletix API v1"}
```

---

### POST /coaching/realtime

Real-time mid-set coaching cue based on a single biomechanics snapshot.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request body:**
```json
{
  "payload": "<aiContextPayload string from iOS>",
  "selected_lift": "Squat",
  "athlete_weight_kg": 90.0
}
```

**Response:** Server-sent event stream
```
data: {"token": "Your"}
data: {"token": " hips"}
...
data: [DONE]
```

---

### POST /coaching/post-set

Full form assessment after a completed set, based on per-rep biomechanics snapshots.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request body:**
```json
{
  "payload_history": ["<snapshot rep 1>", "<snapshot rep 2>", "..."],
  "selected_lift": "Deadlift",
  "rep_count": 3,
  "athlete_weight_kg": 90.0
}
```

**Response:** Server-sent event stream
```
data: {"token": "..."}
...
data: [DONE]
```

---

### POST /coaching/chat

Multi-turn conversational coaching with optional live biomechanics context.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request body:**
```json
{
  "message": "Why is my lower back rounding?",
  "conversation_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "current_payload": "<optional live physics context>",
  "athlete_weight_kg": 90.0
}
```

**Response:** Server-sent event stream
```
data: {"token": "..."}
...
data: [DONE]
```
