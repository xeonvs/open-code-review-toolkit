# Synthetic bounded-context recipes

These files contain no live hostname or credential. Copy `review-context-policy.json` to `.opencodereview/review-context-policy.json` on the protected target branch, then adapt exactly one operator-side adapter JSON file and supply it through `OCR_REVIEW_CONTEXT_ADAPTERS_JSON`.

- `adapters-stdio.json` shows an operator-managed local proxy. Replace the synthetic absolute command and provide `SYNTHETIC_ADAPTER_TOKEN` in the runner environment.
- `adapters-remote.json` shows an HTTPS proxy. Replace the `.invalid` endpoint and provide `SYNTHETIC_ADAPTER_AUTHORIZATION` in the runner environment.

The protected policy can narrow these allowlists but cannot add a command, endpoint, tenant, resource class, or credential. Both proxies must implement `ocr.context-adapter-request/v1` and `ocr.context-adapter-response/v1`, including object-level authorization in the atomic `authorize_and_resolve` operation. See [Bounded review context](../../docs/review-context.md) for the exact contract and deployment boundary.
