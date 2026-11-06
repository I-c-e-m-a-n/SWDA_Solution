# Security boundaries and limitations

This is a governance simulation with synthetic data. No production approval, independent
administration, signature, protected registry, private route, UC grant, OAuth M2M or
identity provider is implemented. A person who can edit local code/policy can change the
simulation. Hash binding detects drift against the checked-in fixture; it does not make
the filesystem immutable or attest the running interpreter/dependencies in memory.
Dependencies are hash-verified at install, not cryptographically attested at each call.

For stdio, the operator trusts the host/process that launches the server and owns its
configuration. For HTTP, loopback accessibility gives no per-caller identity: all local
processes share the simulated service scope. Client metadata, names, headers and text
are never used to grant authority. No public binding or remote client URL is offered.
Origin/Host checks mitigate browser/DNS rebinding attacks but are not authentication.
Enterprise deployment is blocked pending the existing A1/B identity/network gates.

Only `recommend_service` is public. All business/wrapper fields are validated before
execution; no request can provide a file path, catalogue URL, SQL, shell command or
internal tool name to execute. Text is tokenized, never evaluated or interpreted by an
LLM. Injection-like words may still affect lexical routing, so inert execution does not
mean semantic resistance or adequate classification quality for citizens.

Fresh fixture reads and source/schema hashing protect every new discovery/call. Only
PUBLISHED with exact version, digest, scopes, schema and nonexpired UTC approval can run.
There is no positive cache. A listing cannot authorize a later call. Policy read errors
fail closed. Tests mutate only temporary fixture copies. Atomic rename of a reviewed
fixture is recommended for local operator changes; partial reads fail closed. No claim
of multi-process linearizability, signed decisions or immediate cancellation of an
in-flight invocation is made. Clock integrity/rollback protection remains an enterprise
requirement; expiry uses the operator's UTC clock and is injectable in tests.

Resource controls: business text 2000 characters; IDs 64 characters with safe alphabet;
30 catalogue entries; bounded 64 KiB JSON reads; result count three; 16 KiB HTTP bodies
and results; three-second application deadline; four concurrent worker slots. Worker
cancellation is cooperative at the response boundary: a timed-out thread may finish its
read-only task. Concurrency limits are not a durable quota, distributed rate limiter or
OS resource isolation. Stdio transport parsing is SDK-owned and a trusted local host
must bound input frames before sending; business validation is not a universal wire
DoS defence. No public, multi-tenant or hostile-local-user deployment is supported.

Audit logging emits fixed-field metadata to stderr, with no request text, client IDs,
arbitrary tool names, raw exceptions, tokens or user-provided request IDs. It does not
persist to a tamper-proof append-only audit store, detect log loss, or configure enterprise
retention/redaction. SDK payload logging/tracing is not enabled by this application.
External telemetry auto-instrumentation and host log sinks must be reviewed separately.
The protocol client must inspect MCP errors, not assume HTTP 403 for policy denial.

Native macOS execution remains unverified until a macOS Actions job or actual local Mac
run passes. Linux tests do not prove Unity Gateway interoperability, production
revocation propagation, source-data quality, fairness, recovery objectives or costs.
