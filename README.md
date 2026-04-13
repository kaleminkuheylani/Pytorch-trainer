# PyTorch Agent Stream

AI agent that analyzes PyTorch training code **without running it** and streams predicted training metrics (loss, accuracy, epochs) in real-time via WebSocket.

## Architecture

```
┌─────────────────┐     WebSocket      ┌──────────────────┐   GPT-4o-mini   ┌─────────┐
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
- **GPT-4o-mini analysis on submit** — predicts realistic epoch-by-epoch metrics
- **In-memory LRU cache** — skips API calls for previously analyzed code
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

## Deployment (Production)

### Backend → Railway

1. [Railway Dashboard](https://railway.app/dashboard) → **New Project** → **Deploy from GitHub repo**
2. Root directory olarak `backend/` seçin
3. Environment variables ekleyin:
   - `OPENAI_API_KEY` = `sk-...`
   - `OPENAI_MODEL` = `gpt-4o-mini` (opsiyonel, varsayılan)
   - `STREAM_INTERVAL_SECONDS` = `30` (opsiyonel)
4. Deploy edin — Railway otomatik olarak Python'u algılayıp `Procfile`'ı kullanacak
5. Deploy sonrası Railway URL'inizi kopyalayın (örn: `https://pytorch-agent-stream-production.up.railway.app`)

### Frontend → Vercel

1. [Vercel Dashboard](https://vercel.app/new) → **Import Git Repository**
2. Root directory olarak `frontend/` seçin
3. Framework: **Next.js** (otomatik algılanır)
4. Environment variables ekleyin:
   - `NEXT_PUBLIC_API_HOST` = `https://pytorch-agent-stream-production.up.railway.app` (Railway URL'niz)
   - veya `NEXT_PUBLIC_WS_URL` = `wss://pytorch-agent-stream-production.up.railway.app/api/ws/analyze`
5. Deploy edin

> **Not:** `NEXT_PUBLIC_API_HOST` veya `NEXT_PUBLIC_WS_URL` set edilmezse, frontend varsayılan olarak `ws://localhost:8000` kullanır (sadece local development için).

### CORS Ayarı

Backend zaten tüm origin'lere izin veriyor (`allow_origins=["*"]`). Production'da bunu Vercel domain'inizle sınırlandırabilirsiniz.

## Configuration

| Environment Variable       | Default           | Description                           |
|---------------------------|-------------------|---------------------------------------|
| `OPENAI_API_KEY`          | —                 | OpenAI API key (required)             |
| `OPENAI_MODEL`            | `gpt-4o-mini`     | LLM model to use                      |
| `STREAM_INTERVAL_SECONDS` | `30`              | Seconds between epoch predictions     |
| `NEXT_PUBLIC_WS_URL`      | `ws://localhost:8000/api/ws/analyze` | Full WebSocket endpoint URL |
| `NEXT_PUBLIC_API_HOST`    | —                 | Backend host URL (Railway URL)        |

## Tech Stack

- **Backend:** FastAPI, WebSocket, OpenAI API, Pydantic
- **Frontend:** Next.js 16, TypeScript, Tailwind CSS, Monaco Editor, Recharts
- **AI:** GPT-4o-mini for code analysis and metric prediction (configurable)
- **Deployment:** Railway (backend) + Vercel (frontend)

## Cost Optimization

Default configuration targets **~$5-10/month** for 10 users:

| Servis | Plan | Maliyet |
|--------|------|---------|
| Railway (backend) | Hobby | $5-10/ay |
| Vercel (frontend) | Hobby/Free | $0 |
| OpenAI API (GPT-4o-mini) | Kullanım bazlı | ~$4.50/ay |
| **Toplam** | | **~$10-15/ay** |

### Neden GPT-4o-mini?

- **~10x daha ucuz:** $0.15/1M input + $0.60/1M output (vs GPT-4o: $2.50 + $10)
- Kod analizi için yeterli doğruluk
- `OPENAI_MODEL=gpt-4o` ile eski modele dönülebilir

### Ek Tasarruf Yöntemleri

- **In-memory cache:** Aynı kod tekrar gönderildiğinde API çağrısı yapılmaz
- **Kısa prompt'lar:** Token kullanımı ~%30 azaltıldı
- **Ücretsiz alternatifler:** [Render.com](https://render.com) free tier (backend), Vercel free (frontend)
