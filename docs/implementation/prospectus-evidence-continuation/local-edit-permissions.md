# Local file edits and approval prompts

The user's standing permission, also present in the global AGENTS.md, covers creating and editing any file type in the current worktree, `/tmp` and `$TMPDIR` for authorized tasks. Ordinary sandboxed file tools should be used first. No separate consent is needed just because an action writes a file.

This session encountered an actual sandbox startup failure, before Python or the file operation ran:

```
error building bubblewrap command: app-server socket directory has an unsupported host mount at /mnt/wslg/distro; remove the bind-mount alias or nested mount before starting the sandbox
```

The host mount configuration has not been repaired. The saved reusable approval for the following literal command prefix provides a narrow operational fallback:

```
.venv/bin/python scripts/edit_workspace_files.py
```

The helper accepts a JSON specification file or one literal `--json` argument. It creates files or applies exact, unique text replacements; replacing an entire existing file requires its current SHA-256. Targets must resolve within this checkout, `/tmp` or the configured `$TMPDIR`. It rejects protected `.git`, `.codex` and `.agents` metadata, symlink escapes, non-files and stale edits. It validates each batch before writing, preserves modes and uses atomic per-file replacement. A batch is not a multi-file transaction. This guard prevents accidental out-of-scope edits; it is not a security boundary against someone who can alter the helper itself.

The self-test passed for create/replace, mode preservation, outside-root and symlink rejection, protected metadata, stale preconditions and batch validation. An actual edit through the saved prefix also succeeded without a new approval. Future authorized edits should keep the same literal prefix, with no shell wrapper, redirection, environment assignment or generic `python -c` command. Prefer a JSON file for complex prose: literal shell metacharacters in an inline argument may prevent approval matching even when quoted.

The existing prospectus program keeps its separately approved literal prefix:

```
.venv/bin/python scripts/run_prospectus_evidence_master.py continue
```

No global `approval_policy` or sandbox mode was weakened. The observed settings remain `on-request` and `workspace-write`. Protected locations, writes outside the authorized roots and unrelated external actions retain their normal permission requirements. A rule for one command does not approve every possible editor or shell command; once the host sandbox is fixed, ordinary sandboxed edits should work directly.
