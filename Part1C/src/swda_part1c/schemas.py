"""Strict, bounded business contracts. Text is data, never executable instructions."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal["employment", "skills", "care", "unknown", "ambiguous"]
Channel = Literal["web", "phone", "caseworker"]
Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
Reason = Literal[
    "KEYWORD_MATCH",
    "CATEGORY_MATCH",
    "CHANNEL_SUPPORTED",
    "ADVISORY_ONLY",
    "NO_CATEGORY",
    "AMBIGUOUS_CATEGORY",
    "NO_PROGRAMME",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class RecommendationRequest(StrictModel):
    request_id: Identifier
    request_text: Annotated[str, Field(min_length=1, max_length=2000)]
    channel: Channel

    @model_validator(mode="after")
    def nonblank(self):
        if not self.request_text.strip():
            raise ValueError("Blank request")
        return self


class Recommendation(StrictModel):
    programme_id: Identifier
    name: Annotated[str, Field(min_length=1, max_length=100)]
    explanation: Annotated[str, Field(min_length=1, max_length=240)]
    reason_codes: Annotated[list[Reason], Field(min_length=1, max_length=4)]


class RecommendationResponse(StrictModel):
    request_id: Identifier
    category: Category
    recommendations: Annotated[list[Recommendation], Field(max_length=3)]
    reason_codes: Annotated[list[Reason], Field(min_length=1, max_length=4)]
    requires_human_review: bool
    agent_version: Annotated[str, Field(max_length=32)]
    rules_version: Annotated[str, Field(max_length=32)]
    catalogue_version: Annotated[str, Field(max_length=64)]
    trace_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    status: Literal["recommended", "abstained", "human_review"]
    advisory: Literal[True] = True

    @model_validator(mode="after")
    def consistent(self):
        if (self.status == "recommended") != bool(self.recommendations):
            raise ValueError("Inconsistent recommendation status")
        if self.status != "recommended" and not self.requires_human_review:
            raise ValueError("Abstention requires review")
        return self
