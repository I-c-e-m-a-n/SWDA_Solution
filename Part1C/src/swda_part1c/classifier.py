"""Rules v1: unique whole-word matches; priorities order rules, ties abstain."""

import re
from dataclasses import dataclass

from .schemas import Category

# Explicit evaluation order. No category wins a cross-category tie silently.
RULES = (
    ("employment", frozenset({"job", "employment", "unemployed", "career"})),
    ("skills", frozenset({"training", "course", "skills", "reskill"})),
    ("care", frozenset({"caregiver", "caregiving", "respite"})),
)


@dataclass(frozen=True)
class Classification:
    category: Category
    reason: str


def classify(text: str) -> Classification:
    tokens = frozenset(re.findall(r"[a-z]+", text.casefold()))
    scores = [(category, len(tokens & keywords)) for category, keywords in RULES]
    best = max(score for _, score in scores)
    if not best:
        return Classification("unknown", "NO_CATEGORY")
    winners = [category for category, score in scores if score == best]
    if len(winners) != 1:
        return Classification("ambiguous", "AMBIGUOUS_CATEGORY")
    return Classification(winners[0], "KEYWORD_MATCH")
