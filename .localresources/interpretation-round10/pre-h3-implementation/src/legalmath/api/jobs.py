import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import uuid

from ..canonical import canonical, loads
from ..errors import LegalMathError


class Jobs:
    def __init__(self, db, *, recover=True):
        self.db = db
        self.processes, self.threads = {}, {}
        self.lock = threading.Lock()
        if recover:
            with db.transaction() as con:
                con.execute("UPDATE jobs SET state='FAILED',diagnostic='WORKER_INTERRUPTED',revision=revision+1 WHERE state IN ('RUNNING','QUEUED')")

    def submit(self, caller, key, kind, request):
        if kind not in ("draft", "compare"):
            raise LegalMathError("E_UNSUPPORTED_PROFILE")
        def op(con):
            ident = "job." + uuid.uuid4().hex
            rh = self.db.put(con, "job_request", {"caller": caller, "kind": kind, "request": request})
            con.execute("INSERT INTO jobs(id,kind,request_hash,state) VALUES(?,?,?,'QUEUED')", (ident, kind, rh))
            return {"job_id": ident, "state": "QUEUED"}
        return self.db.mutate(caller, key, {"op": "job", "kind": kind, "request": request}, op)

    def get(self, ident):
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
            if not row:
                raise LegalMathError("E_NOT_FOUND")
            result = dict(row)
            if row["result_hash"]:
                result["result"] = self.db.get(con, row["result_hash"])
            return result

    def cancel(self, caller, key, ident):
        def op(con):
            row = con.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
            if not row:
                raise LegalMathError("E_NOT_FOUND")
            if self.db.get(con, row["request_hash"])["caller"] != caller:
                raise LegalMathError("E_AUTHORITY")
            if row["state"] in ("QUEUED", "RUNNING"):
                con.execute("UPDATE jobs SET state='CANCELLED',revision=revision+1 WHERE id=?", (ident,))
                return {"job_id": ident, "state": "CANCELLED"}
            return {"job_id": ident, "state": row["state"]}
        result = self.db.mutate(caller, key, {"op": "cancel", "id": ident}, op)
        with self.lock:
            process = self.processes.get(ident)
            if process and process.poll() is None:
                import signal
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
        return result

    def start(self, ident, budget_seconds=30):
        if not 0 < budget_seconds <= 60:
            raise LegalMathError("E_RESOURCE_LIMIT")
        with self.lock:
            if ident in self.threads:
                return
            thread = threading.Thread(target=self.run, args=(ident, budget_seconds), daemon=True)
            self.threads[ident] = thread
        thread.start()

    def run(self, ident, budget_seconds=30):
        if not 0 < budget_seconds <= 60:
            raise LegalMathError("E_RESOURCE_LIMIT")
        with self.db.transaction() as con:
            row = con.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
            if not row or row["state"] != "QUEUED":
                return
            payload = self.db.get(con, row["request_hash"])
            con.execute("UPDATE jobs SET state='RUNNING',revision=revision+1 WHERE id=?", (ident,))
        diagnostic, result = None, None
        try:
            with tempfile.TemporaryDirectory(prefix="legalmath-job-") as td:
                inp, out = Path(td) / "request.json", Path(td) / "response.json"
                inp.write_bytes(canonical(payload))
                process = subprocess.Popen([sys.executable, "-m", "legalmath.api.worker", str(inp), str(out)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                with self.lock:
                    self.processes[ident] = process
                try:
                    import signal
                    if self.get(ident)["state"] == "CANCELLED":
                        try: os.killpg(process.pid, signal.SIGTERM)
                        except ProcessLookupError: pass
                    process.communicate(timeout=budget_seconds)
                    if process.returncode != 0 or not out.is_file():
                        diagnostic = "WORKER_FAILED"
                    else:
                        result = loads(out.read_bytes())
                except subprocess.TimeoutExpired:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    process.communicate()
                    result = {"status": "UNKNOWN", "reason": "WORKER_TIMEOUT", "authority": "NONE"}
                finally:
                    with self.lock:
                        self.processes.pop(ident, None)
        except (OSError, LegalMathError):
            diagnostic = "WORKER_FAILED"
        with self.db.transaction() as con:
            current = con.execute("SELECT state FROM jobs WHERE id=?", (ident,)).fetchone()[0]
            if current == "RUNNING":
                rh = self.db.put(con, "job_result", result) if result is not None else None
                con.execute("UPDATE jobs SET state=?,result_hash=?,diagnostic=?,revision=revision+1 WHERE id=?", ("FAILED" if diagnostic else "SUCCEEDED", rh, diagnostic, ident))
                self.db.audit(con, {"job_id": ident, "result_hash": rh, "diagnostic": diagnostic})
