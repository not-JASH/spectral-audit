"""Small validated description of a computed estimator quantity."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EstimatorContract:
    method_id: str
    measurement_kind: str
    preprocessing: str
    support_kind: str
    normalization: str
    population_target_kind: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "method_id",
            "measurement_kind",
            "preprocessing",
            "support_kind",
            "normalization",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be nonempty")
        if self.population_target_kind is not None and (
            not isinstance(self.population_target_kind, str)
            or not self.population_target_kind.strip()
        ):
            raise ValueError("population_target_kind must be nonempty or null")
