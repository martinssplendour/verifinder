from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from app.schemas import AskInterpretation, PlanEvidence


GENERATE_CONTENT_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlanRefinement:
    summary: str
    inferences: list[PlanEvidence]


def _output_text(payload: dict) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("The model response did not contain a candidate.")
    content = candidates[0].get("content", {})
    parts = content.get("parts", []) if isinstance(content, dict) else []
    text = "\n".join(
        str(part["text"])
        for part in parts
        if isinstance(part, dict) and part.get("text")
    ).strip()
    if not text:
        raise ValueError("The model response did not contain structured output.")
    return text


class GeminiReasoner:
    """A constrained LLM adapter: Gemini interprets or summarizes; SQL selects all evidence."""

    def __init__(self, api_key: str | None, model: str):
        self.api_key = api_key.strip() if api_key else None
        self.model = model.strip()

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    async def _structured(
        self,
        *,
        instructions: str,
        input_text: str,
        schema: dict,
        max_output_tokens: int = 900,
    ) -> dict:
        if not self.configured:
            raise RuntimeError("Gemini is not configured.")
        body = {
            "system_instruction": {"parts": [{"text": instructions}]},
            "contents": [{"role": "user", "parts": [{"text": input_text}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
            },
        }
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        url = GENERATE_CONTENT_URL.format(model=quote(self.model, safe="-_."))
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response: httpx.Response | None = None
            for attempt in range(3):
                response = await client.post(url, headers=headers, json=body)
                if response.status_code not in RETRYABLE_STATUS_CODES or attempt == 2:
                    break
                await response.aclose()
                await asyncio.sleep(0.5 * (2**attempt))
        if response is None:
            raise RuntimeError("Gemini did not return a response.")
        response.raise_for_status()
        return json.loads(_output_text(response.json()))

    async def interpret_question(self, question: str, requested_limit: int) -> AskInterpretation | None:
        if not self.configured:
            return None
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": [
                        "sponsor_discovery",
                        "qualification_search",
                        "study_provider_search",
                        "food_search",
                        "property_search",
                        "area_check",
                        "general",
                    ],
                },
                "subject": {"type": ["string", "null"]},
                "location": {"type": ["string", "null"]},
                "industry": {"type": ["string", "null"]},
                "sponsorship_route": {"type": ["string", "null"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                "assumptions": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "intent",
                "subject",
                "location",
                "industry",
                "sponsorship_route",
                "limit",
                "assumptions",
            ],
        }
        instructions = (
            "Translate the user's request into VeriFinder's controlled public-data query. "
            "Do not answer the question and do not invent filters. Sponsorship means worker-sponsor discovery. "
            "A phrase such as 'qualifications in cybersecurity' uses cybersecurity as subject, not location. "
            f"Never return a limit above {requested_limit}. Put unavoidable interpretations in assumptions."
        )
        try:
            payload = await self._structured(
                instructions=instructions,
                input_text=question,
                schema=schema,
            )
            payload["limit"] = min(requested_limit, int(payload.get("limit") or requested_limit))
            return AskInterpretation.model_validate(payload)
        except (httpx.HTTPError, ValueError, ValidationError, TypeError, RuntimeError) as exc:
            logger.warning("Gemini query interpretation failed; using deterministic rules: %s", type(exc).__name__)
            return None

    async def refine_plan(
        self,
        *,
        goal: str,
        deterministic_summary: str,
        evidence: list[PlanEvidence],
    ) -> PlanRefinement | None:
        if not self.configured or not evidence:
            return None
        valid_ids = {item.id for item in evidence}
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "summary": {"type": "string"},
                "inferences": {
                    "type": "array",
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "detail": {"type": "string"},
                            "evidence_ids": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["id", "title", "detail", "evidence_ids"],
                    },
                },
            },
            "required": ["summary", "inferences"],
        }
        packet = {
            "goal": goal,
            "draft_summary": deterministic_summary,
            "evidence": [item.model_dump(mode="json") for item in evidence],
        }
        instructions = (
            "Act as a cautious decision analyst. Improve the summary and derive only modest inferences from the "
            "supplied evidence. Do not introduce external facts, scores, neighbourhood claims, or recommendations. "
            "Every inference must cite one or more supplied evidence IDs. Keep uncertainty explicit."
        )
        try:
            payload = await self._structured(
                instructions=instructions,
                input_text=json.dumps(packet),
                schema=schema,
                max_output_tokens=2400,
            )
        except (httpx.HTTPError, ValueError, TypeError, RuntimeError) as exc:
            logger.warning("Gemini plan refinement failed; using deterministic summary: %s", type(exc).__name__)
            return None
        inferences: list[PlanEvidence] = []
        for index, item in enumerate(payload.get("inferences", []), start=1):
            cited = [value for value in item.get("evidence_ids", []) if value in valid_ids]
            if not cited:
                continue
            inferences.append(
                PlanEvidence(
                    id=f"inference-{index}",
                    kind="inference",
                    title=item.get("title", "Evidence-based inference"),
                    detail=f"{item.get('detail', '')} Evidence used: {', '.join(cited)}.",
                )
            )
        return PlanRefinement(summary=str(payload.get("summary") or deterministic_summary), inferences=inferences)
