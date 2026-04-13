# PyTorch Agent Stream

AI agent that analyzes PyTorch training code **without running it** and streams predicted training metrics (loss, accuracy, epochs) in real-time via WebSocket.

## Architecture

```
┌─────────────────┐     WebSocket      ┌──────────────────┐     GPT-4o      ┌─────────┐
│   Next.js UI    │ ◄──────────────────►│   FastAPI Agent  │ ◄──────────────►│ OpenAI  │
│  (Code Editor)  │   event-based      │  (State Machine) │  code analysis  │   API   │
└─────────────────┘                    └──────────────────┘                 └─────────┘
```

### Event-Based State Machine

```
IDLE → user types code → sends "update" action
     → server detects `def` → sends func_pending event
     → server runs lint periodically → sends lint_feedback
IDLE → user sends "return" action → ANALYZING
     → server streams: architecture → epoch predictions → summary
ANALYZING → complete → IDLE
ANALYZING → user sends "cancel" → IDLE
```

## Features

- **Monaco Code Editor** with Python syntax highlighting
- **Live `def` detection** — functions appear as "pending" as you type
- **Periodic lint feedback** — runs between keystrokes with debounce
- **GPT-4o analysis on submit** — predicts realistic epoch-by-epoch metrics
- **Real-time streaming charts** — loss and accuracy plotted with Recharts
- **Training summary** — convergence analysis and recommendations
- **Event log** — full event stream visible in real-time
- **Cancel support** — abort analysis at any point

## Event Protocol

### Client → Server (WebSocket)

| Action   | Description                          |
|----------|--------------------------------------|
| `update` | Code changed while typing            |
| `return` | Submit code for full analysis        |
| `cancel` | Cancel ongoing analysis              |

### Server → Client (WebSocket)

| Event                  | When                                        |
|------------------------|---------------------------------------------|
| `connected`            | WebSocket connection established             |
| `func_pending`         | New `def` detected in code                   |
| `lint_feedback`        | Periodic lint results                        |
| `analysis_start`       | Full analysis begins (after "return")        |
| `architecture_detected`| Model architecture identified                |
| `epoch_prediction`     | Predicted metrics for one epoch (streamed)   |
| `training_summary`     | Final summary with recommendations           |
| `heartbeat`            | Keepalive between predictions                |
| `error`                | Something went wrong                         |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" websockets openai pydantic python-dotenv

# Set your API key
export OPENAI_API_KEY=sk-...

# Run
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000, type PyTorch code, and click **Submit (Return)**.

## Configuration

| Environment Variable       | Default           | Description                           |
|---------------------------|-------------------|---------------------------------------|
| `OPENAI_API_KEY`          | —                 | OpenAI API key (required)             |
| `OPENAI_MODEL`            | `gpt-4o`          | LLM model to use                      |
| `STREAM_INTERVAL_SECONDS` | `30`              | Seconds between epoch predictions     |
| `NEXT_PUBLIC_WS_URL`      | `ws://localhost:8000/api/ws/analyze` | WebSocket endpoint URL |

## Tech Stack

- **Backend:** FastAPI, WebSocket, OpenAI API, Pydantic
- **Frontend:** Next.js 15, TypeScript, Tailwind CSS, Monaco Editor, Recharts
- **AI:** GPT-4o for code analysis and metric prediction
