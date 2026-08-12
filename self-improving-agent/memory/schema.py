from dataclasses import dataclass, asdict
from typing import Literal, Optional
import json

@dataclass
class AttemptOutcome:
    task_id: str
    attempt_number: int
    plan: str
    diff: str
    test_exit_code: int
    test_stdout: str
    verdict: Literal["accepted", "rejected", "flagged"]
    rejection_reason: Optional[str]
    timestamp: str
    category: str = "logic_bug"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AttemptOutcome":
        d = dict(data)
        if d.get("rejection_reason") == "":
            d["rejection_reason"] = None
        return cls(**d)
