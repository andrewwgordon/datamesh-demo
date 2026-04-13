## PR Checklist (AGENTS.md compliant)

### Scope
- [ ] Implements exactly **one** AGENTS.md ticket
- [ ] Ticket ID referenced in PR title

### Contracts
- [ ] JSON Schema updated first (if applicable)
- [ ] AsyncAPI updated (if topics affected)
- [ ] OpenAPI updated (if APIs affected)

### Tests
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] E2E tests added/updated (if flow-level change)

### Verification
- [ ] `make validate`
- [ ] `make test`
- [ ] `make e2e` (if applicable)

### Architecture
- [ ] No scope creep
- [ ] Pure transforms (CDC → canonical)
- [ ] Idempotent bootstrap preserved

### References
- AGENTS.md Ticket:
- Epic:
- Issue:
