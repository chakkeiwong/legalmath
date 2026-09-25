from dataclasses import dataclass
from typing import Protocol


class Provider(Protocol):
    def propose(self, prompt: dict, attempt: int) -> str | dict: ...


@dataclass
class StubProvider:
    responses: list

    def propose(self, prompt, attempt):
        if not self.responses:
            return {"error": "No fixture response configured"}
        return self.responses[min(attempt, len(self.responses) - 1)]
