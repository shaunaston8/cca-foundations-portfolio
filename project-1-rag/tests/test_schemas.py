import pytest
from schemas import RAGResponse, Citation, ConfidenceLevel


def test_valid_answerable_response():
    response = RAGResponse(
        answerable=True,
        answer="The PRA requires firms to maintain model inventories.",
        confidence=ConfidenceLevel.HIGH,
        citations=[
            Citation(
                chunk_id="chunk_001",
                document_name="PRA SS1/23 Model Risk Management",
                page_number=4,
                excerpt="Firms must maintain a comprehensive model inventory..."
            )
        ]
    )
    assert response.answerable is True


def test_valid_refusal_response():
    response = RAGResponse(
        answerable=False,
        refusal_reason="The provided documents do not contain information about Basel IV timelines."
    )
    assert response.answerable is False
    assert response.citations == []


def test_answerable_without_citation_raises():
    with pytest.raises(ValueError, match="at least one citation"):
        RAGResponse(
            answerable=True,
            answer="Some answer.",
            confidence=ConfidenceLevel.HIGH,
            citations=[]
        )


def test_refusal_without_reason_raises():
    with pytest.raises(ValueError, match="refusal_reason must be populated"):
        RAGResponse(answerable=False)