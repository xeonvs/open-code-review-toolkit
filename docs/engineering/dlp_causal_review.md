# DLP causal review

## 0.14.6: safe presentation and exact material boundaries

The authenticated public corpus is the toolkit tree at immutable revision
`72abb6039f82d0601d8207326c1ddff27caf7413`: 121583 units in 452 files.
The published 0.14.5 baseline has 2192 rejected role observations. Final
post-review replay retains 1510: 708 former rejections are admitted and 26
conservative source-boundary rejections are added. No annotated protection is
lost, and retained primary reasons do not change. These are observation
counts, not a false-positive rate or a universal precision/recall claim.

| Former primary detector | Admissions | Basis |
| --- | ---: | --- |
| HTML-like tokens | 273 | Original and hidden material checks followed by visible inert presentation |
| HTML comments | 97 | Complete content remains checked and visible; no hidden execution |
| Markdown destinations | 320 | Independent material and destination validation; images become ordinary links |
| Email | 6 | Exact original Markdown opening delimiters, not a repeated-text search or domain exception |
| Credential-like material | 12 | Complete formal-reference carriers agree in raw and encoded form; continuations remain checked |

All 1611 originally unannotated observations have individual causal dispositions:

| Disposition | Observations | Meaning |
| --- | ---: | --- |
| Confirmed benign | 583 | Reproduced errors corrected by presentation, delimiter positions or complete carrier proof |
| Expected protection | 891 | Address forms, nonempty credential/auth material, explicit contact shapes or unsafe controls remain protected, including synthetic fixtures |
| Conservative ambiguity | 137 | 101 unqualified credential roles, 27 incomplete numeric roles, eight literal-delimiter roles and one incomplete destination fragment lack the specified proof |

Every conservative entry retains its concrete missing evidence. Classification
does not make that evidence available or suppress scanning. The 26 additional
rejections concern quoted absent/masked values inside unqualified calls and
comparisons. They are not claims that 26 secrets were found: neither a separator
nor a partial quote inventory proves independent complete data. A repository,
test path, function name or language extension cannot waive that boundary.

The old annotations included 117 expected-protection and eight conservative
observations whose rejection depended only on formatting. Their migration is
explicit: independently checked inert presentation replaces blanket rejection.
No credential/contact-material exception follows from that change. Every new
admission crosses the production projection and inverse phone, email, credential,
configured-secret and forbidden-origin checks. Exact identities, source facts and
verdicts stay in authenticated private audit state, never runtime allowlists.
Authorized private replay results remain private.

## 0.14.5: complete source and calendar interpretation

The release corrects complete calendar-clock interpretation and unavailable
literal-source proof for short fields in large files. It does not turn a
successful parser result, a filename, or a lower rejection count into permission
to publish. This matrix records the disposition of all fourteen historical
conservative categories; individual correspondence and current replay judgments
stay in private audit state.

| Category | Synthetic example or boundary | Disposition and required proof |
| --- | --- | --- |
| Missing literal proof | `List<Entry> value;` in a large immutable text file | Corrected: validate the entire Git blob and capture the exact bounded excerpt. No fragment syntax authority. |
| Unproved credential value reference | `id-token: write` | Conservative: a permission-map key is not an absent credential. Field names do not confer authority. |
| Literal or computed credential material | `api_token = lookup("CONFIG_TOKEN")` | Conservative: calls and literals do not establish the value's absence. No execution, alias tracing or inferred environment lookup. |
| Raw profile reference without syntax authority | `def probe(token: str):` as arbitrary text | Conservative in prose; a qualified immutable source role can refine the separate code field. Parsing the standalone string cannot grant that role. |
| Numeric candidate without a complete technical role | `component minimum 2026.10.19` | Complete calendar clocks are corrected. Other numbers still require a bounded technical grammar; a dependency-looking name is insufficient. |
| Additional unproved numeric composition | `to0.12.0/1.13.2` | Conservative: glued or partial tokens cannot borrow a neighboring version's interpretation. |
| Secondary unproved identifier role | `TKT-008/009/010/015/016/017` | Conservative: no ticket-prefix allowlist or arbitrary identifier waiver. |
| Numeric operators without authorized syntax | A quoted expression assembling a version comparison | Conservative: source text describing a computation is not its evaluated result. Unknown syntax and embedded strings keep ordinary checks. |
| Unproved or invalid network token | `network 192.0.2.1/255.0.255.0` | Conservative: invalid masks/addresses do not qualify the complete-network exception. No extension or repository exemption. |
| Aggregate source or role ambiguity | Whole-file probe containing multiple roles | Conservative: absence in one line or sink cannot establish absence across the aggregate. Preserve the whole-file and line observations separately. |
| Aggregate requiring complete material replay | A document containing technical values and independent contacts | Replay the complete original and derived representations. A safe technical token cannot erase adjacent material. |
| Whole-unit literals close reference refinement | An entire source excerpt containing a reference and a nonempty literal | Conservative: the bounded syntax rule cannot establish absence for that mixed unit. Narrow line proofs do not authorize the aggregate. |
| Whole unit outside the code-proof budget | A file larger than the publishable code-field bound | Conservative: an audit whole-file unit is not an enlarged publication field. Identity proof does not enlarge fragment limits. |
| Historical oracle correction | `limit = 8 * 1024 * 1024` supplied without a source role | Retain the corrected conservative oracle. Numeric syntax alone does not prove arithmetic intent; the exact qualified source-code path remains separate. |

Calendar qualification checks every numeric candidate against its complete
calendar token, including clock, fractional seconds, timezone and boundaries.
Explicit contact context still wins. Independent inverse controls append phone,
email and credential material; source identity never bypasses those checks.

The historical pre-0.14.5 audit HMAC key is unavailable. Those records remain
unverified locator hints. Fresh authenticated baseline/candidate runs use the
same selected inputs and environment. Where a historical locator corresponds to
that immutable input, retain both identities with that limited correspondence;
it does not authenticate the old record. Unrecoverable locators remain explicitly
unknown. No old classification becomes a current exemption.

Current admission changes have independently reviewed calendar or exact-source
bases. Retained rejection changes are distinguished as newly verified source
facts, independently retained control/material checks, or a different primary
reason after the calendar correction. An unchanged rejection is not evidence
that its material is sensitive; unresolved roles remain conservative.

The executable evidence is in the datetime and source-context property families,
`test_source_reader.py`, `test_source_suggestions.py`, `test_audit_proof.py`,
`test_opaque_code_proof.py`, and `test_opaque_code_publication.py`. The optional
[parser qualification](../development.md#supplemental-parser-qualification)
retains concrete counterexamples to borrowing authority from Tree-sitter,
Pygments or PIISA's lexical stage. It adds no runtime dependency or model.
