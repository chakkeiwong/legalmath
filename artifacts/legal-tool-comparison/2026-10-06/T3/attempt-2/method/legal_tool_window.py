"""Execution deadline; extensions require an explicit retained user grant."""
import time
from scripts.legal_tool_program import OUT, LIMITS, read

def deadline(state):
    original=state["started"]+LIMITS["execution_seconds"]
    path=OUT/"time-extension.json"
    if not path.exists():return original
    grant=read(path)
    if (grant.get("status")!="AUTHORIZED_BY_USER"
        or grant.get("original_started")!=state["started"]
        or grant.get("unchanged_limits")!=LIMITS
        or grant.get("seconds")!=14400
        or not grant.get("user_instruction")
        or not isinstance(grant.get("accepted_at"),(int,float))):
        raise ValueError("Invalid time-only extension; original budget preserved")
    return max(original,grant["accepted_at"]+grant["seconds"])

def remaining(state):
    return int(deadline(state)-time.time())
