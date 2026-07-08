"""Runtime configuration. All of it is mutable in memory via POST /api/config."""
import os

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _Strict(BaseModel):
    # extra="forbid" so a typo in POST /api/config is a 422, not a silent no-op
    model_config = ConfigDict(extra="forbid")


class RateLimitConfig(_Strict):
    capacity: int = Field(60, ge=1)
    refill_rate: float = Field(30.0, gt=0)  # tokens per second


class CacheConfig(_Strict):
    max_entries: int = Field(1000, ge=1)
    ttl_seconds: float = Field(30.0, gt=0)
    max_body_bytes: int = Field(1_048_576, ge=1)  # bigger bodies stream through uncached


class ChaosConfig(_Strict):
    latency_enabled: bool = False
    min_delay_ms: int = Field(100, ge=0)
    max_delay_ms: int = Field(500, ge=0)
    error_injection_enabled: bool = False
    failure_rate_percentage: float = Field(0.1, ge=0.0, le=1.0)  # 0.0-1.0, despite the name
    error_status_codes: list[int] = [500, 502, 503, 504]

    @field_validator("error_status_codes")
    @classmethod
    def _codes(cls, v: list[int]) -> list[int]:
        if not v or any(not 400 <= c <= 599 for c in v):
            raise ValueError("error_status_codes must be a non-empty list of 4xx/5xx codes")
        return v

    @model_validator(mode="after")
    def _range(self) -> "ChaosConfig":
        if self.min_delay_ms > self.max_delay_ms:
            raise ValueError("min_delay_ms must be <= max_delay_ms")
        return self


class AppConfig(_Strict):
    target_url: str | None = None
    rate_limit: RateLimitConfig = RateLimitConfig()
    cache: CacheConfig = CacheConfig()
    chaos: ChaosConfig = ChaosConfig()

    @field_validator("target_url")
    @classmethod
    def _url(cls, v: str | None) -> str | None:
        v = (v or "").strip().rstrip("/")
        if not v:
            return None
        if not v.startswith(("http://", "https://")):
            raise ValueError("target_url must start with http:// or https://")
        return v

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(target_url=os.environ.get("LOCALGATE_TARGET_URL"))
