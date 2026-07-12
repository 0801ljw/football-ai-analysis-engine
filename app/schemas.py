from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Match(BaseModel):
    id: str
    num: str
    home: str
    away: str
    kickoff: str
    stage: str
    venue: str
    source: str = "demo"


class GenerateRequest(BaseModel):
    match_id: str = Field(min_length=1)
    theme: str = Field(default="light")


class OddsFetchRequest(BaseModel):
    nums: str | list[str]
    dry_run: bool = True
    out_path: str | None = None


class OddsInspectRequest(BaseModel):
    odds_path: str


class OddsDiscoverRequest(BaseModel):
    nums: str | list[str]
    timeout: int | None = Field(default=None, gt=0)


class ReportBuildRequest(BaseModel):
    odds_path: str
    out_path: str
    title: str = Field(min_length=1)
    theme: str = Field(default="dark")
    intel_path: str | None = None
    dry_run: bool = True


class RunCreateRequest(BaseModel):
    nums: str | list[str]
    title: str = Field(min_length=1)
    theme: str = Field(default="dark")
    dry_run: bool = True
    background: bool = False
    timeout: int | None = Field(default=None, gt=0)


class DesktopApiKeyUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=False)

    api_key: str = Field(min_length=1, max_length=4096)

    @field_validator("api_key")
    @classmethod
    def api_key_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("api_key must be a non-empty string")
        return value


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=1)
    role: str = Field(default="user")
    plan: str = Field(default="free")
    run_quota: int = Field(default=20, ge=0)


class UserUpdateRequest(BaseModel):
    role: str | None = None
    plan: str | None = None
    run_quota: int | None = Field(default=None, ge=0)
    active: bool | None = None


class ContentCopy(BaseModel):
    title: str
    body: str
    hashtags: list[str]


class ScoreCandidate(BaseModel):
    score: str
    probability: float
    note: str


class EngineMeta(BaseModel):
    source: str
    skill_path: str
    skill_available: bool
    mode: str


class Report(BaseModel):
    match: Match
    probabilities: dict[str, float]
    score_candidates: list[ScoreCandidate]
    market_notes: list[str]
    risk_flags: list[str]
    content_copy: ContentCopy
    compliance_status: dict
    engine: EngineMeta
