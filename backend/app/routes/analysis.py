"""Analysis routes — event-based WebSocket with state machine.

State machine:
  IDLE → user types code → sends "update" action
       → server detects `def` → sends func_pending event
       → server runs lint periodically → sends lint_feedback
  IDLE → user sends "return" action → ANALYZING
       → server streams architecture, epoch predictions, summary
  ANALYZING → complete → IDLE (ready for next submission)
  ANALYZING → user sends "cancel" → IDLE
"""

import asyncio
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import STREAM_INTERVAL_SECONDS
from app.models.events import (
    ClientAction,
    ClientMessage,
    EventType,
    StreamEvent,
)
from app.services.agent import PyTorchAgent
from app.services.linter import lint_pytorch_code
from app.services.parser import detect_pending_functions, has_new_defs

logger = logging.getLogger(__name__)
router = APIRouter()

LINT_DEBOUNCE_SECONDS = 2.0
EPOCHS_PER_BATCH = 5


def _make_event(
    event_type: EventType,
    data: dict | None = None,
    message: str = "",
) -> StreamEvent:
    return StreamEvent(
        event_type=event_type,
        data=data or {},
        message=message,
        timestamp=time.time(),
    )


async def _send(ws: WebSocket, event: StreamEvent) -> None:
    await ws.send_json(event.model_dump())


async def _run_analysis(
    ws: WebSocket,
    agent: PyTorchAgent,
    code: str,
    interval: int,
    cancel_event: asyncio.Event,
) -> None:
    """Run the full analysis pipeline and stream results."""

    # 1. Lint
    lint_issues = lint_pytorch_code(code)
    await _send(
        ws,
        _make_event(
            EventType.LINT_FEEDBACK,
            data={"issues": [i.model_dump() for i in lint_issues]},
            message=f"Lint: {len(lint_issues)} issue(s) found.",
        ),
    )

    if cancel_event.is_set():
        return

    # 2. Detect architecture
    try:
        architecture = await agent.detect_architecture(code)
    except Exception as exc:
        await _send(
            ws,
            _make_event(
                EventType.ERROR,
                data={"detail": str(exc)},
                message="Failed to detect architecture. Check your OpenAI API key.",
            ),
        )
        return

    await _send(
        ws,
        _make_event(
            EventType.ARCHITECTURE_DETECTED,
            data=architecture.model_dump(),
            message=f"Architecture detected: {architecture.model_type}",
        ),
    )

    if cancel_event.is_set():
        return

    # 3. Stream epoch predictions
    total_epochs = architecture.total_epochs or 10
    all_metrics = []
    epoch = 1

    while epoch <= total_epochs and not cancel_event.is_set():
        end_epoch = min(epoch + EPOCHS_PER_BATCH - 1, total_epochs)

        try:
            batch_metrics = await agent.predict_epochs(
                code, architecture, epoch, end_epoch, total_epochs
            )
        except Exception as exc:
            await _send(
                ws,
                _make_event(
                    EventType.ERROR,
                    data={"detail": str(exc)},
                    message=f"Error predicting epochs {epoch}-{end_epoch}",
                ),
            )
            break

        for metrics in batch_metrics:
            if cancel_event.is_set():
                return

            all_metrics.append(metrics)
            msg = (
                f"Epoch {metrics.epoch}/{total_epochs} — "
                f"loss: {metrics.train_loss:.4f}"
            )
            if metrics.train_accuracy is not None:
                msg += f", accuracy: {metrics.train_accuracy:.1f}%"

            await _send(
                ws,
                _make_event(
                    EventType.EPOCH_PREDICTION,
                    data=metrics.model_dump(),
                    message=msg,
                ),
            )

            # Wait between epochs, send heartbeats
            if metrics.epoch < total_epochs:
                remaining = interval
                while remaining > 0 and not cancel_event.is_set():
                    wait = min(10, remaining)
                    await asyncio.sleep(wait)
                    remaining -= wait
                    if remaining > 0 and not cancel_event.is_set():
                        await _send(
                            ws,
                            _make_event(
                                EventType.HEARTBEAT,
                                data={"next_epoch_in": remaining},
                                message="Analyzing next epoch...",
                            ),
                        )

        epoch = end_epoch + 1

    if cancel_event.is_set():
        return

    # 4. Training summary
    if all_metrics:
        try:
            summary = await agent.generate_summary(code, architecture, all_metrics)
            await _send(
                ws,
                _make_event(
                    EventType.TRAINING_SUMMARY,
                    data=summary.model_dump(),
                    message="Training analysis complete!",
                ),
            )
        except Exception as exc:
            await _send(
                ws,
                _make_event(
                    EventType.ERROR,
                    data={"detail": str(exc)},
                    message="Failed to generate training summary.",
                ),
            )


@router.websocket("/ws/analyze")
async def ws_analyze(ws: WebSocket) -> None:
    """Event-based WebSocket endpoint for PyTorch code analysis.

    Protocol (client → server):
      {"action": "update", "code": "..."}   — code changed while typing
      {"action": "return", "code": "...", "stream_interval": 30}  — submit for analysis
      {"action": "cancel"}                   — cancel ongoing analysis

    Protocol (server → client):
      func_pending       — new `def` detected, shown as pending
      lint_feedback      — periodic lint results while typing
      analysis_start     — full analysis begins (after "return")
      architecture_detected
      epoch_prediction   — streamed every stream_interval seconds
      training_summary   — final summary
      heartbeat          — keepalive between predictions
      error              — something went wrong
    """
    await ws.accept()
    agent = PyTorchAgent()

    await _send(
        ws,
        _make_event(EventType.CONNECTED, message="Connected. Start typing your PyTorch code."),
    )

    current_code = ""
    analysis_task: asyncio.Task | None = None
    cancel_event = asyncio.Event()
    lint_task: asyncio.Task | None = None

    async def _periodic_lint(code: str) -> None:
        """Run lint after a debounce period and send results."""
        await asyncio.sleep(LINT_DEBOUNCE_SECONDS)
        issues = lint_pytorch_code(code)
        try:
            await _send(
                ws,
                _make_event(
                    EventType.LINT_FEEDBACK,
                    data={"issues": [i.model_dump() for i in issues]},
                    message=f"Lint: {len(issues)} issue(s) found.",
                ),
            )
        except Exception:
            pass

    try:
        while True:
            raw = await ws.receive_json()
            msg = ClientMessage(**raw)

            if msg.action == ClientAction.UPDATE:
                old_code = current_code
                current_code = msg.code

                # Detect new `def` statements → send func_pending
                new_defs = has_new_defs(old_code, current_code)
                for func in new_defs:
                    await _send(
                        ws,
                        _make_event(
                            EventType.FUNC_PENDING,
                            data=func.model_dump(),
                            message=f"Function '{func.name}' detected — pending return.",
                        ),
                    )

                # Schedule debounced lint
                if lint_task and not lint_task.done():
                    lint_task.cancel()
                lint_task = asyncio.create_task(_periodic_lint(current_code))

            elif msg.action == ClientAction.RETURN:
                # Cancel any running analysis
                if analysis_task and not analysis_task.done():
                    cancel_event.set()
                    analysis_task.cancel()
                    try:
                        await analysis_task
                    except asyncio.CancelledError:
                        pass

                cancel_event.clear()
                code_to_analyze = msg.code or current_code
                current_code = code_to_analyze
                interval = msg.stream_interval or STREAM_INTERVAL_SECONDS

                # Mark all detected functions as analyzing
                funcs = detect_pending_functions(code_to_analyze)
                for func in funcs:
                    func.status = "analyzing"
                    await _send(
                        ws,
                        _make_event(
                            EventType.FUNC_PENDING,
                            data=func.model_dump(),
                            message=f"Function '{func.name}' — analyzing...",
                        ),
                    )

                await _send(
                    ws,
                    _make_event(
                        EventType.ANALYSIS_START,
                        data={"functions": [f.model_dump() for f in funcs]},
                        message="Analysis started. Predicting training metrics...",
                    ),
                )

                # Start analysis in background
                analysis_task = asyncio.create_task(
                    _run_analysis(ws, agent, code_to_analyze, interval, cancel_event)
                )

            elif msg.action == ClientAction.CANCEL:
                if analysis_task and not analysis_task.done():
                    cancel_event.set()
                    analysis_task.cancel()
                    try:
                        await analysis_task
                    except asyncio.CancelledError:
                        pass
                    cancel_event.clear()
                    await _send(
                        ws,
                        _make_event(
                            EventType.HEARTBEAT,
                            message="Analysis cancelled.",
                        ),
                    )

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as exc:
        logger.exception("Unexpected error in WebSocket")
        try:
            await _send(
                ws,
                _make_event(
                    EventType.ERROR,
                    data={"detail": str(exc)},
                    message="Internal server error",
                ),
            )
            await ws.close()
        except Exception:
            pass
    finally:
        # Cleanup background tasks
        if analysis_task and not analysis_task.done():
            cancel_event.set()
            analysis_task.cancel()
        if lint_task and not lint_task.done():
            lint_task.cancel()


@router.post("/analyze")
async def analyze_code_rest(request: ClientMessage) -> dict:
    """REST endpoint for one-shot analysis (non-streaming).

    Returns lint results and detected functions. For full streaming
    analysis use the WebSocket endpoint at /api/ws/analyze.
    """
    lint_issues = lint_pytorch_code(request.code)
    funcs = detect_pending_functions(request.code)

    return {
        "lint_issues": [i.model_dump() for i in lint_issues],
        "functions": [f.model_dump() for f in funcs],
    }
