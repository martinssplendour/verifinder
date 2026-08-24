from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import SourceAttribution


DecisionEvidenceKind = Literal["verified_fact", "calculated_finding", "inference", "unknown"]
DecisionIntent = Literal[
    "job_search",
    "sponsor_discovery",
    "qualification_search",
    "study_provider_search",
    "food_search",
    "property_search",
    "area_check",
    "general",
]
AiMode = Literal["gemini", "deterministic"]


class AskInterpretation(BaseModel):
    intent: DecisionIntent
    subject: str | None = None
    location: str | None = None
    industry: str | None = None
    sponsorship_route: str | None = None
    # Whether the user wants records to open or an answer in words. Phrasing
    # varies too much to detect with a pattern, so the model decides it as part
    # of the same query form; "list" is the safe default.
    response_style: Literal["list", "answer"] = "list"
    limit: int = Field(default=10, ge=1, le=20)
    assumptions: list[str] = Field(default_factory=list)


class DecisionFact(BaseModel):
    kind: DecisionEvidenceKind
    label: str
    value: str


class AskResult(BaseModel):
    rank: int
    id: str
    result_type: str
    title: str
    subtitle: str | None = None
    href: str
    facts: list[DecisionFact] = Field(default_factory=list)
    why_it_matches: list[str] = Field(default_factory=list)
    source: SourceAttribution


class AskConversationTurn(BaseModel):
    question: str = Field(min_length=3, max_length=600)
    headline: str = Field(max_length=300)
    summary: str = Field(max_length=1600)
    interpretation: AskInterpretation
    results: list[AskResult] = Field(default_factory=list, max_length=10)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=600)
    limit: int = Field(default=10, ge=1, le=20)
    conversation_id: str | None = Field(default=None, min_length=36, max_length=36)
    conversation: list[AskConversationTurn] = Field(default_factory=list, max_length=6)


class AskResponse(BaseModel):
    question: str
    conversation_id: str | None = None
    context_turns_used: int = Field(default=0, ge=0, le=6)
    interpretation: AskInterpretation
    headline: str
    summary: str
    results: list[AskResult]
    total: int
    limitations: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list, max_length=4)
    ai_mode: AiMode
    generated_at: datetime


class PlanRequest(BaseModel):
    goal: str = Field(min_length=5, max_length=1200)
    location: str | None = Field(default=None, max_length=180)
    budget: int | None = Field(default=None, ge=0)
    priorities: list[str] = Field(default_factory=list, max_length=8)
    moving_date: date | None = None
    template: Literal["relocation", "study", "employment", "general"] = "relocation"


class PlanQuestion(BaseModel):
    id: str
    question: str
    why_it_matters: str


class PlanEvidence(BaseModel):
    id: str
    kind: DecisionEvidenceKind
    title: str
    detail: str
    source: SourceAttribution | None = None


class PlanMetric(BaseModel):
    label: str
    value: str


class PlanScenario(BaseModel):
    id: str
    title: str
    description: str
    location: str | None = None
    metrics: list[PlanMetric] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class PlanStep(BaseModel):
    position: int
    title: str
    description: str
    status: Literal["ready", "needs_input", "later"] = "ready"
    evidence_ids: list[str] = Field(default_factory=list)


class DecisionPlanResponse(BaseModel):
    id: str
    title: str
    goal: str
    location: str | None = None
    summary: str
    status: str
    questions: list[PlanQuestion] = Field(default_factory=list)
    scenarios: list[PlanScenario] = Field(default_factory=list)
    evidence: list[PlanEvidence] = Field(default_factory=list)
    steps: list[PlanStep] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    ai_mode: AiMode
    created_at: datetime
