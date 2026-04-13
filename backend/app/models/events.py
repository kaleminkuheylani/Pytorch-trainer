"""Pydantic models for the PyTorch analysis events.

Event-based state machine:
  1. Client connects via WebSocket
  2. Client sends code changes as they type (action: "update")
  3. When a `def` is detected → server sends func_pending event
  4. Server periodically runs lint and sends lint_feedback events
  5. Client sends "return" action → server triggers full analysis
  6. Server streams: architecture_detected → epoch_prediction(s) → training_summary
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events streamed via WebSocket."""

    # Connection lifecycle
    CONNECTED = "connected"
    ERROR = "error"
    HEARTBEAT = "heartbeat"

    # Code editing phase
    FUNC_PENDING = "func_pending"
    LINT_FEEDBACK = "lint_feedback"

    # Analysis phase (triggered on "return")
    ANALYSIS_START = "analysis_start"
    ARCHITECTURE_DETECTED = "architecture_detected"
    EPOCH_PREDICTION = "epoch_prediction"
    TRAINING_SUMMARY = "training_summary"


class ClientAction(str, Enum):
    """Actions the client can send over the WebSocket."""

    UPDATE = "update"       # Code changed (typing)
    RETURN = "return"       # Submit for full analysis
    CANCEL = "cancel"       # Cancel ongoing analysis


class ClientMessage(BaseModel):
    """Message sent by the client over WebSocket."""

    action: ClientAction
    code: str = ""
    stream_interval: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Interval in seconds between streamed epoch predictions",
    )


class LintIssue(BaseModel):
    """A single lint issue found in the code."""

    line: int
    column: int = 0
    severity: str = "warning"
    message: str


class PendingFunction(BaseModel):
    """A function definition detected as pending (not yet submitted)."""

    name: str
    line: int
    signature: str
    status: str = "pending"  # pending | analyzing | done


class ArchitectureInfo(BaseModel):
    """Detected PyTorch model architecture information."""

    model_type: str = ""
    layers: list[str] = Field(default_factory=list)
    optimizer: str = ""
    loss_function: str = ""
    dataset: str = ""
    batch_size: int | None = None
    learning_rate: float | None = None
    total_epochs: int | None = None
    device: str = "cpu"


class EpochMetrics(BaseModel):
    """Predicted metrics for a single epoch."""

    epoch: int
    total_epochs: int
    train_loss: float
    val_loss: float | None = None
    train_accuracy: float | None = None
    val_accuracy: float | None = None
    learning_rate: float | None = None
    elapsed_time_estimate: str = ""
    eta: str = ""


class TrainingSummary(BaseModel):
    """Summary of the entire predicted training run."""

    total_epochs: int
    final_train_loss: float
    final_val_loss: float | None = None
    final_train_accuracy: float | None = None
    final_val_accuracy: float | None = None
    best_epoch: int | None = None
    convergence_analysis: str = ""
    recommendations: list[str] = Field(default_factory=list)


class StreamEvent(BaseModel):
    """A single event sent over the WebSocket stream."""

    event_type: EventType
    data: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    timestamp: float = 0.0
