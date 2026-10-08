CREATE TABLE interpretation_runs (
 id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES identities(id),
 packet_hash TEXT NOT NULL REFERENCES records(hash), source_key TEXT NOT NULL,
 hash TEXT NOT NULL REFERENCES records(hash), invalidated INTEGER NOT NULL DEFAULT 0,
 cancelled INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE interpretation_records (
 run_id TEXT NOT NULL REFERENCES interpretation_runs(id), kind TEXT NOT NULL,
 id TEXT NOT NULL, hash TEXT NOT NULL REFERENCES records(hash),
 PRIMARY KEY(run_id,kind,id)
);
CREATE TABLE interpretation_history (
 sequence INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES interpretation_runs(id),
 kind TEXT NOT NULL, id TEXT NOT NULL, hash TEXT NOT NULL REFERENCES records(hash)
);
CREATE TABLE interpretation_bindings (
 bundle_hash TEXT NOT NULL REFERENCES bundles(hash), run_id TEXT NOT NULL REFERENCES interpretation_runs(id),
 candidate_id TEXT NOT NULL, candidate_hash TEXT NOT NULL REFERENCES records(hash),
 PRIMARY KEY(bundle_hash,run_id,candidate_id)
);
CREATE TABLE interpretation_sources (
 source_key TEXT PRIMARY KEY, packet_hash TEXT NOT NULL REFERENCES records(hash)
);
CREATE TABLE interpretation_outbox (
 action_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES interpretation_runs(id),
 signature TEXT NOT NULL, lease_until TEXT, fence INTEGER NOT NULL DEFAULT 0,
 UNIQUE(run_id,signature)
);
CREATE TABLE interpretation_workers (
 run_id TEXT PRIMARY KEY REFERENCES interpretation_runs(id), owner TEXT NOT NULL,
 lease_until TEXT NOT NULL, fence INTEGER NOT NULL
);
