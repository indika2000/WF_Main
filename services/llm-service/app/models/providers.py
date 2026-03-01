from pydantic import BaseModel


class ProviderInfo(BaseModel):
    name: str
    capabilities: list[str]  # ["text", "image", "streaming"]
    status: str  # "available" | "unavailable" | "no_api_key"
    models: list[str]


class ProviderStatus(BaseModel):
    name: str
    status: str
    latency_ms: float | None = None
    error: str | None = None
