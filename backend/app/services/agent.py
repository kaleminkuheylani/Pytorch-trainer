"""LLM-powered PyTorch code analysis agent.

Analyzes PyTorch training code using GPT-4o and predicts training metrics
(loss, accuracy, epochs) without executing the code. Streams results as events.
"""

import json
import logging

from openai import AsyncOpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.models.events import (
    ArchitectureInfo,
    EpochMetrics,
    TrainingSummary,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert PyTorch training analyst. Given PyTorch training code, you analyze it \
WITHOUT running it and predict the training behavior.

Your task is to:
1. Detect the model architecture, optimizer, loss function, dataset, hyperparameters.
2. Based on your deep knowledge of deep learning, predict realistic epoch-by-epoch \
training metrics (loss, accuracy) for the entire training run.
3. Provide a training summary with convergence analysis and recommendations.

You must respond with valid JSON matching the requested schema exactly. \
Be realistic with predictions — consider the model complexity, dataset characteristics, \
learning rate, and other hyperparameters. Loss should generally decrease and accuracy \
increase, but include realistic fluctuations.
"""

ARCHITECTURE_PROMPT = """\
Analyze this PyTorch code and extract the model architecture information.
Return a JSON object with these fields:
{
  "model_type": "string — e.g. CNN, RNN, Transformer, MLP, ResNet, etc.",
  "layers": ["list of layer descriptions"],
  "optimizer": "optimizer name and config",
  "loss_function": "loss function name",
  "dataset": "dataset name or description",
  "batch_size": number or null,
  "learning_rate": number or null,
  "total_epochs": number or null,
  "device": "cpu or cuda"
}

Code:
```python
{code}
```
"""

EPOCH_PREDICTION_PROMPT = """\
Given this PyTorch training code and architecture info, predict the training metrics \
for epochs {start_epoch} to {end_epoch} (out of {total_epochs} total).

Architecture: {architecture}

Return a JSON array of epoch predictions, one per epoch:
[
  {{
    "epoch": number,
    "total_epochs": number,
    "train_loss": number,
    "val_loss": number or null,
    "train_accuracy": number or null (0-100 percentage),
    "val_accuracy": number or null (0-100 percentage),
    "learning_rate": number or null,
    "elapsed_time_estimate": "e.g. 2m 30s",
    "eta": "estimated time remaining"
  }}
]

Be realistic. Consider:
- Initial loss should match the loss function and number of classes
- Loss should generally decrease with realistic fluctuations
- Accuracy should generally increase
- Overfitting patterns if the model is too complex for the dataset
- Learning rate effects on convergence speed

Code:
```python
{code}
```
"""

SUMMARY_PROMPT = """\
Given this PyTorch training code and all predicted epoch metrics, provide a training summary.

Architecture: {architecture}
Epoch metrics: {metrics}

Return a JSON object:
{{
  "total_epochs": number,
  "final_train_loss": number,
  "final_val_loss": number or null,
  "final_train_accuracy": number or null,
  "final_val_accuracy": number or null,
  "best_epoch": number or null,
  "convergence_analysis": "detailed analysis of convergence behavior",
  "recommendations": ["list of actionable recommendations to improve training"]
}}

Code:
```python
{code}
```
"""


class PyTorchAgent:
    """AI agent that analyzes PyTorch code and predicts training metrics."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    async def _call_llm(self, prompt: str) -> str:
        """Call the OpenAI API and return the response text."""
        if not self.client:
            raise ValueError("OpenAI API key is not configured")

        response = await self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM returned empty response")
        return content

    def _parse_json(self, text: str) -> dict | list:
        """Parse JSON from LLM response, handling markdown code blocks."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]
        return json.loads(text)

    async def detect_architecture(self, code: str) -> ArchitectureInfo:
        """Detect the model architecture from PyTorch code."""
        prompt = ARCHITECTURE_PROMPT.format(code=code)
        response = await self._call_llm(prompt)
        data = self._parse_json(response)
        if isinstance(data, list):
            data = data[0] if data else {}
        return ArchitectureInfo(**data)

    async def predict_epochs(
        self,
        code: str,
        architecture: ArchitectureInfo,
        start_epoch: int,
        end_epoch: int,
        total_epochs: int,
    ) -> list[EpochMetrics]:
        """Predict training metrics for a range of epochs."""
        prompt = EPOCH_PREDICTION_PROMPT.format(
            code=code,
            architecture=architecture.model_dump_json(),
            start_epoch=start_epoch,
            end_epoch=end_epoch,
            total_epochs=total_epochs,
        )
        response = await self._call_llm(prompt)
        data = self._parse_json(response)

        if isinstance(data, dict):
            if "epochs" in data:
                data = data["epochs"]
            elif "predictions" in data:
                data = data["predictions"]
            else:
                data = [data]

        return [EpochMetrics(**epoch) for epoch in data]

    async def generate_summary(
        self,
        code: str,
        architecture: ArchitectureInfo,
        all_metrics: list[EpochMetrics],
    ) -> TrainingSummary:
        """Generate a training summary based on all predicted metrics."""
        metrics_json = json.dumps([m.model_dump() for m in all_metrics])
        prompt = SUMMARY_PROMPT.format(
            code=code,
            architecture=architecture.model_dump_json(),
            metrics=metrics_json,
        )
        response = await self._call_llm(prompt)
        data = self._parse_json(response)
        if isinstance(data, list):
            data = data[0] if data else {}
        return TrainingSummary(**data)


