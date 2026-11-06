"""Small deterministic orchestrator; callable only after policy by the MCP adapter."""

from . import AGENT_VERSION, CATALOGUE_VERSION, RULES_VERSION
from .catalogue import lookup
from .classifier import classify
from .policy import SafeFailure
from .schemas import RecommendationRequest, RecommendationResponse


def recommend(request: RecommendationRequest, trace_id: str) -> RecommendationResponse:
    classification = classify(request.request_text)
    try:
        matches = lookup(classification.category, request.channel)
    except Exception:
        raise SafeFailure("dependency_failure") from None
    reason_codes = [classification.reason, "ADVISORY_ONLY"]
    if classification.category == "ambiguous":
        status = "human_review"
    elif not matches:
        status = "abstained"
        if classification.category != "unknown":
            reason_codes.insert(1, "NO_PROGRAMME")
    else:
        status = "recommended"
    response = RecommendationResponse(
        request_id=request.request_id,
        category=classification.category,
        recommendations=matches,
        reason_codes=reason_codes,
        requires_human_review=not bool(matches),
        agent_version=AGENT_VERSION,
        rules_version=RULES_VERSION,
        catalogue_version=CATALOGUE_VERSION,
        trace_id=trace_id,
        status=status,
    )
    # Explicit post-construction output validation, also enforced by the MCP adapter.
    return RecommendationResponse.model_validate(response.model_dump())
