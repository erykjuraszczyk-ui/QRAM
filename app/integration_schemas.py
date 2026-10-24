from pydantic import BaseModel, ConfigDict, Field


class ExperimentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    qubits: int = Field(default=2, ge=1, le=12)
    shots: int = Field(default=1024, ge=1, le=100000)
    label: str = Field(default="hadamard_all", pattern="^hadamard_all$")
