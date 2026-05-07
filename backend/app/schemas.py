"""Request schemas for the SwasthyaSignals API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProjectRequest(BaseModel):
    """User-defined monitoring scope for the dashboard."""

    name: str = "Diabetes drugs - India vs World"
    description: str = (
        "Monitor emerging complaints, lifestyle risks, and official safety "
        "movement for diabetes and cardiometabolic topics."
    )
    keywords: list[str] = Field(
        default_factory=lambda: [
            "diabetes",
            "insulin",
            "metformin",
            "semaglutide",
            "obesity",
            "blood sugar",
        ]
    )
    sources: list[str] = Field(default_factory=list)
    latency_profile: Literal["Realtime", "Daily", "Weekly"] = "Realtime"
    include_official_only: bool = False
