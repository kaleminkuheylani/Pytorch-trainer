"""FastAPI application with WebSocket streaming for PyTorch code analysis."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import analysis, health

app = FastAPI(
    title="PyTorch Agent Stream",
    description="AI agent that analyzes PyTorch code and streams predicted training metrics",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])
