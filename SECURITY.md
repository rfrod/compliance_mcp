# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 1.0.x | ✅ Active support |
| 0.3.x | ⚠️ Security fixes only |
| < 0.3 | ❌ No longer supported |

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email: `security@your-org.com`

Include in your report:
- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact assessment
- Your suggested fix (optional but appreciated)

### What to Expect

| Timeline | Action |
|---|---|
| 24 hours | Acknowledgement of your report |
| 72 hours | Initial severity assessment |
| 7 days | Fix underway or workaround issued |
| 30 days | Full patch released (critical issues sooner) |
| 90 days | Public disclosure (coordinated with reporter) |

We follow responsible disclosure. We will credit you in the release notes
unless you prefer to remain anonymous.

---

## Security Architecture

### API Key Handling
- `ANTHROPIC_API_KEY` and all third-party keys are loaded exclusively from
  environment variables or a secrets manager
- Keys are never logged, committed, or included in error responses
- Rotate keys immediately if exposure is suspected

### Audit Log Integrity
- The audit log table is append-only:
  `REVOKE UPDATE, DELETE ON mcp_audit_log FROM compliance_user;`
- Every tool call that writes data (`flag_transaction`) creates an immutable
  audit entry with timestamp, user_id, tool_name, arguments, and result
- Audit log retention must be ≥ 5 years (FINTRAC PCMLTFA s.6)

### Tool Authorization
- All MCP tool calls pass through `auth.py` OAuth 2.0 scope enforcement
- Write tools (`flag_transaction`) require `compliance:write` scope
- PEP data tools require `compliance:pep:read` scope (privacy-sensitive)
- Unauthenticated calls are rejected with HTTP 401

### Data in Transit
- TLS required on all MCP server endpoints in production
- PostgreSQL connections require SSL (`sslmode=require`)

### Dependency Security
- Dependencies are pinned in `requirements.txt`
- `pip-audit` runs on every CI build
- Dependabot configured for automated security PRs

---

## Known Limitations

- Mock mode (`SCREENING_API_KEY` not set) uses fixture data — not suitable
  for production screening decisions
- OFAC fuzzy matching at threshold 85 may produce false negatives for heavily
  transliterated names — supplement with exact-match on known aliases
- The agent does not currently support human-in-the-loop interruption mid-loop —
  all tool calls execute autonomously once the query is submitted
