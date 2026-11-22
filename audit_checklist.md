# Verification Receipt Audit Checklist

**8 mandatory checks** - Every receipt must pass all 8 to be valid.

---

## 1. Claim Frozen Before Any Read
- [ ] Claim text captured and stored before first network call
- [ ] No claim modification after read paths begin
- [ ] Frozen claim hash recorded in receipt metadata

## 2. Two Independent Read Paths Configured
- [ ] Exactly two read paths specified
- [ ] Paths use different infrastructure (e.g., HTTP + DNS, not HTTP + HTTP)
- [ ] Path types declared: http, dns, api, or ledger
- [ ] No shared dependencies between paths (different libraries, different DNS resolvers)

## 3. Both Paths Executed in Same Tick
- [ ] Path A and Path B timestamps within same verification tick
- [ ] No external state change between paths
- [ ] Tick boundary recorded in receipt

## 4. Raw Responses Stored with Hashes
- [ ] HTTP: response body SHA256 recorded
- [ ] DNS: sorted record set SHA256 recorded
- [ ] API: response body SHA256 recorded
- [ ] Ledger: response body SHA256 recorded
- [ ] Full responses NOT stored (privacy)
- [ ] Hash algorithm: SHA256, prefix "sha256:"

## 5. Verdict Derived from Path Agreement Only
- [ ] No external heuristics, ML, or human judgment in verdict
- [ ] "verified" = both paths succeeded AND agree on key fields
- [ ] "disputed" = both paths succeeded BUT disagree on key fields
- [ ] "unverifiable" = fewer than 2 paths succeeded
- [ ] Agreement logic documented and deterministic

## 6. Receipt ID Generated from Claim + Timestamp
- [ ] Format: `vr-YYYYMMDD-XXXXXX` (6 hex chars from UUID)
- [ ] Deterministic: same claim + same timestamp = same ID
- [ ] No external entropy in ID generation
- [ ] ID recorded in receipt and audit log

## 7. Receipt Written to Immutable Store
- [ ] Receipt JSON written to append-only store
- [ ] Store location recorded (file, database, ledger)
- [ ] Write confirmed before verification returns
- [ ] Tamper-evident: any modification changes receipt hash

## 8. Verifier Identity and Version Recorded
- [ ] `verifier` field: "tallybexro/v1.0" or current version
- [ ] Version matches code that produced receipt
- [ ] Verifier contact: tally@codealpha.io
- [ ] Public key or identity anchor for non-repudiation (future)

---

## Audit Procedure

For any receipt `vr-YYYYMMDD-XXXXXX.json`:

```bash
# 1. Verify receipt structure
python3 -m json.tool receipt.json > /dev/null && echo "Valid JSON"

# 2. Check all 8 checklist items
# (manual or automated)

# 3. Verify receipt hash matches stored hash
sha256sum receipt.json

# 4. Verify claim frozen timestamp <= first read path timestamp
# 5. Verify exactly 2 read paths
# 6. Verify verdict logic
# 7. Verify receipt ID format
# 8. Verify verifier field
```

## Failure Modes

| Check | Failure = | Action |
|-------|-----------|--------|
| 1 | Claim mutated | Receipt void, re-run |
| 2 | Paths not independent | Receipt void, redesign |
| 3 | Paths different ticks | Receipt void, re-run |
| 4 | Missing hashes | Receipt void, re-run |
| 5 | Verdict not from agreement | Receipt void, fix logic |
| 6 | ID non-deterministic | Receipt void, fix ID gen |
| 7 | Not immutable | Receipt suspect, migrate |
| 8 | Verifier missing | Receipt invalid |

---

*Audit checklist v1.0 - part of Verification Receipt Skill*
*Verifier: tallybexro/v1.0*
*Contact: tally@codealpha.io*