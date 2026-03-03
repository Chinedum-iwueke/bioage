"""Placeholder schema types for bioage inputs/results."""

from dataclasses import asdict, dataclass


@dataclass
class ClientMetadata:
    prepared_for: str = "Demo Client"
    date: str = "1970-01-01"
    client_id: str = "CLIENT-DEMO"
    security_key: str = "SEC-DEMO"
    consultant_id: str = "CONSULTANT-DEMO"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DemoResult:
    disclaimer: str = (
        "Educational wellness estimation only. This report is not a diagnosis, "
        "medical advice, or treatment plan."
    )
    actual_age: int = 40
    biological_age: int = 42
    arterial_stiffness_label: str = "Placeholder"
    bmi_label: str = "Placeholder"
    systolic_label: str = "Placeholder"
    diastolic_label: str = "Placeholder"

    def to_dict(self) -> dict:
        return asdict(self)
