"""LLM-powered PyTorch code analysis agent.

Analyzes PyTorch training code using GPT-4o-mini and predicts training metrics
(loss, accuracy, epochs) without executing the code. Streams results as events.
Includes in-memory caching to avoid repeated API calls for the same code.
"""

import hashlib
import json
import logging
from collections import OrderedDict

from openai import AsyncOpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.models.events import (
    ArchitectureInfo,
    EpochMetrics,
    TrainingSummary,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a PyTorch training analyst. Analyze code WITHOUT running it. \
Predict realistic training metrics. Respond with valid JSON only.\
"""

ARCHITECTURE_PROMPT = """\
Extract model architecture from this PyTorch code. Return JSON:
{{"model_type":"string","layers":["descriptions"],"optimizer":"name","loss_function":"name",\
"dataset":"name","batch_size":N,"learning_rate":N,"total_epochs":N,"device":"cpu/cuda"}}

```python
{code}
```"""

EPOCH_PREDICTION_PROMPT = """\
Predict training metrics for epochs {start_epoch}-{end_epoch} (of {total_epochs}).
Architecture: {architecture}

Return JSON array:
[{{"epoch":N,"total_epochs":N,"train_loss":N,"val_loss":N,"train_accuracy":N,\
"val_accuracy":N,"learning_rate":N,"elapsed_time_estimate":"str","eta":"str"}}]

```python
{code}
```"""

SUMMARY_PROMPT = """\
Summarize training results.
Architecture: {architecture}
Metrics: {metrics}

Return JSON:
{{"total_epochs":N,"final_train_loss":N,"final_val_loss":N,"final_train_accuracy":N,\
"final_val_accuracy":N,"best_epoch":N,"convergence_analysis":"str",\
"recommendations":["list"]}}

```python
{code}
```"""


_CACHE_MAX_SIZE = 100


class PyTorchAgent:
    """AI agent that analyzes PyTorch code and predicts training metrics."""

    _cache: OrderedDict[str, dict] = OrderedDict()

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    @staticmethod
    def _code_hash(code: str) -> str:
        """Generate a hash key for the given code."""
        return hashlib.sha256(code.strip().encode()).hexdigest()

    @classmethod
    def _cache_get(cls, key: str) -> dict | None:
        """Get a cached result, returns None on miss."""
        if key in cls._cache:
            cls._cache.move_to_end(key)
            return cls._cache[key]
        return None

    @classmethod
    def _cache_set(cls, key: str, value: dict) -> None:
        """Store a result in the cache with LRU eviction."""
        cls._cache[key] = value
        cls._cache.move_to_end(key)
        while len(cls._cache) > _CACHE_MAX_SIZE:
            cls._cache.popitem(last=False)

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
        cache_key = self._code_hash(code)
        cached = self._cache_get(f"arch:{cache_key}")
        if cached is not None:
            logger.info("Cache hit for architecture detection")
            return ArchitectureInfo(**cached)

        prompt = ARCHITECTURE_PROMPT.format(code=code)
        response = await self._call_llm(prompt)
        data = self._parse_json(response)
        if isinstance(data, list):
            data = data[0] if data else {}
        self._cache_set(f"arch:{cache_key}", data)
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
        cache_key = self._code_hash(code + metrics_json)
        cached = self._cache_get(f"summary:{cache_key}")
        if cached is not None:
            logger.info("Cache hit for training summary")
            return TrainingSummary(**cached)

        prompt = SUMMARY_PROMPT.format(
            code=code,
            architecture=architecture.model_dump_json(),
            metrics=metrics_json,
        )
        response = await self._call_llm(prompt)
        data = self._parse_json(response)
        if isinstance(data, list):
            data = data[0] if data else {}
        self._cache_set(f"summary:{cache_key}", data)
        return TrainingSummary(**data)


