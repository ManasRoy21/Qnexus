from pydantic import BaseModel, ConfigDict, Field, model_validator


class Experiment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pulse_count: int = Field(default=10_000, ge=200, le=20_000)
    distance_km: float = Field(default=25, ge=0, le=100)
    fiber_loss_db_per_km: float = Field(default=0.2, ge=0, le=1)
    detector_efficiency: float = Field(default=0.1, gt=0, le=1)
    baseline_qber: float = Field(default=0.01, ge=0, le=0.5)
    test_fraction: float = Field(default=0.3, gt=0, lt=1)
    authentication_threshold: float = Field(default=0.06, ge=0, lt=0.5)
    verification_threshold: float = Field(default=0.12, gt=0, le=0.5)
    seed: int = Field(default=42, ge=0, le=2**31 - 1)

    @model_validator(mode="after")
    def ordered_thresholds(self):
        if self.verification_threshold <= self.authentication_threshold:
            raise ValueError("Verification threshold must exceed authentication threshold")
        return self


class SignRequest(BaseModel):
    simulation_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=4096)


class VerifyRequest(SignRequest):
    signature: str = Field(pattern=r"^[0-9a-f]{64}$")


class AttackRequest(BaseModel):
    simulation_id: str = Field(min_length=1, max_length=100)
    intensity: float = Field(default=1, ge=0, le=1)


class SweepRequest(BaseModel):
    config: Experiment = Field(default_factory=Experiment)
    minimum: float = Field(default=0, ge=0, le=1)
    maximum: float = Field(default=1, ge=0, le=1)
    step: float = Field(default=0.1, gt=0, le=1)

    @model_validator(mode="after")
    def bounded_sweep(self):
        if self.maximum < self.minimum:
            raise ValueError("Maximum must be at least minimum")
        if (self.maximum - self.minimum) / self.step > 20 + 1e-9:
            raise ValueError("At most 21 sweep points are supported")
        return self


class BoundRequest(BaseModel):
    n: int = Field(ge=1, le=1_000_000)
    epsilon: float = Field(default=0.035, gt=0, le=1)
    observed_qber: float = Field(default=0, ge=0, le=1)
