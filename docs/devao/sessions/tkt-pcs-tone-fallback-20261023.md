<!-- File: docs/devao/sessions/tkt-pcs-tone-fallback-20261023.md -->
<!-- Purpose: Tracked council brief for session tkt-pcs-tone-fallback-20261023. -->
<!-- Related: .devao/chalkboard (gitignored), SessionBoard -->
<!-- Tags: #devao #session #brief -->

# Session `tkt-pcs-tone-fallback-20261023`

- **Target:** `beep-boop`
- **Goal:** Ship tkt:pcs-tone-fallback: local Tone.CONVERSATIONAL when PCS has no known tone. work_id=tkt:pcs-tone-fallback. milestone_id is unset in the spine catalog.
- **Current owner:** verifier
- **Pack:** `None`
- **work_id refs:** tkt:pcs-tone-fallback

## Acceptance

- professional from variables_resolved is Tone.PROFESSIONAL; matter-of-fact is Tone.MATTER_OF_FACT; TimeoutError and HTTP 503 fall back to conversational and the reason does not contain the API key.

## Decisions

- goal=PCS tone fallback; decisions=variables_resolved then metadata then context_used then top-level tone; unknown or transport failure returns Tone.CONVERSATIONAL; artifacts=modules/core/pcs_tone.py, tests/test_pcs_tone.py; open_risks=no call site in the synthesizer yet; next_owner=backend_engineer; model_class=build

## Next

- goal=verify before PR; decisions=tests match expected_io; artifacts=docs/devao/sessions/tkt-pcs-tone-fallback-20261023.md; open_risks=no spine catalog item and no GitHub issue; next_owner=verifier; model_class=fast

## Blockers

- None.
