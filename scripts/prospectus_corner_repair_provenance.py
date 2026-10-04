"""Hash bindings for the repair runner and all local evidence inputs."""
from scripts import run_prospectus_corner_repair as m

def orchestration():
    paths=set((m.ROOT/"scripts").glob("*corner_repair*.py"))
    paths.add(m.ROOT/"scripts/prospectus_jurisdiction_study.py")
    return {m.relative(p):m.sha(p) for p in sorted(paths)}

def inputs():
    paths={m.PLAN}
    # Both the worker's preserved sources and the isolated test resources.
    for name in ("docs/prospectus/corner-cases-2026-10-04",
                 "docs/prospectus/jurisdiction-2026-10-04",
                 "docs/prospectus/difficulty-2026-10-04",
                 "docs/implementation/prospectus-corner-cases-2026-10-04/run-001",
                 "docs/implementation/prospectus-difficulty-2026-10-04/run-001"):
        paths.update(p for p in (m.ROOT/name).rglob("*") if p.is_file())
    for name in ("docs","src","tests"):
        paths.update(p for p in (m.CANDIDATE/name).rglob("*")
                     if p.is_file() and p.suffix not in (".py",".pyc") and "__pycache__" not in p.parts)
    for folder in (m.OLD,m.ROOT/"docs/implementation/prospectus-difficulty-2026-10-04"):
        paths.update(p for p in folder.glob("*.json") if p.name not in {"verification.json","archive-verification.json"})
    for name in ("SOURCE-REVIEW.md",):
        p=m.OUT/name
        if p.exists():paths.add(p)
    new=m.ROOT/"docs/prospectus/corner-repair-2026-10-04"
    paths.update(p for p in new.rglob("*") if p.is_file())
    return {m.relative(p):m.sha(p) for p in sorted(paths)}
