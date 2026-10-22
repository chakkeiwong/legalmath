"""Single prospectus task authority; existing phase runners are delegated workers."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.execution_authority import Authority


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "status", "admit", "run", "record", "refresh", "resume", "revise", "worker"))
    parser.add_argument("--task")
    parser.add_argument("--attempt")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--proposal")
    parser.add_argument("--review")
    parser.add_argument("--lease-fd", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    authority = Authority(ROOT)
    if args.action == "revise":
        if not args.proposal or not args.review:
            parser.error("Revision requires --proposal and --review")
        result = authority.revise(args.proposal, args.review)
    elif args.action in {"record", "worker"}:
        if not args.attempt:
            parser.error("This action requires --attempt")
        result = authority.worker(args.attempt, args.lease_fd) if args.action == "worker" else authority.record(args.attempt)
    elif args.action in {"admit", "run"}:
        result = getattr(authority, args.action)(args.task)
    elif args.action == "check":
        program, tasks, _ = authority.spec()
        result = {"status": "PASS", "revision": program["revision"],
                  "obligations": len(program["obligations"]), "tasks": len(tasks)}
    else:
        result = getattr(authority, args.action)()
    if args.action == "run" and result.get("execution") == "RUNNING":
        print(json.dumps(result), flush=True)
        result = authority.wait_worker()
    if "tasks" in result and isinstance(result["tasks"], list) and not args.full:
        result = {key: result[key] for key in ("revision", "next_task", "running", "completion", "current_build", "program_complete")}
    elif "task_spec" in result and not args.full:
        result = {key: result[key] for key in ("task", "attempt", "reason")}
        task = authority.spec()[1][result["task"]]
        result["dossier"] = task["dossier"]
        result["handler"] = task["handler"]
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
