# Authorization and command approval

The current user instruction is: “you have another 500 calls. continue”.
It authorizes the additional grant recorded in
`artifacts/assurance-new-grant/2026-09-29/grant.json`. The grant is limited to
500 new provider invocations and preserves both exhausted predecessors.

The session permission mechanism approved and saved this narrow command prefix:

```json
[".venv/bin/python", "scripts/run_assurance_new_grant.py"]
```

The approved command runs from the repository root. Its model calls still need
a global grant reservation and any applicable task/issue reservation. A shell
approval does not increase those limits. The provider runs fresh isolated
contexts with tools disabled; the task contains public source text.

No change to protected global configuration files was required. No external
messages, repository push, product deployment or institutional approval was
performed as part of this increment.
