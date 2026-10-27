# Local evidence retention

The user explicitly requested that the approximately 21 GB local evidence
collection not be committed to GitHub. Original files remain in the worktree.
The compressed JSON-lines inventory contains paths, sizes and SHA-256 identities,
not document bodies, provider requests, responses or downloaded runtimes.
`retention.json` records its exact population, identity and limitations.

Source, tests, plans, reviews and selected compact result records are committed.
Previously tracked evidence remains tracked. Large repeated execution snapshots,
model payloads, downloaded tools, local research clones and prospectus source
downloads are excluded. Their exclusion is explicit; a clean Git checkout does
not mean the execution archive has been backed up remotely. Nested downloaded
repositories are identified by local directory and commit where available; the
inventory does not claim to hash their complete contents.

To recover an execution on another machine, restore the exact excluded bytes
from a separate local backup into the recorded relative paths and verify their
hashes. A fresh Git clone alone is insufficient to replay historical campaigns.
No source or evidence has been deleted or substituted to achieve cleanliness.
