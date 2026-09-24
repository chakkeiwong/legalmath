# Local registry, scheduler and Java package contract

The scheduler wraps the existing `assurance-monitor` command with a fixed Python
entry point, bounded ticks, process timeout and output size. Its registry adapter
copies local public-source bytes and configuration into immutable revision
directories before dispatch. The monitored source is the copied revision, so
changing a source file during a call cannot change what that call receives.
Each tick records registry/configuration hashes, command, start/end, exit status
and retained output. A failed or interrupted dispatch consumes an attempt in the
existing monitor; the wrapper does not reset that monitor or the global allowance.

Use the caller's current environment with the repository's locked dependencies
and configured provider, not an arbitrary executable or shell command from a
registry. Local source manifests are trusted operator input. Paths may refer to
retained public documents; no private bank data or credentials are examples.
The schema rejects unknown registry keys and duplicate controls. A registry may
declare either local pinned source bytes or an official URL fetched at tick time.
Unavailable remote sources remain source failures. Source hashes and resolved
bytes are recorded separately from the registry's own hash.

The package builder retains a draft bundle, generated policy source, JAR, host
caller source/classes, original bytes, conformance cases and manifests. A separate
Java host process calls the generated class through its public API. It receives a
snapshot and rule ID and returns the full typed result; it cannot turn an unknown
or conflict into a Boolean authorization. The host probe uses draft mode.

The integration exercise records a gift-rule source revision, creates successor
Java evidence and leaves an unrelated control unchanged. It also tests corrupted
package bytes, an uncertain callback, missed cadence and retry exhaustion.
Changing source evidence invalidates a control's cached assurance; it does not
automatically activate a new policy. Institution activation remains governed by
the existing release service and institution-owned identities.

To install operationally, the bank must supply its staging host/JDK and service
identity, a control registry and fact mappings, a scheduler owned by its operations
team, the source-update cadence, and release-role configuration. No service is
installed by the local acceptance command. These are concrete external inputs,
not a requirement to buy independent legal review of every circular.
