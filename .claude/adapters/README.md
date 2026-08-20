# Host adapters

These manifests bind the canonical `.claude/` layer to a host runtime. They do
not duplicate skills, hooks, rules, or workflow policy. A manifest is evidence
of an intended mapping, not evidence that the mapping works.

`native` means the repository has a checked configuration for the host.
`bridge-required` means the host must invoke the canonical bridge before the
capability may be used. It is not a support claim. `unsupported-refuse` means
the host must stop the dependent action rather than emulate approval, a hook,
or delegation by guess.

The source of truth for the capability names and failure rule is
`../portability/capabilities.json`. The bridge's payload, ordering, and exit
semantics remain in `docs/harness-hook-bridge.md`.

No adapter may call a host "supported" until its manifest's conformance command
has passed against that host. The repository currently proves the Claude Code
configuration structurally. Codex and generic-agent are integration targets;
they must not be represented as runtime-verified until their named conformance
tests exist and pass.
