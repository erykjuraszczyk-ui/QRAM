from pydantic import BaseModel, Field, ConfigDict


class MemoryWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    address: int = Field(ge=0, description="Zero-based memory address")
    value: str = Field(min_length=1, max_length=4096)


class MemoryWriteResponse(BaseModel):
    address: int
    value: str
    written: bool


class QuantumDemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    qubits: int = Field(default=2, ge=1, le=12)
    operation: str = Field(default="hadamard_all", pattern="^hadamard_all$")
