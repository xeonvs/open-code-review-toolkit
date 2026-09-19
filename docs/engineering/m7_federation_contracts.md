# Governed MCP federation contracts

M7 keeps OCR as the only model/review loop. The toolkit mediates external tool
use; upstream services remain responsible for tenant/object authorization. This
contract supersedes M5's external adapter acquisition architecture only. Internal
repository evidence, immutable forge acquisition and the separate context store
retain their existing owners and admission rules.

## Ownership and startup

The internal evidence MCP is mandatory and cannot be replaced by operator
configuration. A separate federation gateway exports only operator-allowlisted
tools. Configuration parses the registry; federation owns schema validation,
transport, dispatch, cache and lifecycle; review_runner coordinates admission;
shared receipt/reporting owners interpret content-free results.

Before OCR starts, an owned background async worker connects to configured
upstreams, discovers and freezes their allowlisted tools, validates schemas and
metadata, and reports readiness. The same sessions remain alive for execution.
OCR connects through a minimal fixed stdio relay to a private Unix socket. The
socket directory is owner-only and the session accepts one bound client. No
upstream secrets are serialized into OCR configuration or relay arguments.

Shutdown stops admission, settles/cancels requests, closes sessions, terminates
and reaps owned process groups, clears caches and joins the worker. Only verified
cleanup permits finalized receipt admission. Unknown cleanup blocks publication.
This is process ownership, not a sandbox against an operator executable escaping
its process group or a compromised host.

## Registry version 2

`OCR_MCP_SERVERS_JSON` is a strict object with `version: 2` and a `servers` object.
Each server has `transport`, `tools`, optional HTTPS `auth` and `headers_from`.
HTTPS transport is `{type: https, url: ...}`. Local-only stdio transport is
`{type: stdio, command: ..., args: [...], env_from: {...}}`; the executable is an
absolute operator-selected path and env_from maps child names to source names.
GitLab accepts only HTTPS. An empty registry configures no external services.

Tool keys are upstream tool names; values hold optional `assurance` (default
`advisory`, or explicit `review_read`) and `resource_origins`. Origins default to
the configured HTTPS endpoint origin; explicit additional origins authorize only
URL-shaped arguments, never toolkit link retrieval. Registry fields contain no
credential values. Auth uses scheme `Bearer` and token_from naming an environment
variable; headers_from maps header names to variable names.

Server/tool components start with an ASCII letter, contain ASCII letters, digits,
underscore or hyphen, and cannot contain `__`. Exported `server__tool` aliases are
at most 64 characters and cannot collide with toolkit tools. Unknown fields,
unsafe combinations, missing secrets/tools and unsupported schemas fail before
model execution. Server metadata and notifications cannot expand the frozen
inventory or promote assurance.

## Dependency and protocol boundary

The federation package uses the official MCP SDK v2, JSON Schema validator,
httpx2 and anyio. This is the documented exception to the zero-runtime-dependency
baseline; SDK extras and another framework are unnecessary. Reporting and pure
receipt validation must not import the SDK or start transport machinery.

SDK major versions are not wire protocol revisions. Negotiate separately with
OCR and each upstream, using SDK automatic modern discovery/legacy initialization.
Qualified SDK v1 and v2 peers run in separate environments. Do not require OCR to
adopt Python SDK v2. Unsupported revisions or optional capabilities fail explicitly.
No sampling, roots, elicitation, OAuth, server-directed headers or model retries
are enabled by federation.

For HTTPS use SDK transport with a bounded raw-byte wrapper, explicit timeouts,
connection limits, trust_env disabled, max_redirects zero and no cookie authority.
Reject compressed bodies before decoding. Observe cleanup HTTP results independently
because SDK exit alone does not prove successful server-session deletion. Stdio
uses the public SDK transport interface with toolkit-owned bounded framing and
process cleanup; the stock unbounded line reader is not an admission boundary.

## Bounded schema and calls

Initial limits are fixed, named product defaults: 16 servers, 128 exported tools,
64 KiB registry, 16 KiB per schema, schema depth 12, 512 nodes, 64 object properties,
32 enum values and eight combinator branches. Reject references, regex constraints,
dynamic/executable schema extensions and unsupported keywords rather than ignoring
them. Validate the admitted JSON Schema profile before model execution.

Arguments have 32 KiB, depth 16 and 1,024-node bounds. Responses have 256 KiB,
128K-character and 128-item limits, with 2 MiB admitted run aggregate. There are
64 model calls, concurrency four, 30-second call deadlines and a 300-second run
deadline. Wire traffic is independently bounded to 256 requests and 8 MiB. Cache
holds at most 32 entries and 1 MiB. Metadata totals at most 128 KiB.

Every argument crosses schema/origin/outbound DLP before upstream dispatch. Every
response crosses content-kind/bounds/inbound DLP before delivery. Descriptions
are external data too. Rejected, truncated or incomplete content is never returned
partially. Returned links remain inert. Reuse context.dlp rather than another
secret/PII detector; fixed authority instructions and lifecycle code prevent
external text from becoming policy or publication authority.

Cache only fully admitted successes, using server/tool/canonical arguments within
one run. Each caller, including a cache hit or shared-flight waiter, gets its own
attempt and terminal outcome and consumes delivery budgets. One waiter's cancellation
does not silently cancel the other waiters' shared operation.

## Receipts and outcomes

`ocr.federation/v1` is a closed content-free finalized receipt bound to run_id.
It includes cleanup state and a mapping of exported aliases to server, assurance,
attempted, completed, denied, failed, timed_out, dlp_rejected, oversized, cache_hits
and single_flight counts. Configured unused aliases have zero counts. No arguments,
URLs, response content, paths, identifiers or raw errors enter this receipt.

Each gateway attempt closes exactly once. OCR attempt counts are independent and
must match per alias; malformed arguments rejected by OCR before dispatch cause a
mismatch, not a fabricated gateway count. Used advisory tools, known failed/denied
calls or accounting mismatch make an otherwise admissible review comment-only.
Missing/corrupt/unfinalized receipts and cleanup uncertainty block normal publication.
Unused configuration and successful review_read use do not independently block
approval; every pre-existing approval gate remains enforced.

Stage-aware publication DLP is separately owned by shared reporting contracts:
OCR coverage, publication projection and posting counters remain distinct. Source
classes are recorded at forbidden-value registration, never inferred from retained
rejected text. Source-class counts are bounded overlapping item counts, not an
alternative total omission count. Local output shares validators and formatter
without claiming GitLab protection, publication or approval.

## Legacy migration

Current protected policy v4 does not accept `references`. Policy v1-v3 remains
parse-only for migration: its safe discussion, remediation, CI, budget and
guidance fields retain their established behavior, while references never invoke
a command, endpoint or adapter. Optional references are unavailable and skipped.
Any required reference makes the run required-degraded and comment-only, including
a references-only policy. One private migration warning and at most one bounded
Technical-details warning are emitted per accepted legacy policy.

`OCR_REVIEW_CONTEXT_ADAPTERS_JSON`, its request/response protocol,
`OCR_MCP_REPLACE`, inherited direct OCR MCP entries and legacy registry shapes
fail closed. Operators migrate reviewed external tools into registry v2 and
reassess schemas, origins, assurance and credentials; federation is model-directed
and is not a field-for-field conversion of pre-OCR adapter records.

## DLP mode

`OCR_DLP_ENABLED` is resolved once before acquisition and defaults to enabled.
The strict boolean families are `true|1|yes|on` and `false|0|no|off`,
case-insensitively; another value fails before OCR. False bypasses context and
federation ingress/egress DLP plus publication DLP only. Schema, size, time,
origin, identity, evidence, cleanup and posting-transaction gates remain active.

Disabled mode emits a prominent private warning and bounded Technical-details
warning, records the effective state in receipt v9, and is always comment-only.
It may expose sensitive material through service/model egress, local Markdown or
GitLab publication, and later re-enablement cannot retract prior disclosure.
Operators should diagnose locally with `--preserve-private-artifacts` before this
escape hatch. Local and GitLab use the same resolved value and formatter.

## Acceptance

Real TLS, stdio child processes, socket relay, installed artifacts and the exact
qualified OCR must cross production owners. Cover mixed SDK peers, startup failures,
malformed-before-dispatch, bounds before parsing, DLP, origins, cache/cancellation,
cleanup, hostile receipts, migration and local/GitLab reporting parity. Synthetic
model peers establish protocol integration, not configured model quality.
