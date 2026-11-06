"""Only the bundled invented catalogue is available; no user paths or queries."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from . import CATALOGUE_VERSION
from .artefacts import ROOT, read_json
from .schemas import Category, Channel, Identifier, Recommendation, StrictModel


class Programme(StrictModel):
    programme_id: Identifier
    name: Annotated[str, Field(min_length=1, max_length=100)]
    category: Literal["employment", "skills", "care"]
    description: Annotated[str, Field(min_length=1, max_length=240)]
    eligibility_example: Annotated[str, Field(min_length=1, max_length=240)]
    channels: Annotated[list[Channel], Field(min_length=1, max_length=3)]
    priority: Annotated[int, Field(ge=1, le=100)]
    active: bool


class Catalogue(StrictModel):
    version: Literal[CATALOGUE_VERSION]
    synthetic: Literal[True]
    programmes: Annotated[list[Programme], Field(min_length=1, max_length=30)]

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [p.programme_id for p in self.programmes]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate programme")
        return self


def lookup(category: Category, channel: Channel) -> list[Recommendation]:
    catalogue = Catalogue.model_validate(read_json(ROOT / "data/synthetic_programmes.json"))
    matches = sorted(
        (
            p
            for p in catalogue.programmes
            if p.active and p.category == category and channel in p.channels
        ),
        key=lambda p: (p.priority, p.programme_id),
    )[:3]
    return [
        Recommendation(
            programme_id=p.programme_id,
            name=p.name,
            explanation=p.eligibility_example,
            reason_codes=["CATEGORY_MATCH", "CHANNEL_SUPPORTED", "ADVISORY_ONLY"],
        )
        for p in matches
    ]
