PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE blobs (
  sha256 TEXT PRIMARY KEY CHECK(length(sha256)=64),
  media_type TEXT NOT NULL, byte_count INTEGER NOT NULL CHECK(byte_count>=0),
  relative_path TEXT NOT NULL UNIQUE
);
CREATE TABLE source_revisions (
  revision_id TEXT PRIMARY KEY, source_id TEXT NOT NULL,
  raw_sha256 TEXT NOT NULL REFERENCES blobs(sha256),
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
CREATE TABLE bundles (
  hash TEXT PRIMARY KEY REFERENCES blobs(sha256), parent_hash TEXT REFERENCES bundles(hash),
  state TEXT NOT NULL CHECK(state IN ('DRAFT','IN_REVIEW','APPROVED','RELEASED','RETIRED')),
  revision INTEGER NOT NULL CHECK(revision>0)
);
CREATE TABLE interpretations (
  bundle_hash TEXT NOT NULL REFERENCES bundles(hash), id TEXT NOT NULL,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json)), PRIMARY KEY(bundle_hash,id)
);
CREATE TABLE issues (
  id TEXT PRIMARY KEY, bundle_hash TEXT NOT NULL REFERENCES bundles(hash),
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
CREATE TABLE review_events (
  id INTEGER PRIMARY KEY, bundle_hash TEXT NOT NULL REFERENCES bundles(hash),
  revision INTEGER NOT NULL, payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
  UNIQUE(bundle_hash,revision)
);
CREATE TABLE snapshots (
  hash TEXT PRIMARY KEY REFERENCES blobs(sha256), subject_id TEXT NOT NULL,
  valid_at TEXT NOT NULL, known_at TEXT NOT NULL
);
CREATE TABLE evaluations (
  result_hash TEXT PRIMARY KEY REFERENCES blobs(sha256),
  bundle_hash TEXT NOT NULL REFERENCES bundles(hash),
  snapshot_hash TEXT NOT NULL REFERENCES snapshots(hash),
  request_json TEXT NOT NULL CHECK(json_valid(request_json))
);
CREATE TABLE streams (
  id TEXT PRIMARY KEY, revision INTEGER NOT NULL CHECK(revision>=0),
  ordering_authority TEXT
);
CREATE TABLE events (
  id TEXT PRIMARY KEY, stream_id TEXT NOT NULL REFERENCES streams(id),
  sequence INTEGER NOT NULL CHECK(sequence>0),
  occurred_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
  payload_hash TEXT NOT NULL REFERENCES blobs(sha256), UNIQUE(stream_id,sequence)
);
CREATE TABLE replay_results (
  hash TEXT PRIMARY KEY REFERENCES blobs(sha256), stream_id TEXT NOT NULL REFERENCES streams(id),
  valid_at TEXT NOT NULL, known_at TEXT NOT NULL, supersedes_hash TEXT REFERENCES replay_results(hash)
);
CREATE TABLE jobs (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, state TEXT NOT NULL,
  request_hash TEXT NOT NULL REFERENCES blobs(sha256), result_hash TEXT REFERENCES blobs(sha256)
);
CREATE TABLE idempotency (
  caller_id TEXT NOT NULL, key TEXT NOT NULL, request_hash TEXT NOT NULL,
  response_json TEXT NOT NULL CHECK(json_valid(response_json)), PRIMARY KEY(caller_id,key)
);
CREATE TABLE audit_events (
  id INTEGER PRIMARY KEY, previous_hash TEXT, hash TEXT NOT NULL UNIQUE,
  payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
