from legalmath.api.jobs import Jobs
from legalmath.storage import Database


def request(case):
    return {"source_inventory": {"source_spans": case["bundle"]["source_spans"]}, "responses": [case["bundle"]], "max_attempts": 1}


def test_persisted_worker_result_and_cancel(db, case):
    jobs = Jobs(db)
    job = jobs.submit("author", "submit", "draft", request(case))
    jobs.run(job["job_id"])
    result = jobs.get(job["job_id"])
    assert result["state"] == "SUCCEEDED" and result["result"]["authority"] == "NONE"
    second = jobs.submit("author", "submit2", "draft", request(case))
    assert jobs.cancel("author", "cancel", second["job_id"])["state"] == "CANCELLED"
    jobs.run(second["job_id"])
    assert jobs.get(second["job_id"])["result_hash"] is None
    restarted = Jobs(Database(db.root))
    assert restarted.get(job["job_id"])["result_hash"] == result["result_hash"]
    assert restarted.submit("author", "submit", "draft", request(case)) == job


def test_restart_never_promotes_interrupted_job(db, case):
    jobs = Jobs(db)
    job = jobs.submit("author", "submit", "draft", request(case))
    with db.transaction() as con:
        con.execute("UPDATE jobs SET state='RUNNING' WHERE id=?", (job["job_id"],))
    resumed = Jobs(Database(db.root)).get(job["job_id"])
    assert resumed["state"] == "FAILED" and resumed["diagnostic"] == "WORKER_INTERRUPTED"
    assert resumed["result_hash"] is None


def test_worker_deadline_cannot_be_a_proof(db, case):
    jobs = Jobs(db)
    job = jobs.submit("author", "submit", "draft", request(case))
    jobs.run(job["job_id"], budget_seconds=0.001)
    result = jobs.get(job["job_id"])
    assert result["result"]["status"] == "UNKNOWN" and result["result"]["authority"] == "NONE"


def test_worker_launch_failure_is_persisted(db, case, monkeypatch):
    def unavailable(*args, **kwargs): raise OSError("Synthetic process launch failure")
    monkeypatch.setattr("legalmath.api.jobs.subprocess.Popen", unavailable)
    jobs = Jobs(db)
    job = jobs.submit("author", "submit", "draft", request(case))
    jobs.run(job["job_id"])
    result = jobs.get(job["job_id"])
    assert result["state"] == "FAILED" and result["diagnostic"] == "WORKER_FAILED"
    assert result["result_hash"] is None
