from dataclasses import dataclass


@dataclass
class Config:
    max_questions: int = 0       # 0 = unlimited
    time_limit_seconds: int = 0  # 0 = unlimited
