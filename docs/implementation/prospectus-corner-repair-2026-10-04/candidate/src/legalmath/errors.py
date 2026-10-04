"""Stable diagnostic vocabulary shared with generated Java diagnostics."""
MESSAGES = {
    "E_SCHEMA": "Input does not conform to the schema.",
    "E_DUPLICATE_ID": "Identifier is not unique.",
    "E_REFERENCE": "Reference does not resolve.",
    "E_TYPE": "Types do not satisfy the operator contract.",
    "E_CYCLE": "Dependency graph contains a cycle.",
    "E_VERSION_TIME": "Assessment time is outside the bundle interval.",
    "E_HASH_MISMATCH": "Content does not match its recorded digest.",
    "E_INEXACT_SCALE": "Scaling would require a fractional result.",
    "E_ORDER_UNRESOLVED": "Event order has no declared authority.",
    "E_EVENT_ID_COLLISION": "Event identity is already bound to different content.",
    "E_SEQUENCE_COLLISION": "Stream sequence is already assigned.",
    "E_UNSUPPORTED_PROFILE": "Profile is not supported.",
    "E_STALE_REVIEW": "Expected revision does not match current revision.",
    "E_RELEASE_BLOCKED": "Release requirements are not satisfied.",
    "E_AUTHORITY": "Caller does not have the required authority.",
    "E_IDEMPOTENCY": "Idempotency key is already bound to another request.",
    "E_NOT_FOUND": "Requested record does not exist.",
    "E_RESOURCE_LIMIT": "Input exceeds the declared resource budget.",
    "E_TIME": "Timestamp or interval is invalid.",
    "E_EVENT_ATTRIBUTION": "Event does not belong to the declared stream.",
    "E_DEPENDENCY": "A required dependency is unresolved.",
    "E_INTEGRITY": "Persistent records fail an integrity check.",
    "E_FETCH": "Official source could not be retrieved safely.",
    "E_JOB_STATE": "Job cannot make the requested transition.",
}


def diagnostic(code, pointer=""):
    return {"code": code, "pointer": pointer, "message": MESSAGES[code]}


class LegalMathError(Exception):
    def __init__(self, code, pointer="", *, details=None):
        super().__init__(MESSAGES[code])
        self.code, self.pointer, self.details = code, pointer, details

    def envelope(self):
        return {"error": self.code, "diagnostics": [diagnostic(self.code, self.pointer)]}


class BoundaryError(LegalMathError):
    def envelope(self):
        return {"error": "BOUNDARY_ERROR", "diagnostics": [diagnostic(self.code, self.pointer)]}
