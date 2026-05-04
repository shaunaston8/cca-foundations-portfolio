from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field, model_validator


class ConfidenceLevel(str, Enum):
    HIGH = "high"        # Answer is directly and explicitly supported by retrieved chunks
    MEDIUM = "medium"    # Answer is reasonably inferable from retrieved chunks
    LOW = "low"          # Retrieved chunks are tangentially related; answer uncertain


class Citation(BaseModel):
    chunk_id: str = Field(
        description="The identifier of the chunk as passed in the prompt, e.g. 'chunk_003'"
    )
    document_name: str = Field(
        description="Human-readable document name, e.g. 'PRA SS1/23 Model Risk Management'"
    )
    page_number: int | None = Field(
        default=None,
        description="Page number from source document if available"
    )
    excerpt: str = Field(
        description="The verbatim excerpt from the chunk that supports the answer, max 200 chars"
    )


class RAGResponse(BaseModel):
    answerable: bool = Field(
        description=(
            "True if the retrieved chunks contain sufficient evidence to answer the question. "
            "False if the question cannot be answered from the provided context."
        )
    )
    answer: str | None = Field(
        default=None,
        description="The answer to the question. None if answerable is False."
    )
    confidence: ConfidenceLevel | None = Field(
        default=None,
        description="Confidence level. None if answerable is False."
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Supporting citations. Empty list if answerable is False."
    )
    refusal_reason: str | None = Field(
        default=None,
        description=(
            "Explanation of why the question cannot be answered from the provided context. "
            "Populated only when answerable is False."
        )
    )

    @model_validator(mode="after")
    def validate_consistency(self) -> RAGResponse:
        if self.answerable:
            if self.answer is None:
                raise ValueError("answer must be populated when answerable is True")
            if self.confidence is None:
                raise ValueError("confidence must be populated when answerable is True")
            if not self.citations:
                raise ValueError("at least one citation is required when answerable is True")
            if self.refusal_reason is not None:
                raise ValueError("refusal_reason must be None when answerable is True")
        else:
            if self.answer is not None:
                raise ValueError("answer must be None when answerable is False")
            if self.refusal_reason is None:
                raise ValueError("refusal_reason must be populated when answerable is False")
        return self