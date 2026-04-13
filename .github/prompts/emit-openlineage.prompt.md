---
version: 1
---
# Emit OpenLineage to Marquez

## Purpose
Add OpenLineage emission for the Normalizer job so lineage appears in Marquez.

## Inputs
- Job name (default: `eam-cdc-to-canonical`)
- Input datasets (CDC topics)
- Output datasets (business topics)
- Marquez/OpenLineage endpoint URL

## Guardrails
- Emit START and COMPLETE events.
- Include dataset identifiers consistently (`kafka://<topic>`).
- Do not emit extremely high-frequency events; batch by interval or count.

## Steps
1) Add `services/normalizer/app/lineage.py` with emitter functions.
2) Integrate emission into normalizer lifecycle:
   - START at run begin / interval
   - COMPLETE after processing window
3) Add configuration via env vars.
4) Add unit tests that validate payload structure.
5) Add integration note: how to confirm in Marquez UI.

## Output
- Lineage emitter implementation
- Tests
- Verification steps
