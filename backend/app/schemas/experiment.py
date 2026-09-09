from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExperimentCreate(BaseModel):
    name: str
    stream_id: str
    protocol: str
    network_profile: str = "normal"
    encoder_params: str | None = None
    avg_latency_ms: float | None = None
    max_latency_ms: float | None = None
    p50_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    p99_latency_ms: float | None = None
    sample_count: int = 0
    measurement_method: str | None = None
    bitrate_kbps: float | None = None
    fps: float | None = None
    stutter_count: int = 0


class ExperimentRead(ExperimentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
