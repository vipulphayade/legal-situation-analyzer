from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator


DISCLAIMER_TEXT = (
    "This information is based on model bye-laws and is for informational "
    "purposes only. Actual applicability depends on the registered bye-laws "
    "of the specific society."
)


class ConditionItem(BaseModel):
    requirement: str
    plain_explanation: str


class RelatedRuleItem(BaseModel):
    section: str
    subsection: Optional[str] = None
    title: str


class RelatedBylawItem(BaseModel):
    section: str
    subsection: Optional[str] = None
    title: str
    score: float = Field(..., ge=0.0, le=1.0)
    statement: str = ""
    why_this_applies: str = ""


class AnalyzeRequest(BaseModel):
    description: str = Field(
        ...,
        min_length=10,
        max_length=3000,
        description="Plain-language description of the housing society issue.",
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Description cannot be empty.")
        return cleaned


class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    law: str
    section: Optional[str]
    subsection: Optional[str]
    title: Optional[str]
    statement: str = ""
    explanation: str
    why_this_applies: str = ""
    practical_guidance: str = ""
    citation: str
    example: str
    conditions_required: list[ConditionItem]
    possible_challenges: list[str]
    related_statutes: list[str]
    related_rules: list[RelatedRuleItem]
    related_bylaws: list[RelatedBylawItem] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_label: str = ""
    disclaimer: str = DISCLAIMER_TEXT
    success: bool = True
    message: str = ""
    match_type: str = "semantic_match"
    needs_clarification: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
    possible_topics: list[str] = Field(default_factory=list)
    when_may_not_apply: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    documents_to_collect: list[str] = Field(default_factory=list)
    possible_authorities: list[str] = Field(default_factory=list)
    session_token: str = ""


class FollowupRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1500)
    context: dict[str, Any] = Field(default_factory=dict)
    session_token: str = ""

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty.")
        return cleaned


class FollowupResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    section: Optional[str]
    subsection: Optional[str]
    title: Optional[str]
    answer: str
    citation: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    disclaimer: str = DISCLAIMER_TEXT
