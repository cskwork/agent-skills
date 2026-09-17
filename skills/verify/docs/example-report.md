# Example report

A real gate-5 output, with the domain generalized. This is what `verify` hands back.

Note what it does *not* do: it does not list files changed, it does not paste response bodies, and it does not say "looks good". It leads with a verdict, then evidence, then the gap.

---

# verify — exclude secondary rows from the group status view

**Verdict: PASS WITH GAPS** — the fix works. Only 1 of the feature's 20 endpoints was checked.

## Context

The group status view listed one row per item per session type. Secondary sessions and primary sessions were both emitted, so a secondary date appeared on the primary detail screen.

The fix removes the cross join that produced both, and keeps primary sessions only.

I compared against the merge base with `origin/main`. The feature's files are not on `main` yet.

## Gates

| Gate | Verdict | Evidence |
|------|---------|----------|
| 1 Build | PASS | `receipts/01-build.log`, exit 0, 2s |
| 2 Static | PASS | `receipts/02-static.log`, 2 checks, 0 failed |
| 3 Clean code | PASS | 0 blocking, 1 note |
| 4 Scenario | PASS | `receipts/04-scenario/`, 6 variants, 6 passed |
| 5 Report | — | this file |

The process under test started at 08:56:34 from a jar built at HEAD. A different process was already listening on the default port, started three minutes *before* the commit, so I ran a second instance rather than trusting it.

## What I proved

1. The endpoint no longer returns secondary rows. The response has 6 rows and none of them is secondary. The database still holds 4 secondary rows for the same period, so the query filtered them — the result is not empty by accident.
2. The module that showed the bug is now correct. Module `2755427` returns `NOT_DEPLOYED` with a null session id and a null start date. Before the fix it carried a secondary session id and a secondary date.
3. Primary rows keep their own session id. Module `2755418` returns session `3053600`, which matches the primary row in the database.
4. Omitting the optional period parameter falls back to the earliest period. Both request shapes return the same period.
5. An account with no content returns 200 and an empty list. An empty list is a valid answer here.
6. A member-role token is refused on this endpoint. The role guard is new in this change.
7. An invalid id is refused with the platform's parameter-error code.

## What I did not verify

1. The feature's other 19 endpoints. This run covered the one endpoint the last commit touched.
2. Row count against the pre-change query. I confirmed 6 versus 10 directly in the database, but did not reproduce the old response from deployed code. I asserted per-record provenance instead.
3. A non-zero completion count. See finding 2 — no dev data can produce one.
4. Any path scoped by a claim the offline-minted token does not carry.

## Findings

| Severity | Location | Finding |
|----------|----------|---------|
| note (pre-existing) | `ErrorCode.java` | Parameter and validation errors are declared as one status in the enum and returned as 500 on the wire. An untouched older endpoint behaves the same, so this is platform-wide, not a regression. The caller cannot tell "you sent something wrong" from "we are broken". |
| note (pre-existing) | the changed query | The completion count is structurally always 0. Progress attaches to child session rows, never the container row the join uses. No dev row can produce a non-zero value. |
| note (pre-existing) | the changed query | The question count is always null on these rows for the same reason: the page count lives on the child. |
| note | the changed query | The `'PRIMARY'` literal now appears in four places in one statement. Worth extracting to a fragment next time this file is touched. |
| checked, no issue | the changed query | Removing the secondary branch from `ORDER BY` is correct. The only other producers of that column are two evaluation categories, so no row falls through to the default. |

## Next

Decide whether to run the same suite over the other 19 endpoints. The scenarios and the token are reusable; sourcing a real id per endpoint is what costs the time.
