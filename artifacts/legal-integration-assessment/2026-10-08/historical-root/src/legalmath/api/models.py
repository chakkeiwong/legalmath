from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SourceImport(Strict):
    source_id: str
    official_url: str
    retrieved_at: str
    media_type: Literal["application/json", "application/pdf", "text/plain"]
    content_base64: str | None = None


class Review(Strict):
    decision: Literal["submit", "reject", "approve_meaning", "approve_engineering"]
    expected_revision: int = Field(ge=1)
    comment: str = ""
    manifest_hash: str | None = None


class Release(Strict):
    java_release_manifest_hash: str
    expected_revision: int = Field(ge=1)
    activated_at: str


class Evaluation(Strict):
    bundle_hash: str
    snapshot: dict
    rule_id: str
    valid_at: str
    known_at: str
    mode: Literal["draft", "production", "replay"] = "draft"
    release_hash: str | None = None
    operational_at: str | None = None


class EventAppend(Strict):
    event: dict
    expected_revision: int = Field(ge=1)


class Replay(Strict):
    valid_at: str
    known_at: str
    profile_version: Literal["0.1"] = "0.1"
    completeness: dict | None = None


class Snapshot(Strict):
    bundle_hash: str
    subject_id: str
    valid_at: str
    known_at: str


class Draft(Strict):
    source_inventory: dict
    responses: list[dict | str] = Field(max_length=3)
    max_attempts: int = Field(default=3, ge=1, le=3)


class Comparison(Strict):
    old_hash: str
    new_hash: str
    rule_id: str
    domain: dict
    valid_at: str
    known_at: str
    budget_ms: int = Field(default=10000, ge=0, le=10000)


class ResolveIssue(Strict):
    resolution: str = Field(min_length=1)
    resolved_at: str
    expected_revision: int = Field(ge=1)


class Coverage(Strict):
    inventory: list[dict] = Field(min_length=1, max_length=10000)
    expected_revision: int = Field(ge=1)


class Build(Strict):
    cases: list[dict] = Field(min_length=1, max_length=1000)
    event_cases: list[dict] = Field(default_factory=list, max_length=1000)


class PrepareRelease(Strict):
    build_manifest_hash: str
    verification_report_hash: str
    applicability_hash: str
    valid_from: str
    valid_until: str | None
